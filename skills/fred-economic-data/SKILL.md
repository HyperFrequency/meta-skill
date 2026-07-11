---
name: fred-economic-data
version: 0.1.0
description: >-
  Query the FRED (Federal Reserve Economic Data) REST API from the St. Louis Fed
  for 800,000+ economic time series across 100+ sources — GDP, unemployment,
  CPI/inflation, interest and exchange rates, housing, money supply, and regional
  data — including vintage "as-reported" values via ALFRED, release calendars, and
  category/tag discovery. Use when you need macroeconomic or financial indicators
  for research, forecasting, dashboards, policy analysis, or as exogenous model
  features, and want programmatic pulls with built-in transformations (percent
  change, log) and frequency aggregation. Not for intraday/tick market data, order
  books, or company fundamentals (use a market-data or securities API); not a
  backtesting, plotting, or statistical-modeling engine — it only retrieves series,
  which you analyze with sibling skills.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# FRED Economic Data

## Overview

FRED (Federal Reserve Economic Data), maintained by the Federal Reserve Bank of
St. Louis, is a free REST API exposing over 800,000 economic time series drawn from
100+ statistical agencies (BLS, BEA, Census, the Federal Reserve Board, OECD, IMF,
World Bank, and more). This skill covers pulling those series programmatically:
fetching observations with transformations and frequency aggregation, discovering
series by category / tag / release / source, retrieving publication calendars, and
accessing revision history (vintage data) through ALFRED and regional data through
GeoFRED.

The API is plain HTTPS GET with an `api_key` query parameter and JSON responses — no
SDK is required. The examples here use Python `requests`, but the same URLs work
from any HTTP client.

## When to Use This Skill

- You need a specific U.S. or international macro indicator (GDP, `UNRATE`,
  `CPIAUCSL`, `FEDFUNDS`, `DGS10`, `PAYEMS`, ...) as a clean time series.
- You are building an economic dashboard, forecast, or nowcast and want current
  values plus history.
- You need **point-in-time / vintage** data — the value *as it was first reported*
  on a past date — to avoid look-ahead bias in a model. See `references/api-basics.md`.
- You want to discover what series exist for a topic, region, source, or release.
- You need a release calendar (when the next CPI or jobs report drops).
- You need regional (state / county / MSA) values for choropleth mapping via GeoFRED.

## When NOT to Use This Skill

- **Intraday, tick, or order-book market data** — FRED is low-frequency (daily at
  finest for most series). Use a market-data / securities API instead.
- **Company fundamentals or equity-level data** — FRED is macro/aggregate, not
  per-issuer.
- **Datasets FRED does not mirror** — for structured pulls from other named
  scientific databases, use `database-lookup`.
- **Analysis itself** — FRED only *retrieves* series. Model them with `statsmodels`
  or `timesfm-forecasting`, run stats with `statistical-analysis`, wrangle frames
  with `polars`, explore with `exploratory-data-analysis`, and map regional data
  with `geopandas`.

## API Key Setup

**Every** request requires a free 32-character key.

1. Create an account at <https://fredaccount.stlouisfed.org> and request an API key.
2. Export it (never hard-code it into shared code):

```bash
export FRED_API_KEY="your_32_character_key"
```

```python
import os
API_KEY = os.environ["FRED_API_KEY"]   # KeyError early if unset — good
```

## The Core Call: Series Observations

`fred/series/observations` is the endpoint you will use ~90% of the time. It returns
the data values for one series, optionally transformed and re-aggregated.

```python
import os, requests

API_KEY = os.environ["FRED_API_KEY"]
BASE = "https://api.stlouisfed.org/fred"

resp = requests.get(
    f"{BASE}/series/observations",
    params={
        "api_key": API_KEY,
        "series_id": "GDP",
        "file_type": "json",          # default is xml — always set json
        "observation_start": "2015-01-01",
        "units": "pc1",               # percent change from a year ago
        "frequency": "q",             # aggregate to quarterly
    },
    timeout=30,
)
data = resp.json()

for obs in data["observations"]:
    if obs["value"] != ".":           # "." marks a missing value — always guard
        print(obs["date"], float(obs["value"]))
```

Two rules that bite everyone: default `file_type` is `xml` (pass `json`), and
missing observations arrive as the string `"."` (never `float()` blindly). Full
parameter tables, transformation codes, and frequency codes are in
`references/api-basics.md` and `references/series-endpoints.md`.

## Popular Series

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `GDP` / `GDPC1` | Gross Domestic Product / Real GDP | Quarterly |
| `UNRATE` | Unemployment Rate | Monthly |
| `CPIAUCSL` | Consumer Price Index (All Urban) | Monthly |
| `PCEPILFE` | Core PCE Price Index | Monthly |
| `FEDFUNDS` | Federal Funds Effective Rate | Monthly |
| `DGS10` / `DGS2` | 10-Year / 2-Year Treasury Yield | Daily |
| `T10Y2Y` | 10Y-2Y Treasury Spread | Daily |
| `PAYEMS` | Total Nonfarm Payrolls | Monthly |
| `INDPRO` | Industrial Production Index | Monthly |
| `HOUST` | Housing Starts | Monthly |
| `M2SL` | M2 Money Stock | Monthly |
| `UMCSENT` | Consumer Sentiment | Monthly |
| `SP500` | S&P 500 Index | Daily |

Don't know the ID? Search or browse — see the discovery reference below.

## Reference Map

Read only the reference you need for the task at hand:

| Reference | Covers |
|-----------|--------|
| `references/api-basics.md` | Auth, base URLs, `file_type`, common params, pagination/sorting, error codes, missing values, **full units-transformation and frequency-code tables**, ALFRED real-time (vintage) parameters, tag groups. |
| `references/series-endpoints.md` | All 10 `fred/series/*` endpoints: metadata, observations, search, updates, tags, vintage dates. |
| `references/discovery-endpoints.md` | Navigation & discovery: `fred/category/*`, `fred/release(s)/*`, `fred/tags` / `fred/related_tags` / `fred/tags/series`, `fred/source(s)/*`, plus common category / release / source / tag IDs. |
| `references/geofred-endpoints.md` | GeoFRED regional data (`geofred/regional/data`, `geofred/series/data`, `geofred/series/group`) and GeoJSON shape files for state / county / MSA mapping. |
| `references/recipes.md` | Copy-paste Python: economic snapshot, multi-series comparison DataFrame, release calendar, regional choropleth, robust error handling + rate-limit backoff, and the optional `fredapi` convenience wrapper. |

## Transformations & Aggregation (quick reference)

Set `units=` to transform values on the server; set `frequency=` (+ optional
`aggregation_method=avg|sum|eop`) to down-sample a higher-frequency series.

- `units`: `lin` (levels, default), `chg`, `ch1`, `pch` (% change), `pc1` (% change
  from year ago), `pca`, `cch`, `cca`, `log`.
- `frequency`: `d`, `w`, `bw`, `m`, `q`, `sa`, `a` (plus weekly/biweekly
  end-of-week variants).

Full definitions and every code are in `references/api-basics.md`.

## Vintage / Point-in-Time Data (ALFRED)

Economic data is revised. To see a series *as it was reported* on a past date (the
correct choice for backtests and honest forecast evaluation), pass real-time
parameters — the same endpoints serve ALFRED:

```python
# GDP exactly as published on 2020-04-29, no later revisions
params = {"api_key": API_KEY, "series_id": "GDP", "file_type": "json",
          "realtime_start": "2020-04-29", "realtime_end": "2020-04-29"}
```

Use `fred/series/vintagedates` to list every revision date for a series. Details in
`references/api-basics.md`.

## Rate Limits & Reliability

- The API rate-limits requests and returns HTTP **429** when exceeded — retry with
  exponential backoff (pattern in `references/recipes.md`).
- Handle HTTP errors and the JSON `error_code` / `error_message` shape; an invalid
  key returns 400/401, an unknown series returns an error body, not observations.
- Set a `timeout` on every request and cache series you re-read to stay well under
  the limit.

## External Resources

- API docs: <https://fred.stlouisfed.org/docs/api/fred/>
- Browse series: <https://fred.stlouisfed.org/>
- ALFRED (vintage data): <https://alfred.stlouisfed.org/>
- **Terms of Use** (attribution, redistribution): <https://fred.stlouisfed.org/legal/>
