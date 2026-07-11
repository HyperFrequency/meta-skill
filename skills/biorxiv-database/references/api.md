# bioRxiv / medRxiv API Reference

The Cold Spring Harbor Laboratory API serves preprint metadata for **bioRxiv**
(life sciences) and **medRxiv** (health sciences) from a single host. Swap the
`[server]` path segment (`biorxiv` or `medrxiv`) to target either server.

- **API host:** `https://api.biorxiv.org`
- **Content host (PDF/HTML):** `https://www.biorxiv.org` / `https://www.medrxiv.org`
- **Format:** JSON (default). Some endpoints also accept `xml` / `csv`.
- Public, keyless, unauthenticated. Be a good citizen: set a descriptive
  `User-Agent`, add a small delay between calls, and cache responses.

> Facts below were checked against the live docs at `https://api.biorxiv.org/`.
> The API is versioned by CSHL, not by this skill — re-confirm page sizes and
> the `category` querystring against the live docs before relying on them in an
> automated pipeline.

## Endpoints

### `/details` — preprint metadata (the workhorse)

```
GET /details/[server]/[interval]/[cursor]/[format]
GET /details/[server]/[DOI]/na/[format]
```

`[interval]` accepts one of:

| Form | Meaning | Example |
|------|---------|---------|
| `YYYY-MM-DD/YYYY-MM-DD` | Posts within a date range (spans two path segments) | `2024-01-01/2024-01-31` |
| `N` | The `N` most recent posts | `50` |
| `Nd` | Posts from the last `N` days | `30d` |
| `DOI` + `/na/` cursor | A single preprint by DOI | `10.1101/2024.01.15.123456/na` |

- **Cursor pagination applies only to the date-range form.** For a date range,
  `/details` serves a **fixed page (currently 30 records) per call**; you MUST
  paginate with `[cursor]` (start at `0`, advance by the page size each call,
  stop when the returned `count` is `0` or the cursor reaches `total`) to get
  everything.
- **The `N` and `Nd` forms take no cursor and are not paginated.** They return a
  single response — `N` gives exactly the N most recent posts; `Nd` returns the
  last N days but is effectively capped (~1300 records observed) and a wide window
  (e.g. `30d`) can time out. Their envelope is minimal (`status` + `category`
  only — no `count`/`total`/`cursor`). Appending a cursor slot to these forms
  (e.g. `/5/0`) errors with `"Both dates must be in yyyy-mm-dd format"`. For
  complete coverage of a busy window, use the date-range form.
- **Category filter:** supported as a **querystring** parameter (not a path
  segment), URL-encoded, with underscores substituting for spaces — e.g.
  `?category=neuroscience`. Confirm exact spelling against the live API; when in
  doubt, filter the record's `category` field client-side instead (reliable).

Response envelope:

```json
{
  "messages": [{ "status": "ok", "count": 30, "total": "412", "cursor": 0 }],
  "collection": [ { /* one record per preprint, fields below */ } ]
}
```

`total` comes back as a **string** (`"412"`) — cast with `int()` before comparing
against the cursor. (Date-range responses also carry `category`, `interval`,
`funder`, and `count_new_papers` fields.)

### `/pubs` — preprint ↔ journal-publication linkage

```
GET /pubs/[server]/[interval]/[cursor]
GET /pubs/[server]/[DOI]/na/[format]
```

Returns preprints that were **subsequently published** in a peer-reviewed
journal, pairing the preprint DOI with the published DOI and journal metadata.
Page size: **100 per call**. Use this to check whether a preprint graduated to a
journal — NOT as a "recent posts" feed (that is the numeric/`Nd` interval on
`/details`).

### `/pub` — published-article view

```
GET /pub/[interval]/[cursor]/[format]
```

Minimal fields only (`biorxiv_doi`, `published_doi`, `title`, `category`,
dates). Page size 100. JSON default; CSV available.

### Other endpoints (rarely needed here)

- `/publisher/[prefix]/[interval]/[cursor]` — filter published links by
  publisher DOI prefix (100/call).
- `/funder/[server]/[interval]/[funder_ROR_ID]/[cursor]/[format]` — filter by
  funder ROR ID (dates from 2025-04-10 onward; 100/call).
- `/sum/[m|y]/[format]` and `/usage/[m|y]/[server]/[format]` — content and usage
  statistics (aggregate counts, downloads, views).

## Record fields (`collection[]`)

| Field | Description |
|-------|-------------|
| `doi` | Preprint DOI, e.g. `10.1101/2024.01.15.123456` |
| `title` | Title |
| `authors` | Comma-separated author string (`"Smith J, Doe J"`) |
| `author_corresponding` | Corresponding author |
| `author_corresponding_institution` | Their institution |
| `date` | Post date `YYYY-MM-DD` |
| `version` | Version number as a string (`"1"`, `"2"`, …) |
| `type` | Submission type, e.g. `"new results"` |
| `license` | License, e.g. `"cc_by"` |
| `category` | Subject category (spaces, API casing) |
| `jatsxml` | URL to the full-text JATS XML |
| `abstract` | Abstract text |
| `published` | Journal DOI once published, else `""` or `"NA"` |

Note: `authors` is a plain string, so author search is a **substring match**,
not a structured field — homographs and initials-only entries are inherent
limitations.

## Full-text URLs (content host, not the API)

Build from `doi` + `version` (use the record's real `version`, never a
hardcoded `v1`):

```
PDF   https://www.biorxiv.org/content/{doi}v{version}.full.pdf
HTML  https://www.biorxiv.org/content/{doi}v{version}
JATS  <value of the record's `jatsxml` field>
```

For medRxiv, substitute `www.medrxiv.org`.

## Subject categories (bioRxiv)

```
animal-behavior-and-cognition   biochemistry            bioengineering
bioinformatics                   biophysics              cancer-biology
cell-biology                     clinical-trials         developmental-biology
ecology                          epidemiology            evolutionary-biology
genetics                         genomics                immunology
microbiology                     molecular-biology       neuroscience
paleontology                     pathology               pharmacology-and-toxicology
physiology                       plant-biology           scientific-communication-and-education
synthetic-biology                systems-biology         zoology
```

medRxiv uses its own health-science category set (e.g. `infectious-diseases`,
`public-and-global-health`, `oncology`). Read the `category` field of a sample
response to learn the exact strings for a given server.

## Error handling

- HTTP `200` with `messages[0].status == "ok"` is the success signal — always
  read the `messages` array, not just the HTTP code.
- `404` / `500` indicate a bad path or a transient server issue; retry with
  backoff.
- An empty `collection` usually means no posts in that window/category, not a
  failure. Cross-check `messages[0].total`.

## External resources

- bioRxiv: https://www.biorxiv.org/ · medRxiv: https://www.medrxiv.org/
- API docs: https://api.biorxiv.org/
- JATS XML spec: https://jats.nlm.nih.gov/
