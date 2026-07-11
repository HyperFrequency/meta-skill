---
name: protocolsio-integration
version: 0.1.0
description: >-
  Programmatic integration with the protocols.io API v3 for scientific protocol
  management. Use when you need to search, retrieve, create, update, version, or
  publish protocols; manage steps, materials, and DOIs; read or post protocol and
  step comments; organize team workspaces and memberships; upload, download, or
  organize workspace files; or record experiment runs, profiles, publications, and
  notifications. Covers OAuth and client-token auth, rate limits, pagination,
  content-format options, and retry/error handling. Do NOT use for generic HTTP
  scripting unrelated to protocols.io, for other protocol repositories (Bio-protocol,
  Nature Protocols), for lab-execution or ELN systems other than protocols.io, or for
  citation-only DOI lookups where a general search or `citation-management` suffices.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Protocols.io Integration

## Overview

Protocols.io is a platform for authoring, versioning, sharing, and publishing
step-by-step scientific protocols. This skill drives its REST API (v3) so you can
treat protocols as data: search the public corpus, pull full step/material trees,
create and publish protocols with a DOI, thread comments, manage team workspaces
and their files, and log experiment runs.

This SKILL.md is a router. Each capability lives in a reference file under
`references/`; load the one you need rather than reading all of them.

> API accuracy: endpoints and parameters below follow the protocols.io API v3 as
> documented at <https://apidoc.protocols.io/>. Confirm exact host, path, and field
> names there before shipping code — the API evolves and this skill does not track
> every revision. Treat any signature you have not seen in a live response as
> tentative.

## When to Use This Skill

- Searching or importing existing protocols by keyword, category, ID, or DOI.
- Creating a protocol, adding/reordering steps and materials, then publishing with a DOI.
- Updating or versioning an already-published protocol.
- Reading or posting protocol-level or step-level comments and threaded replies.
- Listing/joining workspaces, checking roles, and managing workspace protocols.
- Uploading, downloading, tagging, or foldering files attached to a workspace.
- Logging experiment runs (successes, failures, deviations) against a protocol.
- Managing profile, discovering recent publications, or reading notifications.
- Bulk-exporting an organization's protocols/files for archival.

## When NOT to Use This Skill

- The target is a different protocol repository (Bio-protocol, Nature Protocols,
  JoVE) or a non-protocols.io ELN — the endpoints here will not apply.
- You only need to turn a known DOI into a citation record — use `citation-management`.
- You are doing generic web search or reading arbitrary pages — use `parallel-web`,
  `research-lookup`, or `defuddle`.
- You want a structured lookup in a named biological database (UniProt, NCBI,
  Ensembl) — use `database-lookup`.
- The task is generic HTTP scripting with no protocols.io concept involved — write
  the request directly, no skill needed.

## Base URL, Auth, and Conventions

- **Base URL:** `https://www.protocols.io/api/v3` (verify host/version at apidoc.protocols.io).
- **Auth header on every request:** `Authorization: Bearer <ACCESS_TOKEN>`.
- **Token types:** a *client access token* reaches public content plus the token
  owner's private content; an *OAuth access token* reaches an authorized third
  user's private content. See `references/authentication.md` for the OAuth
  code-exchange and refresh flow.
- **Pagination:** most list endpoints take `page_size` and `page_id` (0-indexed)
  and return a `pagination` block. Loop until `current_page + 1 == total_pages`.
- **Content format:** many read endpoints accept `content_format` = `json`
  (Draft.js, default), `html`, or `markdown`. Request `markdown` or `html` when you
  intend to render or parse step text; raw Draft.js JSON is awkward to read.
- **Response envelope:** responses wrap payloads as `{ status_code, status_message,
  item | items, pagination }`. `status_code` of `0` means success at the app layer
  even when HTTP is 200. See `references/account-and-experiments.md` for the exact shape.

## Capabilities → Reference Files

| Task | Load |
| --- | --- |
| Tokens, OAuth flow, refresh, rate limits | `references/authentication.md` |
| Search, CRUD, steps, materials, publish/DOI, bookmarks, PDF | `references/protocols.md` |
| Protocol- and step-level comments, threaded replies | `references/discussions.md` |
| Workspaces, membership/roles, workspace protocols, org export | `references/workspaces.md` |
| File upload/download, folders, tags, versioning | `references/files.md` |
| Profile, recent publications, experiment runs, notifications | `references/account-and-experiments.md` |

## Common Workflows

**Import and analyze a protocol.** Search `GET /protocols?filter=public&key=<terms>`
→ fetch `GET /protocols/{id}?content_format=markdown` → parse steps + materials →
review feedback via `GET /protocols/{id}/comments`. See `references/protocols.md`
and `references/discussions.md`.

**Author and publish.** Create `POST /protocols` → add each step with
`POST /protocols/{id}/steps` → set order with `.../steps/reorder` → publish with
`POST /protocols/{id}/publish` (`publish_type: new`), which mints a permanent DOI.
Published protocols are immutable except via a new version. See `references/protocols.md`.

**Team workspace with data.** Enumerate `GET /workspaces`, confirm your role, create
protocols under `POST /workspaces/{id}/protocols`, upload results with
`POST /workspaces/{id}/files/upload`, and log runs via `POST /protocols/{id}/runs`.
See `references/workspaces.md`, `references/files.md`, `references/account-and-experiments.md`.

## Rate Limits and Error Handling

- **Standard endpoints:** ~100 requests/minute per user.
- **PDF export:** ~5/min signed-in, ~3/min anonymous.
- On `429`, honor the `Retry-After` header; on `5xx`, retry with exponential backoff.
  Treat `401` as a bad/expired token, `403` as a permissions/role problem, `404` as a
  wrong ID or no-access resource. File uploads can also return `413` (too large) or
  `507` (workspace storage full).

Minimal retry loop:

```python
import time, requests

def get_json(url, headers, params=None, max_retries=3):
    for attempt in range(max_retries):
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 30)))
            continue
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
    raise RuntimeError(f"exhausted retries for {url}")
```

## Boundaries and Gotchas

- **DOIs are permanent.** Publishing cannot be undone; iterate as versions, not deletes.
- **Draft.js vs rendered text.** Default step content is Draft.js JSON — request
  `content_format=markdown` unless you specifically need the raw block structure.
- **Role gates writes.** Viewer-role members can comment but not create/edit; check
  the workspace role before attempting writes to avoid surprise `403`s.
- **Secrets stay out of code.** Never hardcode or log access/refresh tokens; read them
  from the environment or a secret store.
- **Endpoints may drift.** This skill is a map, not a contract — reconcile against
  apidoc.protocols.io when a call fails unexpectedly.

## Reference Files

- `references/authentication.md` — token types, OAuth authorize/token/refresh, rate limits.
- `references/protocols.md` — list/search, get, create, update, steps, materials, publish, bookmarks, PDF.
- `references/discussions.md` — protocol/step comments, replies, edit/delete, permissions.
- `references/workspaces.md` — workspaces, roles, membership, workspace protocols, org export.
- `references/files.md` — search/browse, upload/verify, download, metadata, folders, file types.
- `references/account-and-experiments.md` — profile, publications, experiment runs, notifications, response envelope.
