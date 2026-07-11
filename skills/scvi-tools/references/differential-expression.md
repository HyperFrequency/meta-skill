# Bayesian differential expression

scvi-tools tests differential expression (DE) by contrasting the *posterior*
expression distributions the trained generative model assigns to two groups of
cells. Because the model already accounts for batch and dropout, DE inherits
batch correction and needs no pseudocount. The same machinery drives
differential accessibility (PeakVI) and differential protein abundance (totalVI).

## Why the model-based approach

- **Batch correction folded in** — contrasts run on the corrected generative
  model, not raw counts.
- **Uncertainty quantified** — you get a posterior distribution of the log
  fold-change, not a point estimate.
- **Dropout handled** — ZINB/NB likelihoods model technical zeros properly.
- **No arbitrary pseudocount** and better calibrated than a Wilcoxon test.

## How it works (three stages)

1. **Estimate expression** — sample cell states from the posterior and generate
   expression from the decoder, aggregating to per-group means μ_A, μ_B.
2. **Hypothesis test** on the log fold-change `β = log μ_B − log μ_A`, in one of
   two modes (below).
3. **Control discovery** — rank genes by evidence and select the largest set
   whose posterior expected false-discovery proportion stays ≤ target.

## Basic usage

```python
# Two-group contrast
de = model.differential_expression(groupby="cell_type", group1="T cells", group2="B cells")

# One-vs-rest (omit group2)
de = model.differential_expression(groupby="cell_type", group1="T cells")

# Arbitrary cell masks
de = model.differential_expression(idx1=mask_a, idx2=mask_b)
```

## Key parameters

- `groupby` — categorical column in `adata.obs`.
- `group1`, `group2` — groups to contrast; omit `group2` for one-vs-rest.
- `mode` — hypothesis-test mode:
  - `"vanilla"` (default): point null `β = 0`. More sensitive; can flag
    trivially small effects.
  - `"change"`: composite null `|β| ≤ delta`. Requires a biologically meaningful
    change — usually preferred.
- `delta` — minimum |log fold-change| for `"change"` mode. Guides:
  `log2(1.5) ≈ 0.58`, `log2(2) = 1.0`. Common defaults 0.25-0.5.
- `fdr_target` — FDR threshold controlling the `is_de_fdr_*` flags (default 0.05).
- `batch_correction` — contrast across batches (default True) vs within one.
- `n_samples` — posterior samples (default large, e.g. 5000). More = more precise
  but slower; raise it for small groups.
- `protein_expression=True` — run the contrast on the protein modality (totalVI).

```python
de = model.differential_expression(
    groupby="condition", group1="disease", group2="healthy",
    mode="change", delta=0.5, fdr_target=0.05)
```

## Interpreting the results DataFrame

**Effect size**
- `lfc_mean`, `lfc_median` — posterior mean/median log fold-change (group1 vs group2).
- `lfc_std`, `lfc_min`, `lfc_max` — spread / bounds of the LFC posterior.

**Significance**
- `bayes_factor` — evidence for DE; higher is stronger (>3 moderate, >10 strong,
  >100 decisive).
- `is_de_fdr_0.05`, `is_de_fdr_0.1` — boolean DE calls at those FDR targets.

**Expression context**
- `mean1`, `mean2` — mean expression per group.
- `non_zeros_proportion1/2` — fraction of expressing cells per group.

```python
up = de[de["is_de_fdr_0.05"] & (de["lfc_mean"] > 0)].sort_values("lfc_mean", ascending=False)
big_effect = de[de["is_de_fdr_0.05"] & (de["lfc_mean"].abs() > 1)]   # ~2-fold+
```

## Multimodal DE

```python
# totalVI: RNA vs protein
rna_de  = model.differential_expression(groupby="cell_type", group1="A", group2="B")
prot_de = model.differential_expression(groupby="cell_type", group1="A", group2="B",
                                        protein_expression=True)

# PeakVI: differential accessibility (same output schema/interpretation)
da = peakvi_model.differential_accessibility(groupby="cell_type", group1="A", group2="B")
```

## Special cases

- **Small groups** (rare cell types, ~50 cells): raise `n_samples` (e.g. 10000)
  for stable estimates; prefer `mode="change"`.
- **Imbalanced groups**: `mode="change"` with a `delta` avoids calling tiny
  effects that large-sample power would otherwise surface.
- **Per-batch DE**: pass batch-restricted `idx1`/`idx2` masks and loop over
  batches.
- **Large datasets**: lower `n_samples`, raise `batch_size`, and test one
  contrast at a time, writing each to CSV.

## vs. Wilcoxon (scanpy `rank_genes_groups`)

Use scvi-tools DE for the primary analysis: it corrects batch, models dropout,
and quantifies uncertainty. Fall back to a Wilcoxon test only for a fast
exploratory pass or to reproduce a published Wilcoxon-based result. Note scvi
DE and `rank_genes_groups` answer different statistical questions and will not
match gene-for-gene.

## Best practices

1. Prefer `mode="change"` with a biologically motivated `delta`.
2. Ensure ~>50 cells per group; raise `n_samples` for small groups.
3. Sanity-check known markers before trusting novel hits.
4. Report `mode`, `delta`, `fdr_target`, and `n_samples` used.
5. Follow significant hits with pathway/enrichment analysis and, ideally,
   orthogonal validation.
