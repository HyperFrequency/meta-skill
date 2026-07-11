# openFDA Python Recipes

Reusable, copy-paste helpers for the openFDA API: a rate-limited + cached HTTP client,
auto-pagination, and six common analysis patterns. Only `requests` is required; the API
itself needs no client library.

## Minimal request with error handling

```python
import os
import requests

BASE = "https://api.fda.gov"

def fda_get(category, endpoint, api_key=None, **params):
    """One openFDA call. Returns parsed JSON; 404 -> empty result set."""
    url = f"{BASE}/{category}/{endpoint}.json"
    if api_key:
        params["api_key"] = api_key
    params.setdefault("limit", 100)          # API default is 1 — set it
    if "limit" in params:
        params["limit"] = min(params["limit"], 1000)
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError:
        code = r.status_code
        if code == 404:                       # openFDA returns 404 for zero hits
            return {"results": [], "meta": {"results": {"total": 0}}}
        return {"error": f"HTTP {code}: {r.text[:200]}"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# usage
data = fda_get("drug", "event", api_key=os.environ.get("FDA_API_KEY"),
               search="patient.drug.medicinalproduct:aspirin", limit=10)
```

## Rate-limited, cached client

For any multi-call workload, wrap requests with a sliding-window rate limiter (openFDA
allows 240/min) and a simple on-disk cache (substance/label data changes rarely).

```python
import hashlib, json, time
from collections import deque
from pathlib import Path
import requests


class FDAClient:
    BASE = "https://api.fda.gov"

    def __init__(self, api_key=None, max_per_minute=240,
                 cache_dir="fda_cache", cache_ttl=3600):
        self.api_key = api_key
        self.max_per_minute = max_per_minute
        self._hits = deque()                       # request timestamps (last 60 s)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl = cache_ttl

    def _throttle(self):
        now = time.time()
        while self._hits and now - self._hits[0] > 60:
            self._hits.popleft()
        if len(self._hits) >= self.max_per_minute:
            time.sleep(60 - (now - self._hits[0]) + 0.1)
            self._hits.popleft()
        self._hits.append(time.time())

    def _cache_path(self, url, params):
        key = hashlib.md5(f"{url}{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def get(self, category, endpoint, use_cache=True, **params):
        url = f"{self.BASE}/{category}/{endpoint}.json"
        if self.api_key:
            params["api_key"] = self.api_key
        params.setdefault("limit", 100)
        params["limit"] = min(params["limit"], 1000)

        cache_file = self._cache_path(url, params)
        if use_cache and cache_file.exists() and \
                time.time() - cache_file.stat().st_mtime < self.cache_ttl:
            return json.loads(cache_file.read_text())

        self._throttle()
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            if r.status_code == 404:
                return {"results": [], "meta": {"results": {"total": 0}}}
            if r.status_code == 429:               # rate limited: wait once and retry
                time.sleep(60)
                return self.get(category, endpoint, use_cache=False, **params)
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

        data = r.json()
        if use_cache:
            cache_file.write_text(json.dumps(data))
        return data

    def count(self, category, endpoint, search, field, exact=True):
        """Aggregate by a field, auto-adding .exact for multi-word fields."""
        if exact and not field.endswith(".exact"):
            field = field + ".exact"
        return self.get(category, endpoint, search=search, count=field)
```

## Auto-pagination

`skip` is capped at 25,000. Stay under it, or partition by date range for deeper pulls.

```python
def fetch_all(client, category, endpoint, search, max_results=5000, batch=100):
    out, skip = [], 0
    while len(out) < max_results and skip <= 25000:
        data = client.get(category, endpoint, search=search, limit=batch, skip=skip)
        rows = data.get("results", [])
        if not rows or "error" in data:
            break
        out.extend(rows)
        if len(rows) < batch:
            break
        skip += batch
    return out[:max_results]
```

## Pattern 1 — Drug safety profile

```python
def drug_safety_profile(client, drug):
    events = client.get("drug", "event",
                        search=f"patient.drug.medicinalproduct:{drug}", limit=1)
    total = events.get("meta", {}).get("results", {}).get("total", 0)

    reactions = client.count("drug", "event",
                             search=f"patient.drug.medicinalproduct:{drug}",
                             field="patient.reaction.reactionmeddrapt")

    serious = client.get("drug", "event",
                         search=f"patient.drug.medicinalproduct:{drug}+AND+serious:1",
                         limit=1)
    serious_total = serious.get("meta", {}).get("results", {}).get("total", 0)

    recalls = client.get("drug", "enforcement",
                         search=f"product_description:*{drug}*",
                         sort="report_date:desc", limit=10)

    return {
        "drug": drug,
        "total_events": total,
        "serious_events": serious_total,
        "serious_rate_pct": round(serious_total / total * 100, 2) if total else 0,
        "top_reactions": reactions.get("results", [])[:10],
        "recent_recalls": recalls.get("results", []),
    }
```

## Pattern 2 — Temporal trend

```python
from datetime import datetime, timedelta

def monthly_trend(client, drug, months=12):
    trend = []
    for i in range(months):
        end = datetime.now() - timedelta(days=30 * i)
        start = end - timedelta(days=30)
        rng = f"[{start:%Y%m%d}+TO+{end:%Y%m%d}]"
        search = f"patient.drug.medicinalproduct:{drug}+AND+receivedate:{rng}"
        data = client.get("drug", "event", search=search, limit=1)
        trend.append({"month": f"{start:%Y-%m}",
                      "events": data.get("meta", {}).get("results", {}).get("total", 0)})
    return list(reversed(trend))
```

## Pattern 3 — Comparative safety

```python
def compare_drugs(client, drugs):
    out = {}
    for d in drugs:
        total = client.get("drug", "event",
                           search=f"patient.drug.medicinalproduct:{d}", limit=1
                           ).get("meta", {}).get("results", {}).get("total", 0)
        serious = client.get("drug", "event",
                             search=f"patient.drug.medicinalproduct:{d}+AND+serious:1",
                             limit=1).get("meta", {}).get("results", {}).get("total", 0)
        out[d] = {"total_events": total, "serious_events": serious,
                  "serious_rate_pct": round(serious / total * 100, 2) if total else 0}
    return out
```

## Pattern 4 — Cross-database device lookup

```python
def device_dossier(client, name):
    return {
        "adverse_events": client.get("device", "event",
                                     search=f"device.brand_name:*{name}*", limit=10),
        "510k": client.get("device", "510k",
                           search=f"device_name:*{name}*", limit=10),
        "recalls": client.get("device", "enforcement",
                             search=f"product_description:*{name}*", limit=10),
        "udi": client.get("device", "udi",
                         search=f"brand_name:*{name}*", limit=10),
    }
```

## Pattern 5 — Allergen recall monitor

```python
from datetime import datetime, timedelta

def allergen_recalls(client, allergens, days_back=30):
    end, start = datetime.now(), datetime.now() - timedelta(days=days_back)
    rng = f"[{start:%Y%m%d}+TO+{end:%Y%m%d}]"
    hits = []
    for allergen in allergens:                      # e.g. ["peanut", "milk", "sesame"]
        data = client.get("food", "enforcement",
                          search=f"reason_for_recall:*{allergen}*+AND+report_date:{rng}",
                          sort="report_date:desc", limit=100)
        for rec in data.get("results", []):
            rec["_matched_allergen"] = allergen
            hits.append(rec)
    return hits
```

## Pattern 6 — Substance identifier resolution (UNII → CAS / structure)

```python
def resolve_substance(client, unii):
    data = client.get("other", "substance", search=f"approvalID:{unii}", limit=1)
    rows = data.get("results", [])
    if not rows:
        return None
    s = rows[0]

    preferred = next((n["name"] for n in s.get("names", []) if n.get("preferred")),
                     s.get("names", [{}])[0].get("name"))
    cas = [c["code"] for c in s.get("codes", [])
           if "CAS" in c.get("codeSystem", "").upper()]
    struct = s.get("structure", {})
    return {
        "unii": s.get("approvalID"),
        "preferred_name": preferred,
        "substance_class": s.get("substanceClass"),
        "cas_numbers": cas,
        "smiles": struct.get("smiles"),
        "inchikey": struct.get("inchiKey"),
        "formula": struct.get("formula"),
        "molecular_weight": struct.get("molecularWeight"),
    }
```

## Notes

- **Always set `limit`** — the API default is 1.
- **`.exact` for counts** — the `FDAClient.count` helper adds it automatically; add it by
  hand in raw `count=` calls on multi-word fields.
- **404 = no results** — the helpers normalize it to an empty result set.
- **Sparse fields** — guard every access with `.get()`; reports are voluntary and biased,
  so counts reflect *reporting*, not incidence or causation.
- **Deep pulls** — past ~26,000 records, partition the query by `receivedate` /
  `report_date` ranges instead of increasing `skip`.
