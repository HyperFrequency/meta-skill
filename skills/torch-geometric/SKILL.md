---
name: torch-geometric
version: 0.1.0
description: PyTorch Geometric (PyG) for graph neural networks — node/link/graph classification, message passing (GCN, GAT, GraphSAGE, GIN), heterogeneous graphs, neighbor sampling, and custom datasets. Use when working with torch_geometric, not for general NetworkX analytics or non-graph PyTorch models.
license: MIT license
compatibility: Requires Python 3.10+, PyTorch 2.6+, and torch-geometric 2.7.x. Optional extension wheels (pyg-lib, torch-scatter, torch-sparse, torch-cluster) must match your PyTorch/CUDA build from https://data.pyg.org/whl.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# PyTorch Geometric (PyG)

PyG is the standard library for Graph Neural Networks built on PyTorch. It provides data structures for graphs, 60+ GNN layer implementations, scalable mini-batch training, and support for heterogeneous graphs.

This file is a router. Each section gives the minimum you need to start, then points to a `references/` file for full detail.

## Installation

Tested against **torch-geometric 2.7.x** (Oct 2025), **Python 3.10+**, **PyTorch 2.6+**.

```bash
uv pip install torch          # match your CUDA/CPU build first — https://pytorch.org/get-started/locally/
uv pip install torch_geometric
```

Accelerated extension wheels (`pyg-lib`, `torch-scatter`, `torch-sparse`, `torch-cluster`) are **not required** for basic usage since PyG 2.3. For version-matched wheel installs, the conda situation, and PyG 2.7 breaking-change notes, read `references/installation.md`.

## Core Concepts

### Graph Data: `Data` and `HeteroData`

A graph lives in a `Data` object:

```python
from torch_geometric.data import Data

data = Data(
    x=node_features,          # [num_nodes, num_node_features]
    edge_index=edge_index,     # [2, num_edges] — COO format, dtype=torch.long
    edge_attr=edge_features,   # [num_edges, num_edge_features]
    y=labels,                  # node-level [num_nodes, *] or graph-level [1, *]
    pos=positions,             # [num_nodes, num_dimensions] (for point clouds/spatial)
)
```

**`edge_index` format is critical**: a `[2, num_edges]` tensor where `edge_index[0]` = source nodes, `edge_index[1]` = target nodes. It is NOT a list of tuples. If you have edge pairs as rows, transpose and call `.contiguous()`:

```python
edge_index = edge_pairs.t().contiguous()   # [[src1,dst1],[src2,dst2],...] → [2, num_edges]
```

For undirected graphs, include both directions: edge (0,1) needs both `[0,1]` and `[1,0]` in edge_index (or apply `T.ToUndirected()`).

For graphs with multiple node/edge types, use `HeteroData` — see Heterogeneous Graphs below.

### Datasets and Transforms

PyG bundles auto-downloading datasets (`Planetoid`, `TUDataset`, `OGB`, `ShapeNet`, …) and torchvision-style transforms (`NormalizeFeatures`, `ToUndirected`, `AddSelfLoops`, `KNNGraph`, `Compose`). For the dataset-by-task list and the transform catalogue (including `pre_transform` vs `transform`), read `references/datasets_transforms.md`.

## Building GNN Models

### Quick start: built-in layers

Stack conv layers from `torch_geometric.nn`:

```python
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index)
        return x
```

**Important**: PyG conv layers do NOT include activation functions — apply them yourself after each layer. This is by design.

### Choosing a conv layer

| Layer | Best for | Key idea |
|-------|----------|----------|
| `GCNConv` | Homogeneous, semi-supervised node classification | Spectral-inspired, degree-normalized aggregation |
| `GATConv` / `GATv2Conv` | When neighbor importance varies | Attention-weighted messages |
| `SAGEConv` | Large graphs, inductive settings | Sampling-friendly, learnable aggregation |
| `GINConv` | Graph classification, maximizing expressiveness | As powerful as WL test |
| `TransformerConv` | Rich edge features, complex interactions | Multi-head attention with edge features |
| `EdgeConv` | Point clouds, dynamic graphs | MLP on edge features (x_i, x_j - x_i) |
| `RGCNConv` | Heterogeneous with many relation types | Relation-specific weight matrices |
| `HGTConv` | Heterogeneous graphs | Type-specific attention |

All conv layers accept `(x, edge_index)` at minimum; many also accept `edge_attr`.

### Lazy initialization

Use `-1` for input channels to let PyG infer dimensions on the first forward pass — especially useful for heterogeneous models:

```python
conv = SAGEConv((-1, -1), 64)   # input dims inferred on first forward
with torch.no_grad():           # one warm-up pass initializes lazy params
    out = model(data.x, data.edge_index)
```

### High-level model APIs

For common architectures, use ready-made classes (`GraphSAGE`, `GCN`, `GAT`, `GIN`) that take `in_channels`, `hidden_channels`, `out_channels`, `num_layers`.

### Custom layers via `MessagePassing`

To implement a novel GNN layer, subclass `MessagePassing`. The pipeline: `propagate()` orchestrates → `message()` defines per-edge info (phi) → `aggregate()` combines at each node (sum/mean/max) → `update()` transforms the result (gamma).

**The `_i` / `_j` convention**: any tensor passed to `propagate()` is auto-indexed by appending `_i` (target/central node) or `_j` (source/neighbor node) in the `message()` signature. Pass `x=...` to propagate and you can read `x_i` / `x_j` in `message()`.

For full GCN and EdgeConv `MessagePassing` implementations, read `references/message_passing.md`.

## Task-Specific Patterns

- **Node classification**: full-batch loop over `model(data.x, data.edge_index)` with `train_mask`/`test_mask` slicing.
- **Graph classification**: `DataLoader` mini-batching + `global_mean_pool(x, batch)` for graph-level readout.
- **Link prediction**: `RandomLinkSplit` + negative sampling; encode nodes, then score edges by inner product.

Full training-loop code for all three is in `references/training_patterns.md`. The complete link-prediction guide (GAE/VGAE, `LinkNeighborLoader`, heterogeneous links, metrics) is in `references/link_prediction.md`.

## Scaling to Large Graphs

For graphs that don't fit in GPU memory, use neighbor sampling via `NeighborLoader`:

```python
from torch_geometric.loader import NeighborLoader

train_loader = NeighborLoader(
    data,
    num_neighbors=[15, 10],      # hop-1 samples 15, hop-2 samples 10
    batch_size=128,              # seed nodes per batch
    input_nodes=data.train_mask,
    shuffle=True,
)

for batch in train_loader:
    batch = batch.to(device)
    out = model(batch.x, batch.edge_index)
    # Only the first batch_size nodes are seed nodes — slice loss to them:
    loss = F.cross_entropy(out[:batch.batch_size], batch.y[:batch.batch_size])
```

Key points: `len(num_neighbors)` should equal GNN depth; seed nodes are always the first `batch.batch_size` rows; `batch.n_id` maps back to original IDs; works for `Data` and `HeteroData`; use `LinkNeighborLoader` for link prediction; >2–3 hops is generally infeasible (exponential blowup).

Other samplers (`ClusterLoader`, `GraphSAINTSampler`, `ShaDowKHopSampler`), multi-GPU DDP, PyTorch Lightning, and `torch.compile` support are covered in `references/scaling.md`.

## Heterogeneous Graphs

For multiple node/edge types (social networks, knowledge graphs, recommendation), use `HeteroData` — indexed by node-type string and `(src_type, edge_type, dst_type)` triplet:

```python
from torch_geometric.data import HeteroData

data = HeteroData()
data['user'].x = torch.randn(1000, 64)
data['movie'].x = torch.randn(500, 128)
data['user', 'rates', 'movie'].edge_index = torch.randint(0, 500, (2, 3000))
# data.x_dict, data.edge_index_dict, data.metadata() give convenience views
```

Three ways to build a heterogeneous GNN:
1. **`to_hetero(model, data.metadata(), aggr='sum')`** — write a homogeneous model with `(-1, -1)` lazy channels, auto-convert; it then accepts `(x_dict, edge_index_dict)`.
2. **`HeteroConv({...}, aggr='sum')`** — a different conv per edge-type triplet.
3. **Native operators** like `HGTConv(hidden, hidden, data.metadata(), num_heads=4)`.

Gotchas: apply `T.ToUndirected()` for reverse edge types; disable `add_self_loops` in bipartite convs (different src/dst types) and use skip connections instead; for `NeighborLoader` pass `input_nodes=('node_type', mask)` and optionally a per-edge-type `num_neighbors` dict.

Full code with training loops and heterogeneous `NeighborLoader` usage is in `references/heterogeneous.md`.

## Custom Datasets

Loading your own data into PyG:

- **Quick (no class)**: build `Data` objects directly and pass a list to `DataLoader`.
- **Reusable (fits in RAM)**: subclass `InMemoryDataset` — override `raw_file_names`, `processed_file_names`, `download()`, `process()`.
- **Large (disk-backed)**: subclass `Dataset` — also override `len()` and `get()`.
- **From CSV / NetworkX / scipy**: pandas mappings to consecutive indices; `from_networkx(G)`; `from_scipy_sparse_matrix(adj)`.

Complete examples with CSV encoders and the MovieLens walkthrough are in `references/custom_datasets.md`.

## Explainability

`torch_geometric.explain` interprets GNN predictions via an `Explainer` wrapping an algorithm:

```python
from torch_geometric.explain import Explainer, GNNExplainer

explainer = Explainer(
    model=model,
    algorithm=GNNExplainer(epochs=200),
    explanation_type='model',
    node_mask_type='attributes',
    edge_mask_type='object',
    model_config=dict(mode='multiclass_classification', task_level='node', return_type='log_probs'),
)
explanation = explainer(data.x, data.edge_index, index=10)
explanation.visualize_graph()
explanation.visualize_feature_importance(top_k=10)
```

Algorithms: `GNNExplainer` (optimization), `PGExplainer` (parametric/trained), `CaptumExplainer` (gradient), `AttentionExplainer` (attention weights); homogeneous and heterogeneous. All algorithms, hetero explanations, metrics, and PGExplainer training are in `references/explainability.md`.

## Common Pitfalls

1. **edge_index shape**: must be `[2, num_edges]`, not `[num_edges, 2]`. Transpose if needed.
2. **Forgetting activations**: conv layers don't include ReLU/etc — add them manually.
3. **Self-loops in hetero bipartite**: don't use `add_self_loops=True` when src and dst node types differ. Use skip connections.
4. **NeighborLoader slicing**: only the first `batch.batch_size` nodes are seed nodes — slice predictions and labels accordingly.
5. **Undirected graphs**: include both edge directions, or use `T.ToUndirected()`.
6. **Lazy init**: models with `-1` input channels need one `torch.no_grad()` forward pass before training to initialize parameters.
7. **Global pooling for graph tasks**: use `global_mean_pool(x, batch)`, not manual reshape.
8. **num_neighbors alignment**: keep `len(num_neighbors)` equal to the number of GNN layers.

## Reference Map

`references/`: `installation.md`, `datasets_transforms.md`, `message_passing.md`, `training_patterns.md`, `link_prediction.md`, `scaling.md`, `heterogeneous.md`, `custom_datasets.md`, `explainability.md` — each expands the matching section above.
