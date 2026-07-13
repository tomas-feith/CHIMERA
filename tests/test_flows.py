"""Headless end-to-end tests that drive the real Tkinter ``MainWindow``.

Unlike the other test modules (which exercise pure logic), these construct the
actual application on a withdrawn Tk root -- without entering ``mainloop`` -- and
call the real widget methods, so they cover the extracted mixins
(``PlottingMixin``, ``OnlineUIMixin``) as wired into ``MainWindow``.

They require a working Tk display; on a headless machine with no ``$DISPLAY``
(e.g. bare CI) the whole module skips rather than failing. Run CI under a virtual
framebuffer (``xvfb-run``) to execute them there.
"""

import pytest

tk = pytest.importorskip("tkinter")

import pymongo  # noqa: E402

import main  # noqa: E402
import online_ui  # noqa: E402


@pytest.fixture
def app(monkeypatch):
    """A constructed, off-screen MainWindow with dialogs and networking stubbed."""
    import tkinter.messagebox as mb

    calls = []
    monkeypatch.setattr(
        mb, "showwarning", lambda *a, **k: calls.append(("warn", a[0] if a else ""))
    )
    monkeypatch.setattr(mb, "showinfo", lambda *a, **k: calls.append(("info", a[0] if a else "")))
    monkeypatch.setattr(mb, "showerror", lambda *a, **k: calls.append(("err", a[0] if a else "")))
    monkeypatch.setattr(mb, "askyesno", lambda *a, **k: True)
    # __init__ calls check_version(), which hits the network -- stub it out.
    monkeypatch.setattr(main, "check_version", lambda: None)

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display available (headless CI)
        pytest.skip(f"no Tk display available: {exc}")

    root.withdraw()
    instance = main.MainWindow(master=root)
    instance.dialog_calls = calls
    try:
        yield instance
    finally:
        root.destroy()


def _dialog_titles(app):
    return [c[1] for c in app.dialog_calls]


def test_compile_and_fit_recovers_linear_parameters(app):
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

    app.create_login()
    app.username_entry.insert(0, "someone")
    app.password_entry.insert(0, "pw")
    app.login()  # must not raise

    assert any("UNAVAILABLE" in title for title in _dialog_titles(app))
    assert not hasattr(app, "database")


def test_login_with_unreachable_db_is_caught(app, monkeypatch):
    monkeypatch.setenv("CHIMERA_USERNAME", "u")
    monkeypatch.setenv("CHIMERA_PASSWORD", "p")

    def boom(*a, **k):
        raise pymongo.errors.ServerSelectionTimeoutError("simulated: DB unreachable")

    monkeypatch.setattr(online_ui.ChimeraDB, "connect", boom)

    app.create_login()
    app.username_entry.insert(0, "someone")
    app.password_entry.insert(0, "pw")
    app.login()  # the narrowed `except pymongo.errors.PyMongoError` must catch this

    assert any("CONNECTION ERROR" in title for title in _dialog_titles(app))
    assert not hasattr(app, "database")
