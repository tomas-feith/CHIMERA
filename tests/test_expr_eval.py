"""Tests for the AST-allow-list evaluator used to run fit expressions safely."""

import numpy as np
import pytest

from expr_eval import UnsafeExpressionError, safe_eval


def test_evaluates_arithmetic():
    assert safe_eval("B[0]*_x+B[1]", {"np": np, "B": [2.0, 3.0], "_x": 4.0}) == 11.0


def test_evaluates_numpy_call():
    result = safe_eval("np.sin(_x)*B[0]", {"np": np, "B": [2.0], "_x": 0.0})
    assert result == 0.0


def test_evaluates_power_and_constants():
    assert safe_eval("_x**2 + 1", {"np": np, "_x": 3.0}) == 10.0


def test_indexed_independent_variable():
    ns = {"np": np, "B": [2.0], "_x": [10.0, 20.0], "i": 1}
    assert safe_eval("B[0]*_x[i]", ns) == 40.0


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os')",
        "(1).__class__",
        "np.__loader__",
        "os.system('x')",
        "[y for y in range(3)]",
        "(lambda: 1)()",
        "'string'",
        "_x if _x else 0",
    ],
)
def test_rejects_unsafe_expressions(expr):
    with pytest.raises((UnsafeExpressionError, SyntaxError)):
        safe_eval(expr, {"np": np, "_x": 1.0})


def test_no_builtins_available():
    # Even a bare builtin name must not resolve.
    with pytest.raises(Exception):
        safe_eval("abs(_x)", {"np": np, "_x": -1.0})


# --- the invariants the sandbox actually rests on -------------------------
# These are the two properties that keep the np.<name> surface inert. Losing
# either one silently re-opens the sandbox, so pin them explicitly.


@pytest.mark.parametrize(
    "expr",
    [
        "np.load('/etc/passwd')",  # needs a path -> needs a string
        "np.fromfile('x')",
        "np.frombuffer('abc')",
        "np.dtype('O')",
    ],
)
def test_string_constants_are_rejected_so_file_apis_are_unreachable(expr):
    """Every dangerous np entry point needs a string argument; deny strings."""
    with pytest.raises(UnsafeExpressionError, match="numeric constants"):
        safe_eval(expr, {"np": np, "_x": 1.0})


@pytest.mark.parametrize(
    "expr",
    [
        "np.linalg.norm(_x)",
        "np.core.multiarray(_x)",
        "np.random.mtrand._rand",
    ],
)
def test_attribute_chains_are_rejected(expr):
    """Only a single np.<name> hop; walking deeper into the module is denied."""
    with pytest.raises(UnsafeExpressionError):
        safe_eval(expr, {"np": np, "_x": 1.0})


@pytest.mark.parametrize(
    "expr",
    [
        "np.sum(_x, axis=0)",  # ast.keyword
        "np.sum(*_x)",  # ast.Starred
        "_x[0:2]",  # ast.Slice
        "(_x, 1)",  # ast.Tuple
        "_x > 1",  # ast.Compare
        "_x and 1",  # ast.BoolOp
        "_x @ _x",  # ast.MatMult
    ],
)
def test_unlisted_node_types_are_rejected(expr):
    with pytest.raises(UnsafeExpressionError, match="disallowed syntax"):
        safe_eval(expr, {"np": np, "_x": np.array([1.0, 2.0])})


def test_underscore_attributes_are_rejected_not_only_dunders():
    with pytest.raises(UnsafeExpressionError, match="underscore-prefixed"):
        safe_eval("np._core", {"np": np})


def test_compilation_is_cached():
    """The ODR loop evaluates the same expression thousands of times."""
    from expr_eval import _compile

    _compile.cache_clear()
    expr = "B[0]*_x+B[1]"
    safe_eval(expr, {"np": np, "B": [1.0, 2.0], "_x": 1.0})
    safe_eval(expr, {"np": np, "B": [3.0, 4.0], "_x": 2.0})
    assert _compile.cache_info().hits >= 1
