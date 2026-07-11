# Benchling REST API v2 Reference

Use this when calling the API directly (no SDK) — other languages, webhooks, quick
`curl` checks. The `benchling-sdk` wraps all of this. Endpoint paths are stable
within the major version; verify current shapes at
https://benchling.com/api/reference

## Base URL & versioning

```
https://<tenant>.benchling.com/api/v2
```

`v2` is the current major version; Benchling keeps backward compatibility within it.

## Headers

```
Authorization: Bearer <token>        # OAuth/OIDC; or HTTP Basic "api_key:" for API keys
Content-Type: application/json
Accept: application/json
```

```bash
# API key (empty password)
curl https://<tenant>.benchling.com/api/v2/dna-sequences -u "$API_KEY:"
# bearer token
curl https://<tenant>.benchling.com/api/v2/dna-sequences -H "Authorization: Bearer $TOKEN"
```

## Response & error shape

Single resource → a flat JSON object. List → `{"results": [...], "nextToken": "..."}`.
Errors:

```json
{ "error": { "type": "NotFoundError", "message": "...", "userMessage": "..." } }
```

| Status | Meaning |
| ------ | ------- |
| 200 / 201 | success / created |
| 400 | bad request | 
| 401 | missing/invalid credentials |
| 403 | insufficient permissions |
| 404 | not found |
| 422 | validation error (bad field shape) |
| 429 | rate limit exceeded |
| 5xx | server error (SDK retries) |

## Pagination

`pageSize` (default 50, max 100) and `nextToken` (from the previous response):

```bash
curl "https://<tenant>.benchling.com/api/v2/dna-sequences?pageSize=100&nextToken=abc123"
```

Loop until `nextToken` is absent to collect all pages.

## Endpoint catalogue

Registry, inventory, ELN, and workflow resources follow one shape:
`GET /{plural}` (list, filterable) · `GET /{plural}/{id}` (read) ·
`POST /{plural}` (create) · `PATCH /{plural}/{id}` (update) ·
`POST /{plural}:archive` (bulk archive).

| Domain | Path root | Notable filters / actions |
| ------ | --------- | ------------------------- |
| DNA sequences | `/dna-sequences` | `folderId`, `schemaId`, `name`, `modifiedAt` |
| RNA sequences | `/rna-sequences` | same |
| AA sequences  | `/aa-sequences`  | `folderId`, `schemaId` |
| Custom entities | `/custom-entities` | `schemaId` (usually required to scope by type) |
| Mixtures | `/mixtures` | `ingredients` on create |
| Containers | `/containers` | `parentStorageId`, `barcode`; `:transfer`, `:checkout`, `:checkin` |
| Boxes | `/boxes` | `parentStorageId` |
| Locations | `/locations` | — |
| Plates | `/plates` | `wells[]` on create |
| Entries (ELN) | `/entries` | `folderId`, `schemaId`, `modifiedAt` |
| Workflow tasks | `/tasks` | `workflowId`, `statusIds`, `assigneeId` |
| Folders | `/folders` | `projectId`, `parentFolderId` |
| Projects | `/projects` | — |
| Users | `/users` (`/users/me`) | — |
| Teams | `/teams` | — |
| Schemas | `/schemas` | `entityType` (e.g. `dna_sequence`) |
| Registries | `/registries` | — |

### Create example (DNA sequence)

```http
POST /api/v2/dna-sequences
{
  "name": "My Plasmid",
  "bases": "ATCGATCG",
  "isCircular": true,
  "folderId": "fld_abc123",
  "schemaId": "ts_abc123",
  "fields": { "gene_name": { "value": "GFP" } },
  "registryId": "src_abc123",         // register on create (required to register)
  "namingStrategy": "NEW_IDS"         // NEW_IDS | IDS_FROM_NAMES; or set entityRegistryId instead
}
```

### Update (partial — omitted fields untouched)

```http
PATCH /api/v2/dna-sequences/{sequenceId}
{ "fields": { "gene_name": { "value": "mCherry" } } }
```

### Bulk archive

```http
POST /api/v2/dna-sequences:archive
{ "dnaSequenceIds": ["seq_abc123"], "reason": "Made in error" }
```

### Container movement

```http
POST /api/v2/containers:transfer
{ "containerIds": ["cont_abc123"], "destinationStorageId": "box_xyz789" }
```

`:checkout` takes `{containerIds, comment}`; `:checkin` takes
`{containerIds, locationId}`.

## Field-value JSON format

Custom schema fields are always `{"<name>": {"value": <string>}}`. Types encode as
strings: numeric `"123.45"`, date `"2025-10-20"` (`YYYY-MM-DD`), dropdown = exact
option text, entity link = the entity id. Mixture ingredient amounts use
`{"value": "100", "units": "mg"}`.

## Async operations

Bulk endpoints may return `{"taskId": "task_abc123"}`. Poll it:

```http
GET /api/v2/tasks/{taskId}
-> { "id": "...", "status": "RUNNING|SUCCEEDED|FAILED", "response": { ... } }
```

Treat `RUNNING` as "not done" — wait for `SUCCEEDED` before reading `response`.

## Rate limiting

~100 requests / 10s per user/app. Responses carry `X-RateLimit-Limit`,
`X-RateLimit-Remaining`, `X-RateLimit-Reset`. On `429`, honor `Retry-After` (or the
error's `retryAfter` seconds) and back off. Batch, filter server-side, and use
bulk endpoints to reduce call volume.

## Manual pagination (JS)

```javascript
async function getAll(url, token) {
  let out = [], nextToken = null;
  do {
    const u = new URL(url);
    u.searchParams.set("pageSize", "100");
    if (nextToken) u.searchParams.set("nextToken", nextToken);
    const res = await fetch(u, { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 429) {                     // honor rate limit
      await new Promise(r => setTimeout(r, (+res.headers.get("Retry-After") || 5) * 1000));
      continue;
    }
    const data = await res.json();
    out = out.concat(data.results);
    nextToken = data.nextToken;
  } while (nextToken);
  return out;
}
```

## Links

- API reference: https://benchling.com/api/reference
- Interactive explorer (authenticated): `https://<tenant>.benchling.com/api/reference`
- Changelog: https://docs.benchling.com/changelog
