# Ensures the repository root (where main.py lives) is importable from tests.
# Its mere presence puts the repo root on sys.path under pytest's default
# import mode, so `import main` works from the tests/ package.
"""Shared fixtures, including the single Tk root the GUI tests run against."""

from __future__ import annotations

import tkinter.messagebox as mb

import pytest


@pytest.fixture(scope="session")
def app():
    """One constructed, off-screen MainWindow shared by every GUI test module.

    Session-scoped and defined here rather than per-module on purpose. Creating
    a second ``Tk()`` in the same process makes tkinter reuse image names across
    interpreters and fail with "can't use pyimageN as iconphoto" -- so a second
    module with its own root does not merely duplicate work, it silently skips
    (the TclError is caught and turned into a skip, which looks like a pass).

    Requires a working display; on a headless machine with no ``$DISPLAY`` the
    dependent tests skip rather than fail. CI runs them under Xvfb on Linux and
    directly on the Windows runner.
    """
    tk = pytest.importorskip("tkinter")
    import main

    calls: list[str] = []
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

    # Left mapped (not withdrawn) so its geometry is realised before __init__
    # resizes the logo images -- a withdrawn window reports a width of 1 under
    # Xvfb.
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
