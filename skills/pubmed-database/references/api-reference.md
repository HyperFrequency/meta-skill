# PubMed E-utilities API Reference

Programmatic access to PubMed (and every other Entrez database) goes through the NCBI
E-utilities — a set of `.fcgi` REST endpoints under one base URL:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

For PubMed set `db=pubmed`. Records are identified by **PMID**.

## Authentication and rate limits

- **No key:** 3 requests/second.
- **With an API key:** 10 requests/second. Register an NCBI account and generate a key in your
  account settings; pass it on every call as `&api_key=YOUR_KEY`.
- Always send a descriptive **`User-Agent`** header (include a contact email as a courtesy).
- Exceeding the limit returns **HTTP 429** — implement exponential backoff.
- Keys raise throughput, not total quota; for sustained bulk work, throttle and cache.

## Endpoints

### ESearch — search a database

`esearch.fcgi` · returns a list of UIDs (PMIDs) matching a query.

| Parameter | Required | Notes |
| --- | --- | --- |
| `db` | yes | `pubmed` |
| `term` | yes | the query string (URL-encode it) |
| `retmax` | | records to return; default 20, max 10000 |
| `retstart` | | index of first record (paging) |
| `usehistory=y` | | store results on the history server (see below) |
| `retmode` | | `json` or `xml` |
| `sort` | | `relevance`, `pub_date`, `first_author`, `last_author`, `journal` |
| `datetype` | | date field for filtering (`pdat` = publication date, `edat`, `mdat`) |
| `mindate` / `maxdate` | | `YYYY`, `YYYY/MM`, or `YYYY/MM/DD` (require `datetype`) |
| `field` | | restrict the whole query to one field |

Response carries: `count` (total matches — may exceed `retmax`), `retmax`, `retstart`,
`idlist`, and — when `usehistory=y` — `webenv` and `querykey`.

```
esearch.fcgi?db=pubmed&term=breast+cancer&retmax=100&retmode=json&api_key=KEY
```

### EFetch — download full records

`efetch.fcgi` · turns UIDs into full records.

| Parameter | Required | Notes |
| --- | --- | --- |
| `db` | yes | `pubmed` |
| `id` | yes* | comma-separated PMIDs — *or* supply `WebEnv` + `query_key` |
| `rettype` | | `abstract`, `medline`, `uilist`, or empty for full XML |
| `retmode` | | `text` or `xml` |
| `retstart` / `retmax` | | paging within a history set |

Common PubMed format pairs: `rettype=abstract&retmode=text`, `rettype=medline&retmode=text`,
`rettype=""&retmode=xml` (structured PubMed XML with authors, MeSH, grants), `rettype=uilist`.

```
efetch.fcgi?db=pubmed&id=123456,234567&rettype=medline&retmode=text&api_key=KEY
```

### ESummary — document summaries

`esummary.fcgi` · lightweight metadata (DocSum) for a UID list. Cheaper than EFetch when you
only need title/authors/journal/date/DOI. Add `retmode=json`; `version=2.0` gives the richer
DocSum schema. Common fields: `title`, `authors`, `source` (journal), `pubdate`, `volume`,
`issue`, `pages`, `elocationid`/DOI, `pmcrefcount`.

### EPost — upload UIDs to the history server

`epost.fcgi?db=pubmed&id=123,456,789` · stores a caller-supplied PMID list server-side and
returns `WebEnv` + `query_key` for use by EFetch/ESummary/ELink. Use it to fetch a known ID
set too large for a GET URL.

### ELink — related records and cross-database links

`elink.fcgi` · finds neighbors within PubMed or links to other Entrez databases.

| Parameter | Notes |
| --- | --- |
| `dbfrom` | source db (`pubmed`) |
| `db` | target db (same or different, e.g. `pmc`) |
| `id` | source UID(s) |
| `cmd` | `neighbor` (related PMIDs), `neighbor_history` (post them to history), `prlinks` (provider URLs), `llinks` (LinkOut URLs) |
| `linkname` | a specific link type |
| `term` | filter the linked set with a query |

```
elink.fcgi?dbfrom=pubmed&db=pubmed&id=123456&cmd=neighbor&api_key=KEY
```

### EInfo — database and field metadata

`einfo.fcgi?db=pubmed&retmode=json` · lists the searchable fields (with descriptions), record
count, and last-update date. Call it with no `db` to list every Entrez database.

### ESpell — spelling suggestions

`espell.fcgi?db=pubmed&term=cancre` · returns a corrected query. Useful when a search yields
zero results.

### EGQuery — global term counts

`egquery.fcgi?term=cancer` · match counts for a term across all Entrez databases at once.

### ECitMatch — citation → PMID

`ecitmatch.cgi` · resolves partial citations to PMIDs. POST one or more pipe-delimited strings:

```
journal|year|volume|page|author|key|
Science|2008|320|5880|1185|key1|
Nature|2010|463|7279|318|key2|
```

Rate-limited to ~3 req/sec; `User-Agent` required.

## History server: large result sets

For result sets beyond a few hundred, use the history server rather than long ID lists.

1. Search with history:
   ```
   esearch.fcgi?db=pubmed&term=cancer&usehistory=y&retmode=json&api_key=KEY
   ```
   Capture `webenv` + `querykey` (and `count`).
2. Fetch in batches with `retstart`/`retmax` (≤ 500 recommended per call):
   ```
   efetch.fcgi?db=pubmed&query_key=1&WebEnv=MCID_...&retstart=0&retmax=500&rettype=xml&api_key=KEY
   efetch.fcgi?db=pubmed&query_key=1&WebEnv=MCID_...&retstart=500&retmax=500&rettype=xml&api_key=KEY
   ```

`WebEnv`/`query_key` handles expire after ~8 hours of inactivity — fetch promptly or re-run
the search.

## Error codes

| Code | Meaning | Fix |
| --- | --- | --- |
| 200 | success (still check body for `<ERROR>` / empty `idlist`) | — |
| 400 | bad request | check parameter names/values, URL-encoding |
| 414 | URI too long | move IDs to POST or the history server |
| 429 | rate limit exceeded | back off; add an API key |

## Response formats

- **XML** (default for EFetch) — most detailed; each db has its own DTD.
- **JSON** — available on most utilities via `retmode=json`; easiest to parse.
- **Text** — plain text for abstracts (`rettype=abstract`) and MEDLINE (`rettype=medline`).

## Best practices

- Prefer the history server / `EPost` over long GET URLs.
- Cache locally to cut redundant calls and stay under the rate limit.
- Parse the response body for API-level errors, not just the HTTP status.
- For structured metadata at scale, `ESummary` (light) then `EFetch` XML (heavy) only where needed.

## Reference documentation

- E-utilities book: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- PubMed help: https://pubmed.ncbi.nlm.nih.gov/help/
