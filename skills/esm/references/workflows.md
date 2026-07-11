# ESM Workflows

End-to-end recipes that compose the primitives in `esm3-generation.md` and
`esmc-embeddings.md`. Adapt lengths, temperatures, and validation to your target;
treat every generated sequence as a hypothesis to be experimentally validated.

## 1. De novo design with chain-of-thought

Design a protein of a target length toward a function, then fold-and-refine it.

```python
from esm.models.esm3 import ESM3
from esm.sdk.api import ESMProtein, GenerationConfig, FunctionAnnotation

model = ESM3.from_pretrained("esm3_sm_open_v1").to("cuda")
length = 238

# 1. Seed with a function annotation over a fully-masked sequence.
protein = ESMProtein(
    sequence="_" * length,
    function_annotations=[FunctionAnnotation(label="green_fluorescent_protein", start=65, end=75)],
)

# 2. Generate sequence, then structure.
protein = model.generate(protein, GenerationConfig(track="sequence",  num_steps=length // 3, temperature=0.7))
protein = model.generate(protein, GenerationConfig(track="structure", num_steps=length // 2))

# 3. Re-mask a fraction of positions and refine at lower temperature.
residues = list(protein.sequence)
for i in range(length):
    if i % 3 == 0 and not (65 <= i <= 75):   # keep the functional region fixed
        residues[i] = "_"
protein.sequence = "".join(residues)
protein = model.generate(protein, GenerationConfig(track="sequence", num_steps=50, temperature=0.5))

# 4. Fold the refined design and save.
protein = model.generate(protein, GenerationConfig(track="structure", num_steps=30))
protein.to_pdb("design.pdb")
```

## 2. Variant library + embedding triage

Generate variants, embed them with ESM C, cluster, and pick diverse
representatives — a design-of-experiments pass before wet-lab screening.

```python
import numpy as np
from sklearn.cluster import KMeans
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig

# Generate variants by masking random positions of a parent (see esm3-generation.md).
variants = [...]  # list of generated sequences

# Embed with ESM C.
embedder = ESMC.from_pretrained("esmc_300m").to("cuda")

def embed(seq):
    out = embedder.logits(embedder.encode(ESMProtein(sequence=seq)),
                          LogitsConfig(sequence=True, return_embeddings=True))
    return out.embeddings[:, 1:-1, :].mean(dim=1).cpu().detach().numpy().flatten()

matrix = np.vstack([embed(s) for s in variants])

# Cluster and take the medoid of each cluster as a representative.
labels = KMeans(n_clusters=5, random_state=42).fit_predict(matrix)
representatives = []
for c in range(5):
    idx = np.where(labels == c)[0]
    centroid = matrix[idx].mean(axis=0)
    representatives.append(variants[idx[np.argmin(np.linalg.norm(matrix[idx] - centroid, axis=1))]])
```

Report Hamming distance from the parent per variant to quantify mutational load,
and use `umap-learn` to visualize the cluster structure.

## 3. Structure-based sequence optimization

Given a backbone, generate many candidate sequences (inverse folding), keep the
ones that re-fold to a compatible structure, and rank by simple biophysical
proxies.

```python
target = ESMProtein.from_pdb("target.pdb")
candidates = []
for _ in range(20):
    design = ESMProtein(coordinates=target.coordinates, secondary_structure=target.secondary_structure)
    designed = model.generate(design, GenerationConfig(track="sequence", num_steps=len(target.sequence), temperature=0.7))
    candidates.append(designed.sequence)

# Filter: keep designs that yield a structure when re-folded.
kept = []
for seq in candidates:
    refold = model.generate(ESMProtein(sequence=seq), GenerationConfig(track="structure", num_steps=len(seq) // 2))
    if refold.coordinates is not None:
        kept.append(seq)
```

Rank `kept` with cheap sequence proxies (hydrophobic fraction, net charge,
aromatic content) or, better, a learned stability predictor built on ESM C
embeddings. For rigorous fold agreement, compute backbone RMSD/TM-score against
the target with a proper structural-alignment tool — the presence of coordinates
alone is only a smoke test.

## 4. Function prediction, two ways

- **Generative** — run ESM3 on the `function` track at low temperature (~0.3)
  and read `protein.function_annotations`. Good for exploratory annotation with
  no training data.
- **Embedding + classifier** — embed with ESM C and train a supervised model on
  labeled examples (see `esmc-embeddings.md`). More reliable when you have a
  labeled set and a fixed label space.

Use both and treat agreement as a confidence signal.

## 5. Corpus embedding and clustering

Embed a sequence corpus with ESM C, reduce with PCA then UMAP/t-SNE for
visualization, and cluster with DBSCAN/HDBSCAN. This is the standard exploratory
map of a protein family or a screening library. Delegate the reduction and
clustering to `umap-learn` and `scikit-learn`; ESM C only supplies the vectors.

## Scaling notes

- Move generation and embedding of large corpora to Forge (`forge.md`) with
  bounded concurrency and checkpointing.
- On local GPUs, free memory between batches with `torch.cuda.empty_cache()` and
  `gc.collect()`, and cache embeddings so re-analysis is free.
