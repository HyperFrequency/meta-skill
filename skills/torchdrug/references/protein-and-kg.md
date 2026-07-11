# Protein Modeling and Knowledge-Graph Reasoning

Two task families: predicting things about proteins, and completing biomedical /
general knowledge graphs. Confirm exact constructor arguments against the installed
version.

---

## Protein modeling

Proteins are graphs whose nodes are residues and whose edges encode sequential or
spatial relationships. Choose a sequence model when you only have the sequence, and
a structure model when you have 3D coordinates (experimental or predicted).

### Task classes

- **`tasks.PropertyPrediction`** — protein-level labels: enzyme function, stability,
  solubility, subcellular localization, GO terms.
- **`tasks.NodePropertyPrediction`** — residue-level labels: secondary structure,
  disorder, PTM sites, binding-site residues.
- **`tasks.InteractionPrediction`** — protein-protein or protein-ligand pairs;
  symmetric (PPI) or asymmetric (protein-ligand), with negative sampling.
- **`tasks.ContactPrediction`** — residue-residue spatial contacts for
  structure-from-sequence.

### Model choice

Sequence-only: **`models.ESM`** is the state-of-the-art default (pretrained on
~250M sequences; ESM-1b / ESM-2 variants) — load a checkpoint and fine-tune.
Lighter alternatives: `models.ProteinBERT`, `models.ProteinLSTM`,
`models.ProteinCNN`/`ProteinResNet`.

Structure-based: **`models.GearNet`** (geometry-aware, multiple edge types) is the
strong default; `models.SchNet` handles raw 3D coordinates; standard GCN/GAT/GIN
also run on protein graphs with appropriate edge definitions.

### Graph construction

Edge types combine to capture different structure levels:

- **Sequential** — adjacent residues (primary structure).
- **Spatial** — KNN or radius cutoff on Cα positions, e.g. within 10 Å (tertiary
  structure).
- **Contact** — heavy-atom distance below ~8 Å.

Node features: residue identity (one-hot or embedding), 3D coordinates and backbone
angles (phi/psi/omega), physicochemical properties. Edge features: type, distance,
angles/dihedrals.

### Fine-tuning a pretrained encoder

```python
from torchdrug import models, tasks

model = models.ESM(path="esm1b_t33_650M_UR50S.pt")   # pretrained checkpoint
task = tasks.PropertyPrediction(model, task=["stability"],
                                criterion="mse", metric=["mae", "rmse"])
# fine-tune with a small LR (1e-5 to 1e-4); freeze embeddings for very small sets
```

### Pretraining (when labels are scarce)

Self-supervised objectives: masked-residue prediction, residue-distance /
backbone-angle / dihedral prediction, contact-map prediction. `MultiviewContrast`
provides geometric contrastive pretraining that pairs with GearNet.

### Practical guidance

- **Sequence tasks** → start from ESM/ProteinBERT, low LR, dropout; freeze
  embeddings for tiny datasets.
- **Structure tasks** → GearNet with multiple edge types + geometric features;
  pretrain on large structure sets; augment with rotations/crops.
- **Small datasets** → transfer learning + multi-task learning + strong
  regularization.
- **Won't learn?** For sequences use pretrained ESM; for structures re-check edge
  construction and geometric features.

Integrations: load AlphaFold or ESMFold structures via `data.Protein.from_pdb`, or
import Rosetta/PyRosetta models, then run any structure model.

---

## Knowledge-graph reasoning

Link prediction over `(head, relation, tail)` triples: given two parts, rank
candidates for the third. The main application is biomedical — drug repurposing and
disease-gene discovery over Hetionet.

### `tasks.KnowledgeGraphCompletion`

```python
from torchdrug import datasets, models, tasks

dataset = datasets.FB15k237("~/kg-datasets/")
model = models.RotatE(num_entity=dataset.num_entity,
                      num_relation=dataset.num_relation,
                      embedding_dim=2000, max_score=9)
task = tasks.KnowledgeGraphCompletion(model, num_negative=128,
                                      adversarial_temperature=2, criterion="bce")
```

Prediction modes: head prediction (`?, r, t`), tail prediction (`h, r, ?`), or
both (standard evaluation).

### Negative sampling

- **Uniform** — random corrupted entities.
- **Self-adversarial** — weight negatives by the model's current scores;
  `adversarial_temperature` controls focus on hard negatives (`num_negative` sets
  the count).
- **Type-constrained** — only sample entity types valid for the relation (helps on
  biomedical graphs).

Losses: BCE (per-triple), margin (`max(0, margin + neg - pos)`), logistic.

### Evaluation — always filtered

Ranking metrics: mean rank (MR), mean reciprocal rank (MRR), Hits@K (K = 1, 3, 10).
Use **filtered** ranking (remove other known-true triples from the candidate set),
which is the standard protocol; also inspect per-relation performance.

### Choosing an embedding model by relation pattern

- 1-to-1 → TransE fine; 1-to-N / N-to-1 → DistMult / ComplEx / SimplE (avoid
  TransE); N-to-N → ComplEx / SimplE / RotatE.
- Symmetric → DistMult / ComplEx; antisymmetric or inverse → ComplEx / SimplE /
  RotatE (avoid DistMult); composition / multi-hop → RotatE (best), TransE
  (reasonable).
- Sparse graphs → `NeuralLP` (learns rules); unseen entities → `KBGAT` (inductive).

By scale: small (<50K entities) ComplEx/SimplE with dim 200–500; large (>100K)
DistMult for speed or RotatE for accuracy at dim 500–2000.

### Biomedical workflows

- **Drug repurposing** — train on known Compound-treats-Disease links in Hetionet,
  predict new ones, filter by shared gene/pathway mechanism, then validate.
- **Disease-gene discovery** — model gene-disease-pathway subgraphs, predict
  missing gene-disease links, prioritize for experiment.
- **Multi-hop queries** — "drugs that treat diseases caused by gene X" need
  path/rule reasoning (NeuralLP supports this natively).

### Common issues

- Weak on some relation types → pick a model matching the pattern, or use
  relation-specific models.
- Overfitting small graphs → lower embedding dim, more regularization.
- Slow on large graphs → fewer negatives, DistMult, mini-batching.
- New entities → inductive models (KBGAT) or entity features.

Defaults that work: start with ComplEx or RotatE, self-adversarial sampling,
filtered metrics, per-relation analysis, and domain-expert review of top
predictions.
