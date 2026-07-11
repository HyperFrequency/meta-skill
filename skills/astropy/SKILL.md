---
name: astropy
version: 0.1.0
description: >-
  Astropy is the core Python library for astronomy and astrophysics. Use it for
  physical units and quantities with dimensional checking; celestial coordinates
  (`SkyCoord`) and transforms between frames (ICRS, Galactic, FK5, AltAz);
  reading, writing, and editing FITS images and tables; cosmological distances,
  ages, and lookback times; high-precision time across scales (UTC/TAI/TT/TDB)
  and formats (JD/MJD/ISO); unit-aware tables and catalog cross-matching;
  pixel-to-world WCS transforms; and physical constants. Reach for it on unit
  conversions, coordinate transforms, FITS manipulation, cosmological
  calculations, time-scale conversions, or catalog matching. NOT for general
  plotting (use `matplotlib`/`seaborn`), out-of-core array compute (use `dask`),
  non-astronomical tabular ETL (use `polars`/pandas), or ML training loops (use
  `pytorch-lightning`); specialized photometry, spectroscopy, and CCD reduction
  live in affiliated packages (photutils, specutils, ccdproc).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (Astropy)"
---

# Astropy

## Overview

Astropy is the foundational package for astronomy in Python. Its defining idea is
that numbers carry **units** and **frames** — a distance is a `Quantity` in
parsecs, a position is a `SkyCoord` in ICRS, a timestamp is a `Time` on the UTC
scale — so conversions, arithmetic, and transforms stay dimensionally and
astrometrically correct instead of silently mixing degrees with radians or JD
with MJD.

This skill is a **router**. It gives you the mental model, an install path, a
quick start, and a capability map keyed to Astropy's subpackages, then delegates
the deep API surface, parameter tables, and worked patterns to `references/`.
Read the matching reference before writing nontrivial code against a subpackage.

## When to Use This Skill

- Attaching, converting, or doing arithmetic with physical **units** and constants.
- Building **celestial coordinates** and transforming between frames (ICRS,
  Galactic, FK5, AltAz, ecliptic), computing separations, or matching catalogs.
- Reading, writing, or editing **FITS** files — image HDUs, binary/ASCII tables,
  headers, multi-extension files, memory-mapped or remote (S3/HTTP) data.
- **Cosmological** calculations: luminosity/comoving/angular-diameter distance,
  age, lookback time, `H(z)`, density parameters, survey volumes.
- Precise **time** handling: converting scales (UTC/TAI/TT/TDB/UT1) and formats
  (ISO/JD/MJD/Unix/GPS), time arithmetic, sidereal time, barycentric corrections.
- Unit-aware **tables**: reading catalogs, filtering, sorting, joins, grouping,
  cross-matching, and I/O across FITS/CSV/ECSV/VOTable/HDF5/Parquet.
- **WCS** pixel-to-world transforms, plus modeling/fitting, image normalization,
  sigma-clipping statistics, and convolution kernels.

## When NOT to Use This Skill

- **General plotting** — Astropy has no charting engine; extract arrays and use
  `matplotlib` / `seaborn`. (`astropy.visualization` only provides *normalization
  and stretch* for image display, not the plot itself.)
- **Out-of-core array compute** — for lazy/chunked math over huge arrays use
  `dask`; Astropy can *write* a Dask array to FITS but is not a compute engine.
- **Generic, non-astronomical tabular ETL** — reach for `polars` or pandas;
  `astropy.table` earns its keep only when you need unit-aware columns, FITS/
  VOTable I/O, or coordinate cross-matching.
- **ML training loops** — use `pytorch-lightning` / `scikit-learn`; Astropy's
  modeling is for analytic model fitting (Gaussians, polynomials), not deep nets.
- **Specialized pipelines** — source detection/photometry (photutils),
  spectroscopy (specutils), CCD reduction (ccdproc), and cutouts/reproject live
  in **affiliated packages**, not core Astropy.

## Installation

```bash
uv pip install astropy          # core
uv pip install "astropy[all]"   # optional deps (fsspec/S3, HDF5, VOTable, ...)
```

Some operations pull remote data on first use: leap-second/IERS tables for
`ut1`/sidereal time, and site/object databases for `EarthLocation.of_site` and
`SkyCoord.from_name`. These cache locally but require network access initially.

## Quick Start

```python
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.io import fits
from astropy.table import Table
from astropy.cosmology import Planck18

d_km = (100 * u.pc).to(u.km)                      # units + conversion
c = SkyCoord(ra=10.5*u.deg, dec=41.2*u.deg).galactic  # frame transform
jd = Time("2023-01-15 12:30:00").jd               # time -> Julian Date
data = fits.getdata("image.fits", ext=1)          # FITS image (NumPy array)
cat = Table.read("catalog.fits")                  # table from FITS
dL = Planck18.luminosity_distance(z=1.0)          # cosmological distance
```

## Core Subpackages

Each entry names the key API surface and points to its reference.

### Units & quantities — `astropy.units` → `references/units.md`
Create a `Quantity` by multiplying a value with a unit (`42 * u.m`); convert with
`.to(...)`; use `.value`/`.unit` to unpack. Domain conversions (wavelength↔
frequency, Doppler, parallax, brightness temperature) need `equivalencies=`.
Logarithmic units (`u.mag`, `u.dB`, `u.dex`), custom units, `<<` for fast
in-place unit attachment, and `astropy.constants` all live here.

### Coordinates — `astropy.coordinates` → `references/coordinates.md`
`SkyCoord` is the high-level interface: build from decimal or sexagesimal input,
transform via attribute (`.galactic`) or `.transform_to(frame)`, compute
`.separation()` / `.position_angle()`, add `distance`/proper motion/radial
velocity for 3D and kinematics. Observer frames (`AltAz`) need an `obstime` and
`EarthLocation`; catalog matching via `match_to_catalog_sky`; names via
`from_name`. Vectorize with arrays, never Python loops.

### Cosmology — `astropy.cosmology` → `references/cosmology.md`
Use a built-in (`Planck18`, `WMAP9`) or build `FlatLambdaCDM(H0=..., Om0=...)`.
Methods: `luminosity_distance`, `comoving_distance`, `angular_diameter_distance`,
`distmod`, `age`, `lookback_time`, `H(z)`, `Om(z)`, `comoving_volume`. Invert
with `z_at_value`. Objects are immutable — copy with `.clone(...)`.

### FITS I/O — `astropy.io.fits` → `references/fits.md`
Open inside a context manager (`with fits.open(path) as hdul:`); inspect with
`.info()`; reach HDUs by index or name; `.data` is a NumPy array, `.header` a
mutable card dict. Create with `PrimaryHDU`/`ImageHDU`/`BinTableHDU.from_columns`;
one-shot `getdata`/`getheader`/`writeto`. Memory-map big files; use `.section`
and `use_fsspec=True` for remote/cloud reads.

### Tables — `astropy.table` → `references/tables.md`
`Table` for heterogeneous columns, `QTable` for unit-aware columns. `read`/
`write` auto-detect format (FITS/CSV/ECSV/VOTable/HDF5/Parquet). Column/row/
boolean-mask access, `sort`, `vstack`/`hstack`/`join`, `group_by`, `add_index`
for fast `loc` lookup, `MaskedColumn` for missing data, and `to_pandas()` bridge.

### Time — `astropy.time` → `references/time.md`
`Time(value, format=..., scale=...)` stores two 64-bit floats for sub-ns
precision. Convert scales by attribute (`.tai`, `.tt`, `.tdb`) and formats by
attribute (`.jd`, `.mjd`, `.iso`, `.unix`). Do arithmetic with `TimeDelta` or
`Quantity`; compute `sidereal_time` and `light_travel_time` for barycentric/
heliocentric corrections (needs `location`).

### WCS, modeling, viz, stats — `astropy.wcs` and friends → `references/wcs-and-modules.md`
`WCS(header)` then `pixel_to_world` / `world_to_pixel`. Also covers `nddata`
(`NDData`/`CCDData`), `modeling` (Gaussian/polynomial fitting with
`fitting.TRFLSQFitter`), `visualization` (`simple_norm`, `ZScaleInterval`),
`constants`, `convolution` kernels, and robust `stats` (`sigma_clipped_stats`).

## Cross-Cutting Practices

- **Always carry units.** Attach them at the boundary; let `.to()` and
  equivalencies do conversions rather than hardcoding factors.
- **Vectorize.** Pass arrays to `SkyCoord`, `Time`, and cosmology methods; a
  Python `for` loop over scalars is often 100-1000x slower.
- **Context-manage FITS.** `with fits.open(...)` guarantees the file (and memory
  map) is released; use `mode="update"` to write in place.
- **Be explicit about scale and frame.** State `scale=` on `Time` and `frame=`
  on `SkyCoord`; a wrong scale/frame is a silent, plausible-looking error.
- **Prefer `QTable`** when columns have units, and keep raw/unmodified data
  before destructive operations.

## Related Skills

`matplotlib` / `seaborn` (plot arrays extracted from FITS/tables/cosmology),
`dask` (out-of-core arrays behind large FITS writes), `polars` (fast tabular ETL
when you don't need unit-aware columns), `scikit-learn` / `pymc` /
`statsmodels` (modeling beyond analytic fits), `networkx` (graph analysis on
matched catalogs).

## Reference Index

- `references/units.md` — quantities, conversions, equivalencies, constants.
- `references/coordinates.md` — frames, transforms, separations, catalog matching.
- `references/cosmology.md` — models, distances, times, densities, `z_at_value`.
- `references/fits.md` — HDUs, headers, image/table data, create/edit, remote.
- `references/tables.md` — creation, I/O, filter/sort/join/group, masking.
- `references/time.md` — formats, scales, arithmetic, sidereal/barycentric.
- `references/wcs-and-modules.md` — WCS, NDData/CCDData, modeling, viz, stats.

## Resources

- Documentation: https://docs.astropy.org/en/stable/
- Tutorials: https://learn.astropy.org/
- Source: https://github.com/astropy/astropy
