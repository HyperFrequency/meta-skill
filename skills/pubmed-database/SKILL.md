---
name: pubmed-database
version: 0.1.0
description: >-
  Direct REST access to PubMed/MEDLINE through NCBI's E-utilities API: build
  precise Boolean + MeSH + field-tag queries, run ESearch/EFetch/ESummary/ELink,
  paginate large result sets via the history server, match citations, and export
  metadata for systematic reviews and literature analysis. Use when you need
  programmatic HTTP access to biomedical literature, complex controlled-vocabulary
  queries, PMID/DOI/PMC resolution, batch record retrieval, or a reproducible,
  documented search strategy. Do NOT use for Python-first Entrez wrappers (use
  `biopython` Bio.Entrez), DOI→BibTeX or reference-manager formatting (use
  `citation-management` / `pyzotero`), preprints (use `biorxiv-database`), trial
  registries (use `clinicaltrials-database`), ranked cross-source scholarly search
  (use `research-lookup` / `literature-search`), or a structured pull from another
  named database (use `database-lookup`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# PubMed Database

## Overview

PubMed is the U.S. National Library of Medicine's index of MEDLINE and life-sciences
literature — over 37M citations, keyed by **PMID**. NCBI exposes it programmatically
through the **E-utilities**, a public REST API (no key required, but a key raises your
rate limit). This skill covers the two hard parts of using it well: **constructing a
precise query** with Boolean operators, field tags, and MeSH controlled vocabulary; and
**driving the E-utilities** to search, fetch, batch, and link records reproducibly.

All endpoints share one base URL:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

The endpoints you will actually use:

| Endpoint | Verb it does | Returns |
| --- | --- | --- |
| `esearch.fcgi` | Search → list of PMIDs (+ optional history handle) | `Count`, `IdList`, `WebEnv`, `QueryKey` |
| `efetch.fcgi` | Download full records | abstract / MEDLINE / XML text |
| `esummary.fcgi` | Lightweight document summaries | title, authors, journal, date, DOI |
| `epost.fcgi` | Upload a PMID list to the history server | `WebEnv`, `QueryKey` |
| `elink.fcgi` | Related articles + cross-DB links | neighbor PMIDs, LinkOut URLs |
| `einfo.fcgi` · `espell.fcgi` · `ecitmatch.cgi` | field list · spelling · citation→PMID | metadata / suggestion / PMID |

## When to Use This Skill

- Searching biomedical / life-sciences literature by topic, author, journal, date, or article type.
- Building complex queries with Boolean operators, field tags, or MeSH terms.
- Programmatic, automated, or bulk retrieval of citations, abstracts, or MEDLINE records.
- Conducting a systematic review or meta-analysis that needs a documented, reproducible search string.
- Resolving PMIDs, DOIs, or PMC IDs, and matching partial citations to PMIDs.
- Finding related articles and cross-links to other NCBI databases (GenBank, ClinicalTrials.gov, PMC).

## When NOT to Use This Skill

- **Python-first Entrez work** where an object wrapper is cleaner than raw HTTP → use `biopython` (`Bio.Entrez`).
- **DOI → BibTeX, `.nbib` parsing, or reference-manager formatting** → use `citation-management` / `pyzotero`.
- **Preprints** (bioRxiv/medRxiv) → use `biorxiv-database`; **trial registries** → use `clinicaltrials-database`.
- **Ranked or semantic cross-source scholarly search** (arXiv, Scholar, relevance Q&A over a paper you hold) → use `research-lookup`, `literature-search`, `paper-lookup`.
- **A structured lookup in a different named database** → use `database-lookup`.
- Full-text mining as the goal — PubMed serves citations/abstracts; full text lives behind PMC or publisher LinkOut.

## The E-utilities in One Minute

- **Public, keyless** to start. Register an NCBI account to get an `api_key`; pass it as `&api_key=...`.
- **Rate limits:** 3 requests/sec without a key, 10 requests/sec with one. Always send a descriptive `User-Agent`. Cache responses locally.
- **`retmode=json`** for machine parsing on ESearch/ESummary/EInfo; EFetch's rich formats are text/XML only.
- **`retmax`** caps at 10,000 per call; the web display caps at 10,000 total — beyond that, page with the history server.
- Read the response body, not just the HTTP code: a 200 can still carry an `<ERROR>` element or an empty `IdList`.

Full endpoint parameters, response fields, formats, and error codes are in
**[references/api-reference.md](references/api-reference.md)**.

## Query Construction

The precision of a PubMed search lives entirely in the query string. Combine concepts with
`AND` / `OR` / `NOT` (uppercase; group with parentheses), and pin each term to a field with a
`term[tag]` suffix. The tags you will reach for most:

| Tag | Field | Tag | Field |
| --- | --- | --- | --- |
| `[tiab]` | Title/Abstract | `[mh]` | MeSH term (auto-includes narrower terms) |
| `[ti]` | Title | `[majr]` | MeSH major topic |
| `[au]` / `[1au]` | Author / first author | `[pt]` | Publication type (e.g. `randomized controlled trial[pt]`) |
| `[ta]` | Journal abbreviation | `[dp]` | Publication date (`2024[dp]`, range `2020:2024[dp]`) |
| `[la]` | Language | `[nm]` | Substance name |
| `[pmid]` `[doi]` `[pmc]` | Identifiers | `[sb]` | Subset (e.g. `free full text[sb]`) |

Worked example — recent free-full-text RCTs on hypertension, in English:

```
hypertension[mh] AND randomized controlled trial[pt] AND 2023:2024[dp]
  AND free full text[sb] AND english[la]
```

MeSH subheadings attach with `/`: `diabetes mellitus, type 2[mh]/drug therapy`. **Automatic
Term Mapping** silently expands untagged words against the MeSH, journal, and author tables —
great for recall, a trap for precision. Bypass it with quotes (`"machine learning"`) or an
explicit tag. Verify any surprising result count via the Advanced Search "Search Details" box.

Field-tag catalogue, wildcards, proximity search, ATM internals, filters, and a
too-many / too-few / no-results troubleshooting table are in
**[references/search-syntax.md](references/search-syntax.md)**. Ready-made query templates by
disease, study design, and population are in **[references/query-cookbook.md](references/query-cookbook.md)**.

## Search → Fetch Workflow

The canonical two-step: ESearch returns PMIDs, EFetch turns them into records.

```python
import requests

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HDRS = {"User-Agent": "pubmed-skill/0.1 (mailto:you@example.org)"}

pmids = requests.get(BASE + "esearch.fcgi", headers=HDRS, params={
    "db": "pubmed", "term": "diabetes[tiab] AND 2024[dp]",
    "retmax": 100, "retmode": "json",
}, timeout=30).json()["esearchresult"]["idlist"]

abstracts = requests.get(BASE + "efetch.fcgi", headers=HDRS, params={
    "db": "pubmed", "id": ",".join(pmids),
    "rettype": "abstract", "retmode": "text",
}, timeout=60).text
```

Swap `rettype`/`retmode` for the format you need (`medline`/`text`, `""`/`xml` for
structured PubMed XML, `""`/`json` on ESummary for a light metadata table). Parse the XML
when you need structured authors, MeSH terms, or grant data.

## Large Result Sets: the History Server

For anything above a few hundred records, do **not** paste thousands of IDs into a URL (you
will hit HTTP 414). Set `usehistory=y` on ESearch (or `EPost` a known PMID list), capture the
returned `WebEnv` + `query_key`, then fetch in `retmax`-sized windows:

```python
s = requests.get(BASE + "esearch.fcgi", headers=HDRS, params={
    "db": "pubmed", "term": "crispr[tiab] AND 2020:2024[dp]",
    "usehistory": "y", "retmode": "json",
}, timeout=30).json()["esearchresult"]
webenv, key, total = s["webenv"], s["querykey"], int(s["count"])

for start in range(0, total, 500):                 # 500-record batches
    batch = requests.get(BASE + "efetch.fcgi", headers=HDRS, params={
        "db": "pubmed", "WebEnv": webenv, "query_key": key,
        "retstart": start, "retmax": 500,
        "rettype": "medline", "retmode": "text",
    }, timeout=120).text
    # persist batch; sleep to respect the rate limit
```

Details on `EPost` batching, `ELink` neighbor/LinkOut commands, and `ECitMatch` citation
lookup (`journal|year|volume|page|author|key|`) are in
**[references/api-reference.md](references/api-reference.md)**.

## Systematic Reviews

Structure clinical questions with **PICO** (Population, Intervention, Comparison, Outcome),
translate each facet into a `(synonym[tiab] OR MeSH[mh])` block, join facets with `AND`, then
add study-design and date filters. Record the exact string, database, and run date so the
search is reproducible. Full PICO worked examples and comprehensive-review templates are in
**[references/query-cookbook.md](references/query-cookbook.md)**.

## Failure Modes and Boundaries

- **ATM surprises:** untagged terms get expanded — a query can silently return far more (or
  fewer) than intended. Tag terms or quote phrases when precision matters; check Search Details.
- **10,000-record ceiling:** ESearch reports the true `Count`, but you can only *retrieve* up
  to 10,000 without the history server, and the web UI won't display past 10,000.
- **URI length (HTTP 414):** long ID lists in a GET fail — use `EPost`/history or POST.
- **Rate limiting (HTTP 429):** back off exponentially; a key lifts 3→10 req/sec, not to infinity.
- **Citations, not full text:** abstracts yes; full text only via PMC (`free full text[sb]`) or
  publisher LinkOut, subject to access.
- **Coverage edges:** pre-1975 records often lack abstracts; full author names are indexed only
  from 2002 forward, so old-author searches need initials.
- **Transient handles:** history-server `WebEnv`/`query_key` and the web Search History expire
  after ~8 hours of inactivity — fetch promptly or re-run.

## Hand-Off to Sibling Skills

- Object-oriented Entrez in Python → `biopython` (`Bio.Entrez`).
- DOIs/PMIDs → BibTeX, `.nbib`, or a reference manager → `citation-management`, `pyzotero`.
- Cross-source or ranked scholarly search, paper synthesis → `research-lookup`, `literature-search`, `literature-review`, `paper-lookup`.
- Preprints → `biorxiv-database`; trials → `clinicaltrials-database`; other named DBs → `database-lookup`.

## References

- **[references/api-reference.md](references/api-reference.md)** — every E-utility endpoint,
  parameters, response fields, history server, batch/link/citation-match workflows, formats,
  rate limits, error codes.
- **[references/search-syntax.md](references/search-syntax.md)** — full field-tag catalogue,
  Boolean precedence, phrase/wildcard/proximity search, MeSH & subheadings, Automatic Term
  Mapping, filters, and a troubleshooting table.
- **[references/query-cookbook.md](references/query-cookbook.md)** — copy-paste query templates
  by disease area, study design, population, methodology, plus PICO and systematic-review patterns.
