# Molfeat API Reference

Class-by-class surface for the modules you touch most. See the
[official API docs](https://molfeat-docs.datamol.io/) for exhaustive signatures.

Top-level modules:

- `molfeat.calc` — per-molecule calculators
- `molfeat.trans` — batch transformers (sklearn-compatible)
- `molfeat.trans.pretrained` — transformers for pretrained deep models
- `molfeat.store` — model discovery / registration
- `molfeat.utils`, `molfeat.viz` — helpers and visualization

---

## molfeat.calc — Calculators

A calculator is a callable that maps one molecule (SMILES string or RDKit
`Chem.Mol`) to a 1-D feature array. Use a calculator directly only for a single
molecule or a hand-written loop; for batches, wrap it in a transformer.

### FPCalculator

Molecular fingerprints; supports 15+ methods selected by the first positional
`method` argument.

```python
from molfeat.calc import FPCalculator

calc = FPCalculator("ecfp", radius=3, fpSize=2048)
fp   = calc("CCO")        # np.ndarray, shape (2048,)
len(calc)                 # 2048
calc.columns              # feature/bit names
```

Common `method` values: `ecfp`, `ecfp-count`, `fcfp`, `fcfp-count`, `maccs`,
`avalon`, `rdkit`, `pattern`, `layered`, `atompair`, `atompair-count`,
`topological`, `topological-count`, `map4`, `secfp`, `erg`, `estate`.

Key parameters:

- `method` (str) — fingerprint name
- `radius` (int, default 2, i.e. ECFP4) — for circular fingerprints (ECFP/FCFP)
- `fpSize` (int, default 2048) — bit-vector length
- `includeChirality` (bool) — encode chirality
- `counting` (bool) — count vector instead of binary

Reference dimensions: MACCS 167, ECFP 2048 (default), MAP4 1024 (default).

### Descriptor calculators

```python
from molfeat.calc import RDKitDescriptors2D, RDKitDescriptors3D, MordredDescriptors

RDKitDescriptors2D()      # 200+ named 2D physchem descriptors
RDKitDescriptors3D()      # 3D descriptors — needs a molecule with a conformer
MordredDescriptors()      # 1800+ descriptors (needs the mordred package)
```

Descriptor calculators expose `.columns` (the named descriptor list), which is
what makes them useful for interpretable models.

### Pharmacophore & shape calculators

```python
from molfeat.calc import CATS, USRDescriptors, ElectroShapeDescriptors
from molfeat.calc import Pharmacophore2D, Pharmacophore3D

CATS(scale="raw")                        # 2D CATS pharmacophore-pair distributions
CATS(use_3d_distances=True)              # 3D CATS — needs a molecule with a conformer
USRDescriptors()                         # ultrafast shape recognition (needs 3D)
ElectroShapeDescriptors()                # shape + chirality + electrostatics (needs 3D)
```

`CATS` parameters: `use_3d_distances` (bool — topological vs 3D distances; this
flag selects the 2D vs 3D variant), `max_dist`, `bins`, and `scale`
(`"raw"`/`"num"`/`"count"`). The 3D variant requires a generated conformer; call
`len(calc)` for the exact vector length.

### Graph-input calculators

For building GNN inputs (used by graph models rather than as flat vectors):

- `AtomCalculator` — atom-level features
- `BondCalculator` — bond-level features
- `ScaffoldKeyCalculator` — 40+ scaffold-based properties

### get_calculator — factory by name

```python
from molfeat.calc import get_calculator

calc = get_calculator("ecfp", radius=3)   # raises ValueError on unknown names
```

### SerializableCalculator (base class)

Base for custom calculators. Implement `__call__`; optionally `__len__`,
`columns`, and `batch_compute`. State methods: `to_state_dict()`,
`from_state_dict()`, `to_state_json()`, `to_state_yaml()`.

---

## molfeat.trans — Transformers

### MoleculeTransformer

Wraps a calculator into a parallel, sklearn-compatible batch featurizer.

```python
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator

featurizer = MoleculeTransformer(
    FPCalculator("ecfp"),
    n_jobs=-1,             # all cores
    dtype=None,            # e.g. np.float32 or torch.float32
    verbose=True,
    ignore_errors=True,    # failed molecules -> None instead of raising
)
X = featurizer(smiles)     # __call__ == transform
```

Key parameters: `featurizer`, `n_jobs`, `dtype`, `verbose`, `ignore_errors`.

Methods:

- `transform(mols)` / `__call__(mols)` — batch featurize
- `preprocess(mol)` — hook you override for standardization (not auto-applied)
- `to_state_yaml_file(path)` / `from_state_yaml_file(path)`
- `to_state_json_file(path)` / `from_state_json_file(path)`

`.featurizer.columns` gives the underlying feature names (for descriptor-based
transformers), useful for coefficient interpretation.

### FeatConcat

Concatenates several fingerprint featurizers into one representation. It accepts
**fingerprint names** (or `FPVecTransformer` instances) — not raw calculators —
and is itself a batch transformer, so call it directly; do not wrap it in a
`MoleculeTransformer`.

```python
import numpy as np
from molfeat.trans import FeatConcat

featurizer = FeatConcat(["maccs", "ecfp"], dtype=np.float32)   # 167 + 2048
X = featurizer(smiles)                                         # -> (n, 2215)

# per-featurizer parameters go through `params=`:
featurizer = FeatConcat(["maccs", "ecfp"], params={"ecfp": {"radius": 3}})
```

---

## molfeat.trans.pretrained — Pretrained Transformers

Constructed with `kind="<model-name>"` (they do not wrap a calculator). They add
batched inference and caching. Each family needs its optional extra installed.

### PretrainedHFTransformer (HuggingFace)

```python
from molfeat.trans.pretrained import PretrainedHFTransformer

t = PretrainedHFTransformer(
    kind="ChemBERTa-77M-MLM",   # or ChemGPT-1.2B / -19M / -4.7M, MolT5, Roberta-Zinc480M
    notation="smiles",          # use "selfies" for ChemGPT-style models
    pooling="bert",             # pooling strategy, e.g. "bert" / "mean"
    preload=True,
)
emb = t(smiles)                 # (n, 768) for ChemBERTa
```

Import path is also `molfeat.trans.pretrained.hf_transformers.PretrainedHFTransformer`.

### PretrainedDGLTransformer (graph neural nets)

```python
from molfeat.trans.pretrained import PretrainedDGLTransformer

t = PretrainedDGLTransformer(kind="gin_supervised_masking")
# other kinds: gin_supervised_infomax, gin_supervised_edgepred,
#              gin_supervised_contextpred, jtvae_zinc_no_kl
```

Note the DGL `kind` names use underscores. Needs `molfeat[dgl]`.

### GraphormerTransformer / FCDTransformer

`GraphormerTransformer` loads Graphormer quantum-chemistry embeddings
(`molfeat[graphormer]`); `FCDTransformer` loads Fréchet ChemNet features
(`molfeat[fcd]`).

### PrecomputedMolTransformer

Serves already-computed features from a cache/store instead of recomputing.

---

## molfeat.store — Model Store

### ModelStore

```python
from molfeat.store.modelstore import ModelStore

store = ModelStore()               # default read-only store
store.available_models             # list every registered featurizer (ModelCards)
results = store.search(name="ChemBERTa-77M-MLM")
card = results[0]
card.usage()                       # print a runnable usage snippet
transformer = store.load("ChemBERTa-77M-MLM")
```

Point at a custom location with `ModelStore(model_store_root=path)` and register
your own featurizers with `store.register(...)`.

`ModelCard` attributes: `name`, `description`, `version`, `authors`, `tags`,
`usage()`, `load(**kwargs)`.

---

## Common Patterns

**Error tolerance** — `MoleculeTransformer(calc, ignore_errors=True, verbose=True)`;
failed molecules return `None`.

**Dtype control** — pass `dtype=np.float32` (memory) or `dtype=torch.float32`
(PyTorch tensors) to the transformer.

**Persistence** — `to_state_yaml_file(path)` / `from_state_yaml_file(path)` (or
the JSON variants) round-trip the exact featurizer configuration.

**Performance** — `n_jobs=-1` for all cores; batch rather than loop; prefer
`float32`; let pretrained models use their built-in cache.
