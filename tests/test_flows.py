"""Headless end-to-end tests that drive the real Tkinter ``MainWindow``.

Unlike the other test modules (which exercise pure logic), these construct the
actual application on a real (but off-screen) Tk root -- without entering
``mainloop`` -- and call the real widget methods, so they cover the extracted
mixins (``PlottingMixin``, ``OnlineUIMixin``) as wired into ``MainWindow``.

They require a working Tk display; on a headless machine with no ``$DISPLAY``
(e.g. bare CI) the whole module skips rather than failing. Run CI under a virtual
framebuffer (``xvfb-run``) to execute them there.

A single Tk root is shared across the module on purpose: creating multiple
``Tk()`` instances in one process makes tkinter reuse image names across
interpreters and fail with "can't use pyimageN as iconphoto". The window is left
mapped (not withdrawn) so its geometry is realised before ``__init__`` resizes
the logo images -- a withdrawn window reports a width of 1 under Xvfb.
"""

import tkinter.messagebox as mb

import pytest

tk = pytest.importorskip("tkinter")

import pymongo  # noqa: E402

import main  # noqa: E402
import online_ui  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """One constructed, off-screen MainWindow shared by the module's tests."""
    calls = []
    originals = {
        (main, "check_version"): main.check_version,
        (mb, "showwarning"): mb.showwarning,
        (mb, "showinfo"): mb.showinfo,
        (mb, "showerror"): mb.showerror,
        (mb, "askyesno"): mb.askyesno,
    }
    # __init__ calls check_version(), which hits the network -- stub it out.
    main.check_version = lambda: None
    mb.showwarning = lambda *a, **k: calls.append(a[0] if a else "")
    mb.showinfo = lambda *a, **k: calls.append(a[0] if a else "")
    mb.showerror = lambda *a, **k: calls.append(a[0] if a else "")
    mb.askyesno = lambda *a, **k: True

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display available (headless CI without Xvfb)
        for (obj, name), value in originals.items():
            setattr(obj, name, value)
        pytest.skip(f"no Tk display available: {exc}")

    root.geometry("1024x768")
    root.update_idletasks()
    instance = main.MainWindow(master=root)
    instance.dialog_calls = calls
    try:
        yield instance
    finally:
        root.destroy()
        for (obj, name), value in originals.items():
            setattr(obj, name, value)


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
