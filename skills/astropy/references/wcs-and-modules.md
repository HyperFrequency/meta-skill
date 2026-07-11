# WCS and Other Modules

Covers `astropy.wcs`, `nddata`, `modeling`, `visualization`, `constants`,
`convolution`, `stats`, and a few utilities.

## World Coordinate System (`astropy.wcs`)

Transform between image pixel coordinates and world coordinates (usually
celestial).

```python
from astropy.wcs import WCS
from astropy.io import fits

with fits.open("image.fits") as hdul:
    wcs = WCS(hdul[0].header)
```

Pixel to world (returns a `SkyCoord`) and back:

```python
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

world = wcs.pixel_to_world(100, 200)          # -> SkyCoord
world = wcs.pixel_to_world(np.array([100, 200]), np.array([150, 250]))

coord = SkyCoord(ra=10.5*u.deg, dec=41.2*u.deg)
x, y = wcs.world_to_pixel(coord)
```

Inspect and build:

```python
print(wcs)
wcs.wcs.crpix   # reference pixel
wcs.wcs.crval   # world coords at reference pixel
wcs.wcs.ctype   # e.g. ['RA---TAN', 'DEC--TAN']
wcs.calc_footprint()   # corner sky coordinates

# Pixel scale lives in astropy.wcs.utils (NOT a method on WCS):
from astropy.wcs.utils import proj_plane_pixel_scales
scales = proj_plane_pixel_scales(wcs)   # degrees/pixel per axis

wcs = WCS(naxis=2)
wcs.wcs.crpix = [512.0, 512.0]
wcs.wcs.crval = [10.5, 41.2]
wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
wcs.wcs.cdelt = [-0.0001, 0.0001]
wcs.wcs.cunit = ["deg", "deg"]
```

## NDData / CCDData (`astropy.nddata`)

Containers that keep data together with unit, uncertainty, mask, and WCS.

```python
from astropy.nddata import NDData, CCDData, StdDevUncertainty
import numpy as np, astropy.units as u

data = np.random.random((100, 100))
NDData(data, unit=u.electron/u.s,
       uncertainty=StdDevUncertainty(np.sqrt(data)),
       mask=data < 0.1, wcs=wcs)

ccd = CCDData.read("image.fits", unit=u.adu)
ccd.write("out.fits", overwrite=True)
```

## Modeling (`astropy.modeling`)

Analytic models plus fitters. Note the parameter is `amplitude` (not `amp`).

```python
from astropy.modeling import models, fitting
import numpy as np

g = models.Gaussian1D(amplitude=10, mean=5, stddev=1)
models.Gaussian2D(amplitude=10, x_mean=50, y_mean=50, x_stddev=5, y_stddev=3)
models.Polynomial1D(degree=3)
models.PowerLaw1D(amplitude=10, x_0=1, alpha=2)

x = np.linspace(0, 10, 100)
y = g(x) + np.random.normal(0, 0.5, x.shape)
fitter = fitting.TRFLSQFitter()          # robust default; LevMarLSQFitter is the classic
fit = fitter(models.Gaussian1D(amplitude=8, mean=4, stddev=1.5), x, y)
fit.amplitude.value, fit.mean.value, fit.stddev.value
```

Combine models: `+` adds outputs, `|` pipes (composes) them:

```python
double = models.Gaussian1D(amplitude=5, mean=3, stddev=1) + \
         models.Gaussian1D(amplitude=8, mean=7, stddev=1.5)
piped = models.Gaussian1D(amplitude=10, mean=5, stddev=1) | models.Scale(factor=2)
```

## Visualization (`astropy.visualization`)

Normalization and stretching for image display — pair with `matplotlib`
(the plotting itself is not Astropy's job).

```python
import matplotlib.pyplot as plt
from astropy.visualization import (simple_norm, ImageNormalize,
                                   ZScaleInterval, AsinhStretch, PercentileInterval)

norm = simple_norm(data, "sqrt", percent=99)
plt.imshow(data, norm=norm, cmap="gray", origin="lower")

norm = ImageNormalize(data, interval=ZScaleInterval(), stretch=AsinhStretch())
vmin, vmax = PercentileInterval(90).get_limits(data)
```

## Constants (`astropy.constants`)

```python
from astropy import constants as const
import astropy.units as u, numpy as np

const.c, const.G, const.M_sun, const.R_sun, const.L_sun, const.au, const.pc
const.h, const.hbar, const.k_B, const.m_e, const.m_p, const.e, const.N_A

r_s = 2 * const.G * (10*const.M_sun) / const.c**2      # Schwarzschild radius
r_s.to(u.km)
v_esc = np.sqrt(2 * const.G * const.M_earth / const.R_earth).to(u.km/u.s)
```

## Convolution (`astropy.convolution`)

```python
from astropy.convolution import Gaussian2DKernel, convolve, convolve_fft

smoothed = convolve(data, Gaussian2DKernel(x_stddev=2))
smoothed = convolve_fft(data, Gaussian2DKernel(x_stddev=2),
                        nan_treatment="interpolate")   # NaN-aware
```

Astropy's `convolve` interpolates over NaNs, unlike `scipy.ndimage`.

## Statistics (`astropy.stats`)

```python
from astropy.stats import (sigma_clip, sigma_clipped_stats,
                           mad_std, biweight_location, biweight_scale)

clipped = sigma_clip(data, sigma=3, maxiters=5)
mean, median, std = sigma_clipped_stats(data, sigma=3.0)
mad_std(data); biweight_location(data); biweight_scale(data)
```

## Utilities

```python
from astropy.utils.data import download_file
local = download_file("https://example.com/data.fits", cache=True)
```
