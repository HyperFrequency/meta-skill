# SymPy Code Generation, Printing, and Parsing

Bridge symbolic math to fast numeric code, typeset output, and parse expressions
back in from strings/LaTeX. The recurring rule: derive symbolically, then
`lambdify` (or code-gen) for anything numeric at scale — never loop
`subs()` + `evalf()`.

## lambdify — symbolic expression to numeric callable

```python
from sympy import symbols, sin, cos, lambdify
import numpy as np
x, y = symbols('x y')
f = lambdify((x, y), sin(x) + cos(y), 'numpy')   # vectorized
f(np.linspace(0, 1, 100), np.linspace(0, 1, 100))
```

Backends via the third arg / `modules=`:

```python
lambdify(x, expr, 'numpy')    # NumPy (default-ish, vectorized)
lambdify(x, expr, 'scipy')    # SciPy special functions
lambdify(x, expr, 'mpmath')   # arbitrary precision
lambdify(x, expr, 'math')     # stdlib math (scalars only)

# Custom function mapping (dict first, fallback module second):
lambdify(x, sin(x), modules=[{'sin': lambda v: v}, 'numpy'])

# Multiple outputs -> tuple/list of results:
lambdify(x, [x**2, x**3, x**4], 'numpy')
```

`lambdify` builds source and `eval`s it — do not feed untrusted expressions.

## codegen — C / Fortran source

```python
from sympy.utilities.codegen import codegen
x, y = symbols('x y')
[(c_name, c_code), (h_name, h_header)] = codegen(
    ('dist_sq', x**2 + y**2), 'C', header=False, empty=False)
# Fortran 95: pass 'F95' instead of 'C'
```

Language code printers for one-off strings:

```python
from sympy.printing.c import C99CodePrinter
from sympy.printing.fortran import FCodePrinter
from sympy.printing.cxx import CXX11CodePrinter
C99CodePrinter().doprint(x**2 + y**2)
```

## autowrap / ufuncify — compile and import

Require a working C/Fortran toolchain (Cython or f2py).

```python
from sympy.utilities.autowrap import autowrap, ufuncify
f = autowrap(x**2 + y**2, backend='cython')     # compiled callable; f(3, 4) -> 25
g = ufuncify((x, y), x**2 + y**2)               # NumPy ufunc with broadcasting
```

## cse — common-subexpression elimination

```python
from sympy import cse, sin, cos
expr = sin(x + y)**2 + cos(x + y)**2 + sin(x + y)
replacements, reduced = cse(expr)
# replacements: [(x0, sin(x + y)), (x1, cos(x + y))]
# reduced:      [x0**2 + x1**2 + x0]
```

Feed `cse` output into code generation to avoid recomputing shared terms.

## Typeset Output

```python
from sympy import latex, pretty, pprint, srepr, Integral, sin, pi, Matrix
expr = Integral(sin(x)**2, (x, 0, pi))
latex(expr)                       # \int\limits_{0}^{\pi} \sin^{2}{...}\, dx
latex(expr, mode='equation')      # wrapped environment
latex(Matrix([[1, 2], [3, 4]]))   # matrix LaTeX
pprint(expr)                      # 2-D ASCII/Unicode rendering
srepr(sin(x)**2)                  # "Pow(sin(Symbol('x')), Integer(2))" (eval-able)
```

MathML:

```python
from sympy.printing.mathml import mathml
mathml(sin(pi/4))                          # content MathML
mathml(sin(pi/4), printer='presentation')  # presentation MathML
```

Custom printers subclass `StrPrinter`/`CodePrinter` and override
`_print_<Node>` methods.

## Parsing (string / LaTeX / Mathematica -> SymPy)

```python
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations,
                                         implicit_multiplication_application)
parse_expr('x**2 + 2*x + 1')
tf = standard_transformations + (implicit_multiplication_application,)
parse_expr('2x', transformations=tf)       # treats 2x as 2*x

from sympy.parsing.latex import parse_latex           # needs antlr4 runtime
parse_latex(r'\frac{x^2}{y}')                          # x**2/y

from sympy.parsing.mathematica import parse_mathematica
parse_mathematica('Sin[x]^2 + Cos[y]^2')
```

Validate/sanitize anything user-supplied before parsing or lambdifying.

## High-Precision Numerics

```python
from sympy import pi, sqrt, exp
pi.evalf(1000)                     # 1000 significant digits
(sqrt(2) + sqrt(3)).evalf(100)
expr.evalf(subs={x: 1.5, y: 2.3}) # substitute then evaluate

from mpmath import mp
mp.dps = 50                        # set global mpmath precision
```

## Jupyter Display

```python
from sympy import init_printing
init_printing(use_latex='mathjax')   # renders expressions as LaTeX in notebooks
```

## Expression-Tree Tools

```python
from sympy import preorder_traversal, Wild, sin
list(preorder_traversal(sin(x) + cos(y)))   # walk every subexpression
a = Wild('a')
(sin(x) + cos(y)).replace(sin(a), a**2)     # pattern match + replace: sin(x) -> x**2
```

## Notes

- **Numeric performance**: always `lambdify`/codegen instead of `subs()`+`evalf()`
  in loops — often orders of magnitude faster.
- **NumPy compatibility**: with the `'numpy'` backend, ensure the expression only
  uses functions NumPy provides (or supply a custom mapping).
- **Compilers**: `autowrap`/`ufuncify` and `parse_latex` have external
  dependencies (a C/Fortran compiler; the antlr4 runtime). They may need setup.
- **Security**: `lambdify`, `parse_expr`, and `parse_latex` execute/parse input —
  never run them on untrusted strings without sanitizing.
