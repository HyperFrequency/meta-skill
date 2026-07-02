# Datasets and Transforms

## Built-in Datasets

PyG bundles many standard datasets that auto-download and preprocess:

```python
from torch_geometric.datasets import Planetoid, TUDataset

# Single-graph node classification (Cora, Citeseer, Pubmed)
dataset = Planetoid(root='./data', name='Cora')
data = dataset[0]  # single graph with train/val/test masks

# Multi-graph classification (ENZYMES, MUTAG, IMDB-BINARY, etc.)
dataset = TUDataset(root='./data', name='ENZYMES')
# dataset[0], dataset[1], ... are individual graphs
```

Common datasets by task:
- **Node classification**: Planetoid (Cora/Citeseer/Pubmed), OGB (ogbn-arxiv, ogbn-products, ogbn-mag)
- **Graph classification**: TUDataset (MUTAG, ENZYMES, PROTEINS, IMDB-BINARY), OGB (ogbg-molhiv)
- **Link prediction**: OGB (ogbl-collab, ogbl-citation2)
- **Molecular**: QM7, QM9, MoleculeNet
- **Point cloud/mesh**: ShapeNet, ModelNet10/40, FAUST

## Transforms

Transforms preprocess or augment graph data, analogous to torchvision transforms:

```python
import torch_geometric.transforms as T

# Common transforms
T.NormalizeFeatures()    # Row-normalize node features to sum to 1
T.ToUndirected()         # Add reverse edges to make graph undirected
T.AddSelfLoops()         # Add self-loop edges
T.KNNGraph(k=6)          # Build k-NN graph from point cloud positions
T.RandomJitter(0.01)     # Random noise augmentation on positions
T.Compose([...])         # Chain multiple transforms

# Apply as pre_transform (once, saved to disk) or transform (every access)
dataset = ShapeNet(root='./data', pre_transform=T.KNNGraph(k=6),
                   transform=T.RandomJitter(0.01))
```

`pre_transform` runs once and the result is cached on disk; `transform` runs on every access (use it for stochastic augmentation).
