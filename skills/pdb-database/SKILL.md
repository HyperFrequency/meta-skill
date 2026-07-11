---
name: pdb-database
version: 0.1.0
description: >-
  Programmatic access to the RCSB Protein Data Bank (PDB) for experimentally
  determined and computed 3D structures of proteins and nucleic acids. Use to
  search structures by text, attribute (organism, resolution, method, ligand),
  sequence similarity, or 3D-structure similarity; retrieve entry/entity/assembly
  metadata via the Data API (DataQuery or GraphQL); and download coordinate files
  (mmCIF, legacy PDB, BinaryCIF, FASTA). Wraps the official `rcsb-api` Python
  client and RCSB HTTP endpoints. Use when you have or need PDB IDs, are building
  a structural-biology or drug-discovery pipeline, or must batch-fetch structure
  data. Do NOT use for predicting new structures (use AlphaFold/folding tools),
  molecular docking or MD simulation, sequence-only databases like UniProt/NCBI,
  or parsing/analyzing already-downloaded coordinates (use BioPython/Biotite).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT (rcsb-api / py-rcsb-api, Copyright RCSB PDB)
---

# PDB Database

## Overview

The RCSB Protein Data Bank (PDB) is the worldwide archive of 3D structural data
for biological macromolecules: >220,000 experimentally determined structures plus
hundreds of thousands of Computed Structure Models (CSMs). This skill covers three
distinct access paths and when to reach for each:

- **Search API** — you have *criteria* (a name, an organism, a sequence, a query
  structure) and want the *PDB IDs* that match.
- **Data API** — you have *IDs* and want *metadata* (title, resolution, method,
  organism, ligands, sequence) as structured JSON.
- **File download** — you have IDs and want the *atomic coordinates* on disk to
  parse or visualize.

Access is via the official `rcsb-api` Python client (search + data) or plain HTTP
(downloads, REST, GraphQL). This SKILL.md routes; deep query grammar, field
tables, and examples live in `references/`.

## When to Use This Skill

- Finding protein/nucleic-acid structures by keyword, organism, resolution,
  experimental method, or bound ligand.
- Finding structures homologous (sequence) or geometrically similar (3D shape) to
  a query.
- Pulling experimental metadata or sequences for a known set of PDB IDs.
- Downloading mmCIF/PDB/BinaryCIF coordinate files for a pipeline.
- Batch-processing many structures (drug discovery, protein engineering,
  structural bioinformatics).

## When NOT to Use This Skill

- **Predicting a structure from sequence** — this archive only stores existing
  structures; use AlphaFold/ESMFold/Boltz or fetch a CSM by its `AF_`/`MA_` ID.
- **Docking, MD, or energy minimization** — download the coordinates here, then
  hand them to the relevant simulation tool.
- **Deep coordinate analysis** (RMSD, contacts, secondary structure) — parse the
  downloaded file with BioPython/Biotite; this skill fetches, it does not analyze.
- **Sequence-only or annotation databases** (UniProt, NCBI, Ensembl, ChEMBL) —
  use `database-lookup` for those.

## Setup

```bash
uv pip install rcsb-api          # unified Search + Data client (import: rcsbapi)
```

The legacy `rcsbsearchapi` package is deprecated — use `rcsb-api`. Downloads and
raw REST/GraphQL calls need only an HTTP client (`requests`/`httpx`); no key or
account is required for any RCSB endpoint.

## Core Capabilities

### 1. Search for structures → get IDs

Import query terminals and the attribute namespace, build a query from terminals,
then **call** the query object to iterate matching identifiers.

```python
from rcsbapi.search import TextQuery, AttributeQuery
from rcsbapi.search import search_attributes as attrs

# Full-text + attribute, combined with a bitwise AND
q = TextQuery("hemoglobin") & (attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens")

results = list(q())          # -> ['4HHB', '1A3N', ...]  (default return_type="entry")
count   = q(return_counts=True)
```

Operator-overload form (`attrs.<path> == value`) and the explicit
`AttributeQuery(attribute=..., operator=..., value=...)` form are equivalent.
Sequence-similarity (`SequenceQuery`), 3D-shape (`StructSimilarityQuery`), motif,
and chemical-similarity query types, the full operator list, searchable attribute
paths, and `return_type` options are in **[references/search-api.md](references/search-api.md)**.

### 2. Retrieve metadata → give IDs, get JSON

Use `DataQuery`; list the exact fields you want in `return_data_list` (GraphQL
dot-paths). One query can span many IDs.

```python
from rcsbapi.data import DataQuery as Query

q = Query(
    input_type="entries",                      # entries | polymer_entities | assemblies | ...
    input_ids=["4HHB", "1MBN"],
    return_data_list=[
        "struct.title",
        "exptl.method",
        "rcsb_entry_info.resolution_combined",
        "rcsb_entity_source_organism.scientific_name",
    ],
)
data = q.exec()   # dict: data["data"]["entries"][i][...]
```

Input types, the core data-object hierarchy, common field paths, raw REST
endpoints (`https://data.rcsb.org/rest/v1/core/...`), and the GraphQL endpoint are
in **[references/data-api.md](references/data-api.md)**.

### 3. Download coordinate files

Coordinates come from plain HTTPS URLs (no client library needed):

| Format | URL |
| --- | --- |
| mmCIF (modern standard) | `https://files.rcsb.org/download/{ID}.cif` |
| Legacy PDB text | `https://files.rcsb.org/download/{ID}.pdb` |
| Biological assembly 1 | `https://files.rcsb.org/download/{ID}.pdb1` |
| FASTA sequence | `https://www.rcsb.org/fasta/entry/{ID}` |
| BinaryCIF (compact) | `https://models.rcsb.org/{ID}.bcif` (ModelServer) |

Prefer **mmCIF** over legacy PDB — the PDB format cannot represent very large
structures. After download, parse with BioPython/Biotite (this skill stops at the
file). Download helpers, structure-factor/validation files, batch patterns, rate
limits (HTTP 429 + exponential backoff), and troubleshooting are in
**[references/files-and-ops.md](references/files-and-ops.md)**.

## Key Concepts

- **PDB ID** — 4-character code (e.g. `4HHB`). Computed Structure Models use
  longer `AF_`/`MA_` prefixes and coexist in Search/Data results.
- **Entity vs instance** — an *entity* is a unique molecule (a protein chain
  sequence, a ligand); an *instance* is one physical copy (chain) of it in the
  coordinates. IDs compose as `{ENTRY}_{ENTITY}` (e.g. `4HHB_1`).
- **Asymmetric unit vs biological assembly** — deposited coordinates are the
  asymmetric unit; the *biological assembly* is the functional oligomer, which may
  replicate chains via symmetry. Request assemblies explicitly.
- **Resolution** — crystallographic detail in Ångström; lower is sharper
  (~1.5–2.5 Å is high quality). Not defined the same way for NMR.

## References

- **[references/search-api.md](references/search-api.md)** — all 7 query types,
  operators, attribute paths, sequence/structure similarity, return types,
  boolean composition, counts and pagination.
- **[references/data-api.md](references/data-api.md)** — `DataQuery` construction,
  core object hierarchy, common field paths, REST + GraphQL endpoints, batch
  metadata retrieval.
- **[references/files-and-ops.md](references/files-and-ops.md)** — file formats
  and download URLs, BioPython parsing, rate limiting/backoff, error handling,
  worked drug-discovery and quality-filter recipes.

For other biological databases (UniProt, NCBI, ChEMBL), use `database-lookup`.

## External Resources

- RCSB PDB: https://www.rcsb.org · PDB-101 (education): https://pdb101.rcsb.org
- Web APIs overview: https://www.rcsb.org/docs/programmatic-access/web-apis-overview
- Data API: https://data.rcsb.org · Search API: https://search.rcsb.org
- `rcsb-api` client docs: https://rcsbapi.readthedocs.io ·
  source: https://github.com/rcsb/py-rcsb-api
