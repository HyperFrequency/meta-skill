# Coordinate Reference Systems (CRS)

A CRS defines how the numbers in a geometry map to locations on Earth. Getting
it wrong is the single most common source of silent errors in spatial work.
GeoPandas stores the CRS as a `pyproj.CRS` on `gdf.crs`.

## Inspecting a CRS

```python
print(gdf.crs)                 # human-readable summary
if gdf.crs is None:
    print("No CRS defined")

gdf.crs.to_epsg()              # EPSG code, or None
gdf.crs.to_wkt()               # full WKT2 definition
gdf.crs.is_geographic          # True for lat/lon (degrees)
gdf.crs.is_projected           # True for planar (meters/feet)
```

## Set vs Reproject — the critical distinction

### `set_crs` — label only, no coordinate change

Use when the coordinates are already correct but the metadata is missing.

```python
gdf = gdf.set_crs("EPSG:4326")               # attach a CRS label
gdf = gdf.set_crs("EPSG:4326", allow_override=True)  # replace an existing label
```

This does **not** move any coordinates. Using it to "convert" a projection
corrupts your data.

### `to_crs` — actually reproject

Use to transform coordinates from one system to another.

```python
gdf_web = gdf.to_crs("EPSG:3857")   # to Web Mercator
gdf_web = gdf.to_crs(3857)          # integer EPSG also accepted
gdf2 = gdf2.to_crs(gdf1.crs)        # match another frame before a join
```

## Accepted CRS Inputs

Anything `pyproj.CRS.from_user_input()` understands:

```python
gdf.to_crs(4326)                       # EPSG integer
gdf.to_crs("EPSG:4326")                # authority string (preferred)
gdf.to_crs("ESRI:102003")              # ESRI authority
gdf.to_crs("+proj=longlat +datum=WGS84")   # PROJ string
from pyproj import CRS
gdf.to_crs(CRS.from_epsg(4326))        # pyproj.CRS object
```

Prefer authority strings (`EPSG:xxxx`) or WKT2 — PROJ strings can lose
information.

## Common EPSG Codes

| Code | System | Use |
|------|--------|-----|
| `EPSG:4326` | WGS 84 (lat/lon) | storage, web input, GPS |
| `EPSG:4269` | NAD83 (lat/lon) | US federal data |
| `EPSG:3857` | Web Mercator | web/basemap tiles (distorts area) |
| `EPSG:32633` | UTM Zone 33N | accurate local meters (N hemisphere) |
| `EPSG:32733` | UTM Zone 33S | accurate local meters (S hemisphere) |
| `EPSG:5070` | Albers Equal Area | area calcs, North America |
| `EPSG:3035` | Lambert Azimuthal EA | area calcs, Europe |

## Choosing the Right Projection

- **Area / distance:** use an equal-area or local UTM projection. Never measure
  in geographic degrees.
- **Web maps / tiles:** Web Mercator (`EPSG:3857`) — conformal but area-distorted.
- **Navigation / true distance from a point:** an azimuthal equidistant
  projection (e.g. `ESRI:54032`).

```python
# Wrong: area in square degrees is meaningless
bad = gdf.geometry.area                    # CRS is EPSG:4326

# Right: reproject to a projected CRS first
areas_m2 = gdf.to_crs("EPSG:5070").geometry.area
```

## Estimating a Local UTM Zone

Let GeoPandas pick the best UTM CRS from the data's extent:

```python
utm = gdf.estimate_utm_crs()   # returns a pyproj.CRS
gdf_utm = gdf.to_crs(utm)      # accurate local meters
```

## CRS and Operations

Joins, overlays, and `pd.concat` require both frames to share a CRS — reproject
one to the other first:

```python
result = gpd.sjoin(gdf1, gdf2.to_crs(gdf1.crs))
```

A mismatch raises a `ValueError` (or produces misaligned results in older
versions), so align CRS as the first step of any two-frame operation.

## Transforming Individual Coordinates

For raw coordinate pairs outside a GeoDataFrame:

```python
from pyproj import Transformer
tf = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
x, y = tf.transform(lon, lat)
```
