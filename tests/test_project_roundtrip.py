"""Tests for the project load-time re-derivation of fit expressions.

When a project is loaded (from a ``.chi`` file or the database), the stored
pre-compiled ``clean_functions`` must NOT be trusted -- it is re-derived from the
raw fit functions via the validating parser. These tests lock in that behaviour,
which is what prevents a tampered project from smuggling in code to evaluate.
"""

import numpy as np

from chimera_core import parser, rederive_clean_functions
from expr_eval import UnsafeExpressionError, safe_eval


def test_rederives_valid_functions_like_parser():
    functions = ["A*sin(omega*x)", "m*x + b"]
    params = ["A,omega", "m,b"]
    indeps = ["x", "x"]

    clean = rederive_clean_functions(functions, params, indeps)

    assert clean == [
        parser("A*sin(omega*x)", "A,omega", "x")[1],
        parser("m*x + b", "m,b", "x")[1],
    ]
    # And each re-derived expression evaluates safely to a number.
    value = safe_eval(clean[1], {"np": np, "B": [2.0, 1.0], "_x": 3.0})
    assert value == 7.0


def test_invalid_function_becomes_empty_string():
    clean = rederive_clean_functions(["nope("], ["A"], ["x"])
    assert clean == [""]


def test_load_ignores_tampered_clean_functions():
    # Simulate a saved project whose stored `clean_functions` has been tampered
    # with to carry a payload, while the raw function is benign.
    stored_project = {
        "functions": ["A*x"],
        "params": ["A"],
        "indeps": ["x"],
        "clean_functions": ["__import__('os').system('echo pwned')"],
    }

    # The load path re-derives from the raw fields and ignores the stored value.
    rederived = rederive_clean_functions(
        stored_project["functions"],
        stored_project["params"],
        stored_project["indeps"],
    )

    assert rederived == ["B[0]*_x"]
    assert rederived != stored_project["clean_functions"]

    # For good measure: had the tampered expression reached the evaluator, it
    # would be rejected rather than executed.
    try:
        safe_eval(stored_project["clean_functions"][0], {"np": np})
    except (UnsafeExpressionError, SyntaxError):
        pass
    else:
        raise AssertionError("tampered expression should not evaluate")


def test_length_mismatch_is_tolerated():
    # zip stops at the shortest sequence; no crash on ragged inputs.
    clean = rederive_clean_functions(["A*x", "B*x"], ["A"], ["x"])
    assert clean == ["B[0]*_x"]
