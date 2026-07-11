# Workflows, tuning, and troubleshooting

End-to-end pipeline, hyperparameters, GPU usage, batch-integration strategies,
reference mapping, deployment, and failure modes. Pairs with `scanpy` for
QC/clustering/plotting around the model.

## End-to-end scVI pipeline

```python
import scvi, scanpy as sc, numpy as np

# 1. Load + QC (scanpy)
adata = sc.read_h5ad("data.h5ad")
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs.pct_counts_mt < 20].copy()

# 2. Snapshot RAW counts BEFORE any normalization
adata.layers["counts"] = adata.X.copy()

# 3. HVG on counts (seurat_v3 expects raw counts)
sc.pp.highly_variable_genes(adata, n_top_genes=4000, flavor="seurat_v3",
                            layer="counts", batch_key="batch", subset=True)

# 4. Register data + covariates
scvi.model.SCVI.setup_anndata(
    adata, layer="counts", batch_key="batch",
    categorical_covariate_keys=["donor"],
    continuous_covariate_keys=["pct_counts_mt"])

# 5. Build + train
model = scvi.model.SCVI(adata, n_latent=30, n_layers=2, gene_likelihood="nb")
model.train(max_epochs=400, early_stopping=True, check_val_every_n_epoch=5)

# 6. Extract
adata.obsm["X_scVI"] = model.get_latent_representation()
adata.layers["scvi_normalized"] = model.get_normalized_expression(library_size=1e4)

# 7. Downstream (scanpy)
sc.pp.neighbors(adata, use_rep="X_scVI")
sc.tl.umap(adata); sc.tl.leiden(adata, resolution=0.8)

# 8. Persist
model.save("scvi_model", overwrite=True)
adata.write("analyzed.h5ad")
```

**Verify training** by plotting `model.history["elbo_train"]` and
`model.history["elbo_validation"]`; a still-falling validation curve means
undertrained. **Verify integration** by coloring the UMAP by `batch` — batches
should mix within cell types.

## Hyperparameters

**Architecture** — `n_latent` (10-50; larger for heterogeneous data),
`n_layers` (1-3), `n_hidden` (64-256). **Training** — `max_epochs` (200-500 with
early stopping), `batch_size` (128 default), `lr` (0.001 default).
**Likelihood** — `gene_likelihood` (`"nb"` or `"zinb"`), `dispersion`
(`"gene"` vs `"gene-batch"`). Start from defaults; tune only if integration or
DE underperforms.

Sweep with Optuna (or the `dspy`/`optuna` tooling) by maximizing validation
ELBO:

```python
import optuna
def objective(trial):
    m = scvi.model.SCVI(adata,
        n_latent=trial.suggest_int("n_latent", 10, 50),
        n_layers=trial.suggest_int("n_layers", 1, 3),
        n_hidden=trial.suggest_categorical("n_hidden", [64, 128, 256]))
    m.train(max_epochs=200, early_stopping=True)
    return m.history["elbo_validation"].values[-1][0]
study = optuna.create_study(direction="minimize")   # ELBO loss: lower is better
study.optimize(objective, n_trials=20)
```
(scvi-tools also ships `scvi.autotune` for Ray-Tune-based search.)

## GPU

```python
model.train(accelerator="gpu", devices=1)   # or accelerator="auto"
model.train(batch_size=64)                   # shrink if OOM
model.train(precision="16-mixed")            # mixed precision saves memory
```
Use GPU for datasets over ~10k cells. Check `torch.cuda.is_available()`.

## Batch integration strategies

```python
# Single batch key
scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch")

# Multiple technical covariates
scvi.model.SCVI.setup_anndata(
    adata, layer="counts", batch_key="sequencing_batch",
    categorical_covariate_keys=["donor", "tissue"],
    continuous_covariate_keys=["pct_counts_mt"])

# Hierarchical batches: compose a key
adata.obs["batch_h"] = adata.obs["study"].astype(str) + "_" + adata.obs["sample"].astype(str)
```
If integration is weak, try `encode_covariates=True`,
`deeply_inject_covariates=True`, or more `n_latent`.

## Reference mapping (scArches)

```python
# Reference
scvi.model.SCVI.setup_anndata(ref_adata, layer="counts", batch_key="batch")
ref = scvi.model.SCVI(ref_adata); ref.train(); ref.save("ref_model")

# Query — align schema, then architectural surgery
scvi.model.SCVI.prepare_query_anndata(query_adata, "ref_model")
q = scvi.model.SCVI.load_query_data(query_adata, "ref_model")
q.train(max_epochs=200, plan_kwargs={"weight_decay": 0.0})
query_latent = q.get_latent_representation()

# Transfer labels via KNN on the reference latent (or use scANVI.predict())
from sklearn.neighbors import KNeighborsClassifier
knn = KNeighborsClassifier(15).fit(ref.get_latent_representation(), ref_adata.obs["cell_type"])
query_adata.obs["predicted"] = knn.predict(query_latent)
```

## Deployment: model minification

Drop stored counts and keep only latent posterior parameters for fast inference
on a shipped model.

```python
model.minify_adata()
model.save("minified_model", overwrite=True)
```

## Large / out-of-core data

```python
adata = sc.read_h5ad("huge.h5ad", backed="r")   # backed mode
scvi.model.SCVI.setup_anndata(adata, layer="counts")
model = scvi.model.SCVI(adata); model.train()
```
For very large tables, wrangle `.obs` with `polars` and out-of-core arrays with
`dask`.

## Troubleshooting

**NaN loss** — almost always non-raw input. Assert `adata.layers["counts"].min() >= 0`
and no NaNs; lower `lr` (e.g. 1e-4); try `gene_likelihood="nb"`.

**Poor batch correction** — set `encode_covariates=True`, raise `n_latent`,
register the missing covariate, or compose a hierarchical batch key.

**ELBO not decreasing** — raise `lr` slightly, increase `n_hidden`/`n_layers`,
train longer, confirm HVGs were selected sensibly.

**Out of memory** — smaller `batch_size`, `precision="16-mixed"`, smaller
`n_latent`/`n_hidden`, or backed AnnData.

**Non-reproducible results** — set `scvi.settings.seed = 0` before building the
model.

## Best-practice checklist

1. Raw counts only; snapshot to a `counts` layer before normalizing.
2. Select HVGs with `flavor="seurat_v3"` on the counts layer.
3. Register every known technical covariate in `setup_anndata`.
4. Use early stopping with a validation split; inspect the ELBO history.
5. Save the trained model; re-run `setup_anndata` before reloading.
6. GPU for >10k cells.
7. Visually confirm integration (UMAP by batch) before trusting downstream DE.
8. Set a seed for reproducibility.
