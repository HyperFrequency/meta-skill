# SymPy Advanced Topics

Geometry, number theory, combinatorics, logic/sets, polynomials, symbolic
probability, and special functions.

## Geometry

### 2D

```python
from sympy.geometry import Point, Line, Segment, Circle, Triangle, Polygon, Ellipse
p1, p2, p3 = Point(0, 0), Point(1, 1), Point(1, 0)
p1.distance(p2)                       # sqrt(2)

line = Line(p1, p2)
line.slope; line.equation()
Line(p1, p2).intersection(Line(Point(0, 1), Point(1, 0)))  # [Point(1/2, 1/2)]

Segment(p1, p2).midpoint
Circle(Point(0, 0), 5).area           # 25*pi
Triangle(p1, p2, p3).area
Polygon(Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)).perimeter
Ellipse(Point(0, 0), hradius=3, vradius=2).eccentricity
```

Queries: `line.contains(pt)`, `line1.is_parallel(line2)`,
`line1.is_perpendicular(line2)`, `circle.tangent_lines(pt)`.

### 3D

```python
from sympy.geometry import Point3D, Line3D, Plane
plane = Plane(Point3D(0, 0, 0), Point3D(1, 1, 1), Point3D(1, 0, 0))
plane.equation()
plane.distance(Point3D(2, 3, 4))
plane.intersection(Line3D(Point3D(0, 0, 0), Point3D(1, 1, 1)))
```

### Parametric curves

```python
from sympy.geometry import Curve
from sympy import sin, cos, pi
from sympy.abc import t
Curve((cos(t), sin(t)), (t, 0, 2*pi))    # unit circle
```

## Number Theory

```python
from sympy import isprime, primerange, prime, nextprime, prevprime
isprime(7)                     # True
list(primerange(10, 30))       # [11, 13, 17, 19, 23, 29]
prime(10)                      # 29  (the 10th prime)
nextprime(10); prevprime(10)   # 11 ; 7

from sympy import factorint, primefactors, divisors, gcd, lcm, igcd, ilcm
factorint(60)                  # {2: 2, 3: 1, 5: 1}
primefactors(60)               # [2, 3, 5]
divisors(60)                   # [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60]
gcd(60, 48); lcm(60, 48)       # 12 ; 240

from sympy import mod_inverse
from sympy.ntheory import totient, is_primitive_root
mod_inverse(3, 7)              # 5   (3*5 == 15 == 1 mod 7)
totient(10)                    # 4
is_primitive_root(2, 5)        # True
```

Diophantine equations and continued fractions:

```python
from sympy.solvers.diophantine import diophantine
from sympy.abc import x, y
diophantine(3*x + 4*y - 5)     # parametric integer solutions

from sympy import continued_fraction_iterator, Rational
list(continued_fraction_iterator(Rational(415, 93)))   # [4, 2, 6, 7]
```

## Combinatorics

```python
from sympy import factorial, binomial, factorial2, catalan, fibonacci, lucas
from sympy.functions.combinatorial.numbers import nC, nP, partition
factorial(5)        # 120
binomial(5, 2)      # 10
nP(5, 2); nC(5, 2)  # 20 ; 10
partition(5)        # 7   (number of integer partitions of 5)
catalan(5)          # 42
fibonacci(10)       # 55
```

Permutation objects and groups:

```python
from sympy.combinatorics import Permutation, PermutationGroup
p = Permutation([1, 2, 0, 3])      # 0->1, 1->2, 2->0, 3->3
p.order(); p.is_even; p.inversions()
G = PermutationGroup(Permutation([1, 0, 2]), Permutation([0, 2, 1]))
G.order(); G.is_abelian; G.is_cyclic()
```

Iterables: `from sympy.utilities.iterables import multiset_permutations,
partitions`.

## Logic and Sets

```python
from sympy import symbols, And, Or, Not, Xor, Implies, Equivalent
from sympy.logic.boolalg import simplify_logic, truth_table
a, b, c = symbols('a b c')
simplify_logic((a & b) | (a & ~b))       # a
Implies(a, b); Equivalent(a, b); Xor(a, b)
list(truth_table(Implies(a, b), [a, b]))
```

Satisfiability: `from sympy.logic.inference import satisfiable; satisfiable(expr)`.

```python
from sympy import FiniteSet, Interval, Union, Intersection, Complement, S
A = FiniteSet(1, 2, 3, 4); B = FiniteSet(3, 4, 5, 6)
Union(A, B); Intersection(A, B); Complement(A, B)
Interval(0, 1)          # [0, 1]
Interval.open(0, 1)     # (0, 1)
Interval.Lopen(0, 1)    # (0, 1]
S.Reals, S.Integers, S.Naturals, S.EmptySet, S.Complexes
A.is_subset(B); 3 in A

from sympy import ImageSet, Lambda
ImageSet(Lambda(symbols('n'), symbols('n')**2), S.Integers)   # {n^2 | n in Z}
```

## Polynomials

```python
from sympy import Poly, symbols, div, roots, real_roots, factor, factor_list, groebner
x, y, z = symbols('x y z')
p = Poly(x**2 + 2*x + 1, x)
p.degree(); p.coeffs(); p.as_expr()
div(Poly(x**2 + 1, x), Poly(x + 1, x))    # (quotient, remainder)

roots(x**3 - 6*x**2 + 11*x - 6, x)        # {1: 1, 2: 1, 3: 1}
real_roots(x**3 - 6*x**2 + 11*x - 6)
factor(x**3 - x**2 + x - 1)               # (x - 1)*(x**2 + 1)
factor_list(x**3 - x**2 + x - 1)          # structured factor list
groebner([x**2 + y**2 + z**2 - 1, x*y - z], x, y, z)   # Groebner basis
```

## Symbolic Probability (`sympy.stats`)

```python
from sympy.stats import (Normal, Uniform, Exponential, Die, Bernoulli, Binomial,
                         Poisson, P, E, variance, density, covariance)
from sympy.abc import x
X = Normal('X', 0, 1)          # Normal(name, mean, std)
P(X > 0)                       # 1/2
E(X); variance(X)              # 0 ; 1
density(X)(x)                  # sqrt(2)*exp(-x**2/2)/(2*sqrt(pi))

D = Die('D', 6); P(D > 3)      # 1/2
B = Binomial('B', 10, S(1)/2); P(B > 5)
Y1, Y2 = Normal('Y1', 0, 1), Normal('Y2', 0, 1)
covariance(Y1, Y2)             # 0 (independent)
```

Everything is exact and symbolic; `sympy.stats` is for closed-form probability,
not for fitting distributions to data (use `scipy.stats`/`statsmodels`/`pymc`).

## Special Functions

```python
from sympy import (gamma, beta, erf, besselj, bessely, hermite, legendre,
                   laguerre, chebyshevt, zeta, hyper, meijerg)
gamma(5)            # 24
gamma(S(1)/2)       # sqrt(pi)
besselj(0, x)       # J_0(x)
hermite(3, x)       # 8*x**3 - 12*x
legendre(2, x)      # (3*x**2 - 1)/2
chebyshevt(3, x)    # 4*x**3 - 3*x
```

## Notes

- Most results are **exact and symbolic**; call `.evalf()` for numbers.
- Add assumptions (`positive=True`, `integer=True`) to steer simplification.
- Complex symbolic operations can be slow; substitute numerics or drop to
  numeric libraries for large-scale work.
