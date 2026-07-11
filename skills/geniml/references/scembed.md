# scEmbed: Single-Cell ATAC-seq Embeddings

scEmbed applies Region2Vec to single-cell ATAC-seq: each cell's accessible peaks
are treated as a region set, and the model learns a per-cell embedding for
clustering and cell-type annotation. It integrates with scanpy by writing vectors
into `adata.obsm`. Use it for scATAC-seq dimensionality reduction, clustering, and
annotation.

> Function/import names below track geniml's documented modules; confirm exact
> signatures against `https://docs.bedbase.org/geniml/` for your installed version,
> as helper names shift across releases.

## Workflow

### 1. Data preparation

Input is AnnData whose `.var` carries `chr`, `start`, `end` for each peak. Building
it from raw `barcodes.txt` / `peaks.bed` / `matrix.mtx`:

```python
import pandas as pd, scipy.io, anndata

barcodes = pd.read_csv("barcodes.txt", header=None, names=["barcode"])
peaks    = pd.read_csv("peaks.bed", sep="\t", header=None, names=["chr", "start", "end"])
matrix   = scipy.io.mmread("matrix.mtx").tocsr()

adata = anndata.AnnData(X=matrix.T, obs=barcodes, var=peaks)
adata.write("scatac_data.h5ad")
```

Use filtered peak-barcode matrices, not raw counts.

### 2. Pre-tokenize (do this — it is not optional in practice)

```python
from geniml.io import tokenize_cells

tokenize_cells(
    adata="scatac_data.h5ad",
    universe_file="universe.bed",
    output="tokenized_cells.parquet",
)
```

Pre-tokenizing to parquet gives faster training, lower memory, and reusable tokens
across runs. Skipping it is the usual cause of scEmbed OOM.

### 3. Train

```python
from geniml.scembed import ScEmbed
from geniml.region2vec import Region2VecDataset

dataset = Region2VecDataset("tokenized_cells.parquet")

model = ScEmbed(embedding_dim=100, window_size=5, negative_samples=5)
model.train(dataset=dataset, epochs=100, batch_size=256, learning_rate=0.025)
model.save("scembed_model/")
```

### 4. Encode cells

```python
from geniml.scembed import ScEmbed

model = ScEmbed.from_pretrained("scembed_model/")
adata.obsm["scembed_X"] = model.encode(adata)
```

### 5. Cluster & visualize with scanpy

```python
import scanpy as sc

sc.pp.neighbors(adata, use_rep="scembed_X")
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)
sc.pl.umap(adata, color="leiden")
```

## Key parameters

| Parameter          | Meaning                | Typical  |
|--------------------|------------------------|----------|
| `embedding_dim`    | Cell embedding size    | 50 – 200 |
| `window_size`      | Context window         | 3 – 10   |
| `negative_samples` | Negative samples       | 5 – 20   |
| `epochs`           | Training epochs        | 50 – 200 |
| `batch_size`       | Batch size             | 128 – 512 |
| `learning_rate`    | Initial learning rate  | 0.01 – 0.05 |

## Pre-trained models

databio publishes scEmbed models on Hugging Face for common references; load with
`ScEmbed.from_pretrained("databio/<model-id>")` then `encode(adata)`.

## Cell-type annotation

After clustering, transfer labels from a reference by KNN in the embedding space
(`geniml.scembed.annotate_celltypes` — see docs), then validate clusters against
known marker genes. Score predictions with the annotation metrics in
`utilities.md`.

## Best practices

- Filtered matrices, pre-tokenization, and marker-based validation are the three
  things that most affect result quality.
- Scale `embedding_dim` and epochs with dataset size.
- Export trained models to Hugging Face for reproducible sharing.
- The 10x PBMC 10k dataset is a convenient, well-characterized benchmark.
