# Task-Specific Training Patterns

## Node Classification

Full-batch training on a single graph (e.g., Cora):

```python
model.train()
for epoch in range(200):
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.cross_entropy(out[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()

# Evaluation — train(False) puts the model in inference mode (disables dropout/BN)
model.train(False)
pred = model(data.x, data.edge_index).argmax(dim=1)
acc = (pred[data.test_mask] == data.y[data.test_mask]).float().mean()
```

For graphs too large for full-batch, switch to `NeighborLoader` mini-batching — see `scaling.md`.

## Graph Classification

Multiple graphs — use `DataLoader` for mini-batching and global pooling to get graph-level representations:

```python
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool

loader = DataLoader(dataset, batch_size=32, shuffle=True)

class GraphClassifier(torch.nn.Module):
    def __init__(self, in_ch, hidden_ch, out_ch):
        super().__init__()
        self.conv1 = GCNConv(in_ch, hidden_ch)
        self.conv2 = GCNConv(hidden_ch, hidden_ch)
        self.lin = torch.nn.Linear(hidden_ch, out_ch)

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        x = global_mean_pool(x, batch)  # [num_graphs_in_batch, hidden_ch]
        return self.lin(x)

# Training loop
for data in loader:
    out = model(data.x, data.edge_index, data.batch)
    loss = F.cross_entropy(out, data.y)
```

PyG's `DataLoader` batches multiple graphs by creating block-diagonal adjacency matrices. The `batch` tensor maps each node to its graph index. Pooling ops (`global_mean_pool`, `global_max_pool`, `global_add_pool`) use this to aggregate per-graph.

## Link Prediction (quick start)

Split edges into train/val/test, use negative sampling:

```python
from torch_geometric.transforms import RandomLinkSplit

transform = RandomLinkSplit(
    num_val=0.1,
    num_test=0.1,
    is_undirected=True,
    add_negative_train_samples=False,
)
train_data, val_data, test_data = transform(data)

# Encode nodes, then score edges
z = model.encode(train_data.x, train_data.edge_index)
# Positive edges
pos_score = (z[train_data.edge_label_index[0]] * z[train_data.edge_label_index[1]]).sum(dim=1)
```

For the complete link prediction guide — GAE/VGAE autoencoders, full training loops, `LinkNeighborLoader` for large graphs, heterogeneous link prediction, and evaluation metrics — see `link_prediction.md`.
