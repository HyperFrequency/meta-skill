# SymPy Physics: Vectors, Mechanics, Quantum, Units

The `sympy.physics.*` subpackages provide symbolic tooling for classical and
quantum physics. This file covers the most-used pieces; several submodules
(optics, continuum mechanics, control, HEP, biomechanics) exist but have
version-sensitive APIs — check the official docs for exact signatures there.

## Vector Analysis

```python
from sympy.physics.vector import ReferenceFrame, dynamicsymbols, dot, cross
N = ReferenceFrame('N')          # inertial frame
v1 = 3*N.x + 4*N.y
v2 = 1*N.x + 2*N.z
dot(v1, v2)                      # scalar
cross(v1, v2)                    # vector
v1.magnitude()
v1.normalize()
```

Time-varying quantities use `dynamicsymbols`:

```python
t = dynamicsymbols._t
q = dynamicsymbols('q')          # q(t)
qd = dynamicsymbols('q', 1)      # first time derivative q'(t)
velocity = q.diff(t) * N.x
```

### Frame orientation and kinematics

```python
from sympy import symbols
theta = symbols('theta')
B = ReferenceFrame('B')
B.orient(N, 'Axis', [theta, N.z])   # rotate B about N.z by theta
N.dcm(B)                            # direction cosine matrix
B.ang_vel_in(N)                     # angular velocity of B in N

from sympy.physics.vector import Point
O, P = Point('O'), Point('P')
P.set_pos(O, 3*N.x + 4*N.y)
P.set_vel(N, 5*N.x)
P.vel(N); P.acc(N)                  # velocity, acceleration in N
```

## Classical / Analytical Mechanics

### Lagrange's method

```python
from sympy import symbols, cos, Rational
from sympy.physics.mechanics import dynamicsymbols, LagrangesMethod

q = dynamicsymbols('q')
qd = dynamicsymbols('q', 1)
m, g, l = symbols('m g l')

T = Rational(1, 2) * m * (l * qd)**2      # kinetic energy
V = m * g * l * (1 - cos(q))              # potential energy
L = T - V                                 # Lagrangian

LM = LagrangesMethod(L, [q])
LM.form_lagranges_equations()             # equations of motion
LM.rhs()                                  # solved-for accelerations
```

### Kane's method

```python
from sympy.physics.mechanics import KanesMethod, ReferenceFrame
from sympy.physics.vector import dynamicsymbols

N = ReferenceFrame('N')
q, u = dynamicsymbols('q u')
kd = [u - q.diff()]                        # kinematic differential equations
KM = KanesMethod(N, q_ind=[q], u_ind=[u], kd_eqs=kd)
# KM.kanes_equations(bodies, loads)  after defining particles/rigid bodies + forces
```

### Rigid bodies and inertia

```python
from sympy.physics.mechanics import ReferenceFrame, Point, RigidBody, inertia
from sympy import symbols
m, Ixx, Iyy, Izz = symbols('m I_xx I_yy I_zz')
A = ReferenceFrame('A')
P = Point('P')                              # mass center
I = inertia(A, Ixx, Iyy, Izz)               # central inertia dyadic
body = RigidBody('Body', P, A, m, (I, P))   # (dyadic, point) pair
```

`Particle(name, point, mass)` models point masses. Joint helpers
(`PinJoint`, `PrismaticJoint`, ...) and the `System`/`Body` assembly API exist
for building multibody systems; consult the docs, as these classes have evolved
across SymPy versions.

### Linearization

```python
op_point = {q: 0, u: 0}
A_mat, B_mat = KM.linearize(q_ind=[q], u_ind=[u], A_and_B=True, op_point=op_point)
```

## Quantum Mechanics

### States and operators

```python
from sympy.physics.quantum import Ket, Bra, Operator, Dagger, qapply
psi = Ket('psi'); phi = Ket('phi')
A = Operator('A'); B = Operator('B')
Dagger(A)                 # Hermitian conjugate
Bra('psi') * psi          # inner product
qapply(A * psi)           # apply operators
```

### Commutators

```python
from sympy.physics.quantum import Commutator, AntiCommutator
Commutator(A, B).doit()       # A*B - B*A
AntiCommutator(A, B).doit()   # A*B + B*A
```

### Harmonic oscillator, spin, gates

```python
from sympy.physics.quantum.qho_1d import RaisingOp, LoweringOp, NumberOp
from sympy.physics.quantum.spin import JzKet, Jz
from sympy import Rational
JzKet(Rational(1, 2), Rational(1, 2))     # |1/2, 1/2>

from sympy.physics.quantum.gate import H, X, Y, Z, CNOT, SWAP
from sympy.physics.quantum.qubit import Qubit
qapply(H(0) * Qubit('01'))                # Hadamard on qubit 0
```

## Units and Dimensional Analysis

```python
from sympy.physics.units import meter, kilogram, second, newton, convert_to
distance = 5 * meter
mass = 10 * kilogram
time = 2 * second
force = mass * distance / time**2
convert_to(force, newton)                 # express in newtons
```

Physical constants and the SI system:

```python
from sympy.physics.units import speed_of_light, gravitational_constant, SI
```

Custom units:

```python
from sympy.physics.units import Quantity, meter
parsec = Quantity('parsec')
parsec.set_global_relative_scale_factor(Rational(30857) * 10**12 * meter, meter)
```

## Notes

- Use `dynamicsymbols()` (not `symbols()`) for anything time-dependent in
  mechanics; its `.diff()` implicitly differentiates with respect to time.
- Keep units explicit and convert at the end; mixing bare numbers and unit
  quantities silently drops dimensional information.
- Most physics results are symbolic — call `.evalf()` or `lambdify` for numbers.
- Give symbols physical assumptions (`positive=True`, `real=True`) so
  simplification behaves.
