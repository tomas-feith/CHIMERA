"""Safe evaluation of the fit-expression strings produced by ``parser``.

Those strings only ever contain numeric literals, the parameter array ``B``, the
independent variable ``_x`` (optionally indexed by ``i``), arithmetic operators
and calls to a fixed set of NumPy functions (``np.<name>``). Passing them to the
built-in :func:`eval` would execute arbitrary Python if a malicious project file
or database record smuggled one in (e.g. ``__import__('os').system(...)`` or the
classic ``().__class__.__bases__...`` sandbox escape).

Instead we statically validate the AST against an allow-list -- no attribute
access except ``np.<name>``, no dunder names, only numeric constants and a
handful of node types -- and only then compile and evaluate it in a namespace
with the builtins stripped out. Compilation is cached, so evaluating the same
expression repeatedly (as the ODR fit loop does) stays cheap.

Two properties do most of the work, and both are easy to lose by accident:

* **String constants are rejected.** Every dangerous NumPy entry point that is
  reachable as ``np.<name>`` needs a string to do anything (``np.load`` needs a
  path, and with ``allow_pickle`` that would be code execution). With no way to
  write one, the callable surface is inert.
* **Attribute chains are rejected**, because an ``Attribute`` node's value must
  be the ``Name`` ``np`` -- so ``np.linalg.norm`` does not parse as safe, and
  neither does anything reached by walking further into the module.

Known limitation: this bounds *what* an expression can reach, not *how long it
runs*. ``10**10**10`` is inside the allow-list and will exhaust memory. The fit
runs on the UI thread, so a hostile project file can hang the app -- an
availability problem, not an execution one.
"""

import ast
from functools import lru_cache
from types import CodeType
from typing import Any

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
            # Only ``np.<name>`` attribute access is allowed, and never any
            # underscore-prefixed name -- not just dunders, since NumPy's
            # single-underscore internals are an equally good starting point.
            if node.attr.startswith("_"):
                raise UnsafeExpressionError("underscore-prefixed attributes are not allowed")
            if not (isinstance(node.value, ast.Name) and node.value.id == "np"):
                raise UnsafeExpressionError("only np.<name> attribute access is allowed")
        elif isinstance(node, ast.Name):
            if node.id.startswith("__"):
                raise UnsafeExpressionError("dunder names are not allowed")
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, complex)):
                raise UnsafeExpressionError("only numeric constants are allowed")


@lru_cache(maxsize=256)
def _compile(expr: str) -> CodeType:
    """Validate ``expr`` and return a compiled code object (cached).

    Raises SyntaxError if it does not parse, or UnsafeExpressionError if it uses
    constructs outside the allow-list.
    """
    tree = ast.parse(expr, mode="eval")
    _validate(tree)
    return compile(tree, "<fit-expr>", "eval")


def safe_eval(expr: str, namespace: dict) -> Any:
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
