---
name: benchling-integration
version: 0.1.0
description: >-
  Programmatic access to the Benchling life-sciences R&D cloud from Python
  (benchling-sdk) or the REST API v2. Create and query registry entities (DNA,
  RNA, protein/AA, custom entities, mixtures), manage inventory (containers,
  boxes, plates, locations, transfers), read/write ELN entries, drive workflow
  tasks, subscribe to events via AWS EventBridge, and query the Data Warehouse
  with SQL. Use when automating lab-data capture, syncing Benchling with external
  systems, or building Benchling Apps and integrations. Do NOT use for general
  bioinformatics sequence analysis (use Biopython/scanpy/`esm`), for LIMS or ELN
  platforms other than Benchling, or when no Benchling tenant with API access
  exists.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Benchling Integration

## Overview

Benchling is a cloud platform for life-sciences R&D that unifies a sequence/entity
registry, physical-sample inventory, an electronic lab notebook (ELN), and
laboratory workflows. This skill covers driving it programmatically through the
official `benchling-sdk` Python client and the underlying REST API v2, plus the
two push/pull integration surfaces most automations need: event streaming (AWS
EventBridge) and the SQL Data Warehouse.

Everything here mirrors a user's UI permissions — the API can only touch data the
authenticated user or app is allowed to see. Depth (per-entity models, full
endpoint tables, auth flows, error handling) lives in `references/`; this file is
the router.

## When to Use This Skill

- Reading or writing Benchling **registry entities**: DNA/RNA/AA sequences,
  custom entities, mixtures.
- Automating **inventory**: creating containers/boxes/plates/locations, transfers,
  check-in/check-out, barcode lookups.
- Creating or updating **ELN entries** and linking entities/results to them.
- Driving **workflow tasks** (create, assign, advance status) and waiting on
  async bulk operations.
- Building an **integration**: syncing Benchling ↔ an external DB, triggering
  downstream jobs on events, or standing up a Benchling App with OAuth.
- Running **analytics** over historical data via the SQL Data Warehouse.

## When NOT to Use This Skill

- **Sequence/structure analysis** (alignment, folding, variant calling): pull the
  bases/AA out of Benchling, then use Biopython, scanpy, `esm`, or `rdkit`.
- **Other platforms**: a different LIMS/ELN (Benchling-specific IDs and schemas
  will not transfer).
- **No tenant/credentials**: you need a Benchling tenant URL and an API key or app
  credentials — there is no public sandbox.
- **Structured lookups in public bio databases** (UniProt, NCBI, KEGG): use
  `bioservices` or `database-lookup` instead.

## Setup & Authentication

Install the SDK (Python 3.8+):

```bash
uv pip install benchling-sdk   # or: pip install benchling-sdk
```

Instantiate one `Benchling` client and reuse it. API-key auth is simplest for
scripts; OAuth2 client-credentials is for apps and service accounts.

```python
import os
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(
    url=os.environ["BENCHLING_TENANT_URL"],   # https://<tenant>.benchling.com
    auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
)

me = benchling.users.get_me()   # cheap call to confirm credentials work
```

Read credentials from the environment — never hardcode or commit them. For OAuth2
client-credentials, OIDC/SSO, rate limits, credential rotation, and the 401/403/429
troubleshooting matrix, see `references/authentication.md`.

## Registry & Entity Management

All entity resources hang off the client and share one CRUD shape:

```python
benchling.dna_sequences      # also: rna_sequences, aa_sequences,
                             #       custom_entities, mixtures
```

| Operation | Method (pattern) |
| --------- | ---------------- |
| Create    | `benchling.<resource>.create(<Model>Create(...))` |
| Read one  | `benchling.<resource>.get_by_id("<id>")` |
| List      | `benchling.<resource>.list(**server_side_filters)` → paginated generator |
| Update    | `benchling.<resource>.update(id, <Model>Update(...))` (partial; unset fields untouched) |
| Archive   | `benchling.<resource>.archive([ids], reason=EntityArchiveReason.OTHER)` |

Custom schema fields go through the `fields()` helper, and each value is wrapped in
`{"value": ...}`:

```python
from benchling_sdk.models import DnaSequenceCreate
from benchling_sdk.helpers.serialization_helpers import fields

seq = benchling.dna_sequences.create(
    DnaSequenceCreate(
        name="pET28a-GFP",
        bases="ATCGATCG",
        is_circular=True,
        folder_id="fld_abc123",
        fields=fields({"gene_name": {"value": "GFP"}}),
    )
)
```

**Registering** an entity into a registry at creation time needs `registry_id`
(the `src_...` registry) **plus** either an explicit `entity_registry_id` **or** a
`naming_strategy` (`NamingStrategy.NEW_IDS` / `IDS_FROM_NAMES`) — never both
`entity_registry_id` and `naming_strategy`. Full per-entity models (RNA, AA, mixtures with
ingredients, plates with wells), naming-strategy semantics, and forward-compat
(`UnknownType`) handling are in `references/sdk_reference.md`.

## Inventory Management

Containers, boxes, plates, and locations form a storage tree
(`parent_storage_id`). Beyond CRUD, inventory adds movement operations:

- `benchling.containers.transfer(...)` — move item(s) to a new box/location.
- `check_out` / `check_in` — track items leaving and returning to storage.
- Filter by `parent_storage_id`, `schema_id`, or `barcode` to audit a location.

See `references/sdk_reference.md` (Inventory) and `references/api_endpoints.md`
(`:transfer`, `:checkout`, `:checkin`, bulk-transfer) for exact calls.

## Notebook (ELN)

Create/update `entries`, manage entry templates, and link entities or results into
an entry for traceability. Entry field values use the same `fields()` helper as
entities. Details in `references/sdk_reference.md` (Notebook Operations).

## Workflows & Async Tasks

Create workflow tasks, assign them, and advance them by setting a `status_id`.
Bulk mutations return an async **task ID**; poll it to completion before assuming
the change landed — do not fire-and-forget bulk writes. The endpoint contract and
task-status polling loop are in `references/api_endpoints.md` (Async Operations)
and `references/sdk_reference.md` (Async Task Handling).

## Events & Data Warehouse

- **Events (near-real-time):** route Benchling events (entity/inventory/workflow
  changes) to **AWS EventBridge**, filter with rules, and fan out to Lambda or
  other targets. Use for sync-on-change and triggering downstream jobs. Configure
  event forwarding in tenant settings; consult Benchling's event-schema docs for
  payload shapes.
- **Data Warehouse (batch/analytics):** a read-only SQL surface over historical
  Benchling data. Connect a standard SQL/Postgres client or BI tool for
  aggregation and reporting — better than paginating the REST API for large
  analytical scans.

## Failure Modes & Gotchas

- **List generators are single-use.** `list()` returns a generator you can iterate
  once; call `list()` again for a fresh pass. Use `.estimated_count()` for totals
  without draining it.
- **Filter server-side.** Pass `folder_id`/`schema_id`/`name` to `list()` rather
  than pulling everything and filtering in Python.
- **Field format is strict.** Custom fields are strings even for numbers
  (`"123"`), dates are `YYYY-MM-DD`, and dropdown values must match an option
  exactly. Wrong shape → `422`/validation error.
- **Rate limits.** ~100 requests / 10s per user or app; the SDK retries `429` with
  exponential backoff, but batch and cache to stay under it.
- **Permissions mirror the UI.** A `403` usually means the user/app lacks access to
  that project/folder, not that your code is wrong — grant access in the Developer
  Console.
- **Bulk writes are async.** Treat a returned task ID as "queued," not "done."

## References

- `references/authentication.md` — API key, OAuth2 client-credentials, OIDC/SSO,
  credential storage/rotation, rate limits, and the auth-error troubleshooting
  matrix.
- `references/sdk_reference.md` — full `benchling-sdk` reference: per-entity
  models, inventory/ELN/workflow examples, pagination, async tasks, retry config,
  custom API escape hatch, and common pitfalls.
- `references/api_endpoints.md` — REST API v2 endpoint catalogue, request/response
  shapes, field-value JSON format, bulk/async operations, and pagination.

## Related Skills

- `bioservices` / `database-lookup` — pull reference data from public bio
  databases (UniProt, NCBI, KEGG) to enrich Benchling entities.
- `esm`, `rdkit` — analyze protein sequences or small molecules extracted from the
  registry.

## Upstream Documentation

- Benchling docs: https://docs.benchling.com
- Python SDK: https://benchling.com/sdk-docs/
- REST API reference: https://benchling.com/api/reference
