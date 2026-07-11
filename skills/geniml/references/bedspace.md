# BEDspace: Joint Region + Metadata Embeddings

BEDspace trains region sets and their metadata labels into a *single* shared
embedding space using StarSpace. Because regions and labels live in the same space,
you can query across them — find the labels that describe a region set, or the
region sets that match a label. Use it when your BED files carry metadata (cell
type, tissue, condition); if they do not, use Region2Vec (`region2vec.md`).

## Requirement: StarSpace

BEDspace's engine is Facebook Research's StarSpace, an external C++ binary you must
build separately (`https://github.com/facebookresearch/StarSpace`). Pass its path
via `--path-to-starspace` at train time. Missing/misconfigured StarSpace is the
most common BEDspace failure.

## Four-step pipeline

### 1. Preprocess

```bash
geniml bedspace preprocess \
  --input /path/to/regions/ \
  --metadata labels.csv \
  --universe universe.bed \
  --labels "cell_type,tissue" \
  --output preprocessed.txt
```

- `--input`: folder of BED files.
- `--metadata`: CSV with a `file_name` column that **exactly** matches BED
  filenames (no path), plus one column per metadata field.
- `--universe`: tokenization reference (`universes.md`).
- `--labels`: comma-separated metadata columns to embed.

Preprocessing adds `__label__` prefixes to metadata and converts regions into
StarSpace input format.

### 2. Train

```bash
geniml bedspace train \
  --path-to-starspace /path/to/starspace \
  --input preprocessed.txt \
  --output model/ \
  --dim 100 \
  --epochs 50 \
  --lr 0.05
```

| Flag       | Meaning             | Typical |
|------------|---------------------|---------|
| `--dim`    | Embedding dimension | 50 – 200 |
| `--epochs` | Training epochs     | 20 – 100 |
| `--lr`     | Learning rate       | 0.01 – 0.1 |

### 3. Distances

```bash
geniml bedspace distances \
  --input model/ \
  --metadata labels.csv \
  --universe universe.bed \
  --output distances.pkl
```

Builds the distance matrix that search reads. Use the **same** universe as in
preprocessing.

### 4. Search

Three query modes:

```bash
# region -> label: which labels characterize these regions?
geniml bedspace search -t r2l -d distances.pkl -q query_regions.bed -n 10

# label -> region: which region sets match this label?
geniml bedspace search -t l2r -d distances.pkl -q "T_cell" -n 10

# region -> region: which region sets are most similar?
geniml bedspace search -t r2r -d distances.pkl -q query_regions.bed -n 10
```

`-n` sets the number of results.

## Python API

```python
from geniml.bedspace import BEDSpaceModel

model = BEDSpaceModel.load("model/")
results = model.search(query="T_cell", search_type="l2r", top_k=10)
```

## Interpreting results

- **r2l** — labels that best describe your query regions.
- **l2r** — region sets matching your metadata criterion.
- **r2r** — region sets with similar genomic content.

## Best practices

- Keep the `file_name` column an exact match to BED filenames.
- Choose metadata columns that capture the biological variation you care about.
- Use one consistent universe across preprocess, distances, and downstream steps.
- Preprocess and inspect output before committing to a long training run.
