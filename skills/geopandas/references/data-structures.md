# Data Structures

GeoPandas adds two structures on top of pandas: `GeoSeries` (a column of
geometries) and `GeoDataFrame` (a table with an active geometry column and a
CRS).

## GeoSeries

A `GeoSeries` holds one shapely geometry per row and exposes vectorized spatial
methods and properties.

```python
import geopandas as gpd
from shapely.geometry import Point, Polygon

points = gpd.GeoSeries([Point(1, 1), Point(2, 2), Point(3, 3)])

points.area      # 0.0 for points; polygon areas otherwise
points.length    # perimeter (polygons) / length (lines)
points.bounds    # per-geometry [minx, miny, maxx, maxy] as a DataFrame
```

## GeoDataFrame

A `GeoDataFrame` is a pandas `DataFrame` with a geometry column and a CRS.

```python
from shapely.geometry import Point
import pandas as pd

# From a dict that already contains geometries
gdf = gpd.GeoDataFrame(
    {"name": ["A", "B"], "value": [100, 200],
     "geometry": [Point(1, 1), Point(2, 2)]},
    crs="EPSG:4326",
)

# From a plain DataFrame of coordinates
df = pd.DataFrame({"x": [1, 2, 3], "y": [1, 2, 3], "name": ["A", "B", "C"]})
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y),
                       crs="EPSG:4326")
```

## Key Attributes

| Attribute | Meaning |
|-----------|---------|
| `.geometry` | the active geometry column (a GeoSeries) |
| `.crs` | coordinate reference system (a `pyproj.CRS` or `None`) |
| `.bounds` | per-row bounding box (DataFrame of minx/miny/maxx/maxy) |
| `.total_bounds` | one bounding box for the whole frame (array) |
| `.geometry.name` | name of the active geometry column |

## Multiple Geometry Columns

A GeoDataFrame can hold several geometry columns (e.g. polygon boundary and its
centroid). Only one is "active" at a time; spatial operations act on the active
column.

```python
gdf["centroids"] = gdf.geometry.centroid   # add a second geometry column
gdf = gdf.set_geometry("centroids")        # make it active
gdf.geometry.name                          # 'centroids'
```

## Indexing and Selection

Standard pandas indexing works, and boolean masks can use spatial properties.

```python
gdf.loc[0]                      # row by label
gdf.iloc[0:5]                   # rows by position
gdf[gdf.geometry.area > 100]    # boolean spatial mask
gdf[["name", "geometry"]]       # column subset (keep geometry to stay a GDF)
```

Dropping the geometry column turns the object back into a plain pandas
DataFrame, so keep `"geometry"` in any column subset you want to remain spatial.
