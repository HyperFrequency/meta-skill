---
name: geniml
version: 0.1.0
description: >-
  Machine learning on genomic interval data (BED files) with the geniml (databio)
  toolkit. Use to train unsupervised embeddings of genomic regions (Region2Vec),
  joint region-plus-metadata embeddings for cross-modal search (BEDspace),
  single-cell ATAC-seq cell embeddings that plug into scanpy (scEmbed), build
  consensus-peak reference universes (CC/CCF/ML/HMM), tokenize regions against a
  universe, cache remote BED files, generate null models, or score embedding and
  clustering quality. Applies to BED-file collections, scATAC-seq AnnData, and
  chromatin-accessibility datasets. NOT for supervised deep-learning on raw DNA
  sequence (use a genomic sequence model), routine interval arithmetic like
  intersect/merge/slop (use bedtools/pybedtools), variant calling, or non-genomic
  tabular ML.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: BSD-2-Clause (geniml, databio)
---

# Geniml: Machine Learning on Genomic Intervals

## Overview

`geniml` is databio's Python toolkit for building unsupervised ML models on
genomic interval data (BED files). It learns low-dimensional embeddings of
genomic **regions**, single **cells**, and metadata **labels**, so you can run
similarity search, clustering, and downstream ML over chromatin-accessibility
and other region-based genomic data.

Every embedding method shares one mental model — commit it before touching any API:

```
1. Build a UNIVERSE   consensus peaks -> a fixed vocabulary of regions
2. TOKENIZE           map each BED file's regions onto universe tokens
3. EMBED              train Region2Vec / BEDspace / scEmbed on the tokens
4. USE                evaluate, search, cluster, or feed features downstream
```

The universe is load-bearing: it is the shared vocabulary, so the *same* universe
must be used across tokenization, training, and any later query. A weak universe
caps the quality of everything above it.

## Installation

```bash
uv pip install geniml            # core
uv pip install 'geniml[ml]'      # + PyTorch and ML extras (needed for training)
uv pip install git+https://github.com/databio/geniml.git   # dev version
```

`BEDspace` additionally needs StarSpace built separately (see
`references/bedspace.md`). Universe building uses the companion `uniwig` coverage
tool and `gtars` utilities.

## When to Use This Skill

- You have a **collection of BED files** and want feature vectors, similarity
  search, or clustering over region sets (Region2Vec).
- Your regions carry **metadata labels** (cell type, tissue, condition) and you
  want cross-modal search — region→label, label→region, region→region (BEDspace).
- You have **scATAC-seq** data (AnnData with peak coordinates) and need cell
  embeddings, clustering, or cell-type annotation that flows into scanpy (scEmbed).
- You need a **consensus-peak universe** — a statistically defined reference peak
  set — to standardize regions across experiments or to tokenize against.
- You need genomic ML plumbing: tokenization, caching remote BED files, null-model
  randomization, or embedding-quality metrics.

## When NOT to Use This Skill

- **Supervised models over raw DNA sequence** (motif/variant-effect prediction from
  base pairs) — geniml embeds *intervals*, not sequence; use a genomic
  deep-learning framework instead.
- **Routine interval arithmetic** — intersect, merge, slop, coverage-count over
  BED files is `bedtools`/`pybedtools` territory; only reach for geniml when you
  want *learned* representations.
- **Variant calling, alignment, or peak calling** — geniml consumes called peaks,
  it does not produce them.
- **Non-genomic tabular ML** — use `scikit-learn` directly.
- **Plotting embeddings** — geniml produces the vectors; project them with
  `umap-learn` and cluster/score with `scikit-learn`.

## Capabilities

Each capability has a dedicated reference with full parameters, CLI flags, and
runnable examples. Read the relevant one before implementing.

### Region2Vec — region-set embeddings

Word2vec-style unsupervised embeddings of genomic regions and region sets. Use for
dimensionality reduction of BED collections, region similarity, and feature vectors
for downstream supervised learning. Workflow: `hard_tokenization` against a
universe → `region2vec` training → embeddings. See `references/region2vec.md`.

### BEDspace — joint region + metadata embeddings

Trains region sets and their metadata labels into one shared space with StarSpace,
enabling metadata-aware search. Four-step CLI pipeline: `preprocess` → `train` →
`distances` → `search` with three query modes (`r2l`, `l2r`, `r2r`). Use when you
have labels and want to query across content and condition. See
`references/bedspace.md`.

### scEmbed — single-cell ATAC-seq embeddings

Applies Region2Vec to scATAC-seq to produce per-cell embeddings for clustering and
cell-type annotation, integrating with scanpy via `adata.obsm`. Workflow: AnnData
with peak coords → pre-tokenize cells → train → `encode` → `sc.pp.neighbors` /
`leiden` / `umap`. Pre-trained models available on Hugging Face. See
`references/scembed.md`.

### Consensus-peak universes

Build reference peak sets from many BED files with four methods of increasing rigor
and cost: **CC** (coverage cutoff), **CCF** (flexible boundaries via confidence
intervals), **ML** (maximum-likelihood position modeling), **HMM** (hidden-state
modeling). Start with CC; escalate only when boundaries are noisy or you need
statistical rigor. See `references/universes.md`.

### Tokenization & utilities

Supporting tools that the pipeline depends on: hard/soft/universe tokenization and
coverage checks, `BBClient` caching of remote BED files (BEDbase), `bedshift`
null-model randomization, embedding/clustering evaluation metrics (silhouette,
Davies-Bouldin, Calinski-Harabasz), cell-type annotation scoring, and Text2BedNN
search backends. See `references/utilities.md`.

## Choosing the right model

| You have… | You want… | Use |
|-----------|-----------|-----|
| Bulk BED files, no labels | Region vectors / similarity | **Region2Vec** |
| BED files + metadata labels | Cross-modal (region↔label) search | **BEDspace** |
| scATAC-seq AnnData | Cell embeddings + clustering | **scEmbed** |
| Many experiments | A consensus reference peak set | **Universe (CC→HMM)** |

## CLI entry points

```bash
geniml region2vec  --token-folder tokens/ --save-dir model/ --num-shuffle 1000
geniml bedspace    preprocess|train|distances|search ...
geniml universe    build cc|ccf|ml|hmm --coverage-folder coverage/ --output-file universe.bed
geniml bedshift    --input peaks.bed --genome hg38 --preserve-chrom --iterations 100
```

Full flag lists live in the per-capability references.

## Failure modes to anticipate

- **Low tokenization coverage** (<80% of regions map to universe tokens): the
  universe is incomplete or the genome assembly mismatches. Rebuild a broader
  universe or relax the p-value threshold (`1e-6` instead of `1e-9`). Always check
  coverage *before* training — see `references/utilities.md`.
- **Training won't converge**: reduce/raise the learning rate (0.01–0.05), add
  epochs/shufflings, and confirm tokens are non-empty.
- **Out-of-memory on scEmbed**: pre-tokenize to a parquet file, shrink batch size,
  or downsample cells; ML/HMM universe methods are also memory- and CPU-heavy.
- **`StarSpace not found`**: BEDspace's engine is an external C++ binary — build it
  and pass `--path-to-starspace`.
- **Universe/assembly drift**: mixing hg19 and hg38 regions silently degrades
  every embedding; keep one assembly per project and record it.

## Ecosystem & attribution

geniml is part of databio's BEDbase stack (BEDbase, BEDboss, `gtars`, BBClient);
pre-trained models ship under the `databio` org on Hugging Face. Docs:
`https://docs.bedbase.org/geniml/`. Source library is BSD-2-Clause; this skill is
adapted from an openscience (Synthetic Sciences) Apache-2.0 skill.
