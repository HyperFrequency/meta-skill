# Concatenating AnnData Objects

`ad.concat` combines objects along observations (stack samples) or variables
(stack modalities). It aligns on the *other* axis's labels according to `join`.

## Axis choice

```python
import anndata as ad
import numpy as np

a = ad.AnnData(np.random.rand(100, 50))
b = ad.AnnData(np.random.rand(150, 50))

# axis=0 (default): stack observations; variables must align
ad.concat([a, b], axis=0).shape          # (250, 50)

# axis=1: stack variables; observations must align
c = ad.AnnData(np.random.rand(100, 30))
d = ad.AnnData(np.random.rand(100, 70))
ad.concat([c, d], axis=1).shape          # (100, 100)
```

`axis` also accepts the strings `"obs"` and `"var"`.

## Join type — alignment on the non-concatenation axis

- `join="inner"` (default): keep only labels present in **all** objects
  (intersection). Most stringent.
- `join="outer"`: keep the **union**; missing entries are filled (0 for sparse,
  `NaN` for dense, or `fill_value`).

```python
import pandas as pd
a = ad.AnnData(np.random.rand(100, 50),
               var=pd.DataFrame(index=[f"g{i}" for i in range(50)]))
b = ad.AnnData(np.random.rand(150, 60),
               var=pd.DataFrame(index=[f"g{i}" for i in range(10, 70)]))

ad.concat([a, b], join="inner").n_vars           # 40 (overlap g10..g49)
ad.concat([a, b], join="outer").n_vars           # 70 (union)
ad.concat([a, b], join="outer", fill_value=0)    # explicit fill
```

## Tracking provenance — `label` + `keys`

```python
combined = ad.concat(
    [a, b], label="batch", keys=["batch1", "batch2"]
)
combined.obs["batch"].value_counts()   # batch1: 100, batch2: 150
```

Omit `keys` to get integer batch ids (0, 1, ...). Use `index_unique` to
disambiguate colliding obs/var names:

```python
combined = ad.concat([a, b], label="batch", keys=["b1", "b2"], index_unique="_")
# obs_names become cell_1_b1, ..., cell_1_b2, ...
```

## Merge strategies — metadata on the non-concatenation axis

Controlled by `merge` (for obs/var) and `uns_merge` (for `uns`). By default the
non-concatenation axis's annotations are dropped unless you opt in.

| Value | Keeps a column/key when... |
|-------|----------------------------|
| `None` (default) | never — drop non-concat-axis annotations |
| `"same"` | its values are identical across all objects |
| `"unique"` | it resolves to exactly one value per label |
| `"first"` | present anywhere — take the first object's value |
| `"only"` | it appears in exactly one object |

```python
a.var["chrom"] = ["chr1"] * 50
b.var["chrom"] = ["chr1"] * 50
ad.concat([a, b], merge="same")     # 'chrom' survives (identical)

ad.concat([a, b], uns_merge="unique")   # merge uns recursively, keep singletons
```

## What travels automatically

- **`layers`**, **`obsm`/`varm`** aligned to the concatenation axis are
  concatenated when present in all objects.
- **`obsp`/`varp`** are dropped unless `pairwise=True`, which builds a
  block-diagonal matrix.

```python
ad.concat([a, b], pairwise=True)   # obsp becomes block-diagonal (250 x 250)
```

## Large-scale concatenation

### Virtual collection — `AnnCollection`
A lightweight view over many objects/files without materializing the union.
Backs `AnnLoader` for PyTorch training.

```python
coll = ad.experimental.AnnCollection([a, b])   # or a list of .h5ad paths
len(coll)                                       # 250
batch = coll[10:20]                             # lazy random-access slice
adata = coll.to_adata()                         # materialize when needed
```

### On-disk concatenation — `concat_on_disk`
Streams inputs and writes the result without loading any file fully.

```python
ad.experimental.concat_on_disk(
    {"p1": "part1.h5ad", "p2": "part2.h5ad"},
    out_file="combined.h5ad",
    join="inner",
    label="batch",
)
result = ad.read_h5ad("combined.h5ad", backed="r")
```

## Patterns

```python
# Combine experimental batches, keep all genes, then correct downstream
adata = ad.concat(batches, label="batch", keys=keys, join="outer")
import scanpy as sc
sc.pp.combat(adata, key="batch")   # concat does NOT correct batch effects

# Combine modalities (RNA + protein) along variables
mm = ad.concat([adata_rna, adata_protein], axis=1)
mm.var["modality"] = ["RNA"] * adata_rna.n_vars + ["protein"] * adata_protein.n_vars
```

## Validate after concatenation

```python
print(combined.shape)
print(combined.obs["batch"].value_counts())   # expected per-source counts
assert combined.obs_names.is_unique            # catch label collisions early
```

Concatenation merges data but never corrects batch effects — apply correction
(`sc.pp.combat`, Harmony, scVI, ...) afterward.
