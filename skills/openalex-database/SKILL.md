---
name: openalex-database
version: 0.1.0
description: >-
  Query OpenAlex — the free, keyless open catalog of 240M+ scholarly works plus
  authors, institutions, sources, topics, publishers, and funders — through its
  REST API at `api.openalex.org`. Use to search literature; filter works by year,
  author, institution, journal, topic, citation count, or open-access status; run
  the two-step name→ID→works lookup; aggregate with `group_by` for bibliometric
  trends; sample reproducibly; batch-resolve DOIs/ORCIDs/RORs/ISSNs; and paginate
  large extracts with cursors. Do NOT use for semantic Q&A over a paper you already
  hold, DOI→BibTeX formatting (use `citation-management`), cross-source or
  relevance-ranked scholarly search (use `research-lookup`, `literature-search`,
  `paper-lookup`), preprint-only metadata (use `biorxiv-database`), or
  whole-database analytics — download the OpenAlex snapshot instead of hammering
  the API.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-data-license: OpenAlex data is CC0 (public domain)
---

# OpenAlex Database

## Overview

OpenAlex is a fully open bibliographic graph — 240M+ works interlinked with
authors, institutions, sources (journals/repositories/conferences), topics,
publishers, and funders. It exposes one consistent, keyless REST API at
`https://api.openalex.org`. This skill teaches you to query that API correctly:
search and filter works, resolve entity names to IDs, aggregate counts, sample
reproducibly, and stream large extracts without tripping the pagination cap.

Two ideas make everything else fall into place:

1. **Filter by ID, never by name.** Names are ambiguous. Resolve a name to its
   OpenAlex ID first (one request), then filter works by that ID.
2. **`page` dies at 10,000 results; `cursor` does not.** For anything deeper than
   the first 10k rows, page with a cursor, not a page number.

## When to Use This Skill

- Literature search over a topic, with filters on year, OA status, type, or citations.
- Getting every work by an author, lab, institution, journal, funder, or country.
- Bibliometric aggregation: publications per year, top topics, most-cited works,
  collaboration counts — via `group_by`, which returns counts without fetching rows.
- Citation analysis: who cites a work, its references, its citation count over time.
- Reproducible random sampling of the literature for a study.
- Batch-resolving lists of DOIs, ORCIDs, RORs, ISSNs, or PMIDs to full records.
- Bulk-extracting a filtered corpus (titles, abstracts, metadata) to CSV/JSON.

## When NOT to Use This Skill

- **Semantic Q&A or extraction over a full-text PDF you already have** → a
  document-reading tool; OpenAlex serves metadata, not article bodies.
- **DOI → BibTeX / reference-manager formatting** → `citation-management`.
- **Cross-source or relevance-ranked scholarly search** (Semantic Scholar, Google
  Scholar, arXiv, PubMed together) → `research-lookup`, `literature-search`,
  `paper-lookup`, `literature-review`.
- **Preprint-only metadata (bioRxiv/medRxiv)** → `biorxiv-database`.
- **A structured lookup in a different named database** → `database-lookup`.
- **Whole-database analytics** (counting across all 240M works, joins, full scans)
  → download the free OpenAlex data snapshot from S3 and query it locally; do not
  paginate the API through the entire corpus.

## The API in One Minute

- Base URL: `https://api.openalex.org`. No API key, no auth.
- **Always add `mailto=you@example.edu`** to join the polite pool: 10 req/s
  instead of 1, same 100k requests/day. Omitting it risks throttling.
- List endpoints (`/works`, `/authors`, …) wrap results in `{ "meta": {...},
  "results": [...] }`. A single-entity URL (`/works/W2741809807`) returns the bare
  object. `group_by` returns `{ "group_by": [...] }`.
- Seven core entity types: **works, authors, sources, institutions, topics,
  publishers, funders** (plus `/keywords`, `/concepts`, `/text`). All share the
  same query grammar below.

### Query grammar (works on every endpoint)

| Param | Purpose | Example |
| --- | --- | --- |
| `filter=` | AND-joined conditions | `publication_year:2023,is_oa:true` |
| `search=` | full-text (title+abstract+fulltext) | `search=machine+learning` |
| `sort=` | order results | `cited_by_count:desc` |
| `per-page=` | page size, **max 200** | `per-page=200` |
| `page=` / `cursor=` | shallow / deep paging | `cursor=*` |
| `sample=` + `seed=` | reproducible random rows (max 10k) | `sample=100&seed=42` |
| `select=` | trim returned fields | `select=id,title,cited_by_count` |
| `group_by=` | aggregate counts by a field | `group_by=publication_year` |

**Filter operators:** `,` = AND · `|` = OR (up to 50 values, great for batch ID
lookups) · `+` = AND *within one attribute* (e.g. co-authorship) · `!` = negation
· `>` `<` and `2018-2022` ranges for numeric/date fields · `.search` suffix for
per-field text search (`title.search:crispr`).

Full endpoint list, every filter, response schemas, external-ID formats, cursor
pagination, abstract reconstruction, error codes, and rate-limit detail live in
[references/api.md](references/api.md).

## Core Patterns

**Search + filter + sort** (highly-cited recent open-access papers):

```
GET /works?search=quantum+computing&filter=publication_year:>2020,is_oa:true
          &sort=cited_by_count:desc&per-page=200&mailto=you@example.edu
```

**Two-step name → ID → works** (never filter by a raw name):

```
GET /authors?search=Jennifer+Doudna&per-page=1      # → id: A5089…  (or use /autocomplete)
GET /works?filter=authorships.author.id:A5089…&per-page=200
```

The same pattern resolves institutions (`authorships.institutions.id`), journals
(`primary_location.source.id`), funders (`grants.funder`), and topics (`topics.id`).

**Aggregate without fetching rows** (`group_by` returns counts only):

```
GET /works?filter=authorships.institutions.id:I136199984&group_by=publication_year
GET /works?filter=authorships.institutions.id:I136199984&group_by=topics.id
```

**Batch-resolve IDs** with `|` (up to 50 per request) instead of N calls:

```
GET /works?filter=doi:10.1038/xyz|10.1126/abc|10.1371/def&per-page=50
```

**Reproducible sample** (use `sample`+`seed`, never random `page` numbers — those
bias results):

```
GET /works?filter=publication_year:2023&sample=100&seed=42
```

Worked, copy-pasteable recipes (Python `requests` client with backoff, cursor-based
bulk export to CSV, citation graphs, collaboration queries, research-output
dashboards) are in [references/recipes.md](references/recipes.md).

## Critical Rules

- **Polite pool always.** Pass `mailto=`. It is the difference between 10 req/s and
  getting 403-throttled at 1 req/s.
- **IDs, not names, in filters.** `filter=author_name:Einstein` does not exist;
  resolve to an ID first (or `/autocomplete/authors?q=` for a fast picker).
- **`per-page=200`** for extraction — 8× fewer round-trips than the default 25.
- **Deep pagination needs a cursor.** `page`-based paging is capped at 10,000
  results (`page × per-page ≤ 10000`); past that, start with `cursor=*` and follow
  `meta.next_cursor` until it is null. See [references/api.md](references/api.md).
- **Abstracts are inverted.** Works carry `abstract_inverted_index`, not plain
  text — reconstruct word order from the position lists (helper in
  [references/recipes.md](references/recipes.md)).
- **`select=` to shrink payloads.** Return only the fields you use; large `/works`
  objects are heavy.
- **Back off on 403/429/5xx** with exponential delay; retry idempotent GETs.
- **Whole-corpus work → snapshot, not API.** The full dataset is a free CC0
  download; scanning 240M works over HTTP is an anti-pattern.

## Related Skills

- `biorxiv-database` — preprint-only (bioRxiv/medRxiv) metadata.
- `citation-management` — DOI/PMID → BibTeX and reference-manager workflows.
- `research-lookup`, `literature-search`, `paper-lookup`, `literature-review` —
  cross-source, relevance-ranked, or synthesized scholarly search.
- `database-lookup` — generic router to other named scientific databases.
