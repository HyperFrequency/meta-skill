# OpenAlex API Reference

Complete reference for querying `https://api.openalex.org`. See
[recipes.md](recipes.md) for runnable Python patterns.

## Base facts

- **Base URL:** `https://api.openalex.org`
- **Auth:** none. Data is CC0 (public domain).
- **Polite pool:** append `mailto=you@example.edu` to every request → 10 req/s.
  Without it you share the common pool at ~1 req/s and are throttled first.
- **Daily cap:** 100,000 requests/day (both pools).
- **Premium:** OpenAlex sells API keys (`api_key=`) for higher throughput and
  same-day data freshness; not needed for normal use.
- **Docs:** https://docs.openalex.org · Entity schemas:
  https://docs.openalex.org/api-entities · Users list:
  https://groups.google.com/g/openalex-users

## Entity endpoints

| Endpoint | Contents |
| --- | --- |
| `/works` | 240M+ scholarly documents (articles, books, datasets, preprints) |
| `/authors` | disambiguated researcher profiles |
| `/sources` | journals, repositories, conference series |
| `/institutions` | universities and research organizations |
| `/topics` | 3-level subject classification |
| `/publishers` | publishing organizations |
| `/funders` | funding agencies |
| `/keywords`, `/concepts` | tag vocabularies (`concepts` is the legacy scheme) |
| `/autocomplete/{entity}?q=` | fast type-ahead suggestions — ideal for name→ID |
| `/text` | POST your own text to get topics/keywords tagged |

## Query parameters

| Param | Description | Example |
| --- | --- | --- |
| `filter=` | AND-joined filter conditions | `?filter=publication_year:2020,is_oa:true` |
| `search=` | full-text search (title, abstract, fulltext) | `?search=machine+learning` |
| `sort=` | order results (`:asc`/`:desc`) | `?sort=cited_by_count:desc` |
| `per-page=` | page size, **max 200** (default 25) | `?per-page=200` |
| `page=` | page number — **only reaches the first 10,000 results** | `?page=2` |
| `cursor=` | deep pagination; start `cursor=*` | `?cursor=*` |
| `sample=` | random rows, **max 10,000** per request | `?sample=200` |
| `seed=` | seed for reproducible `sample` | `?seed=42` |
| `select=` | comma-list of fields to return | `?select=id,title,cited_by_count` |
| `group_by=` | aggregate counts by a field (no rows returned) | `?group_by=publication_year` |
| `mailto=` | polite-pool email | `?mailto=you@example.edu` |

## Filter syntax

```
Single:            ?filter=publication_year:2020
AND (comma):       ?filter=publication_year:2020,is_oa:true
OR (pipe, ≤50):    ?filter=type:article|book
AND within attr:   ?filter=institutions.country_code:us+gb   (author from US AND author from GB)
Negation:          ?filter=type:!paratext
Greater / less:    ?filter=cited_by_count:>100   ?filter=publication_year:<2020
Range:             ?filter=publication_year:2018-2022
Per-field search:  ?filter=title.search:crispr
Date bounds:       ?filter=from_publication_date:2023-01-01,to_publication_date:2023-06-30
```

`search=` scans the composite index; `.search` suffixes (e.g. `title.search`,
`abstract.search`, `default.search`) scope the match to one field.

### Most-used `/works` filters

| Filter | Meaning | Example value |
| --- | --- | --- |
| `authorships.author.id` | author OpenAlex ID | `A5089…` |
| `authorships.institutions.id` | institution ID | `I136199984` |
| `primary_location.source.id` | journal/source ID | `S137773608` |
| `topics.id` | topic ID | `T10001` |
| `grants.funder` | funder ID | `F4320306076` |
| `publication_year` | year(s) | `2020`, `>2020`, `2018-2022` |
| `cited_by_count` | citations | `>100` |
| `is_oa` | open access | `true` / `false` |
| `open_access.oa_status` | OA colour | `gold`/`green`/`hybrid`/`bronze`/`closed` |
| `type` | document type | `article`, `book`, `dataset` |
| `has_doi`, `has_fulltext` | availability flags | `true` / `false` |
| `authorships.institutions.country_code` | country | `us`, `gb` |
| `language` | language code | `en` |

### Author filters

`last_known_institutions.id`, `works_count`, `cited_by_count`, `orcid`,
`affiliations.institution.id`.

## Response shapes

List endpoint:

```json
{
  "meta": { "count": 240523418, "db_response_time_ms": 42,
            "page": 1, "per_page": 25, "next_cursor": "IlsxNjA…" },
  "results": [ { /* entity */ } ]
}
```

`group_by`:

```json
{ "meta": { "count": 100 },
  "group_by": [ { "key": "https://openalex.org/T10001",
                  "key_display_name": "Artificial Intelligence",
                  "count": 15234 } ] }
```

Single entity (`/works/W2741809807`) returns the object directly — no wrapper.

Useful `Work` fields: `id`, `doi`, `title`, `display_name`, `publication_year`,
`publication_date`, `type`, `cited_by_count`, `cited_by_api_url`, `authorships`,
`primary_location`, `open_access`, `topics`, `referenced_works`,
`abstract_inverted_index`.

## Pagination

- **Shallow (`page`):** only valid while `page × per-page ≤ 10,000`. Beyond that
  the API errors. Fine for small result sets.
- **Deep (`cursor`):** start with `cursor=*`, read rows, then pass the value of
  `meta.next_cursor` as the next `cursor=`. Stop when `next_cursor` is `null`.
  This is the only correct way to stream a filtered set larger than 10k rows.
- `cursor` and `page` are mutually exclusive in one request.
- `sample` cannot be paged with `cursor`; for samples >10,000 issue multiple
  requests with different `seed`s and deduplicate by `id`.

## External identifiers

Resolve entities directly by external ID (no lookup step):

```
Works:        /works/https://doi.org/10.7717/peerj.4375
              /works/pmid:29844763
Authors:      /authors/https://orcid.org/0000-0003-1613-5981
Institutions: /institutions/https://ror.org/02y3ad647
Sources:      /sources/issn:0028-0836
```

The same IDs work inside filters, e.g. `?filter=doi:10.1038/…|10.1126/…`.

## Abstracts

Works store `abstract_inverted_index` — a `{word: [positions]}` map, not text.
Reconstruct by placing each word at each of its positions and joining in order.
There is no `abstract` string field. Reconstruction helper in
[recipes.md](recipes.md).

## Error handling

| Status | Meaning | Action |
| --- | --- | --- |
| 200 | success | — |
| 400 | bad request | check filter/param syntax |
| 403 / 429 | rate limited | add `mailto`, slow down, exponential backoff |
| 404 | entity not found | verify ID/DOI format |
| 5xx | server error | retry with backoff |

Retry idempotent GETs with delays of `2**attempt` seconds (cap the attempts).
Track requests-per-second globally when running concurrent workers so the pool
limit is respected across threads.

## Common mistakes

1. Filtering by a name instead of an ID → resolve via `/autocomplete` or a
   `search` lookup first.
2. Using `page` past 10,000 results → switch to `cursor=*`.
3. Random `page` numbers for "random" data → use `sample=`+`seed=`.
4. Default page size → set `per-page=200`.
5. N sequential ID lookups → one `|`-joined filter (≤50 values).
6. Expecting a plain `abstract` → reconstruct `abstract_inverted_index`.
7. Omitting `mailto` → throttled in the common pool.
8. Scanning the whole corpus over HTTP → use the CC0 data snapshot.
