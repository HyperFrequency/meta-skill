# Geometric Operations

GeoPandas exposes shapely's geometry engine as vectorized GeoSeries methods.
Constructive ops return new geometries; predicates return boolean Series;
property accessors return plain pandas Series/DataFrames.

## Constructive Operations

### Buffer

All points within a distance of each geometry (distance is in CRS units — use a
projected CRS for meters).

```python
buffered = gdf.geometry.buffer(10)                 # grow by 10 units
eroded   = gdf.geometry.buffer(-5)                 # shrink (negative buffer)
smooth   = gdf.geometry.buffer(10, resolution=16)  # rounder caps
```

### Other constructive methods

```python
gdf.geometry.boundary                      # lower-dim boundary
gdf.geometry.centroid                      # center point
gdf.geometry.convex_hull                   # smallest convex polygon
gdf.geometry.concave_hull(ratio=0.5)       # 0 = convex hull, 1 = most concave
gdf.geometry.envelope                      # axis-aligned bounding rectangle
gdf.geometry.simplify(tolerance=10, preserve_topology=True)  # Douglas-Peucker
gdf.geometry.segmentize(max_segment_length=5)   # densify vertices
gdf.geometry.union_all()                   # dissolve all rows into one geometry
```

Use `preserve_topology=True` on `simplify` to avoid introducing
self-intersections.

## Affine Transformations

```python
gdf.geometry.rotate(45, origin="center")            # degrees; or origin=(x, y)
gdf.geometry.scale(xfact=2.0, yfact=2.0, origin="center")
gdf.geometry.translate(xoff=100, yoff=50)
gdf.geometry.skew(xs=15, ys=0, origin="center")
gdf.geometry.affine_transform([a, b, d, e, xoff, yoff])  # 6-parameter matrix
```

## Geometric Properties

```python
gdf.geometry.area          # per-geometry area (CRS units squared)
gdf.geometry.length        # perimeter / line length
gdf.geometry.bounds        # DataFrame: minx, miny, maxx, maxy per row
gdf.geometry.total_bounds  # array: [minx, miny, maxx, maxy] for the frame
gdf.geometry.geom_type     # 'Point' | 'Polygon' | ...
gdf.geometry.is_valid      # boolean Series (False = broken geometry)
gdf.geometry.is_empty      # boolean Series
```

Repair invalid geometries before overlays with `gdf.geometry.make_valid()`.

## Binary Predicates

Element-wise relationship tests returning boolean Series.

```python
gdf1.geometry.within(other)
gdf1.geometry.contains(other)
gdf1.geometry.intersects(other)
gdf1.geometry.touches(other)
gdf1.geometry.crosses(other)
gdf1.geometry.overlaps(other)
gdf1.geometry.covers(other)
gdf1.geometry.covered_by(other)
```

`other` may be a single shapely geometry (compared against every row) or an
aligned GeoSeries (compared row by row).

## Point Extraction

```python
gdf.geometry.representative_point()          # a point guaranteed inside
line_gdf.geometry.interpolate(10)            # point 10 units along the line
line_gdf.geometry.interpolate(0.5, normalized=True)  # midpoint (fraction 0-1)
```

## Delaunay Triangulation

```python
triangles = gdf.geometry.delaunay_triangles()
```

For measuring distances between geometries and computing accurate areas/lengths,
see [spatial-analysis.md](spatial-analysis.md) and
[crs-management.md](crs-management.md).
