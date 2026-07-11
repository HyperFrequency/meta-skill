---
name: fda-database
version: 0.1.0
description: >-
  Query the openFDA REST API (public, api_key optional) for U.S. FDA regulatory data
  across drugs, medical devices, foods, animal/veterinary products, and substances. Use
  to pull adverse events (FAERS/MAUDE/CAERS), drug labeling (SPL), recalls and
  enforcement reports, device 510(k) clearances and PMA approvals, NDC directory and
  UNII/substance records, device classification, and drug shortages — for
  pharmacovigilance, safety-signal detection, recall monitoring, approval/regulatory
  research, and chemical-identifier mapping. Do NOT use for drug bioactivity/chemistry
  (use `chembl-database`), clinical-trial registrations (use `clinicaltrials-database`),
  structured pulls of other named databases (use `database-lookup`), or making
  patient-care decisions (`clinical-decision-support`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# openFDA Database

## Overview

**openFDA** is the U.S. Food and Drug Administration's public API program. It exposes
FDA post-market and regulatory datasets as a uniform REST service that returns JSON — no
client library required, plain HTTP works. Every endpoint follows one URL shape:

```
https://api.fda.gov/{category}/{endpoint}.json
```

There are five categories and ~20 endpoints. An `api_key` is optional but strongly
recommended (it raises the daily quota from 1,000 to 120,000 requests). Requests must use
HTTPS.

Every response is `{ "meta": {...}, "results": [...] }`, where `meta.results.total` is the
match count and each object in `results` is a record. A failed query instead returns
`{ "error": { "code": ..., "message": ... } }`.

See [references/api-reference.md](references/api-reference.md) for the full endpoint
catalogue, per-endpoint key fields, query-syntax operators, rate limits, and error codes.

## When to Use This Skill

- **Pharmacovigilance / safety signals** — mine drug (FAERS), device (MAUDE), or food
  (CAERS) adverse-event reports; count reactions; detect and rank safety signals.
- **Recall & enforcement monitoring** — track drug/device/food recalls by class,
  reason (e.g. undeclared allergen, Listeria), firm, or distribution region.
- **Regulatory / approval research** — Drugs@FDA approval history, device 510(k)
  clearances, PMA approvals, priority-review designations.
- **Product identification** — resolve NDC codes, device UDIs, product/device codes,
  device classification and risk class.
- **Substance / chemistry identifiers** — map UNII ↔ CAS ↔ InChIKey ↔ molecular
  formula and traverse substance relationships (active moiety, metabolite, salt form).
- **Supply monitoring** — current and resolved drug shortages.

## When NOT to Use This Skill

- **Drug bioactivity / molecular chemistry** — for IC50/Ki, targets, or SAR use
  `chembl-database`; openFDA `other/substance` gives identifiers and structure, not assay
  data.
- **Clinical-trial registrations** — trial protocols, eligibility, and outcomes live in
  `clinicaltrials-database`, not openFDA.
- **Published literature** — for papers about a drug or device use `literature-search` /
  `pubmed-database`.
- **Other named scientific databases** — for a structured pull of a different source,
  route through `database-lookup`.
- **Patient-care decisions** — openFDA is population-level surveillance data with strong
  reporting bias; never use a raw adverse-event count as clinical guidance. That needs
  `clinical-decision-support` and licensed judgment.
- **Non-public or full-database analytics** — openFDA carries public data only. For
  whole-dataset joins, download the bulk JSON files from open.fda.gov instead of paging.

## Quick Start

```python
import requests

BASE = "https://api.fda.gov"
API_KEY = "YOUR_KEY"  # optional; omit the api_key param to run keyless

# 1. Drug adverse events for a drug, newest first
resp = requests.get(f"{BASE}/drug/event.json", params={
    "api_key": API_KEY,
    "search": "patient.drug.medicinalproduct:aspirin",
    "sort": "receivedate:desc",
    "limit": 10,
}, timeout=30)
data = resp.json()
print(data["meta"]["results"]["total"], "total reports")

# 2. Aggregate: top reactions for a drug (note the .exact suffix)
counts = requests.get(f"{BASE}/drug/event.json", params={
    "api_key": API_KEY,
    "search": "patient.drug.medicinalproduct:metformin",
    "count": "patient.reaction.reactionmeddrapt.exact",
}, timeout=30).json()
for row in counts["results"][:5]:
    print(row["term"], row["count"])
```

> **Gotcha:** `limit` defaults to **1**. Always set it explicitly (max 1000). To get only
> the total match count without records, set `limit=1` and read
> `meta.results.total`.

## Endpoint Map

| Category | Endpoints | Backing dataset |
| --- | --- | --- |
| `drug` (6) | `event`, `label`, `ndc`, `enforcement`, `drugsfda`, `drugshortages` | FAERS, SPL, NDC Directory, Enforcement, Drugs@FDA |
| `device` (9) | `event`, `510k`, `classification`, `enforcement`, `recall`, `pma`, `registrationlisting`, `udi`, `covid19serology` | MAUDE, GUDID, PMA/510(k) |
| `food` (2) | `event`, `enforcement` | CAERS, Enforcement |
| `animalandveterinary` (1) | `event` | CVM adverse events (VeDDRA-coded) |
| `other` (2) | `substance`, `nsde` | GSRS substance registry |

Per-endpoint purposes and searchable key fields are in
[references/api-reference.md](references/api-reference.md).

## Query Essentials

Filtering is driven by the `search` parameter using Lucene-style syntax:

- **Field match** — `field:value` (e.g. `patient.drug.medicinalproduct:aspirin`).
- **Boolean** — join with `+AND+`, `+OR+`, `+NOT+`; a space inside `(a b)` means OR.
- **Wildcards** — `met*`, `*cillin*` (leading wildcards are slow; avoid `search=*`).
- **Exact phrase** — quote multi-word values: `"heart attack"`.
- **Ranges** — `receivedate:[20200101+TO+20201231]`, open-ended `[65+TO+*]`.
- **Existence** — `_exists_:field`, `_missing_:field`.
- **Aggregate** — `count=field` returns `{term, count}` rows instead of records. For
  multi-word fields append `.exact` or you count individual words.
- **Paginate** — `skip` + `limit`; `skip` is capped at **25,000** (skip+limit ≤ 26,000).
  For deeper pulls, partition the query by date range.
- **Rate limits** — 240 req/min for everyone; 1,000/day keyless vs 120,000/day with a key.
  On HTTP `429`, back off (~60 s) and retry.

## Common Analysis Patterns

Copy-paste helpers (rate-limited + cached HTTP client, auto-pagination, and the patterns
below) are in [references/python-recipes.md](references/python-recipes.md):

- **Drug safety profile** — total events, top reactions, serious-event rate, recent recalls.
- **Temporal trend** — monthly adverse-event counts over a date window.
- **Comparative safety** — serious-event / death rates across a list of products.
- **Cross-database device lookup** — join events, 510(k), recalls, and UDI for one device.
- **Allergen recall monitor** — scan `food/enforcement` for undeclared-allergen recalls.
- **Substance resolution** — UNII → CAS / InChIKey / structure via `other/substance`.

## Failure Modes and Boundaries

- **`limit` defaults to 1** — forgetting it silently returns a single record.
- **Counting words instead of phrases** — a `count` on a text field without `.exact`
  splits multi-word terms; always use `.exact` for reactions, device names, reasons.
- **`skip` cap (25,000)** — deep pagination fails past ~26,000 records; slice by date.
- **`400 INVALID_QUERY`** — malformed `search` (unescaped quote, bad field name, wrong
  boolean encoding). Verify field names against the reference and URL-encode values.
- **`404 NOT_FOUND`** — no matching records; openFDA returns 404 (not an empty list) for
  a zero-hit search. Treat 404 as "no results," not as an error.
- **`429`** — rate limit exceeded; add delay / exponential backoff, register a key.
- **Sparse records** — not every report populates every field; guard every access with
  `.get()`. Reporting is voluntary and biased, so counts reflect *reporting*, not
  incidence or causation.
- **`meta.results.total` is approximate** for very large result sets.

## References

- [references/api-reference.md](references/api-reference.md) — base URL, authentication,
  rate limits, the full `search`/`count`/`sort`/`skip` syntax, response and error-code
  formats, recall classification levels, and the endpoint catalogue (all five categories,
  each endpoint's dataset and searchable key fields).
- [references/python-recipes.md](references/python-recipes.md) — reusable HTTP client with
  rate limiting and caching, auto-pagination, and the six analysis patterns above.
