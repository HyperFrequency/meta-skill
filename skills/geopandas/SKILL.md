---
name: geopandas
version: 0.1.0
description: >-
  GeoPandas extends pandas with spatial types (shapely geometries + a pyproj
  CRS) so you can read, analyze, and write vector geographic data — shapefiles,
  GeoJSON, GeoPackage, PostGIS, GeoParquet. Use it for spatial joins, overlay
  set operations, dissolve/aggregate by attribute, buffering and other
  constructive geometry ops, coordinate reprojection, area/distance
  measurement, clipping, and static or interactive choropleth maps. Reach for it
  whenever a task involves reading, transforming, or writing vector spatial data,
  or joining tabular records to geometry by location. Do NOT use it for
  raster/gridded data (use rasterio/rioxarray), pure non-spatial tabular ETL (use
  pandas or `polars`), graph/network routing (use `networkx`), or datasets far
  larger than RAM (chunk with dask-geopandas / `dask`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (GeoPandas)"
---

# GeoPandas

## Overview

GeoPandas puts a geometry column into a pandas DataFrame. Each row carries a
shapely geometry (point, line, polygon, or their multi-variants), the frame
carries a single coordinate reference system (CRS) via pyproj, and every pandas
operation you already know still works. On top of that you get spatial joins,
set-theoretic overlays, constructive geometry (buffer, simplify, centroid),
reprojection, and matplotlib/folium plotting.

This skill is a **router**. It gives you the object model, the install path, a
quick start, and the boundaries of what GeoPandas is for, then delegates the
full API surface and worked recipes to `references/`.

## When to Use This Skill

- Reading or writing vector formats: Shapefile, GeoJSON, GeoPackage (GPKG),
  GeoParquet/Feather, KML, PostGIS, or cloud-hosted files.
- Joining two datasets **by location** (points-in-polygons, nearest neighbor).
- Combining polygon layers with set operations (intersection, union, difference).
- Aggregating geometries by an attribute (`dissolve`) or clipping to a boundary.
- Constructive geometry: buffer, simplify, centroid, convex/concave hull.
- Reprojecting between coordinate systems, or measuring area/length/distance.
- Making choropleth maps (static via matplotlib, interactive via folium).

## When NOT to Use This Skill

- **Raster / gridded data** (satellite imagery, DEMs, NetCDF) — use `rasterio`,
  `rioxarray`, or `xarray`. GeoPandas is vector-only.
- **Pure tabular ETL** with no geometry — use pandas or `polars`.
- **Graph/network routing** (shortest path on a road network) — build a graph
  with `networkx` (or osmnx) from the geometries; GeoPandas does not do routing.
- **Larger-than-RAM** spatial data — GeoPandas loads everything into memory.
  Partition with dask-geopandas or a PostGIS server-side query instead.
- **Heavy per-vertex geometry math** on millions of features — drop to shapely
  arrays / `shapely.vectorized` or a spatial database.

## Installation

```bash
uv pip install geopandas
```

Optional extras, installed only when a workflow needs them:

```bash
uv pip install pyarrow        # 2-4x faster file I/O (use_arrow=True)
uv pip install mapclassify    # classification schemes for choropleths
uv pip install folium         # interactive .explore() maps
uv pip install contextily     # basemap tiles under a plot
uv pip install cartopy        # cartographic projections
uv pip install psycopg2 geoalchemy2   # PostGIS read/write
```

## Quick Start

```python
import geopandas as gpd

gdf = gpd.read_file("data.geojson")   # -> GeoDataFrame

gdf.head()                 # tabular preview, geometry in last column
gdf.crs                    # coordinate reference system (may be None)
gdf.geometry.geom_type     # 'Point' | 'Polygon' | ...
gdf.total_bounds           # [minx, miny, maxx, maxy] of the whole frame

# Reproject before measuring: geographic degrees are not meters.
gdf_m = gdf.to_crs("EPSG:3857")
gdf_m["area_m2"] = gdf_m.geometry.area

gdf.plot(column="area_m2", cmap="YlOrRd", legend=True)   # choropleth
gdf.to_file("output.gpkg")                               # write GeoPackage
```

## Core Concepts

- **GeoSeries** — a column of geometries with vectorized spatial methods
  (`.area`, `.buffer()`, `.centroid`, predicates).
- **GeoDataFrame** — a pandas DataFrame with one active geometry column plus a
  CRS. It can hold several geometry columns; `set_geometry()` picks the active
  one that operations act on.
- **CRS** — the frame's coordinate system. **Every** area, distance, join, or
  overlay depends on it. Two rules that prevent most bugs: (1) match CRS before
  any join/overlay, (2) use a *projected* CRS (meters) before measuring area or
  distance — never raw lat/lon degrees.

Object model details, active-geometry handling, and pandas-style indexing live
in [references/data-structures.md](references/data-structures.md).

## Capabilities (routed to references)

### Reading and writing data

`read_file` / `to_file` cover Shapefile, GeoJSON, GPKG, KML and more; filter at
read time with `bbox`, `mask`, `rows`, `columns`, or a SQL `where`; use
`read_parquet`/`to_parquet` for fast columnar I/O; `read_postgis`/`to_postgis`
for databases; and pass `use_arrow=True` for a 2-4x speedup. Full format list,
cloud/fsspec paths, and PostGIS engine setup:
[references/data-io.md](references/data-io.md).

### Coordinate reference systems

`set_crs` (label coordinates whose CRS metadata is missing — no transform) vs
`to_crs` (actually reproject). Includes accepted CRS formats, common EPSG codes,
`estimate_utm_crs()`, and how to pick equal-area vs conformal projections:
[references/crs-management.md](references/crs-management.md).

### Geometric operations

Constructive ops (`buffer`, `simplify`, `centroid`, `convex_hull`,
`concave_hull`, `union_all`), affine transforms (rotate/scale/translate/skew),
geometric properties (`area`, `length`, `bounds`, `is_valid`), and binary
predicates (`within`, `contains`, `intersects`):
[references/geometric-operations.md](references/geometric-operations.md).

### Spatial analysis

`sjoin` (predicate joins), `sjoin_nearest` (with `max_distance`/`distance_col`),
`overlay` (intersection/union/difference/…), `dissolve` (aggregate by attribute),
`clip`, the automatic spatial index (`.sindex`), and distance calculations:
[references/spatial-analysis.md](references/spatial-analysis.md).

### Visualization

Static maps with `.plot()` (choropleths, classification schemes, multi-layer,
missing-data styling), interactive maps with `.explore()`, plus contextily
basemaps and cartopy projections:
[references/visualization.md](references/visualization.md).

## Common Workflows

### Load → reproject → measure → export

```python
gdf = gpd.read_file("parcels.shp")
gdf = gdf.to_crs(gdf.estimate_utm_crs())   # local UTM = accurate meters
gdf["area_m2"] = gdf.geometry.area
gdf.to_file("parcels_measured.gpkg", layer="parcels", use_arrow=True)
```

### Points-in-polygons, then aggregate

```python
# Both frames MUST share a CRS before the join.
pts = pts.to_crs(zones.crs)

joined = gpd.sjoin(pts, zones, how="inner", predicate="within")
counts = joined.groupby("index_right").size().rename("n")
zones  = zones.merge(counts, left_index=True, right_index=True)  # keep geometry
```

Call `merge` on the **GeoDataFrame** (`zones.merge(...)`) — calling it on a plain
DataFrame drops the geometry and returns a DataFrame.

## Failure Modes and Gotchas

- **Area/length in degrees.** If `.area` returns tiny numbers, you are in a
  geographic CRS (EPSG:4326). Reproject to a projected CRS first.
- **CRS mismatch on join/overlay/concat.** These raise or silently misalign
  unless both frames share a CRS — reproject one to the other's `.crs`.
- **`set_crs` vs `to_crs`.** `set_crs` only relabels; it does not move
  coordinates. Reaching for it to "fix" a projection corrupts your data.
- **Invalid geometries.** Self-intersecting polygons break overlays; check
  `gdf.geometry.is_valid` and repair with `gdf.geometry.make_valid()`.
- **Mutating geometry in place.** Assign to a `.copy()` before overwriting the
  geometry column so you do not clobber the source frame.
- **Shapefile limits.** Column names truncate to 10 chars and there is no true
  multi-layer support — prefer **GeoPackage** or GeoParquet for new work.

## Reference Files

- [references/data-structures.md](references/data-structures.md) — GeoSeries,
  GeoDataFrame, active geometry, indexing.
- [references/data-io.md](references/data-io.md) — reading/writing formats,
  Arrow, filtered reads, Parquet, PostGIS, cloud storage.
- [references/crs-management.md](references/crs-management.md) — set vs reproject,
  EPSG codes, projection choice, UTM estimation.
- [references/geometric-operations.md](references/geometric-operations.md) —
  constructive ops, affine transforms, properties, predicates.
- [references/spatial-analysis.md](references/spatial-analysis.md) — joins,
  overlay, dissolve, clip, spatial index, distance.
- [references/visualization.md](references/visualization.md) — plotting,
  choropleths, interactive maps, basemaps, cartopy.

Related skills: `polars` and pandas for the non-spatial tabular layer,
`networkx` for graph routing on the geometries, `matplotlib` for figure
composition under `.plot()`, and `dask` for out-of-core partitioning.
