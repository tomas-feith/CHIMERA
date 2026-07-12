"""Tests for ``main.math_2_latex``, which renders a user fit expression as LaTeX
for display/export.
"""

from main import math_2_latex


def test_multiplication_becomes_juxtaposition():
    assert math_2_latex("A*x", "A", "x") == "Ax"


def test_greek_parameter_is_backslashed():
    assert math_2_latex("alpha*x", "alpha", "x") == r"\alphax"


def test_trailing_digits_become_subscript():
    assert math_2_latex("A1*x", "A1", "x") == "A_{1}x"


def test_division_becomes_frac():
    assert math_2_latex("A/x", "A", "x") == r"\frac{A}{x}"


def test_unknown_function_wrapped_in_text():
    assert math_2_latex("sin(x)*A", "A", "x") == r"\text{sin}\left(x\right)A"


def test_power_is_rendered_with_braced_exponent():
    # Regression: previously produced the malformed 'Ax^}{2'.
    assert math_2_latex("A*x**2", "A", "x") == "Ax^{2}"


def test_parenthesised_exponent_is_braced():
    assert math_2_latex("A*x**(2+1)", "A", "x") == "Ax^{2+1}"
