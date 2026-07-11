# Reading and Writing Spatial Data

GeoPandas reads and writes vector formats through a GDAL/OGR backend (pyogrio by
default, or fiona). Columnar (Parquet/Feather) and PostGIS paths are separate.

## Reading Files

```python
import geopandas as gpd

gdf = gpd.read_file("data.shp")
gdf = gpd.read_file("data.geojson")
gdf = gpd.read_file("data.gpkg")
gdf = gpd.read_file("data.zip")                         # zipped shapefile
gdf = gpd.read_file("https://example.com/data.geojson") # remote URL
```

### Arrow acceleration

Pass `use_arrow=True` for roughly 2-4x faster reads/writes (requires
`pyarrow`).

```python
gdf = gpd.read_file("data.gpkg", use_arrow=True)
```

### Filter during read

Load only what you need instead of reading the whole file then subsetting.

```python
gdf = gpd.read_file("data.gpkg", rows=100)                 # first N rows
gdf = gpd.read_file("data.gpkg", rows=slice(10, 20))       # a row range
gdf = gpd.read_file("data.gpkg", columns=["name", "pop"])  # column subset
gdf = gpd.read_file("data.gpkg", bbox=(xmin, ymin, xmax, ymax))  # spatial box
gdf = gpd.read_file("data.gpkg", mask=some_polygon)        # spatial mask
gdf = gpd.read_file("data.gpkg", where="pop > 1000000")    # SQL WHERE
df  = gpd.read_file("data.gpkg", ignore_geometry=True)     # -> pandas DataFrame
```

`bbox`/`mask` use the file's spatial index where available, so they are far
cheaper than reading everything.

## Writing Files

```python
gdf.to_file("output.shp")                              # Shapefile
gdf.to_file("output.geojson", driver="GeoJSON")
gdf.to_file("output.gpkg", layer="layer1", driver="GPKG")  # multi-layer capable
gdf.to_file("output.gpkg", use_arrow=True)
```

List available drivers:

```python
import pyogrio
pyogrio.list_drivers()
```

Common formats: Shapefile, GeoJSON, GeoPackage (GPKG), KML, MapInfo, CSV (with
WKT geometry). **Prefer GeoPackage or GeoParquet** for new work — Shapefile
truncates field names to 10 characters and has no real multi-layer support.

## Parquet and Feather

Columnar formats that preserve the CRS and support multiple geometry columns,
with faster I/O and better compression than legacy formats.

```python
gdf.to_parquet("data.parquet")
gdf.to_feather("data.feather")

gdf = gpd.read_parquet("data.parquet")
gdf = gpd.read_feather("data.feather")
```

## PostGIS

```python
from sqlalchemy import create_engine
engine = create_engine("postgresql://user:password@host:port/database")

# Read
gdf = gpd.read_postgis("SELECT * FROM roads", con=engine, geom_col="geom")
gdf = gpd.read_postgis(
    "SELECT * FROM cities WHERE pop > 100000", con=engine, geom_col="geom"
)

# Write
gdf.to_postgis("roads", con=engine, if_exists="replace")  # or 'append' / 'fail'
```

Requires `psycopg2` (or `psycopg`) plus `geoalchemy2`. Push filtering into the
SQL `WHERE` clause so the database does the work, not Python.

## File-like Objects

```python
from io import StringIO

with open("data.geojson") as f:
    gdf = gpd.read_file(f)

gdf = gpd.read_file(StringIO('{"type": "FeatureCollection", ...}'))
```

## Remote / Cloud Storage (fsspec)

```python
gdf = gpd.read_file("s3://bucket/data.gpkg")        # S3
gdf = gpd.read_file("az://container/data.gpkg")     # Azure Blob
gdf = gpd.read_file("https://example.com/x.geojson")# HTTP(S)
```

Cloud paths require the matching fsspec backend (e.g. `s3fs`, `adlfs`).
