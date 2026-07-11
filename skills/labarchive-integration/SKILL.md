---
name: labarchive-integration
version: 0.1.0
description: >-
  Automate the LabArchives electronic lab notebook (ELN) through its REST API v2
  and the community labarchivespy Python wrapper. Authenticate with an
  institutional access key plus a user's external-applications password, list and
  back up notebooks, create entries/comments/parts, upload attachments, run
  Enterprise site reports, and script third-party integrations (Protocols.io,
  Jupyter, REDCap, SnapGene, Geneious, GraphPad Prism). Use when programmatically
  capturing lab data into LabArchives, backing up notebooks for retention, or
  syncing external tools into LabArchives entries. Do NOT use for other ELN/LIMS
  platforms (use `benchling-integration` for Benchling), for analysis of the
  extracted data (use `biopython`/`scanpy`/`rdkit`), or without an Enterprise
  LabArchives license with API access enabled.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# LabArchives Integration

## Overview

LabArchives is a cloud electronic lab notebook (ELN) used across academic and
enterprise research for documentation, data retention, and regulatory compliance.
This skill drives it programmatically through the LabArchives REST API v2 — and the
community `labarchivespy` Python wrapper (`labarchivespy.client.Client`) that sits
on top of it — to list and back up notebooks, create entries/comments/attachments,
run Enterprise site reports, and script integrations with other lab tools.

API access is Enterprise-gated: you need an institutional **access key ID +
password** from your LabArchives administrator, plus each user's own
**external-applications password**. Every call is scoped to that user's UI
permissions — the API can only touch data the authenticated user may see. Depth
(full method catalogue, auth flows, per-platform integration recipes) lives in
`references/`; this file is the router.

## When to Use This Skill

- Programmatically **backing up** notebooks (full 7z archive or metadata-only
  XML/JSON) for retention or migration.
- **Listing** a user's accessible notebooks and their roles.
- Creating or updating **entries**, adding comments/parts, and **uploading
  attachments** (data files, figures, exports) into notebooks.
- Generating Enterprise **site reports** (usage, notebook inventory, PDF-export
  audit trails) for compliance.
- Building **integrations** that push data from Protocols.io, Jupyter, REDCap,
  SnapGene, Geneious, or GraphPad Prism into LabArchives entries.

## When NOT to Use This Skill

- **A different ELN/LIMS.** For Benchling use `benchling-integration`; LabArchives
  IDs, method names, and auth do not transfer to other platforms.
- **Analyzing the data** you pulled out (sequence alignment, stats, cheminformatics):
  extract it, then use `biopython`, `scanpy`, `rdkit`, or `statistical-analysis`.
- **No Enterprise access.** API access, and especially `site_reports`, require an
  Enterprise license with API enabled by your administrator — there is no public
  sandbox.
- **Structured lookups in public databases** (UniProt, NCBI, PubMed): use
  `database-lookup` or `citation-management` instead.

## Setup & Authentication

There are two credential layers:

1. **Institutional** — `access_key_id` + `access_password`, issued by your
   LabArchives administrator; they identify the calling application.
2. **User** — email + an **external-applications password** generated in the user's
   Account Settings (Security & Privacy → External Applications). This is *not* the
   regular login password.

Pick the regional base URL that matches your tenant:

| Region           | Base URL                            |
| ---------------- | ----------------------------------- |
| US/International | `https://api.labarchives.com/api`   |
| Australia        | `https://auapi.labarchives.com/api` |
| UK              | `https://ukapi.labarchives.com/api` |

Using the wrong region 401s even with correct credentials. Read all four values
from environment variables — never hardcode or commit them. Full auth flow (Python
wrapper, raw `requests`, R), OAuth2 for apps, and the 401/403 troubleshooting matrix
are in `references/authentication.md`.

Install the optional wrapper:

```bash
uv pip install git+https://github.com/mcmero/labarchives-py
```

## Authenticate and Get a UID

Every user-scoped call needs a **UID**, obtained once from `users/user_access_info`.
Its response also carries the list of accessible notebooks.

```python
import os, xml.etree.ElementTree as ET
from labarchivespy.client import Client

client = Client(
    os.environ["LA_API_URL"],
    os.environ["LA_ACCESS_KEY_ID"],
    os.environ["LA_ACCESS_PASSWORD"],
)

resp = client.make_call(
    "users", "user_access_info",
    params={
        "login_or_email": os.environ["LA_USER_EMAIL"],
        "password": os.environ["LA_USER_EXTERNAL_PASSWORD"],
    },
)
uid = ET.fromstring(resp.content)[0].text
```

`make_call(api_class, api_method, params=...)` returns a `requests.Response`.
Responses are XML by default; pass `json=true` in `params` on methods that support
it. The URL contract is
`https://<base_url>/api/<api_class>/<api_method>?<auth>&<params>`.

## Notebook Operations

The `user_access_info` response lists each notebook's `nbid`, name, and role. Back
up a notebook with `notebooks/notebook_backup`:

```python
resp = client.make_call(
    "notebooks", "notebook_backup",
    params={"uid": uid, "nbid": nbid,
            "json": "false", "no_attachments": "false"},
)
open(f"nb_{nbid}.7z", "wb").write(resp.content)
```

- `no_attachments=false` → a **7z archive**: entry HTML, original files, metadata
  XML (timestamps/authors/versions), and comment threads.
- `no_attachments=true` → structured **XML/JSON** only; add `json=true` for JSON.

Loop over the notebook list to back up everything, and stamp each file with a
timestamp. Full parameter and response tables: `references/api_reference.md`.

## Entries & Attachments

The `entries` API class covers creating entries, adding comments, adding parts
(text/table/image), and uploading file attachments. Attachments are **multipart
POSTs** — send the auth params in the form body, not the query string:

```python
import requests
requests.post(
    f"{api_url}/entries/upload_attachment",
    files={"file": open("data.csv", "rb")},
    data={"uid": uid, "nbid": nbid, "entry_id": entry_id,
          "filename": "data.csv",
          "access_key_id": key_id, "access_password": pw},
)
```

Exact entry method names and parameters can vary by API version — confirm against
`references/api_reference.md` and the official LabArchives docs before relying on
them in production.

## Site Reports (Enterprise)

The `site_reports` class returns institution-wide analytics for compliance and
auditing: detailed usage, notebook inventory, PDF/offline-export logs, and member
or settings reports. Example — a usage report over a date range:

```python
client.make_call("site_reports", "detailed_usage_report",
                 params={"start_date": "2026-01-01", "end_date": "2026-06-30"})
```

Report names, parameters, and returned fields are catalogued in
`references/api_reference.md`.

## Third-Party Integrations

The general pattern is uniform across tools: **export** from the source app →
**transform** to HTML or a supported file → **create** a LabArchives entry →
**attach** the original file → **add a comment** carrying source version and
timestamp for traceability. Per-platform recipes (Protocols.io, Jupyter, REDCap,
SnapGene, Geneious, GraphPad Prism, Qeios, SciSpace) and the OAuth2 app-registration
flow are in `references/integrations.md`.

## Failure Modes & Gotchas

- **Wrong password type.** Use the external-applications password, not the login
  password → otherwise 401.
- **Wrong region.** Correct credentials still 401 if the base URL doesn't match the
  tenant's region.
- **Enterprise-gated.** API access, and especially `site_reports`, require an
  Enterprise license plus admin enablement → 403 if not granted.
- **Rate limits.** Stay ≤ ~60 requests/min per key; put 1–2 s between batch calls;
  back off exponentially on 429.
- **Attachments.** Auth goes in the multipart **body**, not the query string;
  typical cap is ~2 GB/file; verify the user's storage quota first.
- **Secrets.** Keep all four credentials in env vars or a secret store; add any
  config file to `.gitignore`.
- **Method drift.** The API is backward-compatible, but some method names vary by
  version — verify names before scripting rather than assuming.

## References

- `references/authentication.md` — credential model, external-applications password
  setup, regional endpoints, auth flow (wrapper / raw `requests` / R), OAuth2 for
  apps, and the 401/403 + network troubleshooting matrix.
- `references/api_reference.md` — REST API structure, the Users/Notebooks/Entries/
  Site-Reports classes with parameters and examples, XML/JSON response shapes, error
  codes, and rate limits.
- `references/integrations.md` — per-platform integration recipes, a reusable custom
  integration template, and the OAuth2 authorization-code flow.

## Related Skills

- `benchling-integration` — the same automation pattern for the Benchling ELN,
  registry, and inventory.
- `dnanexus-integration` — programmatic data management on the DNAnexus platform.
- `citation-management`, `database-lookup` — pull reference/metadata to enrich
  notebook entries.
- `biopython` — analyze sequences or data files extracted from notebooks.

## Upstream Documentation

- LabArchives (contact support@labarchives.com for API access): https://www.labarchives.com
- Community Python wrapper: https://github.com/mcmero/labarchives-py
