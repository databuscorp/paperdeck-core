"""Model-supplied maths expressions must never be executed.

This guards a confirmed remote code execution hole. `function_graph` and `calculus_graph` used
`sympify()` on an expression string written by the LLM, and sympify eval()s its input:

    sympify("__import__('os').getcwd()")  ->  '/…/paperdeck-core'      # it RAN

The LLM's context includes user-controlled text — topic strings, and the OCR'd contents of
uploaded question papers in the import flow — so a crafted upload was a path to running arbitrary
code on the server. Restricting sympy's global_dict does not close it (sympy needs its own
namespace to evaluate at all), so the generated code is gated against an AST whitelist instead.

If any assertion here fails, the hole is open again.
"""
from django.test import SimpleTestCase

from diagrams.service.mathematics.renderer import render_mathematics
from diagrams.service.safeexpr import UnsafeExpression, parse_safe

EXPLOITS = [
    "__import__('os').getcwd()",
    "__import__('os').system('id')",
    "().__class__.__mro__[1].__subclasses__()",
    "().__class__.__base__.__subclasses__()",
    "os.system('id')",
    "x.__class__",
    "eval('1+1')",
    "open('/etc/passwd').read()",
    "exec('import os')",
    "globals()",
]


class ExpressionSandboxTests(SimpleTestCase):

    def test_every_known_escape_is_refused(self):
        """THE one that matters. Each of these executed before the fix."""
        for payload in EXPLOITS:
            with self.assertRaises(UnsafeExpression, msg=f"NOT BLOCKED: {payload}"):
                parse_safe(payload, ("x",))

    def test_the_renderer_itself_refuses_the_payload(self):
        """The gate has to sit in the render path, not merely exist as a helper."""
        for payload in EXPLOITS[:4]:
            with self.assertRaises(ValueError):
                render_mathematics("function_graph", {"functions": [{"expression": payload}]})

    def test_attribute_access_is_refused_even_on_an_allowed_symbol(self):
        """`x` is legal; `x.__class__` is the first step of every sandbox escape."""
        with self.assertRaises(UnsafeExpression):
            parse_safe("x.__class__", ("x",))

    def test_an_unknown_symbol_is_refused_rather_than_silently_plotted(self):
        """sympy's implicit_multiplication_application bundles split_symbols, which shreds
        'N0*exp(-k*t)' into N*0*... = 0 — the renderer then draws a FLAT ZERO LINE instead of
        failing. A wrong graph that renders is worse than no graph, so a stray symbol must raise."""
        with self.assertRaises(UnsafeExpression):
            parse_safe("N0*exp(-x)", ("x",))

    def test_implicit_multiplication_still_works(self):
        """The fix must not cost us sympy-legal input the model actually writes: Python's own
        parser rejects '2x' outright, which is why the RAW string cannot be the thing validated."""
        self.assertEqual(str(parse_safe("2x + 1", ("x",))), "2*x + 1")

    def test_ordinary_maths_still_parses(self):
        for expr in ["x**2 - 4", "sin(x) + cos(2*x)", "exp(-x**2)", "sqrt(abs(x))",
                     "log(x)", "ln(x)", "log10(x)", "x^3", "pi*x", "floor(x)"]:
            parse_safe(expr, ("x",))       # must not raise

    def test_two_symbol_expressions_for_the_lp_constraint_parser(self):
        parse_safe("2x + 3y", ("x", "y"))
        with self.assertRaises(UnsafeExpression):
            parse_safe("2x + 3z", ("x", "y"))     # z was never declared
