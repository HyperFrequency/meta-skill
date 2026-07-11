---
name: string-database
version: 0.1.0
description: >-
  Query the STRING database (v12, ~59M proteins and 20B+ interactions across
  5000+ organisms) for protein-protein interactions and functional associations
  through its public REST API (string-db.org/api). Use to map gene symbols to
  STRING IDs, retrieve interaction networks with per-channel evidence scores,
  list a protein's top interaction partners, test whether a protein set is more
  connected than chance (PPI enrichment), run GO/KEGG/Pfam/Reactome functional
  enrichment on a gene list, fetch homology scores, or render network images
  (PNG/SVG). Drive it with plain HTTP (requests), choosing a confidence
  threshold and a functional-vs-physical network type. NOT for proteome-scale
  analytics (download the STRING flat files instead of hammering the API),
  protein structures (use alphafold-database), gene/sequence lookups (use
  ensembl-database or gget), or local graph metrics after retrieval (use
  networkx).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: STRING data is CC BY 4.0
---

# STRING Database

## Overview

STRING (Search Tool for the Retrieval of Interacting Genes/Proteins) is a
manually curated and computationally predicted database of protein-protein
interactions and functional associations. Version 12 covers ~59 million
proteins and 20+ billion interactions across 5000+ genomes, integrating
evidence from experiments, curated pathway databases, co-expression,
conserved genomic context, and text-mining. It is an ELIXIR Core Data Resource.

This skill drives the public STRING REST API over plain HTTP. You send a gene
list or STRING IDs to a small set of endpoints and get back TSV, JSON, XML, or
a rendered PNG/SVG network. There is no bundled client to install — a few lines
of `requests` cover every operation. Depth (full endpoint specs, output
columns, worked multi-step workflows) lives in `references/`.

## When to Use This Skill

Use this skill when you need to:

- Map gene symbols, UniProt IDs, or synonyms to canonical STRING IDs.
- Retrieve an interaction network for one or more proteins, with per-channel
  evidence scores (experiments, database, co-expression, text-mining, ...).
- List the top-N interaction partners of a protein (hub discovery, network
  expansion from seeds).
- Test whether a protein set has significantly more interactions than a random
  set of the same size (PPI enrichment — "do these proteins form a module?").
- Run functional enrichment (GO BP/MF/CC, KEGG, Reactome, Pfam, InterPro,
  UniProt keywords) over a gene list with FDR-corrected p-values.
- Fetch homology / best-hit similarity scores between proteins.
- Render a publication-style network image (evidence, confidence, or actions
  flavor).
- Compare interaction context across species by re-running with a different
  NCBI taxon ID.

## When NOT to Use This Skill

- **Proteome-scale or whole-database analytics** — do not loop the API over
  thousands of proteins. Download the STRING flat files
  (`string-db.org/cgi/download`) and query them locally.
- **Protein 3D structures / folds** — use `alphafold-database` (or a PDB skill).
- **Gene models, sequences, variants, orthologs at the DNA level** — use
  `ensembl-database` or `gget`.
- **Local graph metrics after retrieval** (centrality, communities, shortest
  paths) — pull the network here, then analyze with `networkx`.
- **A one-off lookup across many biological databases at once** — `database-lookup`
  routes broad queries; `bioservices` also wraps STRING alongside dozens of
  other services if you want one Python client for everything.

## API Basics

- **Base URL**: `https://string-db.org/api`
- **Reproducible URL**: pin a version, e.g. `https://version-12-0.string-db.org/api`.
- **Request shape**: `{base}/{output_format}/{endpoint}`, e.g.
  `/tsv/network`, `/json/ppi_enrichment`, `/image/network`.
- **Method**: GET works for small inputs; use **POST for large identifier
  lists** (avoids URL length limits). The helper in `references/workflows.md`
  uses POST throughout.
- **Identifier separator**: STRING expects identifiers separated by a carriage
  return (`%0d` in a raw URL). With `requests`, join with `"\r"` and let the
  library encode — do **not** pre-encode to `"%0d"` and re-encode.
- **`caller_identity`**: pass a short string naming your app/project on every
  call (STRING asks callers to self-identify). Use your own value, not a
  placeholder.
- **Rate limits**: no hard cap, but pause ~1s between calls; batch identifiers
  into one request rather than looping per protein.
- **Errors**: check HTTP status. 400 = bad params, 404 = unknown
  protein/species, empty body = nothing passed the score threshold.

Minimal call:

```python
import requests

r = requests.post(
    "https://string-db.org/api/tsv/network",
    data={"identifiers": "TP53\rMDM2\rATM", "species": 9606,
          "required_score": 700, "caller_identity": "my_project"},
    timeout=60,
)
r.raise_for_status()
print(r.text)   # TSV: stringId_A/B, preferredName_A/B, score, nscore..tscore
```

## Core Endpoints

Each takes `identifiers`, `species` (NCBI taxon ID), and `caller_identity`.
Full parameter lists and output columns are in `references/rest-api.md`.

| Endpoint | Purpose | Key extra params |
|---|---|---|
| `get_string_ids` | Map names/IDs to STRING IDs | `limit`, `echo_query` |
| `network` | Interaction network as a table | `required_score`, `network_type`, `add_nodes` |
| `interaction_partners` | Top-N partners of the input | `required_score`, `limit` |
| `ppi_enrichment` | Is the set more connected than chance? | `required_score` |
| `enrichment` | GO/KEGG/Reactome/Pfam term enrichment | — |
| `homology` | Pairwise similarity/best-hit scores | — |
| `image/network` | Rendered PNG/SVG network | `network_flavor`, `add_nodes`, `highres` |
| `version` | Current DB version (reproducibility) | — |

Best practice: run `get_string_ids` first, then feed the returned
`9606.ENSP...` identifiers to the other endpoints — it is faster and avoids
ambiguous name matches.

## Confidence Scores and Network Types

STRING reports a **combined score (0-1000)** per interaction, fused from seven
independent evidence channels (columns `nscore` neighborhood, `fscore` fusion,
`pscore` phylogenetic co-occurrence, `ascore` co-expression, `escore`
experiments, `dscore` curated database, `tscore` text-mining). Filter with
`required_score`:

| Threshold | Meaning | Use for |
|---|---|---|
| 150 | low | exploration, hypothesis generation (noisy) |
| 400 | medium (default) | balanced everyday analysis |
| 700 | high | conservative, figure-ready networks |
| 900 | highest | very stringent, experiment-weighted |

Higher thresholds trade recall for precision. Pick `network_type`:

- **`functional`** (default): any association evidence — right for pathway and
  enrichment work.
- **`physical`**: direct binding only — right for complexes and structural
  questions.

See `references/workflows.md` for how thresholds and channels interact and how
to read individual evidence columns.

## Typical Workflow

For an experiment-derived gene list: map -> build network -> test connectivity
-> enrich -> visualize.

```python
genes = ["TP53", "BRCA1", "ATM", "CHEK2", "MDM2", "ATR", "BRCA2"]
# 1. map to STRING IDs (get_string_ids)
# 2. network(required_score=400) -> interaction table
# 3. ppi_enrichment -> p_value; < 0.05 => the set forms a module
# 4. enrichment -> filter rows where fdr < 0.05 for GO/KEGG terms
# 5. image/network(network_flavor="evidence") -> PNG for a figure
```

Runnable helper functions and five end-to-end recipes (single-protein deep
dive, pathway-centric, cross-species, seed-and-expand discovery) are in
`references/workflows.md`.

## Common Species

| Organism | NCBI taxon ID |
|---|---|
| Homo sapiens (human) | 9606 |
| Mus musculus (mouse) | 10090 |
| Rattus norvegicus (rat) | 10116 |
| Drosophila melanogaster (fly) | 7227 |
| Caenorhabditis elegans | 6239 |
| Saccharomyces cerevisiae (yeast) | 4932 |
| Arabidopsis thaliana | 3702 |
| Danio rerio (zebrafish) | 7955 |
| Escherichia coli K-12 | 511145 |

Full list: `https://string-db.org/cgi/input?input_page_active_form=organisms`.
`species` is required whenever you pass more than ~10 identifiers.

## References

- `references/rest-api.md` — every endpoint, all parameters, output columns,
  output formats (TSV/JSON/XML/PSI-MI/image), STRING ID format, the async
  values/ranks enrichment API, error codes, versioned URLs, and bulk download.
- `references/workflows.md` — self-contained `requests` helper module, the five
  analysis workflows, evidence-channel interpretation, troubleshooting, and
  integration notes (`bioservices`, R `STRINGdb`, Cytoscape stringApp).

## Data License and Citation

STRING data is released under **Creative Commons BY 4.0** (free for academic
and commercial use, attribution required). When publishing, cite the most
recent STRING paper listed at `https://string-db.org/cgi/about`.
