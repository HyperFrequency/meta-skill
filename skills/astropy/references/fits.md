# FITS I/O (`astropy.io.fits`)

Read, write, and edit FITS (Flexible Image Transport System) files. A FITS file
is an `HDUList` of Header Data Units (HDUs); each HDU has a `.header` and,
usually, `.data`.

## Opening files

Always use a context manager so the file and its memory map are released:

```python
from astropy.io import fits

with fits.open("image.fits") as hdul:
    hdul.info()          # print the HDU structure
    data = hdul[1].data  # NumPy array
```

Modes: `readonly` (default), `update` (edit in place), `append` (add HDUs).
`memmap=True` (default) loads data chunks lazily — essential for large files.

Remote/cloud files stream with fsspec; `.section` fetches a cutout without
downloading the whole array:

```python
with fits.open("s3://bucket/image.fits", use_fsspec=True,
               fsspec_kwargs={"anon": True}) as hdul:
    cutout = hdul[1].section[100:200, 100:200]
```

## HDU structure

`hdul[0]` is the primary HDU (always present); `hdul[1:]` are extensions
(image or table). `.info()` prints name, type, and dimensions per HDU.

```python
hdul[0]            # by index
hdul["SCI"]        # by EXTNAME
hdul["SCI", 2]     # by name + version
```

## Headers

The header behaves like an ordered, case-insensitive dict of "cards"
(80-character keyword/value/comment records):

```python
hdr = hdul[0].header
hdr["EXPTIME"]                     # read
hdr.get("FILTER", "Unknown")       # read with default
hdr["OBSERVER"] = "Edwin Hubble"   # write
hdr["OBSERVER"] = ("Edwin Hubble", "Name of observer")  # value + comment
hdr.insert(5, ("NEWKEY", 1.0, "comment"))
hdr["HISTORY"] = "Reprocessed 2025-01-15"
del hdr["OLDKEY"]

for card in hdr.cards:
    print(card.keyword, card.value, card.comment)
```

Do not edit structural keywords (`SIMPLE`, `BITPIX`, `NAXIS*`, ...) by hand.

## Image data

`.data` is a NumPy array — use ordinary NumPy on it. Note FITS is row-major with
`data[y, x]` indexing:

```python
data = hdul[1].data
data.shape, data.dtype
region = data[100:200, 300:400]
data[data < 0] = 0                    # in-place edit
cutout = hdul[1].section[500:600, 700:800]   # read a slice without full load
```

## Creating files

```python
import numpy as np

hdu = fits.PrimaryHDU(data=np.random.random((100, 100)))
hdu.header["OBJECT"] = "Test Image"
hdu.writeto("out.fits", overwrite=True)

# Multi-extension
primary = fits.PrimaryHDU()
sci = fits.ImageHDU(data=np.ones((100, 100)), name="SCI")
err = fits.ImageHDU(data=np.ones((100, 100))*0.1, name="ERR")
fits.HDUList([primary, sci, err]).writeto("multi.fits", overwrite=True)
```

## Table HDUs

Read columns by name; build tables from `fits.Column`s:

```python
with fits.open("catalog.fits") as hdul:
    tbl = hdul[1].data          # FITS_rec (structured array)
    ra = tbl["RA"]
    hdul[1].columns.names

col_id = fits.Column(name="ID", format="K", array=[1, 2, 3])       # 64-bit int
col_ra = fits.Column(name="RA", format="D", array=[10.5, 11.2, 12.3])  # 64-bit float
col_nm = fits.Column(name="Name", format="20A", array=["a", "b", "c"]) # 20-char str
fits.BinTableHDU.from_columns([col_id, col_ra, col_nm]).writeto(
    "cat.fits", overwrite=True)
```

Column format codes: `L` logical, `B` byte, `I` int16, `J` int32, `K` int64,
`E` float32, `D` float64, `nA` n-char string.

For most table work, `astropy.table.Table.read(...)` is friendlier than the raw
`FITS_rec` — see `references/tables.md`.

## Editing existing files

```python
with fits.open("file.fits", mode="update") as hdul:
    hdul[0].header["NEWKEY"] = "value"
    hdul[1].data[100, 100] = 999          # saved on context exit

with fits.open("file.fits", mode="append") as hdul:
    hdul.append(fits.ImageHDU(data=np.zeros((50, 50)), name="NEW"))
```

## Convenience one-shots

```python
data = fits.getdata("f.fits", ext=1)
hdr = fits.getheader("f.fits", ext=0)
data, hdr = fits.getdata("f.fits", ext=1, header=True)
fits.getval("f.fits", "EXPTIME", ext=0)
fits.setval("f.fits", "NEWKEY", value="x", ext=0)
fits.writeto("out.fits", data, hdr, overwrite=True)
fits.info("f.fits")
fits.printdiff("a.fits", "b.fits")     # report differences
```

## Non-standard and large files

```python
hdul = fits.open("bad.fits", ignore_missing_end=True)
hdul.verify("fix")                     # attempt to repair violations

import dask.array as da                # write huge arrays lazily
fits.writeto("big.fits", da.random.random((10000, 10000)))
```
