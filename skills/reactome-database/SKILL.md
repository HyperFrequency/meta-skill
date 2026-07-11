---
name: reactome-database
version: 0.1.0
description: >-
  Query the Reactome REST web services — Content Service (data retrieval) and
  Analysis Service (enrichment) — for expert-curated pathway biology. Retrieve
  pathways, reactions, complexes and their participants by stable ID (R-HSA-...);
  free-text search entities; run overrepresentation (enrichment) and expression
  analysis on gene/protein/metabolite lists; project non-human identifiers to
  human pathways; and build Pathway Browser links from analysis tokens. Use when
  you have a gene/protein/metabolite list and need statistically enriched
  pathways, want detail for a Reactome stable ID, or are mapping identifiers to
  pathways for systems-biology work. NOT for KEGG / GO / WikiPathways / STRING /
  MSigDB (different APIs), gene-annotation or sequence retrieval, computing
  differential expression to build the input list, or offline graph/topology math
  on a pathway network (use a graph library) — this wraps only reactome.org.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Reactome Database

## Overview

Reactome is a free, open, peer-reviewed knowledgebase of human biological
pathways (with orthology-inferred data for model organisms). It exposes two
independent REST services over plain HTTP:

- **Content Service** (`https://reactome.org/ContentService`) — retrieve curated
  objects: pathways, reactions, complexes, proteins, small molecules, their
  attributes and participants; free-text search; map identifiers to pathways.
- **Analysis Service** (`https://reactome.org/AnalysisService`) — submit a list of
  identifiers (or an expression matrix) and get back enriched pathways with
  p-values and FDR, addressable later by a 7-day **token**.

Everything here is done with ordinary HTTP requests (`requests` in Python, `curl`
on the shell). No API key is required. The interactive Swagger UIs at
`https://reactome.org/ContentService/` and `https://reactome.org/AnalysisService/`
are the authoritative endpoint reference — consult them if a signature here looks
stale.

## When to Use This Skill

- You have a gene / protein / metabolite list and need the **enriched biological
  pathways** (overrepresentation analysis).
- You have a quantitative **expression matrix** and want pathway-level results.
- You need **detail for a Reactome stable ID** (`R-HSA-69278`): its type, species,
  description, sub-events, or participating molecules.
- You want to **search** Reactome by name/free text and resolve stable IDs.
- You are **mapping identifiers** (UniProt, Ensembl, gene symbol, ChEBI, …) to the
  pathways that contain them.
- You have **non-human** identifiers and want them **projected** to human pathways.
- You need a **Pathway Browser** deep-link to visualize an analysis on the diagram.

## When NOT to Use This Skill

- Querying a **different pathway/annotation resource** — KEGG, Gene Ontology,
  WikiPathways, STRING, MSigDB, PANTHER. Use `database-lookup` or that resource's
  own API; Reactome only knows Reactome.
- **Gene functional annotation, sequence, or variant** lookup — Reactome is
  pathway-centric, not a gene/sequence database.
- **Computing the input list** — differential expression, DESeq2, ranking. That is
  upstream analysis; bring the resulting identifier list here.
- **Offline graph / topology math** on a pathway network (shortest paths,
  centrality, community detection). Pull the structure, then use `networkx`.
- Bulk **whole-database dumps** — download the flat files / graph database from
  `https://reactome.org/download-data` instead of hammering the REST API.

## Base URLs and Quick Start

```python
import requests

CONTENT  = "https://reactome.org/ContentService"
ANALYSIS = "https://reactome.org/AnalysisService"

# Current database version (plain text, e.g. "94")
print(requests.get(f"{CONTENT}/data/database/version").text)
```

## Retrieving Pathway Data (Content Service)

The Content Service returns JSON (or plain text for scalar attributes). Common
starting points:

```python
# Full object for a stable ID (Pathway, Reaction, Complex, ...)
obj = requests.get(f"{CONTENT}/data/query/R-HSA-69278").json()
print(obj["displayName"], obj["schemaClass"], obj["species"][0]["displayName"])

# Molecules participating in a pathway / reaction
parts = requests.get(
    f"{CONTENT}/data/event/R-HSA-69278/participatingPhysicalEntities"
).json()

# Sub-events (reactions, subpathways) contained in a pathway
events = requests.get(f"{CONTENT}/data/pathway/R-HSA-69278/containedEvents").json()

# Free-text search (returns matches with stable IDs)
hits = requests.get(f"{CONTENT}/search/query", params={"query": "glycolysis"}).json()
```

For the full endpoint catalogue — single-attribute queries, identifier→pathway
mapping, bulk `/data/query/ids`, response object schema, and TSV output — see
`references/content-service.md`.

## Running Pathway Analysis (Analysis Service)

Submit identifiers as a plain-text body (one per line). You **must** set
`Content-Type: text/plain`, or the service returns `415 Unsupported Media Type`.

```python
genes = ["TP53", "BRCA1", "EGFR", "MYC", "CDK1"]
r = requests.post(
    f"{ANALYSIS}/identifiers/",
    headers={"Content-Type": "text/plain"},
    data="\n".join(genes),
).json()

token = r["summary"]["token"]                 # valid 7 days — save it
for p in r["pathways"][:10]:
    e = p["entities"]
    print(f"{p['stId']} {p['name']}  p={e['pValue']:.2e}  FDR={e['fdr']:.2e}")
```

- **Non-human input?** POST to `identifiers/projection/` to map orthologs onto
  human pathways.
- **Expression data?** Send a TSV whose header row starts with `#`; column 1 is the
  identifier, later columns are numeric values (period decimal separator).
- **Retrieve later:** `GET /token/{token}` returns the same structure without
  recomputing.
- **Visualize:** deep-link the Pathway Browser with the token:
  `https://reactome.org/PathwayBrowser/#{stId}&DTAB=AN&ANALYSIS={token}`.

For expression format details, file/URL submission, result filtering and
CSV/mapping downloads, the full response schema, a reusable client class, and a
complete enrichment workflow, see `references/analysis-service.md`.

## Identifiers and Input Formats

Reactome auto-detects the identifier type — you can mix a plain list without
declaring the namespace. Supported inputs include UniProt (`P04637`), gene symbols
(`TP53`), Ensembl (`ENSG00000141510`), EntrezGene (`7157`), RefSeq, ChEBI
(`CHEBI:15377`), KEGG Compound, PubChem, miRBase, and InterPro. Full list and
per-namespace notes are in `references/analysis-service.md`.

## Failure Modes and Gotchas

- **`415 Unsupported Media Type`** — you forgot `Content-Type: text/plain` on the
  analysis POST. This is the single most common mistake.
- **`404 Not Found`** — invalid or non-existent stable ID; the error body is JSON
  with `code`, `reason`, `messages`. Check `raise_for_status()` and branch on 404.
- **Token expiry** — analysis tokens live **7 days**. Persist the token if you need
  results across sessions; re-submit if it has expired.
- **Species** — analysis defaults to detecting the input species; use the
  `projection/` endpoints to force mapping onto human pathways.
- **`reactome2py` Python package** — v3.0.0 (Jan 2021) is unmaintained. It wraps the
  same two services via `content` and `analysis` modules, but prefer direct REST
  for anything current; verify function names against
  `https://reactome.github.io/reactome2py/` before relying on them.
- **Politeness / scale** — there is no hard rate limit, but batch all identifiers
  into a single POST rather than looping one gene at a time, cache results by
  token, and pull flat files from `download-data` for bulk needs.
- **Large result sets** — an enrichment can return hundreds of pathways; filter to
  `entities.fdr < 0.05` before presenting.

## References

- `references/content-service.md` — Content Service endpoint catalogue, entity and
  attribute queries, identifier→pathway mapping, search, response object schema,
  TSV output, error codes.
- `references/analysis-service.md` — Analysis Service submission (list, expression,
  file, URL, projection), token retrieval/filter/download, full JSON response
  schema, supported identifiers, Pathway Browser visualization, a reusable Python
  client, and an end-to-end enrichment workflow.

## Additional Resources

- Developer overview: https://reactome.org/dev
- Content Service Swagger: https://reactome.org/ContentService/
- Analysis Service Swagger: https://reactome.org/AnalysisService/
- User guide: https://reactome.org/userguide
- Data downloads: https://reactome.org/download-data
