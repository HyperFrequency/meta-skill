---
name: gtars
version: 0.1.0
description: >-
  High-performance Rust toolkit — with Python bindings and a `gtars` CLI — for
  genomic interval analysis: BED and fragment region sets, IGD-indexed overlap
  detection, uniwig coverage tracks (WIG/BigWig/bedGraph), region tokenization
  for genomic ML (the Rust core behind the geniml library), GA4GH refget
  sequence digests, and single-cell fragment splitting and scoring. Use when
  manipulating genomic regions, detecting overlaps across large interval sets,
  building coverage tracks, tokenizing regions for deep-learning models,
  splitting scATAC fragments by barcode or cluster, or computing refget
  digests. NOT for sequence alignment, variant calling, statistical
  genetics/GWAS, or general non-interval genomics I/O (use the
  bedtools/bcftools/pysam ecosystems); and not for downstream model training
  itself — tokenize regions here, then model with `transformers`.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: gtars is developed by the Databio lab (databio/gtars); check the upstream repository for its current license
---

# Gtars: Genomic Tools and Algorithms in Rust

## Overview

`gtars` is a Rust toolkit for manipulating and analyzing genomic **interval**
data at scale. It ships three surfaces from one codebase:

- a **Rust crate** (`gtars` on crates.io) with feature-gated modules,
- a **`gtars` CLI** binary for shell and batch workflows,
- **Python bindings** (`gtars` on PyPI, built with maturin/PyO3) for use inside
  analysis pipelines.

It is the performance core beneath the **geniml** genomic-interval machine-learning
library (also from the Databio lab): geniml delegates region operations and
tokenization to gtars. Reach for gtars whenever interval work is the bottleneck
— overlap queries over millions of regions, coverage-track generation, or
turning regions into tokens for a model.

The library is organized into focused modules, each gated behind a Cargo
feature and mirrored by a CLI subcommand and a Python submodule:

| Module      | What it does                                              | Reference |
| ----------- | -------------------------------------------------------- | --------- |
| region sets | Load, filter, sort, merge, and export BED interval sets  | [python-api.md](references/python-api.md) |
| `overlaprs` / `igd` | Overlap detection; IGD index for fast queries at scale | [overlap.md](references/overlap.md) |
| `uniwig`    | Coverage tracks (WIG / BigWig / bedGraph) from intervals | [coverage.md](references/coverage.md) |
| `tokenizers`| Region → token conversion for genomic ML (geniml)        | [tokenizers.md](references/tokenizers.md) |
| `refget`    | GA4GH refget sequence retrieval and digests              | [refget.md](references/refget.md) |
| `fragsplit` / `scoring` / `bbcache` | scATAC fragment splitting, region scoring, BEDbase cache | [cli.md](references/cli.md) |

## When to Use This Skill

Use gtars when a task involves genomic **intervals** and any of:

- **Overlap detection** — comparing peak sets, annotating variants against
  features, or querying one region set against a large database. Use the IGD
  index when the reference set is large or queried repeatedly. See
  [overlap.md](references/overlap.md).
- **Coverage tracks** — building ATAC/ChIP/RNA-seq coverage profiles or BigWig
  files for genome browsers. See [coverage.md](references/coverage.md).
- **Genomic ML preprocessing** — tokenizing regions for transformer or
  region-embedding models, especially alongside geniml. See
  [tokenizers.md](references/tokenizers.md).
- **Single-cell fragments** — splitting a 10x scATAC `fragments.tsv` by cell
  barcode or by cluster assignment, then scoring against a reference universe.
  See [cli.md](references/cli.md).
- **Reference sequences** — computing or verifying GA4GH refget digests, or
  extracting subsequences from a FASTA. See [refget.md](references/refget.md).
- **Region-set algebra** — sort, merge, union/intersect/subtract, filter by
  size or chromosome, and BED/NumPy export. See
  [python-api.md](references/python-api.md).

## When NOT to Use This Skill

- **Read alignment or variant calling** — gtars operates on intervals, not raw
  reads or variants. Use `bwa`/`minimap2`, `bcftools`, `samtools`/`pysam`.
- **General BED arithmetic in a shell** where `bedtools` already fits and scale
  is small — gtars pays off mainly at large interval counts or repeated
  queries.
- **Statistical genetics / GWAS / association testing** — out of scope.
- **Downstream model training** — gtars produces tokens and features; train the
  model with `transformers`, `pytorch-lightning`, or `scikit-learn`, and
  analyze result tables with `data-analysis` / `polars`.
- **Non-interval genomics I/O** (SAM/BAM/VCF/GFF parsing beyond intervals) —
  use the htslib ecosystem.

## Installation

```bash
# Python bindings
uv pip install gtars          # or: pip install gtars

# CLI (needs Rust/Cargo). Feature flags gate which modules are compiled in.
cargo install gtars --features "uniwig overlaprs igd bbcache scoring fragsplit"
# or compile only what you need:
cargo install gtars --features "uniwig overlaprs"
```

```toml
# Rust library (Cargo.toml)
[dependencies]
gtars = { version = "0.1", features = ["tokenizers", "overlaprs"] }
```

Feature names map to modules; omit features you do not need to keep the binary
small. Confirm the exact feature set with `cargo search gtars` and the upstream
repository, since the module list evolves pre-1.0.

## Choosing a Surface: Python vs CLI vs Rust

- **Python** — integrating with an analysis pipeline, NumPy/Pandas/Polars
  interop, or programmatic control inside a notebook or script.
- **CLI** — one-off analyses, shell scripting, and batch processing of many
  files. See [cli.md](references/cli.md) for the full subcommand map.
- **Rust** — embedding interval operations in a performance-critical Rust
  service with zero Python overhead.

## Verifying APIs Before You Rely on Them

gtars is pre-1.0 and its Python/CLI signatures change between releases. The
code in the reference files shows **capability and idiomatic shape**, not
guaranteed-stable signatures. Before depending on a specific method or flag:

```python
import gtars
help(gtars)                 # top-level modules actually present
help(gtars.tokenizers)      # submodule surface for your installed version
```

```bash
gtars --help                # available subcommands (depends on compiled features)
gtars uniwig --help         # exact flags for a subcommand
```

If a symbol or flag shown in the references is absent in your build, treat the
reference as describing intent and adapt to what `help()` / `--help` reports.
Authoritative sources: the **databio/gtars** GitHub repository, the PyPI
`gtars` page, and the crates.io `gtars` page.

## Related Skills

- `transformers` / `pytorch-lightning` — train models on tokens produced here.
- `data-analysis` / `polars` — analyze overlap counts and coverage tables.
- `scientific-pipeline-builder` — assemble gtars steps into a reproducible
  pipeline.

## Reference Files

- [references/python-api.md](references/python-api.md) — region-set model,
  region algebra, set operations, export, NumPy interop, streaming, errors.
- [references/overlap.md](references/overlap.md) — IGD indexing and the
  `overlaprs` overlap/count/filter/subtract operations.
- [references/coverage.md](references/coverage.md) — `uniwig` coverage tracks,
  output formats, and per-assay recipes.
- [references/tokenizers.md](references/tokenizers.md) — region tokenization
  for genomic ML and the geniml handoff.
- [references/refget.md](references/refget.md) — GA4GH refget digests and
  sequence retrieval.
- [references/cli.md](references/cli.md) — complete CLI subcommand reference and
  fragment (`fragsplit`), `scoring`, and `bbcache` workflows.
