# Units, formula checking, and non-dimensionalization with `pint`

`pint` (BSD-3-Clause) attaches units to numbers and enforces dimensional homogeneity at
runtime. Treat it as an assertion layer: a unit error becomes a raised exception at the line
that makes the mistake, instead of a plausible-looking wrong number three steps later.

## Quantities and arithmetic

```python
import pint
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity                      # convenient constructor

mass     = Q_(2.0, 'kg')
velocity = Q_(3.0, 'm/s')
height   = Q_(10.0, 'm')
g        = Q_(9.80665, 'm/s**2')

KE = 0.5 * mass * velocity**2
PE = mass * g * height
print(KE.to('J'), PE.to('J'), (KE + PE).to('J'))   # all convert cleanly to joule
```

- `.to(unit)` converts (raises if the target dimension differs); `.to_base_units()` reduces
  to SI base units; `.magnitude` / `.units` / `.dimensionality` expose the parts.
- Multiplication and division combine units automatically; `**` raises them.
- **Addition/subtraction require matching dimensionality** — this is where errors surface.

## Catching dimensional errors

```python
try:
    bad = mass + velocity            # kg + m/s is nonsense
except pint.DimensionalityError as e:
    print("caught:", e)
```

Use `.check(dimension)` to assert a quantity has an expected dimensionality without converting:

```python
assert velocity.check('[length] / [time]')     # True
assert not velocity.check('[mass]')
```

`pint` dimensionality strings use bracketed base dimensions: `[mass]`, `[length]`, `[time]`,
`[temperature]`, `[current]`, `[substance]`, `[luminosity]`, combined multiplicatively, e.g.
energy is `[mass] * [length] ** 2 / [time] ** 2`.

## Converting between unit systems

```python
force = Q_(100, 'N')
print(force.to('dyn'))     # 1.0e7 dyne  (CGS)
print(force.to('lbf'))     # 22.48 pound_force  (US customary)

# switch the registry's default system wholesale:
ureg.default_system = 'cgs'
print((Q_(1, 'kg') * Q_(1, 'm/s**2')).to_base_units())
```

## Checking a derived formula's dimensions

Given a formula as a string plus each variable's fundamental-dimension exponents, evaluate it
with unit-carrying `1`s and report the resulting dimension. If the formula mixes incompatible
terms, `pint` raises.

```python
import pint

_DIM_TO_UNIT = {'M': 'kg', 'L': 'm', 'T': 's', 'Θ': 'K', 'I': 'A', 'N': 'mol', 'J': 'cd'}

def check_dimensions(formula, var_dims, ureg=None):
    """Evaluate `formula` with unit placeholders and return the result's units.

    Args:
        formula:  arithmetic string, e.g. "0.5 * m * v**2"
        var_dims: {var: {dim: exponent}}, e.g. {'m': {'M': 1}, 'v': {'L': 1, 'T': -1}}
    Returns the pint units of the result, or raises pint.DimensionalityError.
    """
    ureg = ureg or pint.UnitRegistry()
    context = {}
    for var, dims in var_dims.items():
        unit = " * ".join(f"{_DIM_TO_UNIT[d]}**({p})" for d, p in dims.items() if p != 0)
        context[var] = ureg.Quantity(1.0, unit or 'dimensionless')
    result = eval(formula, {"__builtins__": {}}, context)  # trusted formula strings only
    return result.to_base_units().units

check_dimensions("0.5 * m * v**2", {'m': {'M': 1}, 'v': {'L': 1, 'T': -1}})
# -> kilogram * meter ** 2 / second ** 2   (i.e. joule)  ✓
```

`eval` here runs with `__builtins__` stripped, but it is still `eval` — only pass formula
strings you control, never untrusted input.

## Non-dimensionalization recipe

To non-dimensionalize an equation, replace each dimensional variable by
`characteristic_scale × dimensionless_star_variable`, then divide the whole equation by a
common prefactor. The dimensionless groups appear as the coefficients that survive.

### Advection–diffusion

```
∂c/∂t + U ∂c/∂x = D ∂²c/∂x²
scales:  x* = x/L,  t* = tU/L,  c* = c/c0
->  ∂c*/∂t* + ∂c*/∂x* = (1/Pe) ∂²c*/∂x*²      with  Pe = U L / D  (Péclet number)
```

`Pe ≫ 1` ⇒ advection dominates (sharp fronts); `Pe ≪ 1` ⇒ diffusion dominates (smooth).

### Navier–Stokes (incompressible)

```
rho(∂u/∂t + u·∇u) = -∇p + mu ∇²u
scales:  x* = x/L,  t* = tU/L,  u* = u/U,  p* = p/(rho U²)
->  ∂u*/∂t* + u*·∇*u* = -∇*p* + (1/Re) ∇*²u*   with  Re = rho U L / mu
```

### Choosing characteristic scales

The scales are yours to pick and are the crux of a useful non-dimensionalization:

- **Length `L`** — a geometric size that controls the physics (pipe diameter, plate length,
  boundary-layer thickness), not an arbitrary domain edge.
- **Velocity `U`** — an imposed or emergent speed (inflow speed, `√(gL)` for gravity waves,
  `√(σ/ρL)` for capillary).
- **Time `t_c`** — an advective `L/U`, a diffusive `L²/D` (or `L²/α`, `L²/ν`), or a forcing
  period `1/f`, depending on which process you want to resolve at O(1).
- **Pressure `p_c`** — `rho U²` (inertial) or `mu U / L` (viscous), whichever balances the
  dominant term.

Pick scales so the terms you care about become O(1); the leftover coefficients are precisely
the dimensionless groups that rank the competing effects. A symbolic substitution check with
`sympy` (substitute, then `simplify`) confirms the algebra.
