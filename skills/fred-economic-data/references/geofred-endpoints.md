# GeoFRED — Regional Data & Maps

GeoFRED serves regional economic values (state / county / MSA / Fed district /
country) plus GeoJSON boundaries for choropleth mapping. Base URL is **different**
from FRED:

```
https://api.stlouisfed.org/geofred/
```

| Endpoint | Purpose | Required |
|----------|---------|----------|
| `geofred/shapes/file` | GeoJSON boundary shapes | `api_key` (+ `shape`) |
| `geofred/series/group` | Regional metadata for a FRED series | `api_key`, `series_id` |
| `geofred/series/data` | Regional values for a FRED series | `api_key`, `series_id` |
| `geofred/regional/data` | Regional values by series-group ID (most flexible) | `api_key`, `series_group`, `region_type`, `date`, `season`, `units` |

## Region / shape types

`bea`, `msa`, `frb`, `necta`, `state`, `country`, `county`, `censusregion`,
`censusdivision`.

## geofred/regional/data — the flexible one

Required: `api_key`, `series_group`, `region_type`, `date` (YYYY-MM-DD), `season`,
`units`. Optional: `start_date`, `frequency`, `transformation` (default `lin`),
`aggregation_method` (`avg`/`sum`/`eop`), `file_type`.

**Seasonality codes:** `SA` (seasonally adjusted), `NSA` (not), `SSA` (smoothed SA),
`SAAR`, `NSAAR`.

```python
data = fred_get(  # helper from api-basics.md, but note the geofred/ base path
    "geofred/regional/data",
    series_group="1220",        # Unemployment Rate
    region_type="state", date="2023-01-01",
    units="Percent", frequency="a", season="NSA",
)
rows = data["data"]["2023-01-01"]   # [{region, code, value, series_id}, ...]
```

> The helper in `api-basics.md` prefixes `fred/` in its examples; for GeoFRED pass
> the full path `geofred/...` — the base host is the same
> (`https://api.stlouisfed.org`).

Response shape: `meta` (title, region, seasonality, units, frequency) plus `data`
keyed by date, each holding a list of `{region, code, value, series_id}`. `code` is
the FIPS code you join to shape features.

**Common series groups:** 882 Per Capita Personal Income · 1220 Unemployment Rate ·
1223 Total Nonfarm Employment · 1282 Real GDP · 1253 House Price Index · 1005
Population.

## geofred/series/data and /series/group

Start from a FRED series ID that has a regional counterpart. `series/group` returns
the group metadata (`series_group`, `region_type`, `season`, `units`, `frequency`,
`min_date`, `max_date`); `series/data` returns the regional values (params: `date`,
`start_date`). Note XML is unavailable for county-level data — use `file_type=json`.

## geofred/shapes/file — boundaries

Pass `shape=state` (or any region type) to get a GeoJSON `FeatureCollection`. Each
feature's `properties.fips` is the join key to the `code` field in regional data.

## Choropleth pattern (state unemployment)

```python
import pandas as pd, plotly.express as px

shapes = fred_get("geofred/shapes/file", shape="state")   # GeoJSON
data = fred_get("geofred/regional/data", series_group="1220",
                region_type="state", date="2023-01-01",
                units="Percent", frequency="a", season="NSA")

df = pd.DataFrame(data["data"]["2023-01-01"])
df["value"] = pd.to_numeric(df["value"], errors="coerce")

fig = px.choropleth(
    df, geojson=shapes, locations="code",
    featureidkey="properties.fips", color="value",
    hover_name="region", scope="usa",
    color_continuous_scale="RdYlGn_r",
    title="Unemployment Rate by State (2023)",
)
fig.show()
```

For heavier geospatial work (joins, projections, spatial ops) hand the GeoJSON and
values to the `geopandas` sibling skill.
