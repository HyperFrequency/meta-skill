# OpenAlex Recipes

Runnable Python patterns using only `requests`. See [api.md](api.md) for the full
parameter and filter reference.

```bash
uv pip install requests
```

## A minimal, polite client

A thin wrapper is all you need: it injects `mailto`, rate-limits, and retries with
exponential backoff. Nothing here is OpenAlex-specific magic — it is the raw REST
API plus courtesy.

```python
import time, requests

BASE = "https://api.openalex.org"

class OpenAlex:
    def __init__(self, email, rps=10):
        self.email = email
        self.min_delay = 1.0 / rps
        self._last = 0.0

    def get(self, path, params=None, max_retries=5):
        params = dict(params or {})
        params["mailto"] = self.email          # polite pool → 10 req/s
        for attempt in range(max_retries):
            wait = self.min_delay - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            r = requests.get(f"{BASE}{path}", params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429) or r.status_code >= 500:
                time.sleep(2 ** attempt)       # back off and retry
                continue
            r.raise_for_status()
        raise RuntimeError(f"{path} failed after {max_retries} retries")

api = OpenAlex(email="you@example.edu")
```

## Search + filter + sort

```python
data = api.get("/works", {
    "search": "quantum computing",
    "filter": "publication_year:>2020,is_oa:true",
    "sort": "cited_by_count:desc",
    "per-page": 200,
    "select": "id,title,publication_year,cited_by_count,doi",
})
print(data["meta"]["count"], "matches")
for w in data["results"][:10]:
    print(w["publication_year"], w["cited_by_count"], w["title"])
```

## Two-step name → ID → works

`filter=author_name:...` does not exist. Resolve the ID, then filter.

```python
def resolve_id(entity, name):
    hits = api.get(f"/{entity}", {"search": name, "per-page": 1})["results"]
    if not hits:
        return None
    return hits[0]["id"].split("/")[-1]     # 'https://openalex.org/A5089…' → 'A5089…'

author_id = resolve_id("authors", "Jennifer Doudna")
works = api.get("/works", {
    "filter": f"authorships.author.id:{author_id}",
    "per-page": 200,
})["results"]
```

The same helper resolves institutions (`authorships.institutions.id`), journals
(`primary_location.source.id`), and funders (`grants.funder`). For an interactive
picker use `/autocomplete/authors?q=doudna`.

## Papers with authors from BOTH institutions (collaboration)

```python
mit = resolve_id("institutions", "MIT")
stanford = resolve_id("institutions", "Stanford University")
n = api.get("/works", {
    "filter": f"authorships.institutions.id:{mit}+{stanford}",   # '+' = AND within attr
    "per-page": 1,
})["meta"]["count"]
print(f"{n} MIT×Stanford co-authored works")
```

## Aggregate with group_by (counts, no rows)

```python
# Publications per year for an institution
trends = api.get("/works", {
    "filter": f"authorships.institutions.id:{mit}",
    "group_by": "publication_year",
})["group_by"]
for g in sorted(trends, key=lambda x: x["key"])[-10:]:
    print(g["key"], g["count"])

# Top research topics
topics = api.get("/works", {
    "filter": f"authorships.institutions.id:{mit},publication_year:>2020",
    "group_by": "topics.id",
})["group_by"]
for t in topics[:10]:
    print(t["key_display_name"], t["count"])
```

## Batch-resolve DOIs (≤50 per request)

```python
dois = ["10.1038/s41586-021-03819-2", "10.1126/science.abc1234", "10.1371/journal.pone.0266781"]
works = api.get("/works", {
    "filter": "doi:" + "|".join(dois),        # '|' = OR
    "per-page": 50,
})["results"]
```

## Reproducible random sample

```python
sample = api.get("/works", {
    "filter": "publication_year:2023,is_oa:true",
    "sample": 100,
    "seed": 42,          # same seed → same rows
    "per-page": 100,
})["results"]
```

For samples larger than 10,000, issue several requests with different `seed`s and
deduplicate by `id`.

## Deep bulk extraction with a cursor

`page` stops at 10,000 results. To stream an entire filtered corpus, page with a
cursor and follow `meta.next_cursor` until it is null.

```python
import csv

def stream_all(path, params, max_results=None):
    params = dict(params, **{"per-page": 200, "cursor": "*"})
    seen = 0
    while True:
        data = api.get(path, params)
        for row in data["results"]:
            yield row
            seen += 1
            if max_results and seen >= max_results:
                return
        cursor = data["meta"].get("next_cursor")
        if not cursor:
            return
        params["cursor"] = cursor

with open("papers.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title", "year", "citations", "doi", "oa_status"])
    for w in stream_all("/works",
                        {"filter": "publication_year:2020-2024,title.search:synthetic+biology"},
                        max_results=10000):
        writer.writerow([
            w.get("title"),
            w.get("publication_year"),
            w.get("cited_by_count", 0),
            w.get("doi"),
            (w.get("open_access") or {}).get("oa_status", "closed"),
        ])
```

For scans across the whole 240M-work corpus, download the CC0 snapshot rather than
paging the API.

## Citation analysis

```python
work = api.get("/works/https://doi.org/10.1038/s41586-021-03819-2")
print(work["title"], "—", work["cited_by_count"], "citations")

# Works that cite it: cited_by_api_url is a ready /works query URL
citing = requests.get(work["cited_by_api_url"],
                      params={"mailto": api.email, "per-page": 200}).json()["results"]

# Works it references:
refs = work["referenced_works"]   # list of OpenAlex IDs
```

## Reconstruct an abstract

Works expose `abstract_inverted_index` (a `{word: [positions]}` map), not text.

```python
def reconstruct_abstract(inverted_index):
    if not inverted_index:
        return ""
    positions = [(pos, word) for word, ps in inverted_index.items() for pos in ps]
    positions.sort()
    return " ".join(word for _, word in positions)

text = reconstruct_abstract(work.get("abstract_inverted_index"))
```

## Research-output snapshot for an entity

```python
def research_output(entity, name, years=">2020"):
    prefix = "authorships.author.id" if entity == "authors" else "authorships.institutions.id"
    ent_id = resolve_id(entity, name)
    base = f"{prefix}:{ent_id},publication_year:{years}"
    total = api.get("/works", {"filter": base, "per-page": 1})["meta"]["count"]
    oa = api.get("/works", {"filter": base + ",is_oa:true", "per-page": 1})["meta"]["count"]
    topics = api.get("/works", {"filter": base, "group_by": "topics.id"})["group_by"][:10]
    return {
        "id": ent_id,
        "total_works": total,
        "open_access_pct": round(100 * oa / total, 1) if total else 0.0,
        "top_topics": [(t["key_display_name"], t["count"]) for t in topics],
    }

print(research_output("institutions", "MIT"))
```
