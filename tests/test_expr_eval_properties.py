"""Property-based tests for the fit-expression sandbox.

`tests/test_expr_eval.py` pins the sandbox against hand-picked attacks. Those
only cover what someone thought to write down. Fit expressions arrive from
project files and database records, so the interesting question is what an
arbitrary string does -- and that is a question for a fuzzer.

The property under test is deliberately blunt: for ANY input string,
``safe_eval`` either raises, or returns a number. It must never import, never
touch the filesystem, and never reach a builtin. Those are asserted directly by
instrumenting the interpreter for the duration of the call, so a future widening
of the allow-list that happens to permit a side effect fails here rather than
in a user's project file.
"""

from __future__ import annotations

import builtins
import math
from typing import Any

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from expr_eval import UnsafeExpressionError, safe_eval

NAMESPACE: dict[str, Any] = {"np": np, "B": np.array([1.0, 2.0, 3.0]), "_x": 2.0, "i": 0}

# Fragments drawn from the shape of real fit expressions, plus the pieces an
# attacker would reach for. Composed freely so the fuzzer can build nonsense.
ATOMS = st.sampled_from(
    [
        "B[0]",
        "B[1]",
        "_x",
        "1",
        "2.5",
        "1e3",
        "0",
        "-1",
        "1j",
        "np.exp",
        "np.sin",
        "np.sqrt",
        "np.abs",
        "np.log",
        "__import__",
        "__class__",
        "__subclasses__",
        "open",
        "eval",
        "exec",
        "os",
        "sys",
        "np.load",
        "np.__loader__",
        "np._core",
        "'x'",
        '"y"',
        "[]",
        "()",
        "{}",
        "lambda",
        "for",
        "if",
        "else",
        "np.linalg.norm",
        "globals",
        "locals",
        "getattr",
    ]
)
OPERATORS = st.sampled_from(
    ["+", "-", "*", "/", "**", "%", "//", "(", ")", ".", ",", "[", "]", " "]
)
EXPRESSIONS = st.lists(st.one_of(ATOMS, OPERATORS), min_size=1, max_size=12).map("".join)


class Tripwire:
    """Records every ``__import__`` and ``open`` while it is installed."""

    def __init__(self) -> None:
        self.triggered: list[str] = []

    def __enter__(self) -> Tripwire:
        self._import = builtins.__import__
        self._open = builtins.open

        def trapped_import(name: str, *a: Any, **k: Any) -> Any:
            self.triggered.append(f"__import__({name!r})")
            return self._import(name, *a, **k)

        def trapped_open(*a: Any, **k: Any) -> Any:
            self.triggered.append(f"open({a[0]!r})" if a else "open()")
            return self._open(*a, **k)

        builtins.__import__ = trapped_import
        builtins.open = trapped_open
        return self

    def __exit__(self, *exc: object) -> None:
        builtins.__import__ = self._import
        builtins.open = self._open


# Importing *anything* is not by itself an escape: CPython and NumPy lazily
# import their own machinery while parsing and evaluating. `0` pulls in
# `collections`; a string containing a non-ASCII letter makes the tokenizer load
# `unicodedata` to normalise identifiers. Neither hands the expression any
# capability.
#
# These do. This is the line the sandbox exists to hold: reaching any of them
# turns a fit expression into arbitrary code execution. Matched on the root
# package, so `os.path` and `urllib.request` are covered too.
CAPABILITY_MODULES = frozenset(
    {
        "builtins",
        "ctypes",
        "gc",
        "http",
        "importlib",
        "inspect",
        "marshal",
        "multiprocessing",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "runpy",
        "shutil",
        "signal",
        "socket",
        "subprocess",
        "sys",
        "tempfile",
        "threading",
        "urllib",
        "webbrowser",
    }
)


def side_effects_of(expr: str, namespace: dict[str, Any]) -> list[str]:
    """Capability-granting side effects caused by evaluating ``expr``.

    Any ``builtins.open`` counts -- the import machinery uses ``io.open_code``
    rather than ``builtins.open``, so a hit here is the expression touching the
    filesystem. Imports count only for CAPABILITY_MODULES, for the reason above.
    """
    with Tripwire() as wire:
        try:
            safe_eval(expr, dict(namespace))
        except Exception:  # noqa: BLE001 -- rejection is fine; side effects are not
            pass

    dangerous = []
    for effect in wire.triggered:
        if effect.startswith("open("):
            dangerous.append(effect)
            continue
        name = effect[len("__import__('") : -2]
        if name.split(".")[0] in CAPABILITY_MODULES:
            dangerous.append(effect)
    return dangerous


@settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(EXPRESSIONS)
def test_arbitrary_input_either_raises_or_returns_a_number(expr: str) -> None:
    try:
        result = safe_eval(expr, dict(NAMESPACE))
    except (
        UnsafeExpressionError,
        SyntaxError,
        ValueError,
        TypeError,
        NameError,
        IndexError,
        KeyError,
        AttributeError,
        ZeroDivisionError,
        MemoryError,
        OverflowError,
        RecursionError,
    ):
        pass  # rejected, or failed on the maths -- both acceptable
    else:
        # Numeric, or one of the NumPy callables the allow-list deliberately
        # exposes. A bare `np.exp` (referenced, not called) evaluates to the
        # ufunc itself -- nonsense as a fit expression, but not an escape: with
        # string constants rejected there is no argument you could hand it that
        # does anything. It fails later, in the fit, rather than here.
        if callable(result):
            assert getattr(result, "__module__", "").startswith("numpy"), (
                f"{expr!r} produced a callable from outside numpy: {result!r}"
            )
        else:
            arr = np.asarray(result)
            assert arr.dtype.kind in "fciub", f"{expr!r} produced {type(result).__name__}"

    assert not side_effects_of(expr, NAMESPACE), f"{expr!r} caused side effects"


@settings(max_examples=200, deadline=None)
@given(st.text(max_size=40))
def test_free_text_never_escapes_the_sandbox(text: str) -> None:
    """Completely unstructured input, not just plausible-looking fragments."""
    effects = side_effects_of(text, NAMESPACE)
    assert not effects, f"{text!r} caused side effects: {effects}"


@settings(max_examples=200, deadline=None)
@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz_.", min_size=1, max_size=20))
def test_bare_identifiers_never_resolve_to_a_builtin(name: str) -> None:
    """The namespace is the whole vocabulary: nothing else may be reachable.

    `eval` with stripped builtins should make every unknown name a NameError,
    so a name that resolves to something is either ours or a hole.
    """
    try:
        safe_eval(name, dict(NAMESPACE))
    except Exception:  # noqa: BLE001
        return
    # It evaluated -- that is only legitimate for names we actually supplied.
    assert name.split(".")[0] in NAMESPACE, f"{name!r} resolved without being in the namespace"


# --- properties of the arithmetic the sandbox is meant to allow -------------


@settings(max_examples=300, deadline=None)
@given(
    st.floats(min_value=-50, max_value=50, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-50, max_value=50, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-20, max_value=20, allow_nan=False, allow_infinity=False),
)
def test_linear_expression_matches_python(a: float, b: float, x: float) -> None:
    """A valid expression must compute what it says, not merely be permitted."""
    got = safe_eval("B[0]*_x+B[1]", {"np": np, "B": np.array([a, b]), "_x": x})
    assert got == pytest.approx(a * x + b, rel=1e-12, abs=1e-12)


@settings(max_examples=200, deadline=None)
@given(st.floats(min_value=-5, max_value=5, allow_nan=False, allow_infinity=False))
def test_numpy_calls_agree_with_the_stdlib(x: float) -> None:
    got = safe_eval("np.exp(_x)", {"np": np, "_x": x})
    assert got == pytest.approx(math.exp(x), rel=1e-12)


def test_the_tripwire_itself_detects_a_side_effect() -> None:
    """Guard the guard: a detector that cannot fire is worse than no detector."""
    with Tripwire() as wire:
        __import__("json")
    assert wire.triggered == ["__import__('json')"]


def test_a_filesystem_touch_is_reported() -> None:
    """side_effects_of must actually catch a real escape, not just stay quiet.

    Drive it through a namespace object that opens a file when multiplied -- if
    the detector were broken this would come back clean.
    """

    class Sneaky:
        def __rmul__(self, other: object) -> float:
            with open(__file__, "rb"):
                pass
            return 1.0

    effects = side_effects_of("_x * B", {"np": np, "_x": 2.0, "B": Sneaky()})
    assert any(e.startswith("open(") for e in effects), effects


def test_a_capability_import_is_reported() -> None:
    """And catches an import of something that grants capability."""

    class Sneaky:
        def __rmul__(self, other: object) -> float:
            __import__("os")
            return 1.0

    effects = side_effects_of("_x * B", {"np": np, "_x": 2.0, "B": Sneaky()})
    assert "__import__('os')" in effects, effects


def test_harmless_interpreter_imports_are_not_reported() -> None:
    """...while ignoring the machinery CPython loads on its own behalf."""

    class Noisy:
        def __rmul__(self, other: object) -> float:
            __import__("unicodedata")
            __import__("collections")
            return 1.0

    assert side_effects_of("_x * B", {"np": np, "_x": 2.0, "B": Noisy()}) == []
