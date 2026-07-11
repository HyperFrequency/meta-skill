---
name: arboreto
version: 0.1.0
description: >-
  Infer gene regulatory networks (GRNs) from a gene-expression matrix using
  arboreto's Dask-parallel regression algorithms — GRNBoost2 (gradient boosting,
  fast, the default) and GENIE3 (random forest, the classic benchmark) — which
  score how strongly each transcription factor regulates each target gene and
  return ranked TF–target–importance links. Use when you have a bulk or
  single-cell RNA-seq expression matrix (observations × genes) and want to
  reconstruct regulatory interactions, restrict inference to a known TF list,
  scale from a laptop's cores to a multi-node Dask cluster, or produce the
  adjacency table that seeds a SCENIC / pySCENIC run. Do NOT use for loading or
  QC of the expression matrix itself (use `scanpy` / `anndata`), for regulon
  pruning and AUCell activity scoring (that is pySCENIC, downstream), for
  differential expression (`pydeseq2`), or for analyzing and visualizing the
  resulting network graph (`networkx`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (arboreto)"
---

# Arboreto

## Overview

Arboreto reconstructs a gene regulatory network by turning inference into an
embarrassingly parallel regression problem. For **each target gene** it fits a
tree-ensemble regressor that predicts that gene's expression from the expression
of candidate regulators (transcription factors), then reads each regulator's
feature importance as an edge weight. The output is a ranked table of
`TF → target` links with importance scores.

Because every target gene is regressed independently, arboreto expresses the
whole job as a **Dask task graph** and the identical code runs on one machine's
cores or a multi-node cluster. Two algorithms share this strategy and differ
only in the regressor: **GRNBoost2** (gradient boosting, fast, recommended) and
**GENIE3** (random forest, the original method, kept for validation).

This skill is a **router**: it gives you the mental model, a working quick-start,
and a capability map, then delegates deep API surface, tuning, and scaling
recipes to `references/`.

## When to Use This Skill

- You have an expression matrix (bulk or single-cell RNA-seq), rows =
  observations (cells/samples), columns = genes, and want candidate regulatory
  edges.
- You want to restrict regulators to a curated transcription-factor list.
- You need to scale inference beyond a single core — local multiprocessing or a
  remote Dask cluster.
- You are producing the GRN adjacency table that feeds a SCENIC / pySCENIC
  pipeline.
- You need reproducible, seed-controlled network inference.

## When NOT to Use This Skill

- **Loading, normalizing, or QC-ing the expression matrix** — that is `scanpy`
  (single-cell pipeline) and `anndata` (the container). Arboreto expects a
  clean numeric matrix as input.
- **Regulon refinement / activity scoring** — cis-target motif pruning and
  AUCell scoring are pySCENIC, applied *after* arboreto.
- **Differential expression** between conditions — use `pydeseq2`.
- **Graph analysis or plotting** of the inferred edges (centrality, modules,
  layout) — export the table and use `networkx`.
- **Causal / dynamical inference** requiring time-series ODEs or interventions —
  arboreto scores associational regulator importance, not causal direction.

## Installation

```bash
uv pip install arboreto
```

Pulls in `scipy`, `scikit-learn`, `numpy`, `pandas`, `dask`, and `distributed`.

## Quick Start

```python
import pandas as pd
from arboreto.algo import grnboost2
from arboreto.utils import load_tf_names

if __name__ == '__main__':                      # REQUIRED — see gotcha below
    # Expression matrix: rows = observations, columns = gene names
    expression_matrix = pd.read_csv('expression_data.tsv', sep='\t')

    # Optional: restrict regulators to a known TF list (one name per line)
    tf_names = load_tf_names('transcription_factors.txt')

    network = grnboost2(
        expression_data=expression_matrix,
        tf_names=tf_names,     # omit or pass 'all' to let every gene be a regulator
        seed=777,              # for reproducibility
    )

    # Columns: TF, target, importance (descending importance)
    network.to_csv('network.tsv', sep='\t', index=False, header=False)
```

> **Critical gotcha:** always wrap execution in `if __name__ == '__main__':`.
> Dask spawns worker **processes** that re-import your module; without the guard
> they recursively re-launch inference and the run hangs or errors.

## The Two Algorithms

| | `grnboost2` | `genie3` |
|---|---|---|
| Regressor | Stochastic gradient boosting (`GBM`) | Random forest (`RF`) |
| Speed | Fast; built for 10k+ observations | Slower |
| Role | Default choice for most work | Classic benchmark / validation |
| Output | `TF, target, importance` | identical |

Both share the signature
`algo(expression_data, gene_names=None, tf_names='all', client_or_address='local', seed=None, verbose=False)`.
Start with `grnboost2`; reach for `genie3` only to reproduce published GENIE3
results or to cross-check GRNBoost2 edges. For custom scikit-learn regressor
kwargs, drop to the lower-level `arboreto.algo.diy(...)` — see
`references/algorithms.md`.

## Capability Map

### Input data and output — `references/inference.md`
Accepted inputs (pandas DataFrame with gene column headers, or NumPy array plus
a matching `gene_names` list); TF restriction via `load_tf_names`; the
`TF / target / importance` output schema and how to interpret and threshold it;
edge-filtering strategies (top-N per target, importance cutoff, consensus over
seeds); a self-contained runnable inference script; and common failure modes
(empty results, transposed matrix, name mismatches).

### Algorithm selection and tuning — `references/algorithms.md`
GRNBoost2 vs GENIE3 in depth; the shared multiple-regression strategy; the
`diy()` escape hatch with `regressor_type` (`'GBM'`, `'RF'`, `'ET'`) and
`regressor_kwargs`; `early_stop_window_length` for GRNBoost2 early stopping; and
a decision guide for picking and configuring a regressor.

### Distributed / Dask scaling — `references/distributed.md`
The Dask task-graph model; default local multiprocessing; a custom `LocalCluster`
+ `Client` for resource control and client reuse across runs; connecting to a
remote `dask-scheduler` for cluster-scale datasets; the Dask dashboard for
monitoring; and worker-configuration and performance tuning (`threads_per_worker=1`
to dodge GIL contention, TF-list narrowing, low-variance gene filtering).

## SCENIC / pySCENIC Integration

Arboreto is step 1 of the SCENIC workflow. It produces the co-expression
adjacencies; pySCENIC then prunes them to regulons using cis-regulatory motif
databases and scores per-cell regulon activity with AUCell.

```python
from arboreto.algo import grnboost2
# Step 1 (this skill): co-expression adjacencies
adjacencies = grnboost2(expression_data=sc_matrix, tf_names=tf_list, seed=42)
# Step 2 (pySCENIC, separate package): ctx -> regulons, then aucell -> activity
```

Keep the raw adjacency table; pySCENIC's `ctx` consumes exactly the
`TF / target / importance` columns arboreto emits.

## Reproducibility

GRNBoost2 and GENIE3 subsample stochastically, so **always pass `seed=`** for a
deterministic run. For robustness, infer across several seeds and keep only the
consensus edges (see the multi-seed pattern in `references/distributed.md`,
which reuses one `Client` across runs).

## Related Skills

- `scanpy` / `anndata` — produce and QC the expression matrix that feeds arboreto.
- `dask` — the distributed engine underneath; use it directly to tune clusters.
- `scikit-learn` — the regressors (`GradientBoostingRegressor`, `RandomForestRegressor`) arboreto wraps.
- `networkx` — analyze and visualize the inferred edge table.
- `scvi-tools` / `pydeseq2` — complementary single-cell modeling and DE that sit around a GRN analysis.

## Reference Index

- `references/inference.md` — input formats, output schema, TF filtering, thresholding, runnable script, failure modes.
- `references/algorithms.md` — GRNBoost2 vs GENIE3, `diy()` custom regressors, parameters, selection guide.
- `references/distributed.md` — Dask local and cluster execution, dashboard, performance tuning.

## Resources

- Documentation: https://arboreto.readthedocs.io/
- Source: https://github.com/aertslab/arboreto
- SCENIC / pySCENIC (downstream): https://pyscenic.readthedocs.io/
