---
name: uspto-database
version: 0.1.0
description: >-
  Query the USPTO's public APIs for U.S. patent and trademark data: full-text patent
  search via the PatentSearch API (ElasticSearch successor to legacy PatentsView), patent
  examination/prosecution history (PEDS / Open Data Portal), trademark status and documents
  (TSDR), patent and trademark assignment (ownership) records, enriched citations,
  office-action text/citations/rejections, PTAB trials, and litigation. Use for prior-art
  and patentability searches, IP landscape and portfolio analysis,
  prosecution-history mining, competitor/freedom-to-operate monitoring, and ownership
  tracking. Endpoints are REST/JSON (assignment APIs return XML) and need a free USPTO API
  key. Do NOT use for scientific literature (`pubmed-database`, `literature-search`),
  chemical/bioactivity data (`chembl-database`, `pubchem-database`), company/economic stats
  (`fred-economic-data`), a structured pull of another named source (`database-lookup`), or
  legal opinions on patentability/infringement — this returns raw records, not counsel.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# USPTO Database

## Overview

The U.S. Patent and Trademark Office (USPTO) publishes a family of REST APIs for patent
and trademark data. They cover four broad jobs:

1. **Search** granted patents and pre-grant publications by keyword, inventor, assignee,
   classification, or date — the **PatentSearch API** (`search.patentsview.org`).
2. **Examination history** — the prosecution timeline, status, and office actions for an
   application (PEDS / the new Open Data Portal at `data.uspto.gov`).
3. **Trademarks** — status, prosecution, and documents via **TSDR**
   (`tsdrapi.uspto.gov`).
4. **Ownership & specialized data** — patent/trademark **assignments**, enriched
   **citations**, **office-action** text, **PTAB** trials, and **litigation** records.

Most endpoints return JSON and authenticate with a single `X-Api-Key` header. The
assignment APIs are the exception — they return XML. This skill is a router: it maps the
API family, shows the query shapes you will use most, and delegates full endpoint/field
tables to `references/`.

## When to Use This Skill

- **Prior-art / patentability search** — find granted patents or publications on a topic
  before filing or to invalidate a claim.
- **IP landscape & competitor analysis** — who holds patents in a technology area (by CPC
  class, assignee, inventor, or date range).
- **Portfolio analysis** — enumerate and characterize a company's or inventor's patents
  and trademarks.
- **Prosecution-history mining** — office actions, rejection types (§102/§103/§112/§101),
  pendency, and outcomes for one or many applications.
- **Freedom-to-operate / monitoring** — track new grants, status changes, PTAB
  challenges, or litigation touching specific patents.
- **Ownership tracking** — assignment (transfer, security interest, merger) chains for a
  patent, application, or trademark.
- **Trademark status monitoring** — is a mark live, pending, published for opposition,
  abandoned, or cancelled.

## When NOT to Use This Skill

- **Scientific literature** — for papers, not patents, use `pubmed-database`,
  `literature-search`, or `openalex-database`.
- **Chemical / bioactivity data** — structures, assays, targets: `pubchem-database`,
  `chembl-database`. USPTO gives you the patent document, not curated chemistry.
- **Non-U.S. IP** — these APIs are USPTO (U.S.) only. For worldwide families use EPO
  OPS / Espacenet, WIPO PATENTSCOPE, or Google Patents (out of scope here).
- **Company or macroeconomic statistics** — use `fred-economic-data` or
  `datacommons-client`.
- **A structured pull of some other named database** — route through `database-lookup`.
- **Legal conclusions** — validity, infringement, and patentability opinions require
  licensed counsel. These APIs return raw records; never present a search result as legal
  advice.

## API Family

| Job | API | Base URL | Format |
| --- | --- | --- | --- |
| Patent/publication search | PatentSearch | `https://search.patentsview.org/api/v1/` | JSON |
| Examination history | PEDS → Open Data Portal | `https://data.uspto.gov/` | JSON |
| Trademark status/docs | TSDR | `https://tsdrapi.uspto.gov/ts/cd/` | JSON/XML |
| Patent ownership | Patent Assignment | `https://assignment-api.uspto.gov/patent/v1.4/` | XML |
| Trademark ownership | Trademark Assignment | `https://assignment-api.uspto.gov/trademark/v1.4/` | XML |
| Citations | Enriched Citation | Open Data Portal | JSON |
| Office actions | OA Text / Citations / Rejection | Open Data Portal | JSON |
| Post-grant trials | PTAB | Open Data Portal | JSON |
| Litigation | Patent Litigation Cases | Open Data Portal | JSON |

## Authentication & Setup

1. Register for a free key at **https://account.uspto.gov/api-manager/**. This single key
   works across TSDR, assignments, and the Open Data Portal APIs.
2. The **PatentSearch API** uses a **separate** PatentsView-issued key — request it at
   **https://patentsview.org/** (search-api access).
3. Store both as environment variables; never hardcode them:

```bash
export USPTO_API_KEY="your_uspto_key"          # TSDR, assignments, Open Data Portal
export PATENTSVIEW_API_KEY="your_patentsview_key"  # PatentSearch API
```

Every request sends the key in the header `X-Api-Key: <key>`.

## Quick Start — PatentSearch

PatentSearch is a `POST` API with a JSON body of four keys: `q` (query, required),
`f` (fields), `s` (sort), `o` (options).

```python
import os, requests

url = "https://search.patentsview.org/api/v1/patent"
headers = {"X-Api-Key": os.environ["PATENTSVIEW_API_KEY"],
           "Content-Type": "application/json"}

body = {
    "q": {"_and": [
        {"patent_date": {"_gte": "2024-01-01"}},
        {"patent_abstract": {"_text_all": ["machine", "learning"]}},
        {"assignees.assignee_organization": {"_text_any": ["Google", "Alphabet"]}},
    ]},
    "f": ["patent_id", "patent_title", "patent_date", "assignees.assignee_organization"],
    "s": [{"patent_date": "desc"}],
    "o": {"size": 100},
}
resp = requests.post(url, headers=headers, json=body, timeout=60)
resp.raise_for_status()
data = resp.json()
print(data["total_hits"], "hits")
for p in data["patents"]:
    print(p["patent_id"], p["patent_title"])
```

**Query operators** (use `_text_*` for text fields — far faster than `_contains`):

- Equality / negation: `{"field": "v"}`, `{"field": {"_eq": "v"}}`, `_neq`
- Comparison: `_gt`, `_gte`, `_lt`, `_lte`
- Full-text: `_text_all` (all terms), `_text_any` (any term), `_text_phrase` (exact)
- String: `_begins`, `_contains`
- Logical: `_and`, `_or`, `_not`; an array `["A", "B"]` is an implicit OR

**Rate limit: 45 requests/minute.** On HTTP `429`, back off and retry.

The exact endpoint list, full field dictionary, response envelope, pagination contract
(field naming and page size have shifted across releases — confirm at the docs), and error
codes are in **[references/patentsearch-api.md](references/patentsearch-api.md)**.

## Examination History (PEDS / Open Data Portal)

Prosecution data — filing → office actions → allowance/abandonment, transaction codes,
status, patent-term adjustment — historically came from **PEDS** (`ped.uspto.gov`), which
replaced the decommissioned PAIR Bulk Data. USPTO is **migrating this data to the Open Data
Portal** (`data.uspto.gov`); PEDS endpoints are being retired, so verify the current
access path before building against it.

For scripted access, the community library **`uspto-opendata-python`**
(`pip install uspto-opendata-python`, docs at `docs.ip-tools.org`) wraps examination data
by application or patent number. Coverage runs **1981–present** (some records to 1935).

Key transaction codes: `CTNF` (non-final rejection), `CTFR` (final rejection), `NOA`
(notice of allowance), `ISS.FEE` (issue fee), `ABND` (abandoned). Full code tables,
library usage, the ODP migration notes, and prosecution-analysis patterns (pendency,
rejection-type counts) are in
**[references/peds-and-examination.md](references/peds-and-examination.md)**.

## Trademarks (TSDR)

TSDR retrieves trademark case status, prosecution history, owners, and goods/services by
serial or registration number:

```python
import os, requests
serial = "87654321"
r = requests.get(
    f"https://tsdrapi.uspto.gov/ts/cd/casedocs/sn{serial}/info.json",
    headers={"X-Api-Key": os.environ["USPTO_API_KEY"]}, timeout=30)
tm = r.json()["TradeMarkAppln"]
print(tm["MarkVerbalElementText"], "→", tm["MarkCurrentStatusExternalDescriptionText"])
```

Use registration lookups via `.../casedocs/rn{registration_number}/info.json`. Common
statuses: `REGISTERED`, `PENDING`, `PUBLISHED FOR OPPOSITION`, `ABANDONED`, `CANCELLED`,
`SUSPENDED`. TSDR response fields, status handling, and the **Trademark Assignment Search**
API are in **[references/trademark-api.md](references/trademark-api.md)**.

## Ownership, Citations, Office Actions & More

- **Assignments** (patent + trademark) — ownership transfers, security interests, mergers.
  `GET .../assignment/patent/{patent_number}` returns **XML** (parse with `xml.etree`).
- **Enriched Citation API** — forward/backward citations, examiner vs. applicant.
- **Office-Action APIs** — full OA text, extracted citations, and rejection reasons
  (§102 anticipation, §103 obviousness, §112 written description/indefiniteness, §101
  eligibility).
- **PTAB API** — IPR/PGR/CBM trials and appeal decisions.
- **Patent Litigation Cases API** — district-court infringement records.

Endpoints, request/response shapes, and combined-workflow patterns (e.g. one patent →
search + examination + assignments + citations) are in
**[references/additional-apis.md](references/additional-apis.md)**.

## Best Practices & Gotchas

- **Two keys, two systems** — PatentSearch uses the PatentsView key; everything else uses
  the USPTO account key. A `401` usually means the wrong key for that host.
- **Request only needed fields** (`f`) and use date ranges to shrink responses.
- **Paginate deliberately** — page sizes are capped (up to 1,000 on PatentSearch); pull in
  batches and cache results, since USPTO data changes slowly.
- **Handle sparse data** — not every field is populated for every record; code defensively
  for missing keys.
- **XML vs JSON** — assignment APIs return XML; don't call `.json()` on them.
- **Coverage & sunsets** — legacy PatentsView API was discontinued (May 2025); PAIR Bulk
  Data is gone; PEDS is migrating to `data.uspto.gov`. Confirm live endpoints before a
  long-running job.
- **Discovery vs. detail** — use PatentSearch to *find* patents, PEDS/ODP for *prosecution*
  detail, and assignments for *ownership*; combine them rather than forcing one API to do
  all three.

## References

- **[references/patentsearch-api.md](references/patentsearch-api.md)** — PatentSearch
  endpoints, field dictionary, operators, pagination, response envelope, error codes.
- **[references/peds-and-examination.md](references/peds-and-examination.md)** — PEDS +
  Open Data Portal examination data, `uspto-opendata-python`, transaction/status codes,
  prosecution-analysis recipes.
- **[references/trademark-api.md](references/trademark-api.md)** — TSDR and Trademark
  Assignment Search.
- **[references/additional-apis.md](references/additional-apis.md)** — Enriched Citation,
  Office-Action (Text/Citations/Rejection/Weekly Zips), Patent Assignment, PTAB,
  Litigation, Cancer Moonshot, OCE status/event codes.
