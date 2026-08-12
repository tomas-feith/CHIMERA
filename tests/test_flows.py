"""Headless end-to-end tests that drive the real Tkinter ``MainWindow``.

Unlike the other test modules (which exercise pure logic), these construct the
actual application on a real (but off-screen) Tk root -- without entering
``mainloop`` -- and call the real widget methods, so they cover the extracted
mixins (``PlottingMixin``, ``OnlineUIMixin``) as wired into ``MainWindow``.

They require a working Tk display; on a headless machine with no ``$DISPLAY``
(e.g. bare CI) the whole module skips rather than failing. Run CI under a virtual
framebuffer (``xvfb-run``) to execute them there.

The ``app`` fixture lives in the root ``conftest.py`` and is session-scoped, so
a single Tk root is shared with every other GUI test module. That is not just
tidiness: creating a second ``Tk()`` in one process makes tkinter reuse image
names across interpreters and fail with "can't use pyimageN as iconphoto", and
because the fixture turns a TclError into a skip, a module with its own root
would quietly stop running rather than fail.
"""

import pytest

tk = pytest.importorskip("tkinter")

import pymongo  # noqa: E402

import online_ui  # noqa: E402


def test_compile_and_fit_recovers_linear_parameters(app):
    app.dialog_calls.clear()
    app.create_scatter()
    app.autoscale_x.set(1)
    app.autoscale_y.set(1)

    # y = 2x + 1, columns: x  y  ey
    data = "0 1 0.1\n1 3 0.1\n2 5 0.1\n3 7 0.1\n4 9 0.1"
    app.data_entry.delete("1.0", tk.END)
    app.data_entry.insert(tk.INSERT, data)
    app.dataset_text[0] = data

    app.function_entry.delete(0, tk.END)
    app.function_entry.insert(0, "a*x+b")
    app.parameter_entry.delete(0, tk.END)
    app.parameter_entry.insert(0, "a,b")
    app.independent_entry.delete(0, tk.END)
    app.independent_entry.insert(0, "x")

    app.update_parameter()  # builds param_boxes for a, b
    for i, guess in enumerate(("1", "0")):
        app.param_boxes[i].delete(0, tk.END)
        app.param_boxes[i].insert(0, guess)

    app.compile_function()
    # The fit expression is the safe re-derived form, not the raw input.
    assert app.clean_functions[0] == "B[0]*_x+B[1]"

    app.fit_activate()  # -> plot_dataset() -> fit_data() -> run_odr_fit()

    assert app.fit_params[0][0] == pytest.approx(2.0, abs=1e-3)
    assert app.fit_params[0][1] == pytest.approx(1.0, abs=1e-3)
    assert float(app.fit_r2[0]) == pytest.approx(1.0, abs=1e-6)
    assert hasattr(app, "canvas")  # the plot was actually rendered


def test_login_without_credentials_is_graceful(app, monkeypatch):
    monkeypatch.delenv("CHIMERA_USERNAME", raising=False)
    monkeypatch.delenv("CHIMERA_PASSWORD", raising=False)

    app.dialog_calls.clear()
    app.create_login()
    app.username_entry.insert(0, "someone")
    app.password_entry.insert(0, "pw")
    app.login()  # must not raise

    assert any("UNAVAILABLE" in title for title in app.dialog_calls)
    assert not hasattr(app, "database")


def test_login_with_unreachable_db_is_caught(app, monkeypatch):
    monkeypatch.setenv("CHIMERA_USERNAME", "u")
    monkeypatch.setenv("CHIMERA_PASSWORD", "p")

    def boom(*a, **k):
        raise pymongo.errors.ServerSelectionTimeoutError("simulated: DB unreachable")

    monkeypatch.setattr(online_ui.ChimeraDB, "connect", boom)

    app.dialog_calls.clear()
    app.create_login()
    app.username_entry.insert(0, "someone")
    app.password_entry.insert(0, "pw")
    app.login()  # the narrowed `except pymongo.errors.PyMongoError` must catch this

    assert any("CONNECTION ERROR" in title for title in app.dialog_calls)
    assert not hasattr(app, "database")
