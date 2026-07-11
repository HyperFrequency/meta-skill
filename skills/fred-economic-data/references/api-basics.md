# FRED API Basics

Cross-cutting mechanics shared by every endpoint. Read this once; the endpoint
references assume it.

## Base URLs

```
https://api.stlouisfed.org/fred/       # FRED and ALFRED endpoints
https://api.stlouisfed.org/geofred/    # GeoFRED (regional) endpoints
```

## Authentication

Pass the key as a query parameter on every request:

```
api_key=YOUR_32_CHARACTER_KEY
```

The key is a 32-character lowercase alphanumeric string from
<https://fredaccount.stlouisfed.org>. Keep it in the `FRED_API_KEY` env var, not in
code.

## Response format

Set `file_type` explicitly — **the API default is `xml`**, which is almost never
what you want.

| `file_type` | Content |
|-------------|---------|
| `json` | JSON (recommended) |
| `xml`  | XML (default) |
| `csv`  | CSV — observation endpoints only |
| `xlsx` | Excel — observation endpoints only |

## Common parameters

Available on most endpoints:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `api_key` | string | required | 32-char key |
| `file_type` | string | `xml` | set `json` |
| `realtime_start` | date | today | YYYY-MM-DD (see ALFRED below) |
| `realtime_end` | date | today | YYYY-MM-DD |
| `limit` | integer | varies | max rows; caps differ per endpoint |
| `offset` | integer | 0 | pagination offset |
| `order_by` | string | varies | sort field (endpoint-specific) |
| `sort_order` | string | `asc` | `asc` or `desc` |

Paginate by advancing `offset` in steps of `limit`. The response `count` field tells
you the total so you know when to stop.

## Dates and missing values

- **Date format is strictly `YYYY-MM-DD`.** `01/15/2023` and `Jan 15, 2023` are
  rejected.
- **Missing observations are the string `"."`,** not `null` and not `0`:

```python
value = obs["value"]
if value != ".":
    numeric = float(value)   # only now is this safe
```

## Real-time periods (ALFRED / vintage data)

FRED shows current values; ALFRED shows the value *as it was known at a point in
time*. Both are served by the same endpoints via two parameters:

- `realtime_start` — beginning of the real-time period
- `realtime_end` — end of the real-time period

Setting both to the same past date returns the series exactly as it was published
that day, with no later revisions — the correct choice for avoiding look-ahead bias:

```python
# GDP as reported on 2020-04-29
params = {
    "series_id": "GDP",
    "realtime_start": "2020-04-29",
    "realtime_end": "2020-04-29",
    "file_type": "json",
}
```

`fred/series/vintagedates` returns every date a series was revised (see
`series-endpoints.md`). On `fred/series/observations` you can also pass
`vintage_dates` (comma-separated) to fetch specific vintages.

## `units` — server-side transformations

Applied by `fred/series/observations` (and GeoFRED via `transformation`):

| Value | Meaning |
|-------|---------|
| `lin` | Levels — no transformation (default) |
| `chg` | Change from previous period |
| `ch1` | Change from a year ago |
| `pch` | Percent change from previous period |
| `pc1` | Percent change from a year ago |
| `pca` | Compounded annual rate of change |
| `cch` | Continuously compounded rate of change |
| `cca` | Continuously compounded annual rate of change |
| `log` | Natural log |

## `frequency` — down-sampling aggregation

Aggregate a higher-frequency series to a lower frequency. Pair with
`aggregation_method` = `avg` (default), `sum`, or `eop` (end of period).

| Code | Frequency | | Code | Frequency |
|------|-----------|-|------|-----------|
| `d`  | Daily     | | `q`  | Quarterly |
| `w`  | Weekly    | | `sa` | Semiannual |
| `bw` | Biweekly  | | `a`  | Annual |
| `m`  | Monthly   | | | |

Weekly variants pin the ending weekday: `wef` (Fri), `weth` (Thu), `wew` (Wed),
`wetu` (Tue), `wem` (Mon), `wesu` (Sun), `wesa` (Sat); biweekly variants `bwew`,
`bwem`. You can only aggregate *down* (e.g. daily → monthly), never up.

## Errors

| HTTP | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request — invalid/missing parameter |
| 401 | Unauthorized — bad or missing API key |
| 404 | Not found — bad endpoint/resource |
| 429 | Too many requests — rate limited; back off and retry |
| 500 | Server error |

JSON error body:

```json
{ "error_code": 400, "error_message": "Bad Request. The value for variable api_key is not registered..." }
```

Always check `resp.status_code` and, on 200, whether the expected list key
(`observations`, `seriess`, `categories`, ...) is present and non-empty before
indexing.

## Tag groups

Tags carry a `group_id` that classifies them:

| `group_id` | Meaning | Examples |
|------------|---------|----------|
| `freq` | Frequency | monthly, quarterly, annual |
| `gen`  | General / topic | gdp, inflation, employment |
| `geo`  | Geography | usa, california, japan |
| `geot` | Geography type | nation, state, county, msa |
| `rls`  | Release | employment situation |
| `seas` | Seasonal adjustment | sa, nsa |
| `src`  | Source | bls, bea, census |
| `cc`   | Citation / copyright | public domain |

## Minimal request helper

```python
import os, requests

BASE = "https://api.stlouisfed.org"
API_KEY = os.environ["FRED_API_KEY"]

def fred_get(path, **params):
    params.setdefault("file_type", "json")
    params["api_key"] = API_KEY
    resp = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

obs = fred_get("fred/series/observations", series_id="UNRATE", limit=12,
               sort_order="desc")
```

See `recipes.md` for a hardened version with 429 backoff.
