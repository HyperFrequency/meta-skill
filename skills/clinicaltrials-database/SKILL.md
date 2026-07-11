---
name: clinicaltrials-database
version: 0.1.0
description: >-
  Query the ClinicalTrials.gov REST API v2 (public, no auth) to search and retrieve
  registered clinical studies worldwide. Use when you need to find trials by condition,
  intervention/drug, location, sponsor, status, or phase; fetch a full study record by
  NCT ID (eligibility, outcomes, contacts, locations, results); paginate large result
  sets; or export trial data to JSON/CSV for research, patient matching, competitive
  intelligence, or trial monitoring. Do NOT use for published-literature or abstract
  search (use `literature-search` or `literature-review`), for drug chemistry/bioactivity
  (use `chembl-database` or `drugbank-database`), for structured pulls of other named
  scientific databases (use `database-lookup`), or for eligibility calls that require
  licensed medical judgment (`clinical-decision-support`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# ClinicalTrials.gov Database

## Overview

ClinicalTrials.gov is the U.S. National Library of Medicine registry of clinical studies
conducted around the world. Its **API v2** is a public REST service (no API key) that
returns structured study records as JSON or CSV. Every study is keyed by an **NCT ID**
(e.g. `NCT04852770`) and organized into hierarchical modules (identification, status,
sponsors, eligibility, outcomes, locations, results).

Two endpoints do almost everything:

| Purpose | Endpoint |
| --- | --- |
| Search / list studies | `GET https://clinicaltrials.gov/api/v2/studies` |
| Fetch one study | `GET https://clinicaltrials.gov/api/v2/studies/{NCT_ID}` |

Search parameters split into two families: `query.*` for free-text/relevance search
(condition, intervention, location, sponsor, term) and `filter.*` for exact-match
narrowing (status, phase, NCT-ID set, geo radius). See
[references/api-reference.md](references/api-reference.md) for the full parameter,
enum, and response-module catalogue.

## When to Use This Skill

- **Patient matching** — find recruiting trials for a condition, age, sex, or location.
- **Drug/intervention research** — track trials testing a specific drug, device, or procedure.
- **Competitive/portfolio intelligence** — enumerate a sponsor's or collaborator's trials.
- **Landscape analysis** — count and slice trials by phase, status, geography, or start date.
- **Detail extraction** — pull eligibility criteria, outcome measures, contacts, or results for a known NCT ID.
- **Bulk export** — paginate an entire result set and dump to JSON/CSV for downstream analysis.

## When NOT to Use This Skill

- **Literature / abstracts** — for publications about a trial, use `literature-search` or `literature-review`, not this registry.
- **Molecular / bioactivity data** — for drug chemistry, targets, or assays, use `chembl-database` or `drugbank-database`.
- **Other named registries/databases** — for a structured pull of a different scientific source, route through `database-lookup`.
- **Clinical decisions** — do not use trial eligibility text to make or imply a patient care decision; that needs `clinical-decision-support` and licensed judgment.
- **Non-registered studies** — trials never registered on ClinicalTrials.gov are simply absent; this API cannot surface them.

## Quick Start

No client library is required — plain HTTP works. `requests` shown for brevity.

```python
import requests

BASE = "https://clinicaltrials.gov/api/v2"

# Search: recruiting breast-cancer trials, newest first
resp = requests.get(f"{BASE}/studies", params={
    "query.cond": "breast cancer",
    "filter.overallStatus": "RECRUITING",
    "sort": "LastUpdatePostDate:desc",
    "countTotal": "true",   # REQUIRED to populate totalCount
    "pageSize": 10,
}, timeout=30)
resp.raise_for_status()
data = resp.json()

print(f"Total matches: {data['totalCount']}")
for study in data["studies"]:
    ident = study["protocolSection"]["identificationModule"]
    print(ident["nctId"], "-", ident["briefTitle"])
```

```python
# Fetch one full study by NCT ID
study = requests.get(f"{BASE}/studies/NCT04852770", timeout=30).json()
elig = study["protocolSection"]["eligibilityModule"]
print(elig.get("minimumAge"), "-", elig.get("maximumAge"), elig.get("sex"))
print(elig.get("eligibilityCriteria"))
```

> **Gotcha:** `totalCount` is omitted unless you pass `countTotal=true`. To advance
> pages, read `nextPageToken` from the response and send it back as the `pageToken`
> request parameter (the names differ).

## Core Capabilities

### Search dimensions

Combine any `query.*` and `filter.*` parameters in one request; they AND together.

- `query.cond` — condition/disease (`"type 2 diabetes"`)
- `query.intr` — intervention/drug/device (`"Pembrolizumab"`)
- `query.locn` — location text (`"New York"`); for a radius use `filter.geo` (see reference)
- `query.spons` — sponsor/collaborator (`"National Cancer Institute"`)
- `query.term` — general full-text search
- `filter.overallStatus` — comma-separated status enums (`RECRUITING,NOT_YET_RECRUITING`)
- `filter.phase` — phase enums (`PHASE2,PHASE3`)
- `filter.ids` — restrict to a set of NCT IDs

`query.*` values accept advanced search expressions (quoted phrases, `AND`/`OR`).
Full enum lists (14 statuses incl. `UNKNOWN` + expanded-access, 6 phases), sort keys, and the `filter.geo` /
`filter.advanced` syntax are in [references/api-reference.md](references/api-reference.md).

### Retrieve and navigate a study

Records are deeply nested. Common paths off `study["protocolSection"]`:

| Field | Path (under `protocolSection`) |
| --- | --- |
| NCT ID | `identificationModule.nctId` |
| Brief title | `identificationModule.briefTitle` |
| Overall status | `statusModule.overallStatus` |
| Phases | `designModule.phases` |
| Enrollment count | `designModule.enrollmentInfo.count` |
| Eligibility | `eligibilityModule` |
| Interventions | `armsInterventionsModule.interventions` |
| Locations & contacts | `contactsLocationsModule` |

Results (when present) live under a top-level `resultsSection`; `study["hasResults"]`
flags availability. Always use `.get()` with defaults — many fields are optional.

### Pagination, CSV export, and rate limits

- **Pagination** — loop on `nextPageToken`, sending it as `pageToken`; use `pageSize=1000` (the max) to minimize round-trips.
- **Field trimming** — pass `fields=` a comma-separated list of dot-path field names to shrink payloads on large pulls.
- **CSV** — set `format=csv`; the response body is CSV text, not JSON.
- **Rate limit** — roughly 50 requests/minute per IP. On HTTP `429`, back off (~60 s) and retry.

Copy-paste reusable helpers (a thin client, auto-paginate, rate-limit retry, summary
extraction, multi-criteria + phase filtering) are in
[references/python-recipes.md](references/python-recipes.md).

## Failure Modes and Boundaries

- **Missing `totalCount`** — you forgot `countTotal=true`; it is not returned by default.
- **`400 Bad Request`** — an invalid enum (status/phase) or malformed parameter; check spelling against the reference enum lists.
- **`404 Not Found`** — the NCT ID does not exist or was deleted; verify the identifier.
- **`429 Too Many Requests`** — you exceeded the rate limit; add delay and exponential backoff.
- **Partial records** — not every trial reports phase, enrollment, results, or contacts; guard every access.
- **Stale data** — the registry reflects sponsor-submitted updates, which can lag; sort by `LastUpdatePostDate` to prioritize freshness, and treat status as a snapshot.

## References

- [references/api-reference.md](references/api-reference.md) — endpoints, full parameter table, status/phase enums, sort keys, `filter.geo`/`filter.advanced`, response-module map, field paths, error codes, data standards (ISO 8601, CommonMark), and classic-API migration notes.
- [references/python-recipes.md](references/python-recipes.md) — reusable request client, auto-pagination, rate-limit retry, CSV export, summary extraction, and combined multi-criteria search patterns.
