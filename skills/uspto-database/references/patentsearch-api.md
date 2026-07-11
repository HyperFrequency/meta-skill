# PatentSearch API Reference

USPTO's modern, ElasticSearch-backed patent search service. It replaced the legacy
PatentsView API (discontinued 1 May 2025). Provided and keyed by PatentsView.

- **Base URL:** `https://search.patentsview.org/api/v1/`
- **Method:** `POST` (JSON body) for all data endpoints
- **Auth header:** `X-Api-Key: <PATENTSVIEW_API_KEY>` (a PatentsView key, *not* the
  USPTO account key)
- **Rate limit:** 45 requests/minute; over-limit returns HTTP `429`
- **Docs (authoritative):** `https://search.patentsview.org/docs/`

## Request body

Four top-level keys:

| Key | Meaning | Required |
| --- | --- | --- |
| `q` | Query object (filters) | Yes |
| `f` | Array of field names to return | No (endpoint defaults) |
| `s` | Sort spec, e.g. `[{"patent_date": "desc"}]` | No |
| `o` | Options: result size / pagination and flags | No |

### Query operators (`q`)

- **Equality:** `{"field": "value"}` or `{"field": {"_eq": "value"}}`
- **Not equal:** `{"field": {"_neq": "value"}}`
- **Comparison:** `_gt`, `_gte`, `_lt`, `_lte`
- **String match:** `_begins` (prefix), `_contains` (substring)
- **Full-text (preferred for text fields):** `_text_all` (all terms present),
  `_text_any` (any term), `_text_phrase` (exact phrase)
- **Logical:** `_and`, `_or`, `_not`
- **Implicit OR:** an array of values, e.g. `{"cpc_subclass_id": ["H04N", "H04L"]}`

```json
{"_and": [
  {"patent_date": {"_gte": "2020-01-01", "_lte": "2020-12-31"}},
  {"patent_abstract": {"_text_all": ["neural", "network"]}},
  {"assignees.assignee_organization": {"_text_any": ["Google", "Alphabet"]}}
]}
```

Prefer `_text_*` over `_contains`/`_begins` on text fields — it is materially faster on
the ElasticSearch backend.

### Options (`o`) — pagination caveat

The current PatentSearch API controls result size through `o` (documented as `size`, up to
**1,000** per request, with cursor-style paging). Older USPTO materials and some client
code show `page` / `per_page` instead. **The naming has shifted across releases** — treat
`o` as "size + pagination + flags" and confirm the exact keys and cursor mechanism against
`https://search.patentsview.org/docs/` before writing paging loops. Additional documented
flags include `pad_patent_id` (zero-pad IDs) and `exclude_withdrawn`.

## Endpoints

### Patents & publications
- `/patent` — granted patents
- `/publication` — pre-grant publications
- `/patent/rel_app_text`, `/publication/rel_app_text` — related-application text

### Entities
- `/inventor`, `/assignee`, `/location`, `/attorney`

### Classifications
- `/cpc_subclass`, `/cpc_at_issue` — Cooperative Patent Classification
- `/uspc` — US Patent Classification
- `/ipc` — International Patent Classification
- `/wipo` — WIPO technology fields

### Text (beta)
- `/brief_summary_text`, `/claims`, `/drawing_description_text`,
  `/detail_description_text`
- Beta: data primarily 2023-onward; historical backfill in progress.

### Supporting
- `/other_reference`, `/related_document`

## Common patent fields

`patent_id` (a.k.a. patent number), `patent_title`, `patent_date` (grant date),
`patent_abstract`, `patent_type`, `inventors` (array), `assignees` (array; org name at
`assignees.assignee_organization`), `cpc_subclass_id`, `uspc_class`,
`cited_patent_number` (backward citations), `citedby_patent_number` (forward citations).

Nested entity fields are dotted (`assignees.assignee_organization`,
`inventors.inventor_name_last`). The complete field dictionary lives in the official docs;
field availability differs per endpoint.

## Response envelope

```json
{
  "error": false,
  "count": 100,
  "total_hits": 5432,
  "patents": [ /* or inventors / assignees / ... */ ]
}
```

- `count` — records in this response
- `total_hits` — total matches for the query
- data array key matches the endpoint (`patents`, `inventors`, …)

## Error handling

| Status | Meaning |
| --- | --- |
| 200 | Success |
| 400 | Bad request (invalid query syntax) |
| 401 | Missing/invalid API key (check you used the PatentsView key) |
| 429 | Rate limit exceeded — back off and retry |
| 500 | Server error |

## Practical tips

- Request only the fields you need via `f` — smaller payloads, faster responses.
- Narrow with date ranges and CPC classes before broad text search.
- Cache results; patent data updates on a slow cadence.
- For very large result sets, page in bounded batches and respect the 45 req/min limit.

## Resources

- Docs: `https://search.patentsview.org/docs/`
- PatentsView key request: `https://patentsview.org/`
- Legacy PatentsView API: discontinued 1 May 2025 — do not target it.
