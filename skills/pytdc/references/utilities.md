# PyTDC Utilities: Splits, Metrics, Processing

TDC's value over raw CSVs is its standardized tooling: meaningful splits, a metric
`Evaluator`, molecule format conversion/filtering, and entity lookups. This file covers
each with concrete calls. Some helper signatures vary by TDC version — the ones to
double-check against your installed version are flagged.

---

## 1. Dataset Splits

Splits come from the loaded dataset via `get_split`. The split **method** is the most
consequential choice for honest evaluation.

```python
from tdc.single_pred import ADME
data  = ADME(name='Caco2_Wang')
split = data.get_split(method='scaffold', seed=42, frac=[0.7, 0.1, 0.2])
train, valid, test = split['train'], split['valid'], split['test']
```

`get_split` returns `{'train', 'valid', 'test'}` DataFrames. `seed` makes it
reproducible; `frac` sets the three-way ratio.

### Methods

- **`random`** — shuffle and cut. Use only as a baseline or for quick prototyping.
  Over-optimistic for drug discovery because near-duplicate analogs leak across sets.
- **`scaffold`** — group by Bemis–Murcko scaffold, then assign whole scaffolds to
  train/valid/test so **test molecules have unseen scaffolds**. The realistic default
  for `single_pred` chemistry; measures generalization to new chemical series.
- **`cold_drug` / `cold_target` / `cold_drug_target`** — for `multi_pred`. Hold out
  entire drugs, targets, or both so the test set contains none seen in training.
  `cold_drug_target` is the hardest and most realistic DTI setting.
- **`temporal`** — order by time and put later points in test; simulates prospective
  prediction (e.g. trial outcomes).

```python
from tdc.multi_pred import DTI
data = DTI(name='BindingDB_Kd')
split = data.get_split(method='cold_drug', seed=1)   # unseen drugs in test
```

**Always verify cold splits actually held out what you think:**

```python
assert set(split['train']['Drug_ID']).isdisjoint(split['test']['Drug_ID'])
```

Custom fractions: `frac=[0.8, 0.1, 0.1]`, `frac=[0.7, 0.15, 0.15]`, etc.

---

## 2. Model Evaluation (`Evaluator`)

Construct by metric name, then call on `(y_true, y_pred)`.

```python
from tdc import Evaluator
Evaluator(name='ROC-AUC')(y_true, y_pred_proba)   # pass probabilities
Evaluator(name='RMSE')(y_true, y_pred)            # regression
```

**Classification** (pass probabilities for AUC metrics, hard labels for F1/Accuracy):
`ROC-AUC`, `PR-AUC`, `F1`, `Accuracy`, `Kappa` (Cohen's kappa), and multi-label
`Micro-F1`, `Macro-F1`, `Micro-AUPR`, `Macro-AUPR`.

**Regression:** `RMSE`, `MAE`, `MSE`, `R2`.

**Ranking / correlation:** `Spearman`, `Pearson`.

Guidance:
- Imbalanced binary → `PR-AUC` alongside `ROC-AUC`; avoid `Accuracy`.
- Binding-affinity regression → `RMSE`/`MAE` plus `Spearman` (rank correlation matters
  more than absolute error for triage).
- Use the **same metric the leaderboard/benchmark group defines** when comparing.

---

## 3. Benchmark Group Evaluation (multi-seed protocol)

Benchmark groups enforce a fixed split and require mean ± std over five seeds — this is
how TDC leaderboards stay comparable.

```python
from tdc.benchmark_group import admet_group
group = admet_group(path='data/')

predictions = {}
for seed in [1, 2, 3, 4, 5]:
    benchmark = group.get('Caco2_Wang')       # fixed split; dict train/valid/test
    train, valid = benchmark['train'], benchmark['valid']
    # ... train on train/valid, predict on benchmark['test'] ...
    predictions[seed] = model.predict(benchmark['test'])

results = group.evaluate(predictions)   # -> {'caco2_wang': [mean, std]}
```

Report **both** numbers. A single-seed score is not a valid benchmark submission. The
ADMET group covers 22 datasets; other groups exist for DTI, drug combination, and more.

---

## 4. Molecule Format Conversion (`MolConvert`)

Convert SMILES to the representation your model expects. This wraps RDKit / PyG / DGL —
for standalone descriptor or fingerprint work outside a TDC pipeline, use `rdkit` or
`datamol` directly.

```python
from tdc.chem_utils import MolConvert
to_pyg = MolConvert(src='SMILES', dst='PyG')
graph  = to_pyg('CC(C)Cc1ccc(cc1)C(C)C(O)=O')
graphs = to_pyg(['SMILES1', 'SMILES2'])   # batch
```

Destinations include:
- **Text:** `SMILES`, `SELFIES`, `InChI`
- **Fingerprints:** `ECFP` (Morgan), `MACCS`, `RDKit`, `AtomPair`, `TopologicalTorsion`
- **Graphs:** `PyG`, `DGL`
- **3D:** `Graph3D`, `Coulomb`, `Distance`

`PyG`/`DGL` targets need the corresponding library installed.

---

## 5. Molecule Filtering (`MolFilter`)

Drop non-drug-like or assay-interfering molecules before training.

```python
from tdc.chem_utils import MolFilter
mol_filter = MolFilter(
    rules=['PAINS', 'BMS'],
    property_filters_dict={'MW': (150, 500), 'LogP': (-0.4, 5.6),
                           'HBD': (0, 5), 'HBA': (0, 10)},
)
kept = mol_filter(smiles_list)
```

Rule sets: `PAINS` (pan-assay interference), `BMS`, `Glaxo`, `Dundee`, `Inpharmatica`,
`LINT`. Filter early to cut downstream compute.

---

## 6. Entity Retrieval

Convert between database identifiers (these hit external services, so they need network
access and can be rate-limited — batch and cache):

```python
from tdc.utils import cid2smiles, uniprot2seq
cid2smiles(2244)         # PubChem CID -> SMILES (aspirin -> 'CC(=O)Oc1ccccc1C(=O)O')
uniprot2seq('P12345')    # UniProt ID  -> amino-acid sequence
```

Enumerate datasets programmatically:

```python
from tdc.utils import retrieve_dataset_names
retrieve_dataset_names('ADME')
```

---

## 7. Label Transforms, Binarization, Balancing (verify per version)

These capabilities exist but their exact import paths and signatures have shifted
across TDC releases. **Confirm against your installed version** (`help(...)` or the
docs) before wiring them in — do not assume the name.

- **Unit conversion** — convert binding-affinity labels between `nM`, `uM`, and log
  forms (`p`/pKd/pKi/pIC50). In recent TDC this is `convert_y_unit(y, from_, to_)` in
  `tdc.utils`. Verify the exact argument names for your version.
- **Binarization** — threshold a continuous label into 0/1 with an `order`
  (ascending/descending) controlling which side maps to 1. Exposed as a method on the
  data object and/or a util; confirm which in your version.
- **Label meaning** — for typed multi-class tasks (e.g. `DrugBank` DDI), a label-map
  helper returns `{code: human-readable interaction}`. Look for `get_label_map` in
  `tdc.utils`.
- **Class balancing** — over/under-sampling helpers exist for imbalanced binary tasks;
  check the current API name rather than guessing.
- **Negative sampling** — for interaction tasks, TDC can synthesize negative
  drug/target pairs at a chosen ratio; confirm the method/util name for your version.
- **Cross-validation folds** — a `create_fold`-style helper produces CV index splits.

Because these drift, prefer the confident core above (`get_split`, `Evaluator`,
`MolConvert`, `MolFilter`, `retrieve_dataset_names`) for anything load-bearing, and
treat the transforms here as convenience wrappers to verify at use time.

---

## End-to-End Pipelines

### Single-prediction training pipeline

```python
from tdc.single_pred import ADME
from tdc import Evaluator
from tdc.chem_utils import MolConvert

data  = ADME(name='Caco2_Wang')
split = data.get_split(method='scaffold', seed=42)
train, valid, test = split['train'], split['valid'], split['test']

to_ecfp = MolConvert(src='SMILES', dst='ECFP')
X_train = to_ecfp(train['Drug'].tolist())
# model.fit(X_train, train['Y']); preds = model.predict(to_ecfp(test['Drug'].tolist()))
# Evaluator(name='MAE')(test['Y'], preds)
```

### DTI cold-split evaluation

```python
from tdc.multi_pred import DTI
from tdc import Evaluator

data  = DTI(name='BindingDB_Kd')
split = data.get_split(method='cold_drug', seed=42)
assert set(split['train']['Drug_ID']).isdisjoint(split['test']['Drug_ID'])
# ... train, predict on split['test'] ...
# Evaluator(name='RMSE')(split['test']['Y'], preds)
```

---

## Best Practices

1. Use `scaffold` (single-pred) or `cold_*` (multi-pred) splits — never `random` — for
   any claim about generalization.
2. Run multiple seeds; for benchmark groups the five-seed protocol is mandatory.
3. Match the metric to the task and to the benchmark's defined metric.
4. Filter PAINS / non-drug-like molecules before training.
5. Batch molecule conversion and cache the result; convert once, reuse.

References: <https://tdc.readthedocs.io> ·
<https://tdcommons.ai/functions/data_split/> ·
<https://tdcommons.ai/functions/model_eval/>
