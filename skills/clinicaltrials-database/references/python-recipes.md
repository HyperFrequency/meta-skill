# ClinicalTrials.gov — Python recipes

Reusable patterns over API v2 using only `requests`. No client library or API key
needed. Adapt freely; these are thin wrappers, not a framework.

## A small client

```python
import requests
from typing import Optional, Union

BASE_URL = "https://clinicaltrials.gov/api/v2"


def search_studies(
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    location: Optional[str] = None,
    sponsor: Optional[str] = None,
    status: Optional[Union[str, list[str]]] = None,
    phase: Optional[Union[str, list[str]]] = None,
    nct_ids: Optional[list[str]] = None,
    sort: str = "LastUpdatePostDate:desc",
    page_size: int = 50,
    page_token: Optional[str] = None,
    count_total: bool = True,
    fmt: str = "json",
):
    """One /studies search. Returns dict (json) or str (csv)."""
    params: dict = {"sort": sort, "pageSize": page_size, "format": fmt}
    if condition:    params["query.cond"] = condition
    if intervention: params["query.intr"] = intervention
    if location:     params["query.locn"] = location
    if sponsor:      params["query.spons"] = sponsor
    if status:
        params["filter.overallStatus"] = status if isinstance(status, str) else ",".join(status)
    if phase:
        params["filter.phase"] = phase if isinstance(phase, str) else ",".join(phase)
    if nct_ids:
        params["filter.ids"] = ",".join(nct_ids)
    if page_token:
        params["pageToken"] = page_token
    if count_total and fmt == "json":
        params["countTotal"] = "true"   # else totalCount is omitted

    resp = requests.get(f"{BASE_URL}/studies", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json() if fmt == "json" else resp.text


def get_study(nct_id: str, fmt: str = "json"):
    """Fetch one study by NCT ID."""
    resp = requests.get(f"{BASE_URL}/studies/{nct_id}", params={"format": fmt}, timeout=30)
    resp.raise_for_status()
    return resp.json() if fmt == "json" else resp.text
```

## Auto-paginate every match

The response field is `nextPageToken`; it is sent back as the `pageToken` request
parameter. Cap the pull to stay polite to the rate limit.

```python
def search_all(max_results: Optional[int] = None, **kwargs) -> list[dict]:
    studies: list[dict] = []
    page_token = None
    kwargs["page_size"] = 1000  # max page size
    while True:
        result = search_studies(page_token=page_token, count_total=False, **kwargs)
        studies.extend(result.get("studies", []))
        if max_results and len(studies) >= max_results:
            return studies[:max_results]
        page_token = result.get("nextPageToken")
        if not page_token:
            return studies
```

## Rate-limit retry (HTTP 429)

```python
import time

def get_with_retry(url, params=None, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(60)            # honor ~50 req/min limit
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError("Max retries exceeded (rate limited)")
```

## Export to CSV

`format=csv` returns CSV text rather than a JSON object.

```python
csv_text = search_studies(condition="heart disease", status="RECRUITING",
                          page_size=1000, fmt="csv")
with open("heart_disease_trials.csv", "w") as f:
    f.write(csv_text)
```

## Extract a compact summary

Guard every access — phase, enrollment, and summary are frequently absent.

```python
def summarize(study: dict) -> dict:
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    return {
        "nct_id":     ident.get("nctId"),
        "title":      ident.get("officialTitle") or ident.get("briefTitle"),
        "status":     status.get("overallStatus"),
        "phase":      design.get("phases", []),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "last_update": status.get("lastUpdatePostDateStruct", {}).get("date"),
        "summary":    p.get("descriptionModule", {}).get("briefSummary"),
    }
```

## Combined multi-criteria search

Prefer server-side `filter.phase` over client-side filtering. Use client filtering
only for conditions the API cannot express.

```python
# Server-side: Phase 2/3 immunotherapy lung-cancer trials in California
result = search_studies(
    condition="lung cancer",
    intervention="immunotherapy",
    location="California",
    status=["RECRUITING", "NOT_YET_RECRUITING"],
    phase=["PHASE2", "PHASE3"],
    page_size=100,
)
print(result.get("totalCount"), "matches")

# Client-side fallback: only trials that already posted results
with_results = [s for s in result["studies"] if s.get("hasResults")]
```

## Eligibility and contacts from a known NCT ID

```python
study = get_study("NCT04852770")
elig = study["protocolSection"]["eligibilityModule"]
print(elig.get("minimumAge"), "-", elig.get("maximumAge"), elig.get("sex"))
print(elig.get("eligibilityCriteria"))   # CommonMark markdown

contacts = study["protocolSection"].get("contactsLocationsModule", {})
for c in contacts.get("centralContacts", []):
    print(c.get("name"), c.get("phone"), c.get("email"))
for loc in contacts.get("locations", []):
    print(loc.get("facility"), "-", loc.get("city"), loc.get("state"), loc.get("status"))
```
