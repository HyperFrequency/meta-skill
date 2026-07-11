# Model Catalog and Selection

All representation and embedding architectures in `torchdrug.models`, grouped by
what they consume. Class names below are the `models.*` entry points; confirm exact
constructor arguments against the installed version, since older releases differ.

Common GNN parameters (shared by most graph models): `input_dim` (node feature
dim), `hidden_dims` (list of layer widths), `edge_input_dim` (optional edge feature
dim), `batch_norm`, `activation`, `dropout`, `readout` (`"sum"` / `"mean"` /
`"max"` graph pooling).

## Graph neural networks (molecules and general graphs)

### `models.GCN` — Graph Convolutional Network
Normalized-adjacency spatial convolution (Kipf & Welling, 2017). Simple, fast, a
solid baseline for homophilic graphs. Good first thing to try.

### `models.GAT` — Graph Attention Network
Learns per-neighbor attention weights with multi-head attention (Veličković et
al., 2018). Extra params: `num_head`, `negative_slope`, `concat`. Use when neighbor
importance varies or you want some interpretability.

### `models.GIN` — Graph Isomorphism Network
Theoretically the most expressive message-passing GNN (Xu et al., 2019); injective
aggregation distinguishes structures GCN cannot. **The default strong choice for
molecular property prediction.** Extra params: `eps` (learnable or fixed), and it
readily consumes `edge_input_dim`.

### `models.RGCN` — Relational GCN
Relation-specific weight matrices for multi-relational graphs (Schlichtkrull et
al., 2018). Params: `num_relation`, `num_bases` (basis decomposition to cut
parameters). Essential for knowledge graphs and reaction graphs with typed bonds.

### `models.MPNN` — Message Passing Neural Network
General framework (Gilmer et al., 2017) with edge-conditioned messages, GRU node
updates, and a Set2Set readout. Params include `num_layer`, `num_mlp_layer`. Strong
for quantum chemistry where edge/bond information matters.

### `models.SchNet` — continuous-filter 3D convolution
Operates on 3D atomic coordinates with RBF-expanded distances; rotation/translation
invariant (Schütt et al., 2017). Params: `num_gaussian` (RBF basis count),
`cutoff` (interaction radius). Best for QM9-style quantum properties, molecular
dynamics, and structure-based binding.

### `models.ChebNet` — Chebyshev spectral CNN
Spectral convolution via Chebyshev polynomial approximation (Defferrard et al.,
2016); param `num_cheb` sets the polynomial order. Captures more global structure.

### `models.NeuralFingerprint` — differentiable ECFP
Learns a differentiable circular fingerprint (Duvenaud et al., 2015), an
interpretable alternative to hand-crafted ECFP. Good for small-data QSAR and
similarity.

## Protein models

### `models.GearNet` — Geometry-Aware Relational Graph Network
Structure encoder using multiple edge types (sequential, radius, KNN) and geometric
edge features; strong on structure-based protein tasks (Zhang et al., 2023). Params:
`input_dim`, `hidden_dims`, `num_relation`, `edge_input_dim`. Pair with
`MultiviewContrast` pretraining. Use when you have 3D structures.

### `models.ESM` — Evolutionary Scale Modeling
Pretrained transformer over ~250M sequences (Rives et al., 2021). Variants: ESM-1b
(650M), ESM-2 (8M–15B). Load a pretrained checkpoint and fine-tune with a small
learning rate. **Best default when you only have sequence.**

### `models.ProteinBERT`, `models.ProteinLSTM`, `models.ProteinCNN`, `models.ProteinResNet`
Lighter sequence encoders: BERT-style masked LM; bidirectional LSTM (fast baseline);
1D CNN / ResNet for local motif detection. Use when ESM is too heavy or you want a
quick sequence baseline.

## Knowledge-graph embedding models

Score a `(head, relation, tail)` triple; used with `tasks.KnowledgeGraphCompletion`.
Params: `num_entity`, `num_relation`, `embedding_dim` (typically 200–2000).

- **`models.TransE`** — translational, `h + r ≈ t`. Simple, memory efficient, best
  on 1-to-1 relations; struggles with N-to-N.
- **`models.RotatE`** — relations as rotations in complex space; models symmetry,
  antisymmetry, inversion, and composition. State-of-the-art on many benchmarks;
  `embedding_dim` must be even.
- **`models.DistMult`** — bilinear, symmetric only. Fast; cannot model
  antisymmetric relations.
- **`models.ComplEx`** — complex-valued embeddings handling asymmetric + symmetric
  relations. A good general default, cheaper than RotatE.
- **`models.SimplE`** — two embeddings per entity (canonical + inverse); fully
  expressive, handles inverse relations.
- **`models.NeuralLP`** — differentiable logic-rule learning; interpretable, good on
  sparse graphs, more expensive.
- **`models.KBGAT`** — graph-attention KG completion; inductive, handles unseen
  entities from neighborhoods.

## Generative models

### GraphAF (Graph Autoregressive Flow)
Normalizing-flow molecular generator (`models.GraphAF`, wrapping the autoregressive
flow) with exact likelihood, stable non-adversarial training, and conditional
generation. Params include `num_flow` and coupling `hidden_dims`. Drives
`tasks.AutoregressiveGeneration` / `tasks.GCPNGeneration`. See
`references/molecular-tasks.md`.

## Pretraining models

- **`models.InfoGraph`** — mutual-information contrastive pretraining for molecular
  encoders; helps in low-data regimes.
- **`MultiviewContrast`** — multi-view geometric contrastive pretraining for
  proteins; the standard way to pretrain GearNet on structures.

## Selection guide

By task:

- Molecular property → GIN (first), GAT (interpretable), SchNet (3D available).
- Protein → ESM (sequence only), GearNet (structure), ProteinBERT (light sequence).
- Knowledge graph → RotatE (accuracy), ComplEx (balance), TransE (huge graphs).
- Generation → GraphAF (exact likelihood), GCPN + GIN backbone (property RL).
- Retrosynthesis → RGCN (center identification, typed bonds), GIN (synthon
  completion).

By dataset size:

- **< 1K** — pretrained models (ESM), simple architectures (GCN, ProteinCNN), heavy
  regularization.
- **1K–100K** — GIN / GAT for molecules, standard training.
- **> 100K** — anything; deeper nets; train from scratch.

By compute budget: low → GCN / DistMult / ProteinLSTM; medium → GIN / GAT /
ComplEx; high → large ESM / SchNet / high-dim RotatE.

Practical tips: 3–5 layers usually suffice; batch norm helps GNNs (not KG
embeddings); add residual connections for deep nets; `readout="mean"` is a safe
default; include edge features when available; regularize with dropout + weight
decay + early stopping.
