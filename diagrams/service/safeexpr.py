"""Safe parsing of model-supplied maths expressions.

`sympify()` and `parse_expr()` both `eval()` the string. Neither is safe on untrusted input,
and sympy says so:

    >>> sympify("__import__('os').getcwd()")
    '/Users/…/paperdeck-core'          # it RAN

The expressions here are written by an LLM, and the LLM's context includes user-supplied text
(topic strings, and the OCR'd contents of uploaded question papers in the import flow). That is
an injection path to arbitrary code execution on the server, so "the model is probably benign"
is not a defence we can rest on.

Restricting sympy's `global_dict` does not fix it — sympy needs its own namespace to evaluate at
all (`NameError: name 'Function' is not defined`). So the string is validated against Python's own
AST first, and only an expression built exclusively from numbers, the whitelisted symbols, the
whitelisted functions and arithmetic operators is handed on. Anything else — an attribute access,
a subscript, a lambda, a call to an unlisted name — is rejected before sympy sees it.
"""
from __future__ import annotations

import ast
from typing import Iterable

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, eval_expr, implicit_multiplication, standard_transformations,
    stringify_expr,
)

exec_ = exec  # named, so the one deliberate exec below is greppable and obvious

# `implicit_multiplication` lets "2x" mean 2*x. Deliberately NOT
# `implicit_multiplication_application`, which drags in `split_symbols`: that shreds any
# multi-letter name into a product of single letters, so "N0*exp(-k*t)" silently becomes
# N*0*… = 0 and the renderer draws a flat zero line instead of failing. A wrong graph that
# renders is worse than no graph.
_TRANSFORMS = standard_transformations + (implicit_multiplication, convert_xor)

_ALLOWED_FUNCS = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "exp", "log", "ln", "log10", "sqrt", "cbrt",
    "Abs", "abs", "sign", "floor", "ceiling", "factorial",
    "Min", "Max", "Piecewise", "erf",
})

_ALLOWED_CONSTS = frozenset({"pi", "E", "e", "oo", "I"})

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Call,
    ast.Compare, ast.Tuple, ast.Load, ast.keyword,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)

# sympy's transformations rewrite the source into constructor calls — "2x" becomes
# `Integer(2)*Symbol('x')` — so the generated code legitimately calls these.
_SYMPY_CTORS = frozenset({
    "Integer", "Float", "Rational", "Symbol", "Function", "Add", "Mul", "Pow", "Tuple",
})


def _log10(arg):
    return sp.log(arg, 10)


class UnsafeExpression(ValueError):
    """Raised for anything outside the arithmetic whitelist. The generator's repair loop feeds
    the message back to the model, so the message names the offending token."""


def _validate_code(code: str, allowed_symbols: Iterable[str]) -> None:
    """Validate the code sympy GENERATED, not the string the model wrote.

    Validating the raw string cannot work: Python's own parser rejects sympy-legal input like
    "2x" (invalid decimal literal). So we let sympy do its purely textual transform first —
    `stringify_expr` tokenises and rewrites, and crucially does NOT eval — and gate the result.
    A payload like `__import__('os').getcwd()` survives that transform as a call to a name that
    is not in the whitelist, and is rejected here, before anything is evaluated.
    """
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"not a valid expression: {exc.msg}") from exc

    callable_names = _SYMPY_CTORS | _ALLOWED_FUNCS
    names = set(allowed_symbols) | _ALLOWED_CONSTS | callable_names

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise UnsafeExpression(
                f"'{type(node).__name__}' is not allowed in a maths expression"
            )
        if isinstance(node, ast.Call):
            # Only a bare whitelisted name may be called — never an attribute (os.system),
            # never the result of another call ( ().__class__.__mro__[1] ... ).
            if not isinstance(node.func, ast.Name) or node.func.id not in callable_names:
                called = getattr(node.func, "id", type(node.func).__name__)
                raise UnsafeExpression(f"function '{called}' is not allowed")
        elif isinstance(node, ast.Name):
            if node.id not in names:
                raise UnsafeExpression(
                    f"unknown name '{node.id}' — allowed symbols are "
                    f"{sorted(set(allowed_symbols) | _ALLOWED_CONSTS)}"
                )
        elif isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, str)):
            raise UnsafeExpression("only numeric and symbol-name literals are allowed")


def parse_safe(expr: str, allowed_symbols: Iterable[str] = ("x",)) -> sp.Expr:
    """Parse a model-supplied expression, or raise UnsafeExpression."""
    if not isinstance(expr, str) or not expr.strip():
        raise UnsafeExpression("expression is empty")

    allowed = tuple(allowed_symbols)
    local = {s: sp.Symbol(s) for s in allowed}
    global_dict: dict = {}
    exec_("from sympy import *", global_dict)
    # sympy exports Abs and log, not the spellings a model actually writes.
    global_dict.update({"abs": sp.Abs, "ln": sp.log, "log10": _log10, "cbrt": sp.cbrt})

    code = stringify_expr(expr, local, global_dict, _TRANSFORMS)
    _validate_code(code, allowed)
    try:
        parsed = eval_expr(code, local, global_dict)
    except Exception as exc:
        # The whitelist already refused anything dangerous; whatever is left is merely
        # malformed. Surface it as UnsafeExpression so the caller has ONE exception type to
        # catch and the repair loop gets a usable message instead of a raw TypeError.
        raise UnsafeExpression(f"could not evaluate expression: {exc}") from exc

    # A stray free symbol is how a "flat line" bug reaches the page: lambdify returns a symbolic
    # object instead of a number and the plot silently collapses. Refuse rather than draw it.
    stray = {str(s) for s in parsed.free_symbols} - set(allowed)
    if stray:
        raise UnsafeExpression(f"expression contains unknown symbol(s): {sorted(stray)}")
    return parsed
