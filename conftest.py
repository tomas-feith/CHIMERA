# Ensures the repository root (where main.py lives) is importable from tests.
# Its mere presence puts the repo root on sys.path under pytest's default
# import mode, so `import main` works from the tests/ package.
