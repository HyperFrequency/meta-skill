# Spatial Analysis

Combine and aggregate datasets by attribute or by location. Every two-frame
operation here requires a **matching CRS** — reproject first (see
[crs-management.md](crs-management.md)).

## Attribute Joins

Non-spatial merge on a shared column. Call `merge` on the GeoDataFrame so the
result keeps its geometry.

```python
result = gdf.merge(df, on="key", how="left")   # gdf.merge(...) stays a GDF
# df.merge(gdf, ...) returns a plain DataFrame — geometry is lost.
```

## Spatial Joins (`sjoin`)

Join rows whose geometries satisfy a spatial predicate.

```python
joined = gpd.sjoin(gdf1, gdf2, how="inner", predicate="intersects")

# predicates: 'intersects' (default), 'contains', 'within',
#             'touches', 'crosses', 'overlaps'
joined = gpd.sjoin(points, polygons, predicate="within")
```

`how` controls which side's geometry and index survive:

| how | keeps |
|-----|-------|
| `left` | left frame's rows, index, and geometry |
| `right` | right frame's rows, index, and geometry |
| `inner` | only matching pairs; left geometry retained |

The matched right-side index arrives as an `index_right` column — group on it to
aggregate.

## Nearest Joins (`sjoin_nearest`)

Join each left geometry to its nearest right geometry.

```python
nearest = gpd.sjoin_nearest(gdf1, gdf2)
nearest = gpd.sjoin_nearest(gdf1, gdf2, distance_col="dist")  # record distance
nearest = gpd.sjoin_nearest(gdf1, gdf2, max_distance=1000)    # cap search radius
```

Always set `max_distance` when you can — it prunes the search and greatly
improves performance on large frames.

## Overlay (set operations)

Set-theoretic combination of two polygon layers; the result carries attributes
from both inputs.

```python
gpd.overlay(gdf1, gdf2, how="intersection")        # areas in both
gpd.overlay(gdf1, gdf2, how="union")               # all areas, split
gpd.overlay(gdf1, gdf2, how="difference")          # in gdf1 but not gdf2
gpd.overlay(gdf1, gdf2, how="symmetric_difference")# in either but not both
gpd.overlay(gdf1, gdf2, how="identity")            # intersection + difference
```

## Dissolve (aggregate geometries)

Merge geometries that share an attribute value, aggregating the other columns.

```python
gdf.dissolve(by="region")                          # union geometries per region
gdf.dissolve(by="region", aggfunc="sum")           # sum numeric columns
gdf.dissolve(by="region", aggfunc={"pop": "sum", "area": "mean"})
gdf.dissolve()                                      # everything into one row
gdf.dissolve(by="region", as_index=False)          # keep 'region' as a column
```

## Clipping

Cut geometries to the boundary of another geometry or frame.

```python
clipped = gpd.clip(gdf, boundary_polygon)
clipped = gpd.clip(gdf, boundary_gdf)
```

## Appending / Concatenating

```python
import pandas as pd
combined = pd.concat([gdf1, gdf2], ignore_index=True)  # CRS must match
```

## Spatial Index

GeoPandas builds an R-tree automatically for joins/overlays. Query it directly
for custom filtering.

```python
sindex = gdf.sindex
idx = list(sindex.intersection((xmin, ymin, xmax, ymax)))  # bbox candidates
hits = gdf.iloc[idx]

idx = list(sindex.query(polygon))                          # geometry candidates
hits = gdf.iloc[idx]
```

The index returns *candidate* matches (bounding-box level); confirm with an
exact predicate on the candidates.

## Distance, Area, and Length

Reproject to a projected CRS first so results are in meters.

```python
gdf_m = gdf.to_crs(gdf.estimate_utm_crs())
gdf_m.geometry.area                 # square meters
gdf_m.geometry.length               # meters

d = gdf_m.geometry.distance(other)  # row-wise, or vs a single geometry
min_dist = gdf_m.geometry.distance(some_point).min()
```
