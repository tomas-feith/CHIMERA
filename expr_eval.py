"""Safe evaluation of the fit-expression strings produced by ``parser``.

Those strings only ever contain numeric literals, the parameter array ``B``, the
independent variable ``_x`` (optionally indexed by ``i``), arithmetic operators
and calls to a fixed set of NumPy functions (``np.<name>``). Passing them to the
built-in :func:`eval` would execute arbitrary Python if a malicious project file
or database record smuggled one in (e.g. ``__import__('os').system(...)`` or the
classic ``().__class__.__bases__...`` sandbox escape).

Instead we statically validate the AST against an allow-list -- no attribute
access except ``np.<non-dunder>``, no dunder names, only numeric constants and a
handful of node types -- and only then compile and evaluate it in a namespace
with the builtins stripped out. Compilation is cached, so evaluating the same
expression repeatedly (as the ODR fit loop does) stays cheap.
"""

import ast
from functools import lru_cache

import numpy as np

# Node types permitted in a fit expression. Anything else (comprehensions,
# lambdas, string constants, boolean/compare ops, starred args, ...) is rejected.
_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Load,
    ast.Name,
    ast.Constant,
)


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains constructs outside the allow-list."""


def _validate(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpressionError("disallowed syntax: {}".format(type(node).__name__))
        if isinstance(node, ast.Attribute):
            # Only ``np.<name>`` attribute access is allowed, and never dunders.
            if node.attr.startswith("_"):
                raise UnsafeExpressionError("dunder attribute access is not allowed")
            if not (isinstance(node.value, ast.Name) and node.value.id == "np"):
                raise UnsafeExpressionError("only np.<name> attribute access is allowed")
        elif isinstance(node, ast.Name):
            if node.id.startswith("__"):
                raise UnsafeExpressionError("dunder names are not allowed")
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, complex)):
                raise UnsafeExpressionError("only numeric constants are allowed")


@lru_cache(maxsize=256)
def _compile(expr: str):
    """Validate ``expr`` and return a compiled code object (cached).

    Raises SyntaxError if it does not parse, or UnsafeExpressionError if it uses
    constructs outside the allow-list.
    """
    tree = ast.parse(expr, mode="eval")
    _validate(tree)
    return compile(tree, "<fit-expr>", "eval")


def safe_eval(expr: str, namespace: dict):
    """Evaluate a validated fit expression with no access to builtins.

    ``namespace`` supplies the symbols the expression may reference (typically
    ``np``, ``B``, ``_x`` and, for the plotting path, ``i``).
    """
    code = _compile(expr)
    # Stripping builtins is what makes the eval safe, but it also breaks NumPy's
    # floating-point warning path (it tries to reach __import__), so silence FP
    # warnings for the duration -- an invalid value simply yields nan/inf.
    with np.errstate(all="ignore"):
        return eval(code, {"__builtins__": {}}, namespace)
