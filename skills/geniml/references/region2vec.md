# Region2Vec: Region-Set Embeddings

Unsupervised embeddings of genomic regions and region sets. Regions are mapped to
a vocabulary (the universe), region sets become "sentences," and word2vec-style
training learns a vector per region. Reach for it when you want dimensionality
reduction of BED collections, region-similarity queries, or feature vectors that
feed a downstream supervised model — and you have no metadata labels to exploit
(use `bedspace.md` when you do).

## Workflow

### 1. Prepare data

Gather BED files in one source folder and build (or reuse) a universe file as the
tokenization vocabulary — see `universes.md`.

### 2. Tokenize against the universe

```python
from geniml.tokenization import hard_tokenization

hard_tokenization(
    src_folder="/path/to/raw/bed",     # input BED files
    dst_folder="/path/to/tokens",      # tokenized output
    universe_file="/path/to/universe.bed",
    p_value_threshold=1e-9,            # overlap-significance cutoff
)
```

The p-value threshold controls how strict overlap must be to count as a token
match. Lower is stricter. Validate coverage before training (`utilities.md`).

### 3. Train

```python
from geniml.region2vec import region2vec

region2vec(
    token_folder="/path/to/tokens",
    save_dir="./region2vec_model",
    num_shufflings=1000,   # sentence shuffles — main driver of training signal
    embedding_dim=100,
    context_len=50,
    window_size=5,
    init_lr=0.025,
)
```

## Key parameters

| Parameter        | Meaning                        | Typical range |
|------------------|--------------------------------|---------------|
| `init_lr`        | Initial learning rate          | 0.01 – 0.05   |
| `window_size`    | Context window                 | 3 – 10        |
| `num_shufflings` | Shuffling iterations           | 500 – 2000    |
| `embedding_dim`  | Output embedding dimension     | 50 – 300      |
| `context_len`    | Context length during training | 30 – 100      |

## CLI

```bash
geniml region2vec \
  --token-folder /path/to/tokens \
  --save-dir ./region2vec_model \
  --num-shuffle 1000 \
  --embed-dim 100 \
  --context-len 50 \
  --window-size 5 \
  --init-lr 0.025
```

## Output & downstream use

Training saves region embeddings you can use for similarity search, clustering of
region sets, feature vectors for supervised learning, and 2D/3D visualization via
`umap-learn` or t-SNE. Score embedding quality with the metrics in `utilities.md`.

## Best practices

- Tune `init_lr`, `window_size`, `num_shufflings`, and `embedding_dim` per dataset;
  defaults are a starting point, not an answer.
- Use a universe comprehensive enough to cover the regions you care about — thin
  universes discard signal at tokenization time.
- Validate tokenization coverage before spending compute on training.
- Record parameters and random seeds for reproducibility.
- Large collections are compute- and memory-heavy; monitor usage.
