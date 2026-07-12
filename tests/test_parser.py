"""Tests for ``main.parser``, which turns a user-entered fit expression into a
Python/NumPy expression string (with parameters mapped to ``B[i]`` and the
independent variable mapped to ``_x``) or returns a validation error.
"""

import pytest

from main import parser


def test_simple_linear_expression():
    ok, expr = parser("A*x", "A", "x")
    assert ok is True
    assert expr == "B[0]*_x"


def test_two_parameters_are_indexed_in_order():
    # Whitespace in the expression is stripped by the parser.
    ok, expr = parser("A*x + C", "A,C", "x")
    assert ok is True
    assert expr == "B[0]*_x+B[1]"


def test_parameter_named_like_coefficient_array_does_not_collide():
    # Regression: a parameter literally named 'B' used to collide with the
    # internal 'B[i]' substitution token and raise an uncaught TypeError.
    ok, expr = parser("A*x + B", "A,B", "x")
    assert ok is True
    assert expr == "B[0]*_x+B[1]"


def test_prefix_parameter_names_do_not_collide():
    # Regression: substituting 'a' before 'ab' used to corrupt 'ab'. Longest
    # names are now substituted first.
    ok, expr = parser("a*x + ab", "a,ab", "x")
    assert ok is True
    assert expr == "B[0]*_x+B[1]"


def test_numpy_function_is_namespaced():
    ok, expr = parser("sin(x)*A", "A", "x")
    assert ok is True
    assert expr == "np.sin(_x)*B[0]"


def test_empty_expression_is_rejected():
    ok, msg = parser("", "A", "x")
    assert ok is False
    assert msg == "No fitting function was found."


def test_expression_without_independent_variable_is_rejected():
    ok, msg = parser("A", "A", "x")
    assert ok is False
    assert "Independent variable is not present" in msg


def test_unknown_function_is_rejected():
    ok, msg = parser("foo(x)*A", "A", "x")
    assert ok is False
    assert "Function 'foo' not recognized." == msg


def test_invalid_parameters_propagate_error():
    # process_params rejects an empty parameter list; parser surfaces it.
    ok, msg = parser("sin(x)", "", "x")
    assert ok is False
    assert msg == "No parameters were found."


@pytest.mark.parametrize(
    "func,expected",
    [
        ("exp(x)*A", "np.exp(_x)*B[0]"),
        ("sqrt(x)*A", "np.sqrt(_x)*B[0]"),
        ("cos(x)*A", "np.cos(_x)*B[0]"),
    ],
)
def test_supported_functions_map_to_numpy(func, expected):
    ok, expr = parser(func, "A", "x")
    assert ok is True
    assert expr == expected
