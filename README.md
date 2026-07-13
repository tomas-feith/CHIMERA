# CHIMERA

CHIMERA is a desktop application for **curve fitting and publication-quality
plotting** of experimental data. It fits arbitrary user-defined functions to
(x, y) data with uncertainties using orthogonal distance regression, and can
export figures and LaTeX tables. An optional "CHIMERA Online" mode stores
projects in a shared database and lets connected users collaborate.

For the full user documentation see the project home page:
<https://sites.google.com/view/chimera-fit>.

## Project layout

| Path | Purpose |
| --- | --- |
| `main.py` | The core Tkinter application (windows, widgets, fitting/plotting flow). |
| `online_ui.py` | `OnlineUIMixin`: the CHIMERA Online windows (login, account, projects, connections, groups). |
| `project_io.py` | `ProjectIOMixin`: save/open `.chi` projects and LaTeX export. |
| `plotting.py` | `PlottingMixin`: data-entry parsing, function compile, plotting and ODR fitting. |
| `chimera_core.py` | Pure, GUI-independent helpers: expression parsing/validation, LaTeX generation, data-file reading. |
| `expr_eval.py` | AST-allow-list evaluator used to run fit expressions safely (no `eval` of untrusted input). |
| `fitting.py` | Orthogonal-distance-regression curve fitting, decoupled from the UI. |
| `db.py` | `ChimeraDB`: the MongoDB data-access layer for CHIMERA Online. |
| `tests/` | Pytest suite covering the pure logic in `chimera_core` and `expr_eval`. |

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency and
environment management.

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Run the application
uv run python main.py
```

### Quality checks

The same checks run in CI (`.github/workflows/ci.yml`):

```bash
uv run ruff check .        # lint
uv run ruff format --check --exclude main.py --exclude chimera_core.py .
uv run mypy .              # type check
uv run pytest              # tests
```

To run the linters/formatters automatically on every commit, enable the
pre-commit hooks once:

```bash
uv run pre-commit install
```

## CHIMERA Online (optional)

The online features require a MongoDB connection. The client reads the database
credentials from the `CHIMERA_USERNAME` and `CHIMERA_PASSWORD` environment
variables; if they are not set, the application still runs and only the online
menu items are unavailable.

> **Note:** the current online design has the client connect to the database
> directly. This is a known architectural limitation (see the code review notes)
> and a server-side API is the intended long-term direction.

## Building a standalone executable

Executables are produced with [PyInstaller](https://pyinstaller.org/). See
`Executable_Checklist.txt` for the current step-by-step build commands on
Windows and Ubuntu.
