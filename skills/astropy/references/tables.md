# Tables (`astropy.table`)

`Table` holds heterogeneous columns with metadata and multi-format I/O; `QTable`
makes columns unit-aware (each column is a `Quantity`).

## Creating

```python
from astropy.table import Table, QTable
import astropy.units as u
import numpy as np

Table([[1, 4, 5], [2.0, 5.0, 8.2], ["x", "y", "z"]],
      names=("id", "flux", "name"))                     # from column lists
Table(rows=[(1, 10.5, "A"), (2, 11.2, "B")], names=("id", "value", "name"))
Table(np.random.random((100, 3)), names=["c1", "c2", "c3"])   # 2D array
Table.from_pandas(df)                                   # from a DataFrame

QTable([[1.2, 2.3]*u.Jy, [500, 600]*u.nm], names=("flux", "wavelength"))
```

## Access

```python
t["ra"]                 # Column
t[0]                    # Row
t[10:20]                # new Table (slice)
t["ra"][5]              # cell
t["ra", "dec", "mag"]   # multi-column subset
t.colnames, len(t), t.info, t.meta
```

## Modifying

```python
t["new"] = [1, 2, 3]                  # add column
t["calc"] = t["a"] + t["b"]           # computed column
t.add_column([7, 8, 9], name="ins", index=2)
t.remove_column("old"); t.remove_columns(["a", "b"]); t.keep_columns(["ra", "dec"])
t.rename_column("old", "new")
t.add_row([1, 2.5, "z"])              # slow one at a time; batch when possible
t["flux"][t["flux"] < 0] = np.nan
```

## Sort and filter

```python
t.sort("mag"); t.sort("mag", reverse=True); t.sort(["priority", "mag"])
t[t["mag"] < 18]                              # boolean mask
t[(t["mag"] < 18) & (t["dec"] > 0)]           # combine with & | (parenthesize!)
```

## I/O

`read`/`write` auto-detect format from the extension; override with `format=`.
Supported: FITS, HDF5, ASCII (CSV, ECSV, IPAC, fixed-width, LaTeX), VOTable,
Parquet, ASDF.

```python
t = Table.read("catalog.fits")
t = Table.read("file.fits", hdu=2)
t = Table.read("data.txt", format="ascii")
t.write("out.fits", overwrite=True)
t.write("out.csv", format="ascii.csv", delimiter="|")
t.write("table.tex", format="ascii.latex")
```

Prefer **ECSV** (`.ecsv`) when you need to round-trip units, masks, and metadata
through a text format.

## Combining tables

```python
from astropy.table import vstack, hstack, join

vstack([t1, t2])                      # stack rows (same columns)
hstack([t1, t2])                      # stack columns (same length)
join(t1, t2, keys="id")               # inner join on shared key
join(t1, t2, join_type="left")        # left / right / outer
```

## Group and aggregate

```python
g = t.group_by("filter")
g.groups.aggregate(np.mean)           # per-group means
for grp in g.groups:
    print(grp["filter"][0], np.mean(grp["mag"]))
t.unique(["ra", "dec"])               # distinct rows
```

## Units (QTable)

```python
t = QTable()
t["flux"] = [1.2, 2.3, 3.4]*u.Jy
t["wavelength"] = [500, 600, 700]*u.nm
t["flux"].to(u.mJy)
t["freq"] = t["wavelength"].to(u.Hz, equivalencies=u.spectral())
```

## Missing data

```python
from astropy.table import MaskedColumn
t = Table([MaskedColumn([1.2, np.nan, 3.4], mask=[False, True, False])],
          names=["flux"])
t["flux"].filled(0)                   # replace masked with 0
```

## Fast lookup and big tables

```python
t.add_index("id")
t.loc[12345]                          # find row(s) where id == 12345
t.loc[100:200]                        # range query on the index

t = Table.read("huge.fits", memmap=True)   # don't load it all
t[10000:10100]                             # loads only what's accessed
```

## Bridges and display

```python
t.to_pandas(); np.array(t)
print(t); t.show_in_browser(jsviewer=True)
t["flux"].format = "%.3f"
```

## Cross-matching (with coordinates)

```python
from astropy.coordinates import SkyCoord
c1 = SkyCoord(t1["ra"], t1["dec"], unit="deg")
c2 = SkyCoord(t2["ra"], t2["dec"], unit="deg")
idx, sep, _ = c1.match_to_catalog_sky(c2)
keep = sep < 1*u.arcsec
t1_matched, t2_matched = t1[keep], t2[idx[keep]]
```

## Performance

- Build from lists/arrays in one shot; repeated `add_row` is O(n^2)-ish.
- Column selection returns a **view** (shares memory); `.copy()` to detach.
- `memmap=True` for FITS tables larger than RAM.
