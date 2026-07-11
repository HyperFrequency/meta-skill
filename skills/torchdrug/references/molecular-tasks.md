# Molecular Tasks: Property Prediction, Generation, Retrosynthesis

Workflows for the three molecule-centric task families. Each maps to a `tasks.*`
class wrapped around a representation model. Confirm exact constructor arguments
against the installed version.

---

## 1. Property prediction

Predict a graph-level chemical, physical, or biological property.

### `tasks.PropertyPrediction`

Handles classification and regression. Key parameters:

- `model` — the GNN encoder.
- `task` — the label field(s); `dataset.tasks` is the built-in list.
- `criterion` — `"bce"` (binary/multi-label), `"ce"` (multi-class), `"mse"`/`"mae"`
  (regression).
- `metric` — e.g. `("auroc", "auprc")` or `("mae", "rmse")`.
- `num_mlp_layer` — MLP layers in the readout head.

```python
import torch
from torchdrug import datasets, models, tasks, core

dataset = datasets.BBBP("~/molecule-datasets/")
train_set, valid_set, test_set = dataset.split()

model = models.GIN(input_dim=dataset.node_feature_dim,
                   hidden_dims=[256, 256, 256, 256],
                   edge_input_dim=dataset.edge_feature_dim,
                   batch_norm=True, readout="mean")

task = tasks.PropertyPrediction(model, task=dataset.tasks,
                                criterion="bce", metric=("auprc", "auroc"))

optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(task, train_set, valid_set, test_set, optimizer,
                     gpus=[0], batch_size=32)
solver.train(num_epoch=100)
solver.evaluate("test")
```

### `tasks.MultipleBinaryClassification`

For multi-label datasets (Tox21, SIDER) where each molecule carries several binary
labels with missing values. Computes per-label and averaged metrics and supports
weighted loss for imbalance.

### Recipe checklist

1. **Split with scaffolds** for drug-like data (see `references/datasets.md`).
2. **Pick the model by size**: RF/fingerprint-scale baselines below ~1K; GIN in the
   1K–100K range; pretrained/self-supervised encoders above ~100K.
3. **Include edge features** (`edge_input_dim`) — bonds matter.
4. **Match metrics** to the label balance (AUROC/AUPRC for imbalanced).
5. **Regularize** small sets: dropout, weight decay, early stopping, or pretraining.

Common failures: imbalanced data → weighted/focal loss or resampling; overfitting →
simpler model or transfer learning; OOM → smaller batch or gradient accumulation.

---

## 2. Molecular generation

Create novel structures, optionally optimized for properties.

### `tasks.AutoregressiveGeneration`

Builds molecules atom-by-atom / bond-by-bond, allowing validity constraints and
property shaping during construction. Decode with greedy, sampling, or beam search
to trade determinism for diversity.

### `tasks.GCPNGeneration` — Graph Convolutional Policy Network

Reinforcement learning: a policy network chooses actions (add atom / add bond), a
reward function scores the molecule, and training uses policy gradient (e.g. PPO).
Optimizes non-differentiable objectives and complex domain rules directly.

```python
from torchdrug import tasks

def reward(mol):
    return 0.5 * predicted_affinity(mol) + 0.3 * qed(mol) + 0.2 * (1 - sa_score(mol))

task = tasks.GCPNGeneration(model, reward_function=reward, criterion="ppo")
```

### Generative backbone

GraphAF (`models.GraphAF`, a normalizing flow) gives exact likelihood and stable
non-adversarial training; train by maximum likelihood on ZINC or QM9, optionally
conditioned on a property head.

### Generation modes

- **Unconditional** — sample from the learned distribution; measure validity,
  uniqueness, novelty, internal diversity.
- **Conditional** — optimize QED / LogP / synthesizability (SA score) / predicted
  bioactivity / ADMET, single- or multi-objective (linear weights, Pareto, or
  hard constraints on secondary objectives).
- **Scaffold-based** — keep a fixed core, vary R-groups (lead optimization).
- **Fragment-based** — assemble from a validated fragment vocabulary.

### Validation and filtering (always run)

- Chemical validity: valence, aromaticity, charge — post-check with RDKit.
- Drug-likeness: Lipinski, Veber, PAINS, BRENK filters.
- Synthesizability: SA score, retrosynthesis feasibility, precursor availability.
- Rank survivors by predicted affinity, drug-likeness, novelty, diversity, ADMET;
  select via Pareto frontier or weighted scoring.

Best practice: start unconditional, add constraints incrementally, iterate
generate→validate→retrain, and have a chemist review before synthesis.

---

## 3. Retrosynthesis

Plan routes from a target back to purchasable building blocks. TorchDrug
decomposes single-step retrosynthesis into two learned subtasks plus an end-to-end
wrapper; the benchmark is `datasets.USPTO50k`.

### `tasks.CenterIdentification`

Predicts which bonds are the reaction center (formed/broken). Input: the product
graph; output: per-bond scores. Use an `RGCN` backbone (typed bonds). Metrics:
top-K accuracy, bond-level F1. Parameter: `top_k`.

### `tasks.SynthonCompletion`

Given product + reaction center, generate the reactant structures (synthons):
break bonds at the center, fix atom environments, add leaving groups. Use a `GIN`
backbone. Parameters: `center_topk`, `num_synthon_beam`. Metrics: exact match,
top-K accuracy, chemical validity.

### `tasks.Retrosynthesis` (end-to-end)

Combines both stages into one ranked list of reactant sets.

```python
from torchdrug import datasets, models, tasks

dataset = datasets.USPTO50k("~/retro-datasets/")

center_model = models.RGCN(input_dim=dataset.node_feature_dim,
                           num_relation=dataset.num_bond_type,
                           hidden_dims=[256, 256, 256])
synthon_model = models.GIN(input_dim=dataset.node_feature_dim,
                           hidden_dims=[256, 256, 256])

task = tasks.Retrosynthesis(center_model, synthon_model,
                            center_topk=5, num_synthon_beam=10)
```

### Multi-step planning

Apply single-step retrosynthesis recursively until reaching commercial compounds.
Search strategies: BFS (shortest routes, memory heavy), DFS (memory light), MCTS
(the strong default, balances exploration/exploitation), A* (heuristic-guided).
Score routes by step count, convergence, availability of building blocks, per-step
feasibility, yield, cost, and green-chemistry factors. Stop at purchasable
compounds, standard intermediates, a max depth (~6–10), or low confidence.

### Validation

Check reactant validity, reaction plausibility, atom-map consistency, and
stoichiometry; filter by literature precedent and functional-group compatibility;
verify commercial availability early (eMolecules, ZINC vendor annotations,
Reaxys). Generate several diverse routes, not just top-1, and have a chemist
review.

Known limits: most models are single-step, ignore explicit reaction conditions,
and handle stereochemistry poorly; rare reaction types are underrepresented.
