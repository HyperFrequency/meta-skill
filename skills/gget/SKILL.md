---
name: gget
version: 0.1.0
description: >-
  Query 20+ genomics and bioinformatics databases from one consistent CLI/Python
  interface (gget, Pachter Lab): gene lookup (ref, search, info, seq), sequence
  alignment (blast, blat, muscle, diamond), protein structure (pdb, alphafold,
  elm), and expression/disease data (archs4, cellxgene, enrichr, bgee,
  opentargets, cbio, cosmic). Use for fast, reproducible one-liners against live
  reference databases — resolve gene IDs, fetch sequences/structures, run
  enrichment, pull tissue/single-cell expression, or map disease/drug
  associations — where each module doubles as a shell command and a Python
  function returning a DataFrame. Do NOT use for heavy batch pipelines or custom
  BLAST parameterization (use `biopython`), broad programmatic multi-database
  orchestration (use `bioservices`), or local single-cell analysis on data you
  already hold (use `anndata`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: BSD-2-Clause
---

# gget

## Overview

`gget` is a bioinformatics tool from the Pachter Lab that wraps 20+ public
genomic databases behind a single, uniform interface. Every module works two
ways with identical semantics:

- **Shell:** `gget <module> [args] [flags]` — prints JSON (default) or CSV (`-csv`).
- **Python:** `gget.<module>(args, ...)` — returns a pandas DataFrame, dict, or
  domain object (FASTA string, AnnData, PDB file).

Reach for gget when you want a quick, correct answer from a live database
without writing an API client. The databases behind gget change structure over
time; gget is tested biweekly and patched to track them, so **keep it current**
(`uv pip install --upgrade gget`) and pin releases when reproducibility matters
(see `references/databases.md`).

## When to Use This Skill

- Resolve a gene symbol or description to Ensembl/UniProt/NCBI IDs and metadata.
- Fetch nucleotide or protein sequences (including all isoforms) as FASTA.
- Run a one-off BLAST/BLAT/DIAMOND search or a multiple-sequence alignment.
- Retrieve or predict a protein structure (RCSB PDB download, or AlphaFold2).
- Pull tissue-level, single-cell, or co-expression data for a gene.
- Run ontology/pathway enrichment on a gene list.
- Map a gene to diseases, drugs, tractability, or cancer mutations.
- Download Ensembl reference genome/annotation files for a downstream pipeline.

## When NOT to Use This Skill

- **Heavy batch jobs or custom BLAST tuning** (thousands of queries, non-default
  scoring matrices, local databases you control) — use `biopython`.
- **Programmatic orchestration across many databases** with fine-grained control
  of each web service — use `bioservices`.
- **Single-cell analysis on data you already have** (QC, clustering, DE) — gget
  only *fetches* the AnnData; analyze it with `anndata` / a scanpy pipeline.
- **Cancer cohort analysis beyond a quick heatmap** — `gget cbio` plots
  cBioPortal data, but curated cohort workflows belong in `cancer-genomics-analysis`.
- Anything requiring an offline/air-gapped environment — most modules hit live
  APIs.

## Install and Invoke

```bash
# Recommended: install into a clean virtualenv to avoid dependency conflicts
uv pip install gget            # or: pip install --upgrade gget

# Some modules need one-time setup that downloads local assets/binaries:
gget setup alphafold           # ~4GB model params (also needs: uv pip install openmm)
gget setup cellxgene           # installs cellxgene-census
gget setup elm                 # downloads local ELM database
```

```python
import gget
gget.search(["ACE2"], species="homo_sapiens")   # -> DataFrame
```

**Flags common to most modules:** `-o/--out` (save to file), `-q/--quiet`
(suppress progress), `-csv` (CSV instead of JSON, CLI only). In Python, pass
`save=True` or `out="file"` and `json=True` where supported.

## Module Map

Pick a module by task. Full parameter tables, return schemas, and per-module
gotchas live in **`references/module-reference.md`**.

### Gene & reference lookup

| Module | Does | Key input |
|--------|------|-----------|
| `ref` | Ensembl reference genome/annotation FTP links + download | species (`homo_sapiens`, `mouse`) |
| `search` | Find genes by name/description across Ensembl | search words + `-s` species |
| `info` | Merged Ensembl/UniProt/NCBI metadata (opt. PDB IDs) | Ensembl IDs (≤~1000) |
| `seq` | Nucleotide or protein FASTA, incl. all isoforms | Ensembl IDs |

### Sequence alignment & similarity

| Module | Does | Backend |
|--------|------|---------|
| `blast` | Sequence similarity search | NCBI BLAST |
| `blat` | Genomic position of a sequence | UCSC BLAT |
| `muscle` | Multiple sequence alignment | Muscle5 |
| `diamond` | Fast local protein / translated-DNA alignment | DIAMOND |

### Structure & motifs

| Module | Does | Notes |
|--------|------|-------|
| `pdb` | Download RCSB PDB structures/metadata | by PDB ID |
| `alphafold` | Predict 3D structure (simplified AlphaFold2) | needs `gget setup alphafold` |
| `elm` | Predict Eukaryotic Linear Motifs | needs `gget setup elm`; returns 2 DataFrames |

### Expression & disease

| Module | Does | Source |
|--------|------|--------|
| `archs4` | Correlated genes or tissue expression | ARCHS4 |
| `cellxgene` | Single-cell RNA-seq matrices (AnnData) | CZ CELLxGENE; needs setup; **case-sensitive genes** |
| `enrichr` | Ontology/pathway enrichment on a gene list | Enrichr |
| `bgee` | Orthologs or expression across species | Bgee |
| `opentargets` | Disease/drug/tractability/interactions | Open Targets |
| `cbio` | Cancer genomics heatmaps | cBioPortal |
| `cosmic` | Somatic cancer mutations | COSMIC (account + license) |

### Utilities

| Module | Does |
|--------|------|
| `mutate` | Generate mutated sequences from mutation annotations |
| `setup` | Install per-module dependencies (alphafold, cellxgene, elm, gpt) |
| `gpt` | Text generation via OpenAI API (needs key; peripheral to the bio core) |

## Quick Examples

```bash
gget ref --list_species                          # available vertebrate genomes
gget search -s human gaba receptor               # gene discovery
gget info ENSG00000034713 ENSG00000104853 -pdb   # metadata + PDB IDs
gget seq -t -iso ENSG00000034713                 # all protein isoforms (FASTA)
gget blast MKWMFKEDHSLEHRCVESAK -db swissprot -l 10
gget enrichr -db ontology ACE2 AGT AGTR1         # GO enrichment
gget opentargets ENSG00000169194 -r diseases -l 5
gget pdb 7S7U -o 7S7U.pdb
```

```python
adata = gget.cellxgene(gene=["ACE2", "ABCA1"], tissue="lung",
                       cell_type="mucus secreting cell")   # -> AnnData
ortholog_df, regex_df = gget.elm("LIAQSIGQASFV")           # two outputs
```

For chained, multi-module pipelines (gene discovery → sequence → structure →
enrichment → disease), see **`references/workflows.md`**.

## Boundaries & Failure Modes

- **Live databases drift.** A module that worked last month can error after a
  database restructures; the fix is usually `uv pip install --upgrade gget`.
  Check https://github.com/pachterlab/gget/issues.
- **`gget info` caps at ~1000 IDs** per call — batch larger sets and concatenate.
- **`cellxgene` gene symbols are case-sensitive:** `PAX7` (human) vs `Pax7`
  (mouse). Wrong case silently returns nothing.
- **`alphafold` is heavy:** ~4GB download, OpenMM dependency, Python-version
  sensitive, and compute-intensive. Check `gget pdb` for an experimental
  structure before predicting one. Raise `-mr 20` for multimer accuracy.
- **`cosmic` is gated:** requires a COSMIC account, a one-time database download,
  and a commercial license for non-academic use.
- **Rate limits:** for many sequential queries, add delays and cache results;
  prefer local backends (`diamond`, downloaded `cosmic`) when repeating work.
- **Reproducibility:** pin `release=` (Ensembl) / `census_version=` (cellxgene)
  and save raw outputs — details in `references/databases.md`.

## References

- **`references/module-reference.md`** — full parameter tables, defaults, and
  return schemas for every module.
- **`references/databases.md`** — the underlying databases, update cadence,
  versioning/pinning, and citation guidance.
- **`references/workflows.md`** — worked multi-module pipelines (gene analysis,
  comparative structure, cancer genomics, single-cell, reference building,
  mutation impact, drug-target discovery) plus caching/rate-limit helpers.

**Upstream:** docs https://pachterlab.github.io/gget/ ·
cite Luebbert, L. & Pachter, L. (2023), *Bioinformatics*,
https://doi.org/10.1093/bioinformatics/btac836
