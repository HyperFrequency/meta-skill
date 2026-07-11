# CELLxGENE Census — Query Patterns, Best Practices & Troubleshooting

Copy-ready patterns organized by query size, plus integration recipes, best
practices, and a failure-mode guide. All examples assume an open Census:

```python
import cellxgene_census
with cellxgene_census.open_soma(census_version="2023-12-15") as census:
    ...  # patterns below run inside this block
```

## 1. Exploratory Queries (metadata only)

Learn what exists and size a request without touching expression matrices.

```python
# Unique cell types in a tissue
obs = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="tissue_general == 'brain' and is_primary_data == True",
    column_names=["cell_type"],
)
print(f"{obs['cell_type'].nunique()} cell types")

# Count cells by condition
obs = cellxgene_census.get_obs(
    census, "homo_sapiens",
    value_filter="disease != 'normal' and is_primary_data == True",
    column_names=["disease", "tissue_general"],
)
print(obs.groupby(["disease", "tissue_general"]).size())

# Browse the dataset catalog
datasets = census["census_info"]["datasets"].read().concat().to_pandas()
covid = datasets[datasets["disease"].str.contains("COVID", na=False)]
```

## 2. Small-to-Medium Queries (AnnData, < ~100k cells)

```python
# Tissue + cell-type slice, trimmed columns
adata = cellxgene_census.get_anndata(
    census=census, organism="Homo sapiens",
    obs_value_filter="cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True",
    obs_column_names=["assay", "disease", "sex", "donor_id"],
)

# Marker-gene panel across cell types
adata = cellxgene_census.get_anndata(
    census=census, organism="Homo sapiens",
    var_value_filter="feature_name in ['CD4', 'CD8A', 'CD19', 'FOXP3']",
    obs_value_filter="cell_type in ['T cell', 'B cell'] and is_primary_data == True",
)

# Multi-tissue in one call
adata = cellxgene_census.get_anndata(
    census=census, organism="Homo sapiens",
    obs_value_filter="tissue_general in ['lung', 'liver', 'kidney'] and is_primary_data == True",
    obs_column_names=["cell_type", "tissue_general", "dataset_id"],
)
```

Query gene / cell metadata separately with `get_var` / `get_obs`:

```python
genes = cellxgene_census.get_var(
    census, "homo_sapiens",
    value_filter="feature_name in ['CD4', 'CD8A']",
    column_names=["feature_id", "feature_name", "feature_length"],
)
```

## 3. Large Queries (out-of-core streaming)

When a slice will not fit in RAM, iterate the X matrix as Arrow tables and never
materialize the whole thing.

```python
import tiledbsoma as soma

query = census["census_data"]["homo_sapiens"].axis_query(
    measurement_name="RNA",
    obs_query=soma.AxisQuery(value_filter="tissue_general == 'brain' and is_primary_data == True"),
    var_query=soma.AxisQuery(value_filter="feature_name in ['FOXP2', 'TBR1', 'SATB2']"),
)

# Each batch is a pyarrow.Table with columns:
#   soma_data  -> expression value
#   soma_dim_0 -> cell (obs) coordinate
#   soma_dim_1 -> gene (var) coordinate
for batch in query.X("raw").tables():
    process(batch)
```

**Incremental mean / variance (Welford's online algorithm)** — numerically stable
across billions of values:

```python
n = 0; mean = 0.0; M2 = 0.0
for batch in query.X("raw").tables():
    for x in batch["soma_data"].to_numpy():
        n += 1
        delta = x - mean
        mean += delta / n
        M2 += delta * (x - mean)
variance = M2 / (n - 1) if n > 1 else 0.0
```

## 4. PyTorch Integration (experimental — version-sensitive)

The streaming dataloader lets you train directly off the Census without loading
the matrix. **The API is experimental and names have moved between releases**
(older `cellxgene_census.experimental.ml` with `ExperimentDataPipe`; newer builds
factor this into the standalone `tiledbsoma_ml` package). Check what your
installed version exposes before copying names verbatim.

```python
# Illustrative — confirm class/function names against your installed version
from cellxgene_census.experimental.ml import experiment_dataloader

dataloader = experiment_dataloader(
    census["census_data"]["homo_sapiens"],
    measurement_name="RNA", X_name="raw",
    obs_value_filter="tissue_general == 'liver' and is_primary_data == True",
    obs_column_names=["cell_type"],
    batch_size=128, shuffle=True,
)
for epoch in range(num_epochs):
    for batch in dataloader:
        X = batch["X"]                       # expression tensor
        labels = batch["obs"]["cell_type"]   # cell-type labels
        # standard forward / backward / step
```

For train/test splitting, build a dataset from an experiment axis query and split
it (again, confirm the exact class name for your version), then wrap each split in
a dataloader. Once tensors are flowing, hand model mechanics to
`pytorch-lightning`.

## 5. Integration Workflows

**scanpy** — the standard continuation after `get_anndata`:

```python
import scanpy as sc
adata = cellxgene_census.get_anndata(
    census=census, organism="Homo sapiens",
    obs_value_filter="cell_type == 'neuron' and is_primary_data == True",
)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pp.pca(adata, n_comps=50)
sc.pp.neighbors(adata)
sc.tl.umap(adata)                            # or hand off to the umap-learn skill
sc.pl.umap(adata, color=["cell_type", "tissue_general", "disease"])
```

**Multi-dataset integration** — pull per dataset, then batch-correct:

```python
adatas = []
for dsid in ["dataset_id_1", "dataset_id_2", "dataset_id_3"]:
    a = cellxgene_census.get_anndata(
        census=census, organism="Homo sapiens",
        obs_value_filter=f"dataset_id == '{dsid}' and is_primary_data == True",
    )
    adatas.append(a)
import scanpy.external as sce
sce.pp.scanorama_integrate(adatas)           # or harmony, bbknn, etc.
```

**Cross-tissue contrast** — one cell type, many tissues:

```python
adata = cellxgene_census.get_anndata(
    census=census, organism="Homo sapiens",
    obs_value_filter="cell_type == 'macrophage' and tissue_general in ['lung', 'liver', 'brain'] and is_primary_data == True",
)
sc.tl.rank_genes_groups(adata, groupby="tissue_general")
```

## Best Practices

1. **Always `is_primary_data == True`** unless intentionally studying duplicates.
2. **Pin `census_version`** for reproducibility; `"stable"` drifts.
3. **Use the context manager** so remote handles close.
4. **Select only needed columns** via `obs_column_names` / `var_column_names` to
   cut transfer.
5. **Check the presence matrix** for gene-specific claims (see census-schema.md).
6. **Prefer `tissue_general`** for broad groupings, `tissue` for fine granularity.
7. **Explore, then query** — inspect metadata counts before pulling expression.
8. **Size before loading** large queries:

   ```python
   n = len(cellxgene_census.get_obs(
       census, "homo_sapiens",
       value_filter="tissue_general == 'brain' and is_primary_data == True",
       column_names=["soma_joinid"]))
   print(f"{n:,} cells")   # if huge, stream out-of-core instead of get_anndata
   ```
9. **Use ontology term IDs** (`cell_type_ontology_term_id == 'CL:...'`) for
   cross-dataset consistency.
10. **Loop conditions** for systematic sweeps (one `get_anndata` per tissue /
    disease), collecting results in a dict.

## Common Pitfalls

- Forgetting `is_primary_data == True` → duplicate cells inflate counts.
- Loading too much at once → size with a metadata query first.
- Skipping the context manager → leaked remote handles.
- Inconsistent versions → non-reproducible results.
- Overly broad first queries → start focused, widen as needed.
- Ignoring presence → treating "gene absent in a dataset" as "gene not expressed".
- Mixing UMI vs read counts without accounting for it in normalization.

## Troubleshooting

**Query returns too many cells** — add filters; use `tissue` instead of
`tissue_general`; restrict to a `dataset_id`; or switch to `axis_query` streaming.

**Memory errors** — tighten `obs_value_filter`, narrow genes with
`var_value_filter`, stream out-of-core, or process in batches.

**Duplicate cells in results** — add `is_primary_data == True`; if intentional,
confirm you meant to span multiple datasets.

**Gene not found** — check spelling (case-sensitive); try `feature_id` (Ensembl)
instead of `feature_name`; consult the presence matrix; the gene may have been
filtered during Census construction.

**Version inconsistencies** — always set `census_version` explicitly, keep it
constant across a study, and read release notes for schema changes.

**PyTorch import / attribute errors** — the experimental ML API moved between
versions (`cellxgene_census.experimental.ml` vs `tiledbsoma_ml`); confirm the
class/function names your installed version actually exports.
