# scipy.constants — constants, conversions, search

`scipy.constants` bundles one CODATA edition (tied to your scipy version) plus a
large table of unit-conversion factors. It is BSD-3-Clause licensed. Import once:

```python
from scipy import constants as const
```

## 1. Common fundamental constants (named attributes)

```python
const.c              # speed of light in vacuum       m/s
const.h              # Planck constant                 J·s
const.hbar           # reduced Planck constant (h/2π)  J·s
const.k              # Boltzmann constant              J/K
const.G              # Newtonian gravitation           m³/(kg·s²)
const.e              # elementary charge               C
const.m_e            # electron mass                   kg
const.m_p            # proton mass                     kg
const.m_n            # neutron mass                    kg
const.epsilon_0      # vacuum electric permittivity    F/m
const.mu_0           # vacuum magnetic permeability     H/m
const.N_A            # Avogadro number                 1/mol
const.R              # molar gas constant              J/(mol·K)
const.sigma          # Stefan-Boltzmann constant       W/(m²·K⁴)
const.fine_structure # fine-structure constant α       dimensionless
const.Rydberg        # Rydberg constant R∞             1/m
const.g              # standard acceleration of gravity m/s²
const.atm            # standard atmosphere             Pa
```

Constants without a named attribute (e.g. Bohr radius, magnetic moments) live in
the `physical_constants` table — see §3.

## 2. Unit-conversion factors

All values below are the SI value of one unit, so multiply to convert *into* SI.

### Energy
```python
const.eV            # 1 electron-volt in joules
const.calorie       # 1 thermochemical calorie in joules
const.calorie_IT    # 1 international-table calorie in joules
const.erg           # 1 erg in joules
const.Btu           # 1 British thermal unit in joules
const.electron_volt # alias of const.eV
```

### Length
```python
const.angstrom      # 1 Å in metres (1e-10)
const.au            # 1 astronomical unit in metres
const.light_year    # 1 light-year in metres
const.parsec        # 1 parsec in metres
const.inch, const.foot, const.mile, const.nautical_mile
const.micron        # 1 micron in metres
```

### Pressure
```python
const.atm           # standard atmosphere in Pa
const.bar           # 1 bar in Pa (1e5)
const.torr          # 1 torr (mmHg) in Pa
const.psi           # 1 psi in Pa
```

### Temperature and time
```python
const.zero_Celsius  # 273.15 K
const.minute, const.hour, const.day, const.week, const.year
```

### Angle and mass
```python
const.degree        # 1 degree in radians
const.arcmin, const.arcsec
const.gram, const.metric_ton, const.pound, const.atomic_mass  # (unified amu, kg)
```

Temperature scales need functions, not factors:

```python
const.convert_temperature([0, 100], 'Celsius', 'Kelvin')   # -> [273.15, 373.15]
```

## 3. The physical_constants table

Every CODATA quantity is keyed by its full descriptive name and returns a
`(value, unit, uncertainty)` tuple:

```python
value, unit, uncertainty = const.physical_constants['Bohr radius']
# value       -> 5.29177...e-11
# unit        -> 'm'
# uncertainty -> absolute standard uncertainty (0.0 for exact/defined constants)
```

Convenience accessors avoid unpacking:

```python
const.value('Bohr radius')      # float value only
const.unit('Bohr radius')       # unit string
const.precision('Bohr radius')  # RELATIVE standard uncertainty (dimensionless)
```

A value with `uncertainty == 0.0` is exact by SI definition (post-2019 SI:
c, h, e, k, N_A, and several others are exact).

## 4. Search by keyword

`const.find(sub)` returns the list of `physical_constants` keys whose name
contains `sub` (case-insensitive). Use it to discover exact key spellings:

```python
const.find('electron')
# ['classical electron radius', 'electron g factor',
#  'electron mass', 'electron magnetic moment', ...]

const.find('magnetic moment')
const.find('Bohr')

# Print value + uncertainty for every match
for key in const.find('proton'):
    v, u, du = const.physical_constants[key]
    print(f"{key:45s} = {v:.10e} {u}  (± {du:.2e})")
```

`const.find()` with no argument returns every key.

## 5. Practical patterns

Propagate uncertainty from tabulated values:

```python
import numpy as np
alpha, _, dalpha = const.physical_constants['fine-structure constant']
rel = dalpha / alpha          # relative uncertainty of α
```

Guard against silent CODATA drift when reproducibility matters — pin scipy in
your environment and record its version alongside results:

```python
import scipy
provenance = f"CODATA via scipy.constants {scipy.__version__}"
```

## Edge cases and gotchas

- **CODATA edition is implicit.** There is no attribute that returns the CODATA
  year; it is fixed by the scipy version. Check scipy's release notes and record
  the version. Two environments on different scipy versions can return slightly
  different values for the same key.
- **`precision()` is relative; the tuple's third element is absolute.** Do not
  mix them up when propagating error.
- **Key names are exact strings.** `physical_constants['electron mass']` works;
  `['electron_mass']` raises `KeyError`. Use `find()` to get the spelling.
- **Deprecated/renamed keys** occasionally change between CODATA editions;
  wrap lookups in try/except if you must support multiple scipy versions.
