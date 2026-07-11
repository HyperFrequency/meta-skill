# Tokenization & Utilities

Supporting tools the geniml pipeline depends on. Tokenization is a required
preprocessing step for every embedding method; the rest are optional helpers.

> Function/import names track geniml's documented modules; confirm exact
> signatures against `https://docs.bedbase.org/geniml/` for your installed version.

## Tokenization

Converts genomic regions into discrete tokens against a universe so word2vec-style
training can run. Required for Region2Vec and scEmbed.

### Hard tokenization (strict overlap)

```python
from geniml.tokenization import hard_tokenization

hard_tokenization(
    src_folder="bed_files/", dst_folder="tokenized/",
    universe_file="universe.bed", p_value_threshold=1e-9,
)
```

`p_value_threshold` sets overlap significance — lower is stricter (`1e-9` strict,
`1e-6` permissive).

### Soft tokenization (partial matches)

```python
from geniml.tokenization import soft_tokenization

soft_tokenization(
    src_folder="bed_files/", dst_folder="tokenized/",
    universe_file="universe.bed", overlap_threshold=0.5,
)
```

`overlap_threshold` is the minimum overlap fraction (0–1).

### Coverage check (run before training)

```python
from geniml.tokenization import check_coverage

coverage = check_coverage(bed_file="peaks.bed", universe_file="universe.bed",
                          threshold=1e-9)
print(f"{coverage:.1%}")   # aim for >80%
```

Low coverage means the universe is incomplete or the assembly mismatches — fix that
before spending compute on training.

## BBClient — remote BED caching

Caches BED files from remote sources (BEDbase) for fast repeated access.

```python
from geniml.bbclient import BBClient

client = BBClient(cache_folder="~/.bedcache")
bed = client.load_bed(bed_id="GSM123456")
regions = client.get_regions("GSM123456")
```

Also usable from R via `reticulate` (`import("geniml.bbclient")`). Point the cache
at a directory with enough storage and keep it consistent across analyses.

## BEDshift — null-model randomization

Randomizes BED files while preserving chosen genomic context, for null
distributions and significance testing.

```python
from geniml.bedshift import bedshift

bedshift(input_bed="peaks.bed", genome="hg38",
         preserve_chrom=True, n_iterations=100)
```

Strategies (pick the one matching your null hypothesis):

- `preserve_chrom=True` — keep regions on the same chromosomes.
- `preserve_distance=True` — keep inter-region distances.
- `preserve_size=True` — keep region lengths.

CLI:

```bash
geniml bedshift --input peaks.bed --genome hg38 \
  --preserve-chrom --iterations 100 --output randomized.bed
```

Generate many iterations for robust statistics and record the parameters.

## Evaluation — embedding & clustering quality

```python
from geniml.evaluation import evaluate_embeddings

m = evaluate_embeddings(
    embeddings_file="region2vec_model/embeddings.npy",
    labels_file="metadata.csv",
    metrics=["silhouette", "davies_bouldin", "calinski_harabasz"],
)
```

- **Silhouette** (−1…1, higher better): cohesion vs separation.
- **Davies-Bouldin** (≥0, lower better): average inter-cluster similarity.
- **Calinski-Harabasz** (higher better): between/within dispersion ratio.

Cell-type annotation scoring:

```python
from geniml.evaluation import evaluate_annotation

r = evaluate_annotation(predicted=adata.obs["predicted_celltype"],
                        true=adata.obs["true_celltype"],
                        metrics=["accuracy", "f1", "confusion_matrix"])
```

Use multiple complementary metrics, compare against a baseline, report on held-out
data, and visualize embeddings (`umap-learn`) alongside the numbers.

## Text2BedNN — neural search backend

Builds a search index over trained embeddings for natural-language or metadata
queries against genomic regions.

```python
from geniml.search import build_search_index, SearchBackend

build_search_index(embeddings_file="bedspace_model/embeddings.npy",
                   metadata_file="metadata.csv", output_dir="search_backend/")

backend = SearchBackend.load("search_backend/")
backend.query(text="T cell regulatory regions", top_k=10)
backend.query(metadata={"cell_type": "T_cell", "tissue": "blood"}, top_k=10)
```

Train the underlying embeddings (BEDspace/Region2Vec) with rich metadata for
better search relevance.

## I/O and model helpers

```python
from geniml.io import read_bed, write_bed, load_universe
from geniml.models import save_model, load_model
```

## End-to-end pattern

```python
# 1. universe -> 2. tokenize -> 3. embed -> 4. evaluate
build_universe(coverage_folder="coverage/", method="cc", cutoff=5,
               output_file="universe.bed")
hard_tokenization("beds/", "tokens/", "universe.bed", p_value_threshold=1e-9)
region2vec(token_folder="tokens/", save_dir="model/", num_shufflings=1000)
evaluate_embeddings(embeddings_file="model/embeddings.npy", labels_file="metadata.csv")
```
