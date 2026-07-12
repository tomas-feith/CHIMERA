"""Tests for ``main.process_params``, which validates the parameter and
independent-variable names entered by the user before a fit expression is built.
"""

import pytest

from main import process_params


def test_comma_separated_params():
    ok, result = process_params("A,B", "x")
    assert ok is True
    assert result == ["A", "B"]


def test_space_separated_params():
    ok, result = process_params("A B", "x")
    assert ok is True
    assert result == ["A", "B"]


def test_mixed_separators_and_blanks():
    ok, result = process_params("A, B ,C", "x")
    assert ok is True
    assert result == ["A", "B", "C"]


def test_no_parameters():
    ok, msg = process_params("", "x")
    assert ok is False
    assert msg == "No parameters were found."


def test_no_independent_variable():
    ok, msg = process_params("A", "")
    assert ok is False
    assert msg == "No independent variable was found."


def test_multiple_independent_variables():
    ok, msg = process_params("A", "x y")
    assert ok is False
    assert "Multiple independent variables" in msg


def test_forbidden_character_in_param():
    ok, msg = process_params("A!", "x")
    assert ok is False
    assert "contains the character '!'" in msg


def test_param_named_like_function_is_rejected():
    ok, msg = process_params("sin", "x")
    assert ok is False
    assert "already binded to a function" in msg


def test_reserved_keyword_is_rejected():
    ok, msg = process_params("PI", "x")
    assert ok is False
    assert "reserved keyword" in msg


def test_numeric_param_is_rejected():
    ok, msg = process_params("3", "x")
    assert ok is False
    assert "is a number" in msg


def test_duplicate_param_is_rejected():
    ok, msg = process_params("A A", "x")
    assert ok is False
    assert "more than once" in msg


def test_param_clashing_with_independent_variable():
    ok, msg = process_params("x", "x")
    assert ok is False
    assert "given to the independent variable and to a parameter" in msg


@pytest.mark.parametrize("bad_indep", ["x!", "sin"])
def test_invalid_independent_variable(bad_indep):
    ok, _ = process_params("A", bad_indep)
    assert ok is False
