# Coordinates (`astropy.coordinates`)

`SkyCoord` is the high-level object for celestial positions. It knows its
reference frame and handles transforms, separations, and catalog matching.

## Building a SkyCoord

```python
from astropy import units as u
from astropy.coordinates import SkyCoord

SkyCoord(ra=10.625*u.deg, dec=41.2*u.deg, frame="icrs")   # decimal degrees
SkyCoord(ra="00h42m30s", dec="+41d12m00s", frame="icrs")  # sexagesimal
SkyCoord("00h42.5m +41d12m", unit=(u.hourangle, u.deg))   # mixed, explicit units
SkyCoord(l=120.5*u.deg, b=-23.4*u.deg, frame="galactic")  # galactic input
```

Pass arrays to process many positions at once — always prefer this to a loop:

```python
coords = SkyCoord(ra=[10, 11, 12]*u.deg, dec=[41, -5, 42]*u.deg)
coords[0], coords[1:3], coords.shape, len(coords)
```

## Components and formatting

```python
c.ra, c.dec              # Longitude / Latitude quantities
c.ra.hour, c.ra.hms      # hours; (h, m, s) tuple
c.dec.dms                # (d, m, s) tuple
c.to_string("hmsdms")    # '00h42m43.2s +41d16m12s'
c.ra.to_string(unit=u.hour, sep=":", precision=2)
```

## Frame transforms

Common frames are attributes; anything is reachable via `transform_to`:

```python
c = SkyCoord(ra=10.68*u.deg, dec=41.27*u.deg, frame="icrs")
c.galactic                       # attribute shortcut
c.transform_to("fk5")
c.transform_to(FK5(equinox="J1975"))   # frame with parameters
```

Frame families:
- Celestial: `icrs` (default), `fk5` (J2000 by default), `fk4`, `gcrs`, `cirs`.
- Galactic: `galactic`, `supergalactic`, `galactocentric` (3D).
- Horizontal: `altaz` (observer-dependent), `hadec`.
- Ecliptic: `geocentricmeanecliptic`, `barycentricmeanecliptic`,
  `heliocentricmeanecliptic`.

## Observer-dependent frames (AltAz)

Altitude/azimuth needs a time and an Earth location:

```python
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz

loc = EarthLocation(lat=40.8*u.deg, lon=-121.5*u.deg, height=1060*u.m)
# or: EarthLocation.of_site("Apache Point Observatory")   # needs network first time
frame = AltAz(obstime=Time("2023-01-15 23:00:00"), location=loc)
aa = c.transform_to(frame)
aa.alt, aa.az
```

`EarthLocation.get_site_names()` lists known observatories;
`EarthLocation.of_address(...)` geocodes a street address (network).

## Separations and position angle

```python
c1 = SkyCoord(ra=10*u.deg, dec=9*u.deg, frame="icrs")
c2 = SkyCoord(ra=11*u.deg, dec=10*u.deg, frame="fk5")
c1.separation(c2)        # on-sky angle; frames reconciled automatically
c1.position_angle(c2)    # PA east of north
```

## 3D coordinates and kinematics

Add `distance` for full 3D; add proper motion / radial velocity for kinematics:

```python
c = SkyCoord(ra=10*u.deg, dec=9*u.deg, distance=770*u.kpc, frame="icrs")
c.cartesian.x, c.cartesian.y, c.cartesian.z
c1.separation_3d(c2)     # physical 3D distance (both need distance)

SkyCoord(ra=10*u.deg, dec=41*u.deg, distance=150*u.pc,
         pm_ra_cosdec=15*u.mas/u.yr, pm_dec=5*u.mas/u.yr,
         radial_velocity=20*u.km/u.s)
```

Switch representations with `representation_type` (`"cartesian"`,
`"cylindrical"`, `"spherical"`).

## Catalog matching

```python
idx, sep2d, dist3d = target.match_to_catalog_sky(catalog)
matched = catalog[idx]
keep = sep2d < 1*u.arcsec       # apply a separation threshold
```

`idx[i]` is the index in `catalog` of the nearest source to `target[i]`; `sep2d`
is the on-sky separation of each match. For symmetric cross-matching between two
catalogs, call `match_to_catalog_sky` on the `SkyCoord` of one against the other.

## Named objects

```python
SkyCoord.from_name("M31")           # resolves via SIMBAD/NED (network)
SkyCoord.from_name("Crab Nebula")
```

## Performance

- Vectorize: one `SkyCoord` over N positions beats N `SkyCoord`s in a loop.
- Reuse a single frame object for repeated transforms.
- For dense time sampling of AltAz, trade a little accuracy for speed by
  interpolating the ERFA astrometry parameters:

```python
from astropy.coordinates import erfa_astrom, ErfaAstromInterpolator
import astropy.units as u

with erfa_astrom.set(ErfaAstromInterpolator(300 * u.s)):
    aa = coords.transform_to(altaz_frame)   # recomputes astrom every ~300 s
```
