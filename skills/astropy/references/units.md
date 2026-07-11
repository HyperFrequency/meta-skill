# Units & Quantities (`astropy.units`)

A `Quantity` binds a number (or array) to a physical unit and enforces
dimensional consistency through every operation.

## Creating quantities

Multiply or divide a value by a unit:

```python
from astropy import units as u
import numpy as np

distance = 42.0 * u.meter
velocity = 100 * u.km / u.s
distances = np.array([1., 2., 3.]) * u.m      # array-valued
wavelengths = [500, 600, 700] * u.nm          # list is promoted to array
```

Unpack with `.value` (the raw number/array) and `.unit` (a `Unit` object).

## Converting

`.to(target_unit)` returns a new quantity in the requested unit:

```python
(1.0 * u.parsec).to(u.km)      # <Quantity 3.0857e+13 km>
(500 * u.nm).to(u.angstrom)    # <Quantity 5000. Angstrom>
```

`.si` and `.cgs` convert to those systems; `.decompose()` reduces to base units;
`(u.s**-1).compose()` lists equivalent named units.

## Arithmetic

Units propagate and cancel automatically:

```python
(5 * u.m) * (3 * u.m)          # 15 m2
(10 * u.m) / (5 * u.m)         # 2.0 (dimensionless)
(3*u.km) / (130*u.m/u.s)       # a time; call .decompose() -> seconds
```

Mismatched dimensions raise `UnitConversionError` — the safety you want.

## Equivalencies

Conversions that hold only under a physical relationship require an
`equivalencies=` argument:

```python
(1000 * u.nm).to(u.Hz, equivalencies=u.spectral())            # wavelength<->frequency
(1000*u.km/u.s).to(u.Hz, equivalencies=u.doppler_optical(500*u.nm))
```

Other equivalencies: `u.doppler_radio`, `u.doppler_relativistic`,
`u.brightness_temperature(freq)`, `u.parallax()`, `u.mass_energy()`,
`u.dimensionless_angles()` (treat radians as dimensionless).

## Logarithmic units

```python
-2.5 * u.mag(u.ct / u.s)       # magnitude referenced to a physical unit
3 * u.dB(u.W)                  # decibel
8.5 * u.dex(u.cm**-3)          # base-10 dex
```

## Common units by dimension

- Length: `m, km, cm, mm, micron, angstrom, au, pc, kpc, Mpc, lyr`
- Time: `s, min, hour, day, year, Myr, Gyr`
- Mass: `kg, g, M_sun, M_earth, M_jup`
- Angle: `deg, arcmin, arcsec, mas, rad, hourangle`
- Energy/power: `J, erg, eV, keV, MeV, GeV, W, L_sun`
- Frequency: `Hz, kHz, MHz, GHz`
- Flux: `Jy, mJy` (and composites like `erg / u.s / u.cm**2`)

## Performance: attach units without copying

For hot array loops, pre-build the composite unit and use `<<` (attach in place)
instead of `*` (which allocates intermediates):

```python
UNIT = u.m / u.s / u.kg / u.sr
result = array << UNIT          # far faster than array * UNIT for large arrays
```

## Formatting

```python
v = 15.1 * u.m / (32.0 * u.s)
f"{v:0.3f}"          # '0.472 m / s'
f"{v.unit:FITS}"     # 'm s-1'  (FITS-standard unit string)
```

## Custom units

```python
fortnight = u.def_unit("fortnight", 14 * u.day)
u.add_enabled_units([fortnight])   # now parseable from strings
```

## Constants (`astropy.constants`)

Physical constants are quantities with units and uncertainties:

```python
from astropy.constants import c, G, M_sun, h, k_B
c.to(u.km / u.s)
G.to(u.m**3 / u.kg / u.s**2)
```

See `references/wcs-and-modules.md` for a fuller constants list and worked
examples (Schwarzschild radius, escape velocity).
