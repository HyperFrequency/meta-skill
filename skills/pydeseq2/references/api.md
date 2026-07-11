# PyDESeq2 API Reference

Reference for the two core classes plus supporting utilities. PyDESeq2 targets
DESeq2 v1.34.0 default behavior; expect small numerical differences from R
DESeq2. The `design=` formula parameter shown here is the Wilkinson-formula API
used by recent PyDESeq2 releases — confirm your installed version if you see a
legacy `design_factors=` signature instead.

---

## `DeseqDataSet` — count modeling

`from pydeseq2.dds import DeseqDataSet`

Handles everything from normalization through log2 fold-change fitting. Subclasses
`AnnData`, so results are stored on standard AnnData slots.

### Initialization parameters

| Parameter | Type | Notes |
| --- | --- | --- |
| `counts` | DataFrame | Shape (samples × genes), non-negative **integer** read counts |
| `metadata` | DataFrame | Shape (samples × variables); index must match `counts` |
| `design` | str | Wilkinson formula, e.g. `"~condition"`, `"~batch + condition"`, `"~group + condition + group:condition"` |
| `refit_cooks` | bool | Refit after removing Cook's-distance outliers (default `True`) |
| `n_cpus` | int | CPUs for parallel fitting (optional) |
| `quiet` | bool | Suppress progress output (default `False`) |

### `deseq2()`

Runs the full modeling pipeline in place (returns `None`):

1. Compute size factors (median-of-ratios normalization)
2. Fit gene-wise dispersions (per-gene MLE)
3. Fit the dispersion trend curve (mean–dispersion relationship)
4. Compute dispersion priors
5. Fit MAP (maximum a posteriori) dispersions — shrinkage toward the trend
6. Fit log2 fold changes (negative-binomial GLM)
7. Compute Cook's distances for outlier detection
8. If `refit_cooks=True`, refit affected genes with outliers removed

### `to_picklable_anndata()`

Returns a plain `AnnData` snapshot safe to `pickle` (strips unpicklable
inference objects). Use to persist an expensive fit:

```python
import pickle
with open("dds_result.pkl", "wb") as f:
    pickle.dump(dds.to_picklable_anndata(), f)
```

### Stored attributes (populated after `deseq2()`)

- `dds.obsm["size_factors"]` — per-sample normalization factors (each ~1 in a
  balanced library).
- `dds.varm["dispersions"]` — final (MAP) per-gene dispersion estimates.
- `dds.varm["LFC"]` — fitted GLM coefficients (log2 scale) per gene.
- `dds.layers` — matrices: raw `"counts"`, `"normed_counts"`, plus intermediate
  fitting layers.
- `dds.uns` — global parameters (trend-curve coefficients, prior variances, run
  settings).

Exact layer/key names can vary across PyDESeq2 versions; inspect
`dds.layers.keys()`, `dds.varm.keys()`, and `dds.uns.keys()` on your install
rather than hard-coding.

---

## `DeseqStats` — statistical testing

`from pydeseq2.ds import DeseqStats`

Runs Wald tests and computes adjusted p-values from a fitted `DeseqDataSet`.

### Initialization parameters

| Parameter | Type | Notes |
| --- | --- | --- |
| `dds` | DeseqDataSet | Must have had `deseq2()` run |
| `contrast` | list \| None | `[variable, test_level, reference_level]`; `None` uses the last design coefficient |
| `alpha` | float | Significance level for independent filtering / adjusted p-values (default `0.05`) |
| `cooks_filter` | bool | Set outlier-gene p-values to `NaN` via Cook's distance (default `True`) |
| `independent_filter` | bool | Independent filtering to boost power on low-count genes (default `True`) |
| `n_cpus` | int | CPUs for parallel testing (optional) |
| `quiet` | bool | Suppress progress output (default `False`) |

### `summary()`

Runs the test pipeline and stores the result table on `ds.results_df` (returns
`None`):

1. Wald tests for the contrast coefficient
2. Optional Cook's-distance outlier filtering
3. Optional independent filtering of low-power genes
4. Benjamini–Hochberg FDR correction → `padj`

### `results_df` columns

| Column | Meaning |
| --- | --- |
| `baseMean` | Mean normalized count across samples |
| `log2FoldChange` | Log2 fold change (test vs reference) |
| `lfcSE` | Standard error of the LFC |
| `stat` | Wald statistic |
| `pvalue` | Raw p-value |
| `padj` | BH-adjusted p-value (FDR) |

`padj = NaN` marks genes removed by Cook's or independent filtering.

### `lfc_shrink(coeff=None)`

Applies **apeGLM** shrinkage to the log2 fold changes to stabilize noisy
estimates (low counts / high dispersion), improving visualization and
effect-size ranking. Updates `results_df` in place.

- `coeff`: coefficient name to shrink; if `None`, uses the contrast's
  coefficient.
- **P-values and `padj` are unchanged** — shrinkage touches only
  `log2FoldChange`. Report unshrunken p-values; use shrunken LFCs for plots and
  ranking.

### Contrast notes

- **Two-level factor:** `["condition", "treated", "control"]` → LFC of treated
  relative to control.
- **`None`:** tests the last coefficient of the design formula.
- **Interaction / multi-level terms:** the contrast targets the corresponding
  design coefficient. Coefficient naming depends on your PyDESeq2 version and the
  factor encoding — inspect `dds.varm["LFC"].columns` (or the equivalent
  coefficient list on your install) to find the exact name before constructing
  the contrast. Do not assume a name.

---

## Utilities and inference

### `pydeseq2.utils.load_example_data(modality="single-factor")`

Loads a synthetic demo dataset for testing/tutorials. `modality` is
`"single-factor"` or `"multi-factor"`. Returns `(counts_df, metadata_df)`.

### `pydeseq2.preprocessing`

Helpers for count preparation (gene filtering by minimum counts, normalization
utilities). In practice most filtering is done directly with pandas (see
`workflows.md`).

### Inference backend

- `pydeseq2.inference.Inference` — abstract interface for the numerical routines
  (GLM fitting, dispersion estimation, trend fitting, testing).
- `pydeseq2.inference.DefaultInference` — the default scipy/sklearn/numpy
  implementation used automatically. Pass a custom `inference=` object to
  `DeseqDataSet` only if you need an alternative backend.

---

## Data structure requirements

**Count matrix:** DataFrame, shape (samples × genes), non-negative integers,
unique gene column names, index = sample IDs matching the metadata index.

**Metadata:** DataFrame, shape (samples × variables), index = sample IDs.
Discrete design factors are best cast to `category`; continuous covariates must
be numeric. Handle missing values before fitting.

Sample order and identity must align between the two frames. Count files
frequently arrive genes × samples and must be transposed (`.T`).
