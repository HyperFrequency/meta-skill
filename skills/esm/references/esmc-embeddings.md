# ESM C Embeddings Reference

ESM C (Cambrian) is a family of encoder protein language models optimized for
representation learning. Use it to turn a sequence into per-residue or pooled
embedding vectors for similarity, clustering, classification, and as frozen
features for downstream models. It is positioned as a faster, higher-quality
successor to ESM-2 with a compatible mental model.

## Models

Local `from_pretrained` names use underscores; the 6B variant is served through
Forge. The `hidden` dimension is the embedding width — read it at runtime from
the tensor shape rather than hard-coding.

| Model | Params | Layers | hidden (approx) | Access |
|-------|--------|--------|-----------------|--------|
| `esmc_300m` | 300M | 30 | 960 | Open weights |
| `esmc_600m` | 600M | 36 | 1152 | Open weights |
| `esmc-6b` (Forge) | 6B | 80 | 2560 | Forge only |

Pick by budget: `esmc_300m` for high-throughput/real-time, `esmc_600m` for a
quality/speed balance, `esmc-6b` when downstream accuracy is critical.

## Correct embedding API

The current EvolutionaryScale SDK exposes embeddings through `logits(...)` with a
`LogitsConfig`, **not** through a bare `forward()` call. Request embeddings
explicitly with `return_embeddings=True`.

```python
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig

client = ESMC.from_pretrained("esmc_300m").to("cuda")

protein = ESMProtein(sequence="MPRTKEINDAGLIVHSPQWFYK")
protein_tensor = client.encode(protein)                 # tokenize -> tensor

out = client.logits(
    protein_tensor,
    LogitsConfig(sequence=True, return_embeddings=True),
)

out.embeddings        # shape (1, L+2, hidden) — includes BOS/EOS tokens
out.logits            # per-track logits (per-position sequence predictions)
```

**Gotcha — special tokens.** The tokenizer adds start/end tokens, so
`out.embeddings` has length `L + 2` for a length-`L` sequence. Strip the first
and last positions before per-residue analysis, and exclude them when pooling.

## Pooling to a fixed-size vector

Most downstream uses want one vector per protein. Mean-pool over the residue
positions (dropping the special tokens):

```python
def embed(client, sequence):
    tensor = client.encode(ESMProtein(sequence=sequence))
    out = client.logits(tensor, LogitsConfig(sequence=True, return_embeddings=True))
    residues = out.embeddings[:, 1:-1, :]          # drop BOS/EOS
    return residues.mean(dim=1)                     # (1, hidden)
```

## Downstream uses

### Similarity

```python
import torch.nn.functional as F

a, b = embed(client, seq_a), embed(client, seq_b)
similarity = F.cosine_similarity(a, b).item()
```

Normalize (cosine) rather than using raw Euclidean distance when comparing
sequences of different lengths.

### Classification / regression (frozen features)

```python
import numpy as np
from sklearn.linear_model import LogisticRegression

def embed_matrix(client, sequences):
    return np.vstack([embed(client, s).cpu().detach().numpy() for s in sequences])

X = embed_matrix(client, train_sequences)
clf = LogisticRegression(max_iter=1000).fit(X, train_labels)
```

For a neural downstream head, run ESM C under `torch.no_grad()` / `client.eval()`
and backprop only through your head:

```python
client.eval()
with torch.no_grad():
    features = embed(client, sequence)   # frozen ESM C features
prediction = head(features)              # your trainable module
```

### Clustering

```python
from sklearn.cluster import KMeans
labels = KMeans(n_clusters=5, random_state=42).fit_predict(embed_matrix(client, sequences))
```

Pair with `umap-learn` for 2D visualization of the embedding space, and
`scikit-learn` (DBSCAN/HDBSCAN) for density-based clustering.

### Nearest-neighbor search

Precompute an embedding matrix for the database once, then score a query with
cosine similarity and take the top-k. For large corpora, store vectors in a
proper ANN index instead of a dense scan.

## Performance

- **Half precision** — `.half()` roughly halves memory; wrap calls in
  `torch.autocast("cuda")` for mixed precision.
- **Batching** — sort sequences by length and group similar lengths to minimize
  padding waste; process in fixed-size batches and call
  `torch.cuda.empty_cache()` periodically on long runs.
- **Cache embeddings** — key a persistent cache on a hash of the sequence
  string; embeddings are deterministic for a fixed model, so recomputation is
  pure waste across repeated analyses.

## Relationship to ESM-2

ESM C is intended as a drop-in upgrade path from ESM-2 (`fair-esm`) with faster
inference and improved representations. The APIs differ: ESM-2 uses
`esm.pretrained.esm2_*` + an alphabet/batch-converter, whereas ESM C uses the
`ESMProtein` + `encode` + `logits(LogitsConfig(...))` flow above. Migrate the
call sites; the downstream pooling/similarity/classification logic is unchanged.

## Citation

ESM Cambrian (ESM C), EvolutionaryScale (2024).
Blog: https://www.evolutionaryscale.ai/blog/esm-cambrian
