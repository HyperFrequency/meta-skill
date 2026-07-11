# PyDESeq2 Workflows

Step-by-step patterns for data loading, single- and multi-factor designs,
export, and best practices. See `api.md` for parameter detail and
`plots-and-troubleshooting.md` for visualization and failure modes.

---

## Full workflow

A standard analysis is two phases: **count modeling** (`dds.deseq2()`) then
**statistical testing** (`ds.summary()`).

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# --- Load (transpose if genes are in rows) ---
counts_df = pd.read_csv("counts.csv", index_col=0).T
metadata  = pd.read_csv("metadata.csv", index_col=0)

# --- Filter ---
genes_to_keep = counts_df.columns[counts_df.sum(axis=0) >= 10]
counts_df = counts_df[genes_to_keep]

samples_to_keep = ~metadata.condition.isna()
counts_df = counts_df.loc[samples_to_keep]
metadata  = metadata.loc[samples_to_keep]

# --- Model ---
dds = DeseqDataSet(counts=counts_df, metadata=metadata,
                   design="~condition", refit_cooks=True)
dds.deseq2()

# --- Test ---
ds = DeseqStats(dds, contrast=["condition", "treated", "control"],
                alpha=0.05, cooks_filter=True, independent_filter=True)
ds.summary()

# --- (Optional) shrink LFCs for plotting/ranking ---
ds.lfc_shrink()

results = ds.results_df
```

---

## Data loading

Count matrices commonly arrive genes × samples and must be transposed to
samples × genes.

```python
# CSV (genes × samples → transpose)
counts_df = pd.read_csv("counts.csv", index_col=0).T
metadata  = pd.read_csv("metadata.csv", index_col=0)

# TSV
counts_df = pd.read_csv("counts.tsv", sep="\t", index_col=0).T

# AnnData
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
counts_df = pd.DataFrame(adata.X, index=adata.obs_names, columns=adata.var_names)
metadata  = adata.obs
```

### Validation before fitting

```python
print(counts_df.shape)   # expect (n_samples, n_genes)
print(metadata.shape)    # expect (n_samples, n_variables)
assert (counts_df >= 0).all().all(), "counts must be non-negative"
assert counts_df.index.equals(metadata.index), "sample indices must align"
```

---

## Filtering

```python
# Drop genes with < 10 total reads (raises power, cuts runtime)
genes_to_keep = counts_df.columns[counts_df.sum(axis=0) >= 10]
counts_df = counts_df[genes_to_keep]

# Drop samples missing the factor of interest
samples_to_keep = ~metadata.condition.isna()
counts_df = counts_df.loc[samples_to_keep]
metadata  = metadata.loc[samples_to_keep]

# Align to common samples if the two frames disagree
common = counts_df.index.intersection(metadata.index)
counts_df, metadata = counts_df.loc[common], metadata.loc[common]
```

---

## Single-factor designs

```python
dds = DeseqDataSet(counts=counts_df, metadata=metadata, design="~condition")
dds.deseq2()

ds = DeseqStats(dds, contrast=["condition", "treated", "control"])
ds.summary()
significant = ds.results_df[ds.results_df.padj < 0.05]
```

**Multiple treatment groups vs one control** — refit-free; reuse the same `dds`
and only rebuild `DeseqStats` per contrast:

```python
all_results = {}
for treatment in ["treated_A", "treated_B", "treated_C"]:
    ds = DeseqStats(dds, contrast=["condition", treatment, "control"])
    ds.summary()
    all_results[treatment] = ds.results_df
    n = (ds.results_df.padj < 0.05).sum()
    print(f"{treatment}: {n} significant genes")
```

---

## Multi-factor designs

**Control for batch** (adjustment variable first, factor of interest last):

```python
dds = DeseqDataSet(counts=counts_df, metadata=metadata,
                   design="~batch + condition")
dds.deseq2()
ds = DeseqStats(dds, contrast=["condition", "treated", "control"])
ds.summary()
```

**Continuous covariate** (must be numeric):

```python
metadata["age"] = pd.to_numeric(metadata["age"])
dds = DeseqDataSet(counts=counts_df, metadata=metadata, design="~age + condition")
dds.deseq2()
```

**Interaction** — does the condition effect differ across groups:

```python
dds = DeseqDataSet(counts=counts_df, metadata=metadata,
                   design="~group + condition + group:condition")
dds.deseq2()
# The interaction contrast targets the group:condition coefficient. Inspect the
# fitted coefficient names on your install before naming it (see api.md).
```

### Design formula rules

- Wilkinson (R-style) notation: `~a + b`, interactions with `:`.
- **Order:** adjustment variables before the variable of interest —
  `~batch + condition`, not `~condition + batch`.
- Every term must be a column in `metadata`.
- Cast discrete factors to `category`; keep continuous covariates numeric:

```python
metadata["condition"] = metadata["condition"].astype("category")
metadata["batch"]     = metadata["batch"].astype("category")
```

---

## Export and reuse

```python
import pickle

ds.results_df.to_csv("deseq2_results.csv")
ds.results_df[ds.results_df.padj < 0.05].to_csv("significant_genes.csv")
ds.results_df.sort_values("padj").to_csv("results_sorted.csv")

# Persist the expensive fit so future contrasts skip deseq2()
with open("dds_result.pkl", "wb") as f:
    pickle.dump(dds.to_picklable_anndata(), f)
```

To save both LFC versions, write the unshrunken table before calling
`lfc_shrink()`, then write the shrunken table after.

---

## Result interpretation

```python
res = ds.results_df

significant = res[res.padj < 0.05]
strong = res[(res.padj < 0.05) & (res.log2FoldChange.abs() > 1)]  # add effect size
up   = significant[significant.log2FoldChange > 0]
down = significant[significant.log2FoldChange < 0]

top_by_padj = res.sort_values("padj").head(20)
```

For effect-size ranking, run `ds.lfc_shrink()` first, then sort on
`log2FoldChange.abs()`.

---

## Best-practice checklist

- Counts are non-negative **integers**, oriented samples × genes.
- Sample IDs align between counts and metadata; missing metadata handled.
- Low-count genes filtered (typically `< 10` total reads).
- Discrete factors are `category`; covariates numeric.
- Design lists adjustment variables before the factor of interest.
- Significance thresholded on `padj`, not raw `pvalue`.
- `lfc_shrink()` used only for plotting/ranking; p-values reported unshrunken.
- Fitted `dds` pickled for reuse across contrasts.
- For large datasets, set `n_cpus`; if memory is tight, filter more aggressively
  or reduce parallelism (see `plots-and-troubleshooting.md`).

---

## Optional standalone driver

The two-object workflow above is short enough to inline in most cases. For
repeated batch runs, wrap it in a small CLI of your own that: loads and validates
inputs, filters, runs `dds.deseq2()`, runs `ds.summary()` for the requested
`[variable, test, reference]` contrast, optionally calls `ds.lfc_shrink()`, and
writes the CSV/pickle outputs above plus volcano/MA plots
(`plots-and-troubleshooting.md`). Keep every guarantee from the checklist —
especially count orientation and `padj`-based significance.
