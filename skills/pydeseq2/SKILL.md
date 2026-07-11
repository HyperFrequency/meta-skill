---
name: pydeseq2
version: 0.1.0
description: >-
  Run differential gene expression analysis on bulk RNA-seq with PyDESeq2, the
  pure-Python reimplementation of the DESeq2 method. Fits size factors, gene-wise
  and shrunk (MAP) dispersions, and log2 fold changes from a raw integer count
  matrix, then runs Wald tests with Benjamini-Hochberg FDR control and optional
  apeGLM LFC shrinkage. Use when testing bulk RNA-seq counts for differential
  expression between conditions (treated vs control), building single- or
  multi-factor designs that adjust for batch or continuous covariates, porting an
  R DESeq2 workflow to Python, or embedding DE analysis in a pandas/AnnData
  pipeline. Do NOT use for already-normalized values (TPM/FPKM/CPM — DESeq2 needs
  raw counts), single-cell differential expression (use scanpy/scverse tooling),
  microarray or continuous-intensity data (use limma), transcript quantification
  from reads (that is upstream salmon/kallisto), or gene-set enrichment
  (downstream). For the AnnData container itself see `anndata`.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (PyDESeq2, owkin/PyDESeq2)"
---

# PyDESeq2

## Overview

PyDESeq2 reimplements the DESeq2 differential-expression method in Python
(NumPy/SciPy/scikit-learn), so you can run a full bulk RNA-seq DE workflow
without R. It targets parity with DESeq2 v1.34.0 defaults; because it is a
from-scratch reimplementation, minor numerical differences from R DESeq2 are
expected.

An analysis has two objects and two phases:

1. **`DeseqDataSet` (dds)** — models the counts: size-factor normalization,
   dispersion estimation (gene-wise → trend → MAP shrinkage), log2 fold-change
   fitting, and Cook's-distance outlier detection. Driven by `dds.deseq2()`.
2. **`DeseqStats` (ds)** — runs Wald tests for one contrast, applies Cook's and
   independent filtering, and BH-adjusts p-values. Driven by `ds.summary()`;
   `ds.lfc_shrink()` optionally shrinks fold changes for plotting/ranking.

This SKILL.md is a router. It gives the quick path and a capability map, then
delegates deep API detail, extended patterns, and troubleshooting to
`references/`.

## When to Use This Skill

Use this skill when you need to:

- Identify differentially expressed genes from **bulk RNA-seq raw counts** (a
  samples × genes integer matrix plus per-sample metadata).
- Compare expression between groups — e.g. treated vs control — via a Wald-test
  contrast with FDR-adjusted p-values.
- Build **multi-factor designs** (`~batch + condition`, continuous covariates,
  interaction terms) to control for confounders.
- Port an existing R **DESeq2** pipeline to Python, or embed DE analysis inside a
  pandas / AnnData / scverse workflow.
- Produce volcano and MA plots, or rank genes by shrunken effect size for
  follow-up.

Trigger terms: "DESeq2", "PyDESeq2", "differential expression", "DE genes",
"RNA-seq analysis", "log2 fold change", "volcano plot".

## When NOT to Use This Skill

- **Not raw counts.** DESeq2's model assumes raw integer counts. Do not feed
  TPM, FPKM, RPKM, CPM, or otherwise normalized/log-transformed values.
- **Single-cell RNA-seq DE** — use scanpy/scverse (`rank_genes_groups`,
  pseudobulk) rather than per-cell DESeq2. See `anndata` for the container.
- **Microarray or continuous intensities** — use limma.
- **Read → counts quantification** — alignment/quantification (salmon, kallisto,
  featureCounts, STAR) is upstream of this skill; PyDESeq2 starts from a count
  matrix.
- **Gene-set / pathway enrichment** (GSEA, ORA) is a downstream step that
  consumes these results, not part of PyDESeq2.

## Installation

```bash
uv pip install pydeseq2   # or: pip install pydeseq2
```

Runtime: Python 3.10–3.11; pandas, numpy, scipy, scikit-learn, anndata.
Add `matplotlib` (and optionally `seaborn`) for plots.

## Quick Start

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# 1. Load. Count CSVs are usually genes × samples — transpose to samples × genes.
counts_df = pd.read_csv("counts.csv", index_col=0).T
metadata  = pd.read_csv("metadata.csv", index_col=0)

# 2. Filter low-count genes (improves power and speed).
genes_to_keep = counts_df.columns[counts_df.sum(axis=0) >= 10]
counts_df = counts_df[genes_to_keep]

# 3. Model the counts.
dds = DeseqDataSet(
    counts=counts_df,
    metadata=metadata,
    design="~condition",   # Wilkinson (R-style) formula
    refit_cooks=True,
)
dds.deseq2()

# 4. Test one contrast: [factor, test_level, reference_level].
ds = DeseqStats(dds, contrast=["condition", "treated", "control"], alpha=0.05)
ds.summary()

# 5. Interpret. Use padj (FDR), not raw pvalue, for significance.
results = ds.results_df
significant = results[results.padj < 0.05]
print(f"{len(significant)} significant genes (padj < 0.05)")
```

## Result Columns (`ds.results_df`)

| Column | Meaning |
| --- | --- |
| `baseMean` | Mean normalized count across all samples |
| `log2FoldChange` | Log2 fold change, test vs reference level |
| `lfcSE` | Standard error of the log2 fold change |
| `stat` | Wald test statistic |
| `pvalue` | Raw p-value |
| `padj` | BH-adjusted p-value (FDR) — filter on this |

`NaN` in `padj` means the gene was dropped by independent or Cook's filtering.

## Capability Map — Where to Go Next

- **Data loading, filtering, single/multi-factor designs, interactions,
  covariates, export, and best practices** → `references/workflows.md`
- **Full API surface** — `DeseqDataSet`/`DeseqStats` parameters, `deseq2()`,
  `summary()`, `lfc_shrink()`, stored attributes (`layers`, `varm`, `obsm`,
  `uns`), `to_picklable_anndata()`, utility/inference classes →
  `references/api.md`
- **Volcano/MA plots, QC diagnostics, and troubleshooting** (index mismatch,
  transpose errors, non-full-rank design, no significant genes, memory) →
  `references/plots-and-troubleshooting.md`

## Non-Negotiable Rules

1. **Orientation:** counts must be **samples × genes**. Genes-in-rows CSVs need
   `.T`. If "all genes have zero counts," you likely forgot to transpose.
2. **Raw integer counts only** — never normalized values (see When NOT above).
3. **Design order:** put adjustment variables *before* the variable of interest,
   e.g. `~batch + condition`, not `~condition + batch`.
4. **Contrast form:** `[variable, test_level, reference_level]`; the LFC sign is
   test relative to reference. `contrast=None` uses the design's last coefficient.
5. **Significance:** threshold on `padj` (BH-FDR), not raw `pvalue`.
6. **LFC shrinkage** (`ds.lfc_shrink()`, apeGLM) changes only `log2FoldChange` for
   visualization/ranking — p-values are unchanged. Report unshrunken p-values;
   use shrunken LFCs for plots and effect-size ranking only.
7. **Persist expensive fits:** `pickle.dump(dds.to_picklable_anndata(), f)` so you
   can re-test contrasts without re-running `deseq2()`.
