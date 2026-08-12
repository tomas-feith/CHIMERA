"""The ``.chi`` project format: what is stored, and how a loaded file is checked.

``project_io.ProjectIOMixin`` used to spell out every field twice -- once when
saving and once when loading -- as forty-odd hand-written lines in each
direction. Nothing tied the two halves together, so a mismatch between them was
invisible: ``func_fit_width`` was saved from ``self.func_fit_width`` but
restored from ``data["error_width"]``, silently replacing the fit-curve width
with the error-bar width on every open.

The field lists below are that contract, written once. Both directions iterate
them, so the two halves cannot drift apart again.

This module is deliberately free of Tkinter so the format can be exercised
without a display -- see ``tests/test_project_format.py``.
"""

from __future__ import annotations

from typing import Any

# Copied straight to and from attributes of the same name.
PLAIN_FIELDS: tuple[str, ...] = (
    "plot_text",
    "text_pos",
    "text_size",
    "width_ratio",
    "height_ratio",
    "x_ticks_ref",
    "y_ticks_ref",
    "data_list",
    "dataset_text",
    "indeps",
    "params",
    "functions",
    "data_labels",
    "plot_labels",
    "fit_labels",
    "init_values",
    "marker_color_var",
    "line_color_var",
    "error_color_var",
    "func_fit_color_var",
    "func_plot_color_var",
    "marker_option_translater",
    "line_option_translater",
    "func_fit_option_translater",
    "func_plot_option_translater",
)

# Text entries: read with .get(), restored with delete()/insert(). The widget
# attribute is the key plus "_entry".
ENTRY_FIELDS: tuple[str, ...] = (
    "x_axis_max",
    "x_axis_min",
    "x_axis_tick_space",
    "x_axis_title",
    "y_axis_max",
    "y_axis_min",
    "y_axis_tick_space",
    "y_axis_title",
)

# One Tk variable per dataset: read with .get(), restored with .set().
WIDTH_FIELDS: tuple[str, ...] = (
    "marker_size",
    "line_width",
    "error_width",
    "func_fit_width",
    "func_plot_width",
)

# Stored for backwards compatibility but never trusted on load: the compiled
# expression is re-derived from the raw function through the validating parser,
# so a tampered project cannot smuggle in something to evaluate.
REDERIVED_FIELDS: tuple[str, ...] = ("clean_functions",)

REQUIRED_FIELDS: frozenset[str] = frozenset(
    PLAIN_FIELDS + ENTRY_FIELDS + WIDTH_FIELDS + REDERIVED_FIELDS
)


class ProjectError(ValueError):
    """A project file is missing fields or is internally inconsistent."""


def entry_widget_name(field: str) -> str:
    """The MainWindow attribute holding the entry widget for ``field``."""
    return f"{field}_entry"


def validate(data: Any) -> None:
    """Raise :class:`ProjectError` unless ``data`` is a loadable project.

    Checks the shape only -- that every field is present and the per-dataset
    lists all agree with the number of datasets. Field *values* are still the
    caller's problem; the point is to fail with something specific before the
    loader is halfway through mutating the window.
    """
    if not isinstance(data, dict):
        raise ProjectError(f"expected a JSON object, got {type(data).__name__}")

    missing = sorted(REQUIRED_FIELDS - data.keys())
    if missing:
        raise ProjectError(f"missing field(s): {', '.join(missing)}")

    data_list = data["data_list"]
    if not isinstance(data_list, list):
        raise ProjectError(f"'data_list' should be a list, got {type(data_list).__name__}")
    n = len(data_list)

    for field in WIDTH_FIELDS:
        value = data[field]
        if not isinstance(value, list):
            raise ProjectError(f"'{field}' should be a list, got {type(value).__name__}")
        if len(value) != n:
            raise ProjectError(f"'{field}' has {len(value)} entries but there are {n} datasets")

    for field in ("dataset_text", "indeps", "params", "functions"):
        value = data[field]
        if not isinstance(value, list):
            raise ProjectError(f"'{field}' should be a list, got {type(value).__name__}")
        if len(value) != n:
            raise ProjectError(f"'{field}' has {len(value)} entries but there are {n} datasets")


def dataset_count(data: dict) -> int:
    """How many datasets a validated project holds."""
    return len(data["data_list"])
