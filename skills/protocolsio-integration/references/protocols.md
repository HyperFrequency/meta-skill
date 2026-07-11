# Protocols

Core lifecycle: search → read → create → add steps/materials → publish (DOI).
Base URL `https://www.protocols.io/api/v3`; confirm signatures at apidoc.protocols.io.
Read endpoints accept `content_format` = `json` (Draft.js, default), `html`, or
`markdown` — request `markdown` when you need to parse step text.

## Search and list

`GET /protocols`

| Param | Meaning |
| --- | --- |
| `filter` | `public`, `private`, `shared`, `user_public` |
| `key` | keyword search over title, description, content |
| `order_field` | `activity`, `created_on`, `modified_on`, `name`, `id` |
| `order_dir` | `desc`, `asc` |
| `page_size` | results per page (default 10, max 50) |
| `page_id` | 0-indexed page |
| `fields` | comma-separated field allowlist to trim the payload |
| `content_format` | `json` / `html` / `markdown` |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://www.protocols.io/api/v3/protocols?filter=public&key=CRISPR&page_size=20&content_format=markdown"
```

Fetch one by ID or DOI: `GET /protocols/{id_or_doi}`. The response carries metadata
(title, authors, description, DOI, version, publication status) plus the full step
tree, materials, guidelines, and warnings.

## Create and update

`POST /protocols` — body fields (only `title` is required):

- `title`, `description`, `tags` (array)
- `vendor_name`, `vendor_link`
- `warning`, `guidelines`
- `manuscript_citation`, `link`

`PATCH /protocols/{id}` updates any subset of the same fields.

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"CRISPR Gene Editing Protocol","description":"Cas9-mediated editing","tags":["CRISPR","gene editing"]}' \
  "https://www.protocols.io/api/v3/protocols"
```

The created protocol's ID is at `response.item.id`.

## Steps

- Create: `POST /protocols/{id}/steps` — fields: `title` (required), `description`
  (HTML / Markdown / Draft.js), `duration` (seconds), `temperature`, `components`
  (materials/reagents), `software`, `commands`, `expected_result`.
- Update: `PATCH /protocols/{id}/steps/{step_id}` (all fields optional).
- Delete: `DELETE /protocols/{id}/steps/{step_id}`.
- Reorder: `POST /protocols/{id}/steps/reorder` with body `{ "step_order": [id, id, ...] }`.

## Materials

`GET /protocols/{id}/materials` returns reagent names, catalog numbers, vendors,
concentrations/amounts, and product links. Per-step materials are set via the step's
`components` field.

## Publish and DOI

`POST /protocols/{id}/publish`

- `publish_type`: `new` (first publication) or `update` (new version of a published protocol).
- `version_notes`: change summary.

Publishing mints a **permanent** DOI. Published protocols cannot be deleted — only
superseded by a new version. Plan edits as versions, not rollbacks.

## Bookmarks

- `POST /protocols/{id}/bookmarks` — add.
- `DELETE /protocols/{id}/bookmarks` — remove.
- `GET /bookmarks` — list.

## PDF export

`GET /view/{protocol_uri}.pdf` — add `?compact=1` for tight spacing. Rate limited to
~5/min signed-in, ~3/min anonymous; back off on `429`.

## Errors

`400` bad params · `401` bad/expired token · `403` insufficient permission ·
`404` not found or no access · `429` rate limited · `5xx` server error. Retry `429`
(honor `Retry-After`) and `5xx` with exponential backoff.
