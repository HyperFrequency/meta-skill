---
name: curated-bio-datasets
version: 0.1.0
description: >-
  Field guide to accessing eight major curated biological datasets for
  computational biology: COSMIC (somatic cancer mutations, Cancer Gene Census),
  GTEx (tissue expression, eQTLs), GWAS Catalog (SNP-trait associations),
  GeneBass (exome-wide burden tests), BioGRID (protein-protein interactions),
  MSigDB (gene set collections), DisGeNET (disease-gene associations), and Gene
  Ontology (GO terms and hierarchy). Covers download URLs, file formats, column
  schemas, parsing code, and the two workhorse analyses these datasets feed:
  overlap/pathway enrichment (hypergeometric + BH-FDR, gseapy) and PPI network
  construction (networkx). Use when downloading, parsing, filtering, or
  integrating any of these BULK datasets locally. NOT for one-off REST lookups
  of a single gene/variant/compound across many databases (use
  `database-lookup`), for cheminformatics on small molecules (use `rdkit`), or
  for querying your own/private/SQL databases.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Curated Bio-Datasets

## Overview

Eight public datasets cover most gene-, variant-, and pathway-level questions in
computational biology. Each ships as bulk files (or a REST API) with its own
schema, size, and licensing quirks. This skill routes you to the right dataset,
tells you how to download and parse it, and points to the two analyses these
datasets exist to feed: **pathway/overlap enrichment** and **protein-interaction
networks**. Deep column schemas, parsing snippets, and the enrichment/network
algorithms live in `references/` — read the relevant file before writing code.

## When to Use This Skill

- Downloading and filtering the COSMIC Cancer Gene Census (tiers, roles, tumour types).
- Loading GTEx tissue expression (TPM matrices, per-tissue medians, eQTLs).
- Filtering the GWAS Catalog for SNP-trait associations by trait, gene, or p-value.
- Reading GeneBass exome-wide burden-test results (pLoF / missense / synonymous).
- Building a protein-protein interaction network from a BioGRID download.
- Loading MSigDB `.gmt` collections and running pathway enrichment on a gene list.
- Querying DisGeNET disease-gene associations by gene or disease.
- Parsing Gene Ontology (`.obo` / `.json`) terms and walking the hierarchy.

## When NOT to Use This Skill

- **A single record over the REST API** (one gene, one variant, one compound
  across dozens of databases) → use `database-lookup`, which already wires up
  COSMIC, GTEx, GWAS Catalog, and 75 other endpoints.
- **Small-molecule cheminformatics** (SMILES, descriptors, similarity) → `rdkit`.
- **Statistical modeling or ML on the loaded tables** → `statsmodels`,
  `scikit-learn`, `statistical-analysis`.
- **Your own private / SQL databases** — nothing here queries user-owned data.

For single-database API deep-dives, prefer dedicated database skills where they
exist over the generic REST calls shown here.

## Install

```bash
uv pip install pandas requests networkx gseapy numpy
```

`gseapy` is only needed for enrichment; `networkx` only for PPI networks. The
enrichment math in `references/enrichment-and-networks.md` is pure-Python and
has no hard dependency on either.

## Dataset Map

Pick the dataset, then open its section in `references/dataset-catalog.md` for
exact URLs, column names, and parse code.

| Dataset | Contents | Access | Bulk format | Notes |
| --- | --- | --- | --- | --- |
| **COSMIC** | Somatic cancer mutations; Cancer Gene Census | Free academic registration required | CSV / TSV(.gz) | Full mutation export ~30 GB; use CGC for curated genes |
| **GTEx** | Tissue expression (TPM), eQTLs | Open; portal API + bulk | GCT(.gz), TSV, tar | TPM matrix ~2 GB; GRCh38/v8 coordinates |
| **GWAS Catalog** | SNP-trait associations | Open download | TSV | Apply genome-wide threshold 5e-8; prefer MAPPED_GENE |
| **GeneBass** | Exome-wide burden tests (UKB) | Open | TSV per phenotype | Exome-wide significance ~2.5e-6 |
| **BioGRID** | Protein-protein interactions | Open | tab3 TSV(.zip) | Filter by organism + experiment type |
| **MSigDB** | Gene set collections (H, C1-C8) | Open registration | GMT | Hallmark (H) most interpretable |
| **DisGeNET** | Disease-gene associations | Account required (post-2023) | TSV(.gz) | Filter by `score`; curated sources first |
| **Gene Ontology** | GO terms + is-a hierarchy | Open | OBO / JSON | Use QuickGO API for single-term lookups |

## The Two Workhorse Analyses

Most of these datasets terminate in one of two computations. Both are written up
in full — with runnable code — in `references/enrichment-and-networks.md`.

- **Pathway / overlap enrichment.** Given a gene list (DE genes, a cancer gene
  set, hits from a screen) and a collection of gene sets (MSigDB, GO, KEGG),
  score each set for overlap. Two paths: `gseapy` against Enrichr libraries
  online, or a local hypergeometric / Fisher's-exact test with Benjamini-Hochberg
  FDR correction over a downloaded `.gmt`. Use FDR < 0.05 and require the query
  list to have more than ~5 genes.

- **Protein-interaction networks.** Parse BioGRID tab3, filter to one organism
  (taxid 9606 = human) and high-confidence experiment types (`Affinity
  Capture-MS`, `Two-hybrid`), weight edges by publication support, build a
  `networkx` graph, and extract a subnetwork + hub genes around genes of
  interest. Topology metrics (density, clustering, components, degree hubs) come
  for free from `networkx`.

## Common Pitfalls

- **Gene-symbol mismatches** silently zero out overlaps and API hits. Normalize
  to current HUGO symbols; try ENSG IDs when a symbol returns nothing.
- **Reloading huge files.** COSMIC/GTEx bulk files are tens of GB. Filter once
  (organism, chunked reads, or command-line `grep`) and cache locally.
- **DisGeNET licensing changed in 2023** — the open TSV dumps were retired; the
  current API requires a free account and key. Verify access before scripting.
- **COSMIC requires registration** and enforces license terms; academic use is
  free but you must download the CSV manually or via its CLI first.
- **p-value columns arrive as strings.** Coerce with `pd.to_numeric(...,
  errors='coerce')` before thresholding GWAS or GeneBass results.
- **BioGRID self-interactions and cross-species rows** inflate networks — drop
  self-loops and filter both interactors to the target organism.

## References

- `references/dataset-catalog.md` — per-dataset download URLs, file formats,
  column schemas, parsing snippets, REST endpoints, and licensing caveats for
  all eight datasets.
- `references/enrichment-and-networks.md` — GMT parsing, hypergeometric/Fisher
  overlap enrichment with Benjamini-Hochberg FDR, `gseapy` usage, and BioGRID →
  `networkx` PPI network construction with topology statistics.
