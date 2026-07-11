# Account, Publications, Experiments, Notifications

Supplementary endpoints: user profile, publication discovery, experiment runs,
notifications, org export, and the response envelope shape. Base URL
`https://www.protocols.io/api/v3`.

## Profile

- Get: `GET /profile` — ID, username, name, email, affiliation, bio, image URL,
  creation date, protocol stats.
- Update: `PATCH /profile` — `first_name`, `last_name`, `email`, `affiliation`,
  `bio`, `location`, `website`, `twitter`, `orcid`.
- Image: `POST /profile/image` (`multipart/form-data`, field `image`; square JPEG/PNG,
  ≥200×200, ≤5 MB).

Set `orcid` for correct research attribution.

## Recently published protocols

`GET /publications` — discover public protocols:

| Param | Meaning |
| --- | --- |
| `key` | keyword search |
| `category` | e.g. `molecular-biology`, `cell-biology`, `biochemistry` |
| `date_from` / `date_to` | ISO 8601 (`YYYY-MM-DD`) window |
| `order_field` | `published_on`, `title`, `views` |
| `order_dir` | `desc`, `asc` |
| `page_size` / `page_id` | pagination (default 10, max 50) |

Use for monitoring new work in a field or finding citable protocols. For turning a
discovered DOI into a formatted citation, hand off to `citation-management`.

## Experiment runs

Records document one execution of a protocol — what happened, what changed.

- Create: `POST /protocols/{id}/runs` — `title` (required), `date` (ISO 8601),
  `status` (`success`/`partial`/`failed`), `notes`, `modifications`, `results`,
  `attachments` (file IDs from the File Manager).
- List: `GET /protocols/{id}/runs` — filter by `status`, `date_from`, `date_to`,
  paginate.
- Update: `PATCH /protocols/{id}/runs/{run_id}`.
- Delete: `DELETE /protocols/{id}/runs/{run_id}`.

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"CRISPR - HEK293 - Trial 3","date":"2025-10-20","status":"success",
       "notes":"87% editing efficiency; sgRNA 100→150 nM","modifications":"step 3 incubation 30→45 min"}' \
  "https://www.protocols.io/api/v3/protocols/12345/runs"
```

Log failures as well as successes — reproducibility analysis needs both.

## Notifications

- List: `GET /notifications` — filter `type` (`comment`, `mention`,
  `protocol_update`, `workspace`, `publication`) and `read` (`true`/`false`/omit),
  paginate (`page_size` default 20, max 100).
- Mark one read: `PATCH /notifications/{id}` with `{ "read": true }`.
- Mark all read: `POST /notifications/mark-all-read`.
- Delete: `DELETE /notifications/{id}`.

## Organization export

`GET /organizations/{org_id}/export` — params `format` (`json`/`csv`/`xml`),
`include_files` (`true`/`false`), `include_comments` (`true`/`false`). Returns a
download URL for the export package. Use for institutional archival, compliance, or
migration.

## Response envelope

Success and error payloads share a wrapper:

```json
{
  "status_code": 0,
  "status_message": "Success",
  "item": {  },
  "items": [  ],
  "pagination": { "current_page": 0, "total_pages": 5, "page_size": 10, "total_items": 42 }
}
```

Errors set a nonzero `status_code` plus `error_message` / `error_details`. Note the
app-layer `status_code` (0 = success) is distinct from the HTTP status — check both.
Paginate by requesting `page_id` until `current_page + 1 == total_pages`.
