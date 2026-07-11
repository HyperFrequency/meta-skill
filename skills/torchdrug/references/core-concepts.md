# Core Concepts, Training, and Internals

Architecture, data structures, the model/task contracts, training loops, and the
pitfalls you hit in real use.

## Design in one sentence

TorchDrug factors every problem into three swappable parts — **data** (graph
structures), a **representation model** (encodes a graph into vectors), and a
**task** (loss + metrics) — so you reuse one encoder across many objectives.

Modules:

- `data` / `datasets` — graph structures and 40+ ready datasets.
- `models` — representation and embedding architectures.
- `tasks` — learning objectives with `predict` / `target` / `evaluate`.
- `layers` — reusable GNN building blocks (message passing, readouts).
- `core` — base classes (`Configurable`, `Registry`) and the training `Engine`.

## Configurable and Registry

Every component subclasses `core.Configurable`, so a model or task can serialize
to a plain dict and reconstruct from it — useful for reproducible experiments and
checkpoints.

```python
from torchdrug import core, models

model = models.GIN(input_dim=10, hidden_dims=[256, 256])
config = model.config_dict()                 # {'class': 'GIN', 'input_dim': 10, ...}
model2 = core.Configurable.load_config_dict(config)
```

`@core.Registry.register("models.CustomModel")` (commonly imported as
`core.register`) registers a custom class by string so it participates in the same
serialization and lookup machinery. Register custom models, tasks, and datasets to
make them Configurable.

## Data structures

### Graph

The base structure for any graph.

- Attributes: `num_node`, `num_edge`, `node_feature` `[num_node, d]`,
  `edge_feature` `[num_edge, d]`, `edge_list` `[num_edge, 2 or 3]`,
  `num_relation` (for multi-relational graphs).
- Methods: `node_mask(mask)`, `edge_mask(mask)`, `undirected()`, `directed()`.
- Batching: a batch is stored as one big disconnected graph (a `PackedGraph`); the
  data loader does this automatically and preserves per-graph indices.

### Molecule (extends Graph)

- Extra attributes: `atom_type` (atomic numbers), `bond_type`, `formal_charge`,
  `explicit_hs`.
- Construction / export: `Molecule.from_smiles(smiles)`,
  `Molecule.from_molecule(rdkit_mol)`, `to_smiles()`, `to_molecule()` (to RDKit).

```python
from torchdrug import data
mol = data.Molecule.from_smiles("CCO")
mol.atom_type   # [6, 6, 8]  -> C, C, O
mol.bond_type   # single bonds
rdkit_mol = mol.to_molecule()
```

### Protein (extends Graph)

- Nodes usually represent **residues**, not atoms.
- Extra attributes: `residue_type`, `atom_name`, `atom_type`, `residue_number`,
  `chain_id`.
- Construction: `Protein.from_pdb(path)`, `Protein.from_sequence(seq)`,
  `to_pdb(path)`.
- Edges are built by strategy: sequential (adjacent residues), spatial radius
  cutoff, or K-nearest-neighbors — configured through graph-construction transforms
  (e.g. `layers.geometry.SpatialEdge`, `KNNEdge`, `SequentialEdge`) or the protein
  graph helpers.

```python
protein = data.Protein.from_pdb("AF-P12345-F1-model_v4.pdb")  # AlphaFold output loads fine
```

### PackedGraph

The batching structure for graphs of different sizes: one contiguous memory block
holding many graphs, with `num_nodes` / `num_edges` per-graph counts and a
`graph_ind` node-to-graph map. Produced automatically by the data loader; you
rarely build it by hand.

## Model interface

All models share one forward signature:

```python
def forward(self, graph, input, all_loss=None, metric=None):
    # graph : batched (Packed)Graph
    # input : node features [num_node, input_dim]
    # all_loss, metric : accumulators the task threads through for multi-objective training
    output = self.layers(graph, input)
    return {"node_feature": output, "graph_feature": self.readout(graph, output)}
```

Every model must set `input_dim` and `output_dim` so tasks can compose models and
check dimensions. Returned dicts carry named representations (`node_feature`,
`graph_feature`, `residue_feature`, ...); tasks pick the key they need.

## Task interface

A task wraps a model with a prediction head, a loss, and metrics:

```python
from torchdrug import tasks

class CustomTask(tasks.Task):
    def predict(self, batch, all_loss=None, metric=None):
        graph = batch["graph"]
        output = self.model(graph, graph.node_feature.float())
        return self.mlp(output["graph_feature"])

    def target(self, batch):
        return batch["label"]

    def forward(self, batch):          # returns the training loss
        pred, target = self.predict(batch), self.target(batch)
        return self.criterion(pred, target)

    def evaluate(self, pred, target):  # returns a metric dict
        return {"auroc": auroc(pred, target)}

    def preprocess(self, train_set, valid_set, test_set):
        ...   # optional: compute label stats, class weights, etc.
```

Built-in tasks (`PropertyPrediction`, `KnowledgeGraphCompletion`, generation and
retrosynthesis tasks) already implement these; you subclass only for something new.

## Training

### With `core.Engine` (idiomatic)

```python
import torch
from torchdrug import core

optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(task, train_set, valid_set, test_set, optimizer,
                     gpus=[0], batch_size=32)
solver.train(num_epoch=100)
solver.evaluate("valid")
solver.save("checkpoint.pth")
```

`core.Engine` handles batching (via `data.DataLoader`), device placement, logging,
and multi-GPU. `gpus=None` runs on CPU. Pass a `scheduler` for LR schedules and
`gradient_interval` for gradient accumulation.

### Manual loop (full control)

```python
from torchdrug import data

loader = data.DataLoader(train_set, batch_size=32, shuffle=True)
for epoch in range(100):
    task.train()
    for batch in loader:
        loss = task(batch)
        optimizer.zero_grad(); loss.backward(); optimizer.step()

    task.eval()
    pred = task.predict(next(iter(valid_loader)))
    target = task.target(...)
    print(task.evaluate(pred, target))
```

You can also wrap `task` in a `pytorch_lightning.LightningModule`
(`training_step` → `task(batch)`; `configure_optimizers` → an Adam) if you want
Lightning's callbacks and multi-node scaling.

## Losses and metrics

- Classification criteria: `"bce"` (binary / multi-label), `"ce"` (multi-class).
- Regression criteria: `"mse"`, `"mae"`.
- Classification metrics: AUROC, AUPRC, accuracy, F1.
- Regression metrics: MAE, RMSE, R², Pearson.
- Ranking (knowledge graphs): mean rank (MR), MRR, Hits@K.
- Multi-task: metrics computed per task and macro-averaged; weight tasks with
  `task_weight=[...]`.

## Transforms

Datasets accept a `transform=` applied per sample:

```python
from torchdrug import transforms, datasets

transform = transforms.Compose([transforms.VirtualNode(), transforms.VirtualEdge()])
dataset = datasets.BBBP("~/data/", transform=transform)

# proteins: cap sequence length
protein_ds = datasets.Fold("~/data/", transform=transforms.TruncateProtein(max_length=500))
```

Molecule transforms include `VirtualNode` / `VirtualEdge`; protein transforms
include `TruncateProtein` and the geometry edge-construction layers.

## Self-supervised pretraining

For small labeled sets, pretrain the encoder unsupervised then fine-tune:

- Molecules: attribute masking (mask node features), edge prediction, context
  prediction / `InfoGraph` contrastive learning.
- Proteins: masked-residue prediction, distance/angle prediction,
  `MultiviewContrast` geometric pretraining (pairs well with GearNet).

## Custom GNN layers

Subclass the message-passing base and implement the three primitives:

```python
from torchdrug import layers

class CustomConv(layers.MessagePassingBase):
    def message(self, graph, input): ...     # per-edge message
    def aggregate(self, graph, message): ...  # combine incoming messages per node
    def combine(self, input, update): ...     # merge with the node's own state
```

## Install caveats and pitfalls

- **`torch-scatter` / `torch-cluster`.** These compiled extensions must match your
  exact `torch` + CUDA build. Install `torch` first, then the matching
  scatter/cluster wheels, then `torchdrug`. The conda channel
  `-c milagraph -c conda-forge torchdrug` sidesteps most of this.
- **Maintenance.** TorchDrug is largely unmaintained (latest 0.2.x). It targets
  older PyTorch versions; on a very recent torch you may hit API breaks. If you
  need a maintained stack, prefer `deepchem` or raw PyTorch Geometric.
- **Forgetting `input_dim` / `output_dim`** on a custom model — it will not compose
  with tasks.
- **Not batching with PackedGraph** for variable-sized graphs — use the
  `data.DataLoader`, which packs automatically.
- **Data leakage** from random splits or overlapping pretraining data — use scaffold
  splits and check pretraining corpora.
- **Ignoring edge features** — bond types and spatial distances are often decisive;
  pass `edge_input_dim` and a featurizer that emits them.
- **Wrong metric for imbalanced labels** — use AUROC/AUPRC, not raw accuracy.
- **Overfitting tiny datasets** — pretrain, use simpler models, and add dropout /
  weight decay / early stopping.
