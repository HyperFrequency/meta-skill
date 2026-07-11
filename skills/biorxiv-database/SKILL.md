---
name: biorxiv-database
version: 0.1.0
description: >-
  Query the public bioRxiv (and medRxiv) preprint API for life-sciences and
  health-sciences preprints: fetch metadata by date range, DOI, or recent
  interval; paginate the full result set; screen locally for keywords or
  authors; and resolve PDF/HTML/JATS-XML URLs for full text. Use when building a
  systematic preprint literature review, tracking an author or topic across a
  date window, or pulling structured preprint metadata for citation or trend
  analysis. Do NOT use for peer-reviewed journal articles (use a PubMed/Crossref
  tool via `citation-management`), for arXiv or general scholarly search (use
  `research-lookup` / `literature-search`), or for semantic Q&A over a paper you
  already have — this reaches only the bioRxiv/medRxiv metadata API.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# bioRxiv Database

## Overview

bioRxiv and medRxiv expose a free, keyless REST API at `api.biorxiv.org` that
returns structured JSON metadata for preprints — DOI, title, authors, abstract,
date, version, category, and links to full text. This skill teaches you to query
that API correctly: retrieve by date range / DOI / recent interval, paginate the
full result set, screen results locally for keywords and authors, and build
PDF/HTML/JATS-XML URLs for retrieval. The same host serves medRxiv — swap the
server segment to reach it.

Only three things are true server-side queries: **date range**, **single DOI**,
and **recent interval**. Keyword and author search are **client-side filters**
over a fetched window. Internalize that and the rest follows.

## When to Use This Skill

- Systematic or scoping literature review over preprints in a topic and window.
- Tracking a specific author's or lab's preprints over time.
- Pulling structured metadata (titles, DOIs, abstracts) for downstream citation,
  deduplication, or trend analysis.
- Downloading preprint PDFs or JATS XML for full-text processing.
- Checking whether a preprint was later published in a journal (`/pubs`).
- Filtering by bioRxiv/medRxiv subject category.

## When NOT to Use This Skill

- **Peer-reviewed journal articles** as the primary target → use a
  PubMed/Crossref/Scholar tool; `citation-management` for DOI→BibTeX.
- **arXiv, SSRN, or cross-source scholarly search** → `research-lookup`,
  `literature-search`, or `paper-lookup`.
- **Relevance-ranked or semantic search** → this API returns posts in date order
  with no ranking; rank yourself or use a search-oriented sibling.
- **Q&A / extraction over a PDF you already hold** → a document-reading tool.
- **A structured lookup in a different named database** → `database-lookup`.

## The API in One Minute

- Host: `https://api.biorxiv.org` · content host: `https://www.biorxiv.org`.
- Server segment: `biorxiv` or `medrxiv` — everything else is identical.
- Public and keyless. Set a descriptive `User-Agent`, add a ~0.5s delay between
  calls, and cache responses.
- Read `messages[0].status == "ok"` and `messages[0].total` — not just the HTTP
  code — to know a call succeeded and how many records exist.

Core endpoint (the workhorse):

```
GET /details/{server}/{interval}/{cursor}/{format}
GET /details/{server}/{DOI}/na/{format}      # single paper; /na/ = cursor slot
```

`{interval}` is a date range `YYYY-MM-DD/YYYY-MM-DD`, a number `N` (the N most
recent posts), or `Nd` (posts from the last N days). Only the **date-range** form
takes the `{cursor}`/`{format}` slots and paginates; the `N` and `Nd` forms take
**no cursor** and return a single response — appending `/0` errors with `"Both
dates must be in yyyy-mm-dd format"`. Full endpoint list, record fields,
categories, and error semantics live in **[references/api.md](references/api.md)**.

## Retrieval Patterns

Fetch a date range (paginating to the end — see the critical note below):

```python
import requests
API, HDRS = "https://api.biorxiv.org", {"User-Agent": "biorxiv-skill/0.1"}
url = f"{API}/details/biorxiv/2024-01-01/2024-01-31/0"
page = requests.get(url, headers=HDRS, timeout=30).json()
records = page["collection"]            # first page only — keep going by cursor
total = int(page["messages"][0]["total"])
```

Single paper by DOI, and last-30-days feed:

```python
requests.get(f"{API}/details/biorxiv/10.1101/2024.01.15.123456/na", headers=HDRS)
requests.get(f"{API}/details/biorxiv/30d", headers=HDRS)   # last 30 days — NO cursor slot
```

Ready-to-run, correctly-paginated functions for range fetch, keyword/author
screening, DOI lookup, PDF download, published-version check, and DataFrame
analysis are in **[references/recipes.md](references/recipes.md)**.

## Keyword and Author Search Are Client-Side

There is no server-side keyword or author endpoint. Fetch a date window (and
optionally a category), then filter locally:

- **Keyword**: case-insensitive substring over `title` + `abstract` (OR by
  default; combine with `all()` for AND).
- **Author**: `authors` is a plain comma-separated string, so matching is a
  coarse substring — prefer a distinctive last name plus a date window, and
  de-duplicate on `doi`.

Because filtering happens after retrieval, always fetch the **whole** window
first. See `screen_keywords` / `screen_author` in `references/recipes.md`.

## Categories and medRxiv

Filter by subject category either as a `category=` querystring on `/details`, or
(more reliably) by filtering the record's `category` field client-side — the
exact querystring spelling varies. The 27 bioRxiv categories and guidance for
medRxiv's health-science set are in `references/api.md`. For medRxiv, swap
`biorxiv` → `medrxiv` in both the API path and the `www.medrxiv.org` content
host; the shapes are otherwise identical.

## Full Text

Build URLs from the record's `doi` and its **real** `version` (never a hardcoded
`v1` — the source tool's bug):

```
PDF   https://www.biorxiv.org/content/{doi}v{version}.full.pdf
HTML  https://www.biorxiv.org/content/{doi}v{version}
JATS  <the record's `jatsxml` field>
```

## Failure Modes and Boundaries

- **Silent truncation (most common bug):** for a date range, `/details` serves a
  fixed page (currently 30 records) per call. Fetching one page drops the rest of
  a busy window. Loop `cursor` by the page size until `count == 0` or
  `cursor >= total`.
- **Recent-feed forms don't paginate:** the numeric `N` and `Nd` intervals take
  no cursor and return a single response — `N` yields exactly N posts; `Nd`
  returns the last N days but is effectively capped (~1300 records observed) and a
  wide window like `30d` can time out. For complete coverage of a busy window, use
  the paginated date-range form.
- **No relevance ranking:** results come back in post order; rank yourself.
- **Metadata only:** abstracts are included; full text only via the PDF/HTML/JATS
  URLs above.
- **Coarse author/keyword matching:** substring over strings, not structured
  fields — expect false positives; de-duplicate on `doi`.
- **`published` lag:** journal linkage in `/details` can trail reality; use the
  `/pubs` endpoint when the publication status is the actual question.
- **Rate/etiquette:** no hard published limit, but add delays and cache; heavy
  unpaced scraping risks throttling.

## Hand-Off to Sibling Skills

- DOIs → BibTeX / reference management: `citation-management`.
- Broader synthesis across sources: `literature-review`, `literature-search`.
- arXiv / cross-source or ranked scholarly search: `research-lookup`,
  `paper-lookup`.

## References

- [references/api.md](references/api.md) — full endpoint spec, record fields,
  pagination and category rules, error handling, category list.
- [references/recipes.md](references/recipes.md) — copy-paste Python for
  paginated fetch, keyword/author screening, DOI lookup, PDF download,
  published-version check, and analysis.
