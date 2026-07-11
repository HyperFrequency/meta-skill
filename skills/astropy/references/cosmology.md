# Cosmology (`astropy.cosmology`)

Compute distances, times, and densities for a chosen cosmological model. A
cosmology object is immutable and vectorized over redshift.

## Built-in models

```python
from astropy.cosmology import Planck18, Planck15, WMAP9
from astropy import units as u

cosmo = Planck18
cosmo.luminosity_distance(4)     # distance to z=4
cosmo.age(0).to(u.Gyr)           # current age of the universe
```

## Custom models

```python
from astropy.cosmology import FlatLambdaCDM, LambdaCDM, FlatwCDM, w0wzCDM

FlatLambdaCDM(H0=70*u.km/u.s/u.Mpc, Om0=0.3, Tcmb0=2.725*u.K)   # most common
LambdaCDM(H0=70*u.km/u.s/u.Mpc, Om0=0.3, Ode0=0.7)             # non-flat
FlatwCDM(H0=70*u.km/u.s/u.Mpc, Om0=0.3, w0=-0.9)              # constant w
w0wzCDM(H0=70*u.km/u.s/u.Mpc, Om0=0.3, Ode0=0.7, w0=-1.0, wz=0.1)  # w(z)=w0+wz*z
```

`H0` sets the Hubble constant, `Om0` the matter density parameter, `Ode0` the
dark-energy density (non-flat models), `Tcmb0` the CMB temperature.

## Distances

```python
cosmo.comoving_distance(z)               # line-of-sight comoving
cosmo.luminosity_distance(z)             # flux -> luminosity
cosmo.angular_diameter_distance(z)       # angular size -> physical size
cosmo.comoving_transverse_distance(z)    # equals comoving distance if flat
cosmo.distmod(z)                         # distance modulus m - M
```

Absolute magnitude from apparent magnitude and redshift:

```python
M_abs = m_app - cosmo.distmod(z).value
```

Physical size from angular size:

```python
theta = 1 * u.arcsec
size_kpc = (cosmo.angular_diameter_distance(z) * theta.to(u.rad)).to(u.kpc)
```

## Scale and volume

```python
cosmo.kpc_proper_per_arcmin(z)              # proper kpc per arcmin at z
cosmo.comoving_volume(z)                    # total comoving volume to z
cosmo.differential_comoving_volume(z)       # dV/dz per steradian
```

Survey volume between two redshifts:

```python
vol = cosmo.comoving_volume(1.5) - cosmo.comoving_volume(0.5)
vol.to(u.Gpc**3)
```

## Times

```python
cosmo.age(z)             # age of universe at z
cosmo.lookback_time(z)   # time since light at z was emitted
```

## Expansion and densities

```python
cosmo.H(z)          # Hubble parameter H(z) [km/s/Mpc]
cosmo.efunc(z)      # E(z) = H(z)/H0
cosmo.Om(z)         # matter density parameter at z
cosmo.Ode(z)        # dark-energy density parameter at z
cosmo.Ok(z)         # curvature; also Ogamma(z), Onu(z)
cosmo.critical_density(z)
```

## Inverse: redshift from a value

`z_at_value` numerically inverts any monotonic method:

```python
from astropy.cosmology import z_at_value

z_at_value(cosmo.lookback_time, 10*u.Gyr)
z_at_value(cosmo.luminosity_distance, 1000*u.Mpc)
z_at_value(cosmo.age, 1*u.Gyr)
```

## Arrays and neutrinos

Every method accepts array redshifts:

```python
import numpy as np
z = np.linspace(0, 5, 100)
cosmo.luminosity_distance(z)     # returns a Quantity array
```

Massive neutrinos add accuracy at a 3-4x speed cost:

```python
FlatLambdaCDM(H0=70*u.km/u.s/u.Mpc, Om0=0.3, Tcmb0=2.725*u.K,
              Neff=3.04, m_nu=[0., 0., 0.06]*u.eV)
```

## Modifying a cosmology

Objects are immutable; make a modified copy with `.clone()`:

```python
cosmo.clone(H0=72*u.km/u.s/u.Mpc)
cosmo.clone(name="My Cosmology")
```

Results are reliable for `z` up to ~5000-6000 depending on the model.
