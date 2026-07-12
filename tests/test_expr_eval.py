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
