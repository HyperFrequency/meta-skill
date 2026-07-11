# PyDESeq2: Plots, QC, and Troubleshooting

Visualization recipes, quality diagnostics, and the failure modes you actually
hit. See `workflows.md` for the analysis flow and `api.md` for parameters.

---

## Volcano plot — significance vs effect size

```python
import matplotlib.pyplot as plt
import numpy as np

res = ds.results_df.copy()
res["-log10(padj)"] = -np.log10(res.padj.fillna(1))
sig = res.padj < 0.05

plt.figure(figsize=(10, 6))
plt.scatter(res.loc[~sig, "log2FoldChange"], res.loc[~sig, "-log10(padj)"],
            s=10, alpha=0.3, c="gray", label="Not significant")
plt.scatter(res.loc[sig, "log2FoldChange"], res.loc[sig, "-log10(padj)"],
            s=10, alpha=0.6, c="red", label="padj < 0.05")
plt.axhline(-np.log10(0.05), color="blue", ls="--", alpha=0.5)
plt.axvline(1, color="gray", ls="--", alpha=0.5)
plt.axvline(-1, color="gray", ls="--", alpha=0.5)
plt.xlabel("Log2 Fold Change"); plt.ylabel("-Log10(Adjusted P-value)")
plt.title("Volcano Plot"); plt.legend(); plt.tight_layout()
plt.savefig("volcano_plot.png", dpi=300)
```

Use shrunken LFCs (`ds.lfc_shrink()` first) so the x-axis is not inflated by
noisy low-count genes.

---

## MA plot — fold change vs mean expression

```python
plt.figure(figsize=(10, 6))
plt.scatter(np.log10(res.loc[~sig, "baseMean"] + 1), res.loc[~sig, "log2FoldChange"],
            s=10, alpha=0.3, c="gray")
plt.scatter(np.log10(res.loc[sig, "baseMean"] + 1), res.loc[sig, "log2FoldChange"],
            s=10, alpha=0.6, c="red")
plt.axhline(0, color="blue", ls="--", alpha=0.5)
plt.xlabel("Log10(Base Mean + 1)"); plt.ylabel("Log2 Fold Change")
plt.title("MA Plot"); plt.tight_layout()
plt.savefig("ma_plot.png", dpi=300)
```

---

## Quality diagnostics

```python
# Size factors — should sit near 1 in a balanced library
print(dds.obsm["size_factors"])

# Dispersion distribution
plt.hist(dds.varm["dispersions"], bins=50)
plt.xlabel("Dispersion"); plt.ylabel("Frequency"); plt.show()

# P-value histogram: expect a roughly uniform bulk with a spike near 0.
# A U-shape or right-skew signals model misspecification or hidden batch effects.
plt.hist(ds.results_df.pvalue.dropna(), bins=50)
plt.xlabel("P-value"); plt.ylabel("Frequency"); plt.show()
```

---

## Troubleshooting

### "All genes have zero counts" / empty results

Counts are almost certainly oriented genes × samples. Transpose:

```python
print(counts_df.shape)                 # want (n_samples, n_genes)
if counts_df.shape[1] < counts_df.shape[0]:
    counts_df = counts_df.T             # heuristic: usually more genes than samples
```

### Index / sample-name mismatch

```python
print(counts_df.index.tolist())
print(metadata.index.tolist())
common = counts_df.index.intersection(metadata.index)
counts_df, metadata = counts_df.loc[common], metadata.loc[common]
```

### "Design matrix is not full rank"

A variable is confounded — e.g. every treated sample sits in one batch, so batch
and condition are indistinguishable.

```python
print(pd.crosstab(metadata.condition, metadata.batch))  # look for empty cells
```

Resolve by dropping the confounded variable (`design="~condition"`) or, if you
genuinely want the interaction and the design supports it, modeling it
explicitly (`design="~condition + batch + condition:batch"`). You cannot recover
an effect the experiment did not separate.

### Too many genes filtered out

```python
print(counts_df.sum(axis=0).describe())
# Lower the threshold if the library is shallow
genes_to_keep = counts_df.columns[counts_df.sum(axis=0) >= 5]
```

### No significant genes

Likely biology or power, not a bug. Common causes: small effect sizes, high
biological variability, too few replicates, or uncorrected batch effects.

```python
# Inspect the strongest signals even if none pass FDR
print(ds.results_df.nsmallest(20, "pvalue"))
# Confirm dispersions and size factors look sane (see diagnostics above)
```

If a batch effect is visible in QC, add the batch term to the design and refit.

### Memory errors on large datasets

- Filter genes more aggressively before fitting.
- Reduce `n_cpus` — high parallelism raises peak memory and can, paradoxically,
  be slower here.
- Split genes into chunks, fit separately, and concatenate result tables.

### Non-integer or normalized values rejected

DESeq2 requires raw integer counts. If you have TPM/FPKM/CPM or log-transformed
values, go back to the raw count matrix — there is no valid way to run PyDESeq2
on normalized data.
