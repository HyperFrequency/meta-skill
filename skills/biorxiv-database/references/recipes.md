# bioRxiv Query Recipes

Copy-paste Python recipes built on `requests`. They assume the API facts in
`api.md`. The two things that bite people — **pagination** and **client-side
filtering** — are handled explicitly here.

## Minimal client with correct pagination

The `/details` endpoint returns a fixed page (currently 30 records) per call.
Fetching one page silently truncates a busy date range. Always loop the cursor.

```python
import time
import requests

API = "https://api.biorxiv.org"
HEADERS = {"User-Agent": "biorxiv-database-skill/0.1 (mailto:you@example.com)"}
PAGE = 30  # /details page size; /pubs and /pub serve 100

def fetch_range(start, end, server="biorxiv", category=None, delay=0.5):
    """All preprints posted in [start, end], following the cursor to the end."""
    cursor = 0
    records = []
    while True:
        url = f"{API}/details/{server}/{start}/{end}/{cursor}"
        params = {"category": category} if category else None
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("messages", [{}])[0]
        if msg.get("status") != "ok":
            break
        batch = data.get("collection", [])
        records.extend(batch)
        total = int(msg.get("total", 0))
        cursor += PAGE
        if not batch or cursor >= total:
            break
        time.sleep(delay)  # be polite
    return records
```

`category=None` fetches every category, then filter client-side (below) if the
querystring spelling is uncertain.

## Keyword screening (client-side)

The API has no full-text keyword endpoint. Pull a date range, then filter titles
and abstracts locally.

```python
def screen_keywords(records, keywords, fields=("title", "abstract")):
    needles = [k.lower() for k in keywords]
    hits = []
    for rec in records:
        hay = " ".join(str(rec.get(f, "")) for f in fields).lower()
        if any(n in hay for n in needles):  # OR semantics; use all() for AND
            hits.append(rec)
    return hits

recent = fetch_range("2024-01-01", "2024-12-31", category="genomics")
crispr = screen_keywords(recent, ["CRISPR", "gene editing"])
```

## Author screening (client-side, substring)

```python
def screen_author(records, name):
    q = name.lower()
    return [r for r in records if q in r.get("authors", "").lower()]

smith = screen_author(fetch_range("2023-01-01", "2024-12-31"), "Smith")
```

Substring matching is coarse: `"Li"` matches many names. Prefer a distinctive
last name plus a date window, and de-duplicate on `doi`.

## Single paper by DOI

```python
def get_paper(doi, server="biorxiv"):
    doi = doi.split("doi.org/")[-1]  # accept full DOI URLs
    url = f"{API}/details/{server}/{doi}/na"
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    coll = data.get("collection", [])
    return coll[0] if coll else None
```

## Recent posts (numeric / N-days interval)

```python
def fetch_recent_days(days, server="biorxiv"):
    # The Nd (and numeric N) forms take NO cursor slot — appending /0 errors out.
    url = f"{API}/details/{server}/{days}d"
    return requests.get(url, headers=HEADERS, timeout=60).json().get("collection", [])
```

These recent-feed forms return a single response and cannot be paginated: `N`
gives exactly N posts; `Nd` returns the last N days but is effectively capped
(~1300 records) and a wide window like `30d` may time out. For complete coverage
of a busy window, use the paginated `fetch_range(start, end)` instead.

## PDF download (use the record's real version)

```python
def download_pdf(record, out_path, server="biorxiv"):
    doi = record["doi"]
    version = record.get("version", "1")  # do NOT hardcode v1
    host = "www.medrxiv.org" if server == "medrxiv" else "www.biorxiv.org"
    url = f"https://{host}/content/{doi}v{version}.full.pdf"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
```

Batch downloads: iterate, add a delay, and expect occasional 403/404 (embargoed
or withdrawn preprints) — catch and continue rather than aborting the batch.

## Published-version check

```python
def published_link(doi, server="biorxiv"):
    doi = doi.split("doi.org/")[-1]
    data = requests.get(f"{API}/pubs/{server}/{doi}/na", headers=HEADERS, timeout=30).json()
    coll = data.get("collection", [])
    return coll[0].get("published_doi") if coll else None
```

## Analysis: results to a DataFrame

```python
import pandas as pd

df = pd.DataFrame(fetch_range("2020-01-01", "2024-12-31", category="bioinformatics"))
df["date"] = pd.to_datetime(df["date"])
print(df.groupby(df["date"].dt.to_period("M")).size())        # monthly volume
top = df["authors"].str.split(",").explode().str.strip().value_counts().head(10)
df.to_csv("bioinformatics_2020_2024.csv", index=False)
```

## Literature-review workflow

1. `fetch_range(start, end, category=...)` — pull the full window (paginated).
2. `screen_keywords(...)` / `screen_author(...)` — narrow client-side.
3. De-duplicate on `doi`; keep the highest `version` per DOI.
4. `download_pdf(...)` the shortlist, or hand DOIs to `citation-management` for
   BibTeX and to `literature-review` for synthesis.

## Boundaries to design around

- **Silent truncation** if you skip pagination — the single most common bug.
- **No relevance ranking**: results come back in post order; rank yourself.
- **Metadata-only**: abstracts yes, full text only via PDF/HTML/JATS URLs.
- **`published` lag**: journal linkage in `/details` can trail the actual
  publication; `/pubs` is more current for that question.
- **Category strings differ by server**; read a sample record to confirm.
