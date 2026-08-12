"""A real save -> reopen cycle through the live MainWindow.

`test_project_format.py` covers the format contract without Tk, and
`test_project_roundtrip.py` covers the clean_functions re-derivation. Neither
drives the actual mixin, which is where the fields are read off widgets and
written back to them -- and that is precisely where they had drifted:
``func_fit_width`` was saved from its own variable and restored from
``data["error_width"]``, so the fit-curve width was quietly replaced by the
error-bar width every time a project was opened.

This is the test that fails against that bug. It needs a Tk display for the
same reason `test_flows.py` does, and skips without one.
"""

from __future__ import annotations

import json

import pytest

tk = pytest.importorskip("tkinter")

# The `app` fixture is session-scoped in conftest.py, shared with test_flows.py:
# a second Tk() root in the same process fails with "can't use pyimageN as
# iconphoto", which this module's own fixture turned into a silent skip.

# One distinct value per width field, so a field restored from the wrong key
# lands on a number that is visibly not its own.
#
# Every one of these is bound to a tk.Scale with from_=1, to=5, resolution=0.5.
# Tk clamps a bound variable to its widget's range and snaps it to the
# resolution, so values outside [1, 5] or off the half-step grid come back
# changed and the test would fail for a reason that has nothing to do with the
# round trip.
WIDTHS = {
    "marker_size": 4.5,
    "line_width": 3.5,
    "error_width": 1.5,
    "func_fit_width": 5.0,
    "func_plot_width": 2.5,
}


def _prepare(app) -> None:
    """A one-dataset project with a distinct value in every width field."""
    app.dialog_calls.clear()
    app.create_scatter()
    data = "0 1 0.1\n1 3 0.1\n2 5 0.1"
    app.data_entry.delete("1.0", tk.END)
    app.data_entry.insert(tk.INSERT, data)
    app.dataset_text[0] = data

    app.x_axis_title_entry.delete(0, tk.END)
    app.x_axis_title_entry.insert(0, "time / s")
    app.y_axis_title_entry.delete(0, tk.END)
    app.y_axis_title_entry.insert(0, "voltage / V")

    for field, value in WIDTHS.items():
        getattr(app, field)[0].set(value)


def test_every_width_survives_a_save_and_reopen(app) -> None:
    """The regression: each width must come back as itself, not as a neighbour."""
    _prepare(app)
    saved = app._serialize_project()

    # Scramble the live values so a no-op load cannot pass by accident. 1.0 is
    # in range for every one of these scales, and differs from all five.
    for field in WIDTHS:
        getattr(app, field)[0].set(1.0)

    app.open_project(data=json.loads(json.dumps(saved)))

    for field, expected in WIDTHS.items():
        got = getattr(app, field)[0].get()
        assert got == pytest.approx(expected), f"{field} came back as {got}, expected {expected}"


def test_axis_titles_survive_a_save_and_reopen(app) -> None:
    _prepare(app)
    saved = app._serialize_project()

    app.x_axis_title_entry.delete(0, tk.END)
    app.x_axis_title_entry.insert(0, "scrambled")

    app.open_project(data=json.loads(json.dumps(saved)))
    assert app.x_axis_title_entry.get() == "time / s"
    assert app.y_axis_title_entry.get() == "voltage / V"


def test_a_saved_project_contains_every_required_field(app) -> None:
    from chimera_project import REQUIRED_FIELDS, validate

    _prepare(app)
    saved = app._serialize_project()

    assert REQUIRED_FIELDS <= saved.keys()
    validate(saved)  # what the loader will demand of it


def test_a_truncated_project_is_refused_with_a_dialog(app) -> None:
    """A malformed file reports 'File corrupted' rather than raising."""
    _prepare(app)
    saved = app._serialize_project()
    del saved["func_plot_width"]

    app.dialog_calls.clear()
    app.open_project(data=saved)

    assert any("ERROR" in call for call in app.dialog_calls)
