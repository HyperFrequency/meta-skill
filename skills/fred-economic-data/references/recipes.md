# FRED Recipes

Copy-paste patterns built on the raw REST API. All assume the `fred_get` helper from
`api-basics.md` (or inline `requests.get`).

## Hardened request helper (429 backoff + error surfacing)

```python
import os, time, requests

BASE = "https://api.stlouisfed.org"
API_KEY = os.environ["FRED_API_KEY"]

def fred_get(path, retries=4, **params):
    params.setdefault("file_type", "json")
    params["api_key"] = API_KEY
    backoff = 1.0
    for attempt in range(retries):
        resp = requests.get(f"{BASE}/{path}", params=params, timeout=30)
        if resp.status_code == 429:            # rate limited
            time.sleep(backoff)
            backoff *= 2                        # exponential
            continue
        resp.raise_for_status()
        body = resp.json()
        if "error_code" in body:               # FRED app-level error
            raise RuntimeError(f"FRED {body['error_code']}: {body['error_message']}")
        return body
    raise RuntimeError("FRED rate limit: retries exhausted")
```

## Economic snapshot — latest value of key indicators

```python
def economic_snapshot(series_ids=("GDP", "UNRATE", "CPIAUCSL", "FEDFUNDS", "DGS10")):
    out = {}
    for sid in series_ids:
        body = fred_get("fred/series/observations",
                        series_id=sid, limit=1, sort_order="desc")
        obs = body.get("observations")
        if obs and obs[0]["value"] != ".":
            out[sid] = {"date": obs[0]["date"], "value": float(obs[0]["value"])}
    return out
```

## Multi-series comparison DataFrame (normalized)

```python
import pandas as pd

def compare_series(series_ids, start_date, units="pc1"):
    """Aligned DataFrame; units='pc1' normalizes to % change YoY."""
    cols = {}
    for sid in series_ids:
        body = fred_get("fred/series/observations",
                        series_id=sid, observation_start=start_date, units=units)
        cols[sid] = {o["date"]: float(o["value"])
                     for o in body["observations"] if o["value"] != "."}
    df = pd.DataFrame(cols)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

df = compare_series(["GDPC1", "PAYEMS", "INDPRO"], "2000-01-01")
```

Hand `df` to `polars`, `statsmodels`, or `statistical-analysis` for modeling.

## Upcoming release calendar

```python
from datetime import date, timedelta

def upcoming_releases(days=14):
    today = date.today()
    body = fred_get(
        "fred/releases/dates",
        realtime_start=today.isoformat(),
        realtime_end=(today + timedelta(days=days)).isoformat(),
        order_by="release_date", sort_order="asc",
        include_release_dates_with_no_data="true",
    )
    calendar = {}
    for item in body.get("release_dates", []):
        calendar.setdefault(item["date"], []).append(item["release_name"])
    return calendar
```

## Point-in-time reconstruction (avoid look-ahead)

```python
def value_as_of(series_id, as_of):
    """Series as it was reported on `as_of` (YYYY-MM-DD), no later revisions."""
    body = fred_get("fred/series/observations", series_id=series_id,
                    realtime_start=as_of, realtime_end=as_of)
    return [(o["date"], o["value"]) for o in body["observations"]]
```

List every revision date first with `fred/series/vintagedates` (see
`series-endpoints.md`).

## Robust value parsing

```python
def clean_observations(body):
    """(datetime, float) pairs, dropping missing '.' values."""
    import pandas as pd
    return [(pd.Timestamp(o["date"]), float(o["value"]))
            for o in body.get("observations", []) if o["value"] != "."]
```

---

## Optional: the `fredapi` convenience wrapper

If you prefer pandas-native returns over raw JSON, the third-party
[`fredapi`](https://pypi.org/project/fredapi/) package (MIT) wraps these same
endpoints:

```bash
uv pip install fredapi
```

```python
from fredapi import Fred

fred = Fred(api_key=os.environ["FRED_API_KEY"])
gdp   = fred.get_series("GDP")            # -> pandas Series indexed by date
info  = fred.get_series_info("PAYEMS")    # -> pandas Series of metadata
found = fred.search("consumer price index")   # -> DataFrame of matches
```

`fredapi` also exposes vintage/ALFRED helpers (first release, latest release,
as-of-date, all releases). For exact method names and signatures consult the
`fredapi` docs — do not guess them; the raw endpoints in `series-endpoints.md` and
`api-basics.md` remain the ground truth if the wrapper lags the API.
