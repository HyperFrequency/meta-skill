# Molfeat Workflows

Copy-paste-adaptable recipes. All assume `smiles` is a list/array of SMILES
strings and, where relevant, `y` is the aligned target. Load example data with
`datamol`: `dm.data.freesolv()`, `dm.data.esol()`, etc.

---

## QSAR / QSPR model

Interpretable descriptors → linear model, with feature attribution.

```python
import numpy as np
from molfeat.trans import MoleculeTransformer
from molfeat.calc import RDKitDescriptors2D
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

featurizer = MoleculeTransformer(RDKitDescriptors2D(), n_jobs=-1, ignore_errors=True)
X = featurizer(smiles)
X = StandardScaler().fit_transform(X)

model = Ridge(alpha=1.0)
scores = cross_val_score(model, X, y, cv=5, scoring="r2")
print(f"R^2 = {scores.mean():.3f} +/- {scores.std():.3f}")

model.fit(X, y)
names = featurizer.featurizer.columns          # named descriptors
for idx in np.abs(model.coef_).argsort()[-10:][::-1]:
    print(f"{names[idx]}: {model.coef_[idx]:.3f}")

featurizer.to_state_yaml_file("qsar_featurizer.yml")   # pin config for deployment
```

For a fingerprint QSAR baseline swap in `FPCalculator("ecfp")` and a
`RandomForestRegressor` — no scaling needed.

---

## Virtual screening

Train on known actives/inactives, score a large library, take top hits.

```python
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator
from sklearn.ensemble import RandomForestClassifier

featurizer = MoleculeTransformer(FPCalculator("ecfp"), n_jobs=-1, ignore_errors=True)

X_train = featurizer(train_smiles)
clf = RandomForestClassifier(n_estimators=500, n_jobs=-1)
clf.fit(X_train, train_labels)                 # 1 = active, 0 = inactive

X_screen = featurizer(screening_library)       # e.g. 1M compounds
scores = clf.predict_proba(X_screen)[:, 1]
top_hits = [screening_library[i] for i in scores.argsort()[::-1][:1000]]
```

For libraries above ~100K compounds, featurize in chunks (see below).

---

## Similarity search

```python
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator
from sklearn.metrics.pairwise import cosine_similarity

calc = FPCalculator("ecfp")
query_fp = calc(query_smiles).reshape(1, -1)

featurizer = MoleculeTransformer(calc, n_jobs=-1)
db_fps = featurizer(database_smiles)

sims = cosine_similarity(query_fp, db_fps)[0]
for idx in sims.argsort()[-10:][::-1]:
    print(f"{database_smiles[idx]}  sim={sims[idx]:.3f}")
```

(For binary fingerprints, Tanimoto is the conventional metric; cosine is a fast
approximation. Use `rdkit`/`datamol` Tanimoto helpers when it matters.)

---

## Scikit-learn pipeline (featurize inside the estimator)

```python
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator

pipe = Pipeline([
    ("feat", MoleculeTransformer(FPCalculator("ecfp"), n_jobs=-1)),
    ("clf",  RandomForestClassifier(n_estimators=100)),
])
pipe.fit(smiles_train, y_train)                # fits on raw SMILES
pred = pipe.predict(smiles_test)
```

Grid-search featurizer + model together by prefixing param names with the step:

```python
from sklearn.model_selection import GridSearchCV
from sklearn.svm import SVC

pipe = Pipeline([
    ("feat", MoleculeTransformer(FPCalculator("ecfp"), n_jobs=-1)),
    ("clf",  SVC()),
])
grid = {"clf__C": [0.1, 1, 10], "clf__kernel": ["rbf", "linear"]}
search = GridSearchCV(pipe, grid, cv=5, n_jobs=-1).fit(smiles_train, y_train)
print(search.best_params_, search.best_score_)
```

---

## Benchmark several featurizers

```python
from molfeat.trans import MoleculeTransformer, FeatConcat
from molfeat.calc import FPCalculator, RDKitDescriptors2D
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

# Each value is already a batch transformer (callable on a list of SMILES).
# FeatConcat takes fingerprint *names* and is used directly, not wrapped.
candidates = {
    "ECFP":     MoleculeTransformer(FPCalculator("ecfp"), n_jobs=-1),
    "MACCS":    MoleculeTransformer(FPCalculator("maccs"), n_jobs=-1),
    "Desc2D":   MoleculeTransformer(RDKitDescriptors2D(), n_jobs=-1),
    "Combined": FeatConcat(["maccs", "ecfp"]),
}
for name, feat in candidates.items():
    clf = RandomForestClassifier(n_estimators=100).fit(feat(smiles_train), y_train)
    auc = roc_auc_score(y_test, clf.predict_proba(feat(smiles_test))[:, 1])
    print(f"{name}: AUC={auc:.3f}")
```

---

## Pretrained embeddings

```python
from molfeat.trans.pretrained import PretrainedHFTransformer, PretrainedDGLTransformer

chemberta = PretrainedHFTransformer(kind="ChemBERTa-77M-MLM", notation="smiles")
X = chemberta(smiles)                          # (n, 768)

chemgpt = PretrainedHFTransformer(kind="ChemGPT-4.7M", notation="selfies")
gin     = PretrainedDGLTransformer(kind="gin_supervised_masking")   # needs molfeat[dgl]
```

Or resolve by name through the store:

```python
from molfeat.store.modelstore import ModelStore
transformer = ModelStore().load("ChemBERTa-77M-MLM")
```

### Cache expensive embeddings

Molfeat caches internally, but persist the array for large libraries you reuse:

```python
import pickle
from pathlib import Path

cache = Path("chemberta_emb.pkl")
if cache.exists():
    emb = pickle.loads(cache.read_bytes())
else:
    emb = chemberta(smiles)
    cache.write_bytes(pickle.dumps(emb))
```

---

## PyTorch dataset

```python
import torch
from torch.utils.data import Dataset, DataLoader
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator

class MoleculeDataset(Dataset):
    def __init__(self, smiles, labels, featurizer):
        self.X = featurizer(smiles)            # featurize once, up front
        self.y = torch.tensor(labels, dtype=torch.float32)
    def __len__(self):  return len(self.y)
    def __getitem__(self, i):
        return torch.tensor(self.X[i], dtype=torch.float32), self.y[i]

featurizer = MoleculeTransformer(FPCalculator("ecfp"), n_jobs=-1)
loader = DataLoader(MoleculeDataset(smiles, y, featurizer), batch_size=32, shuffle=True)
```

---

## Custom preprocessing (standardize before featurizing)

`MoleculeTransformer.preprocess` is a hook, not auto-applied — override it, or
clean upstream with `datamol`.

```python
import datamol as dm
from molfeat.trans import MoleculeTransformer
from molfeat.calc import FPCalculator

class CleanTransformer(MoleculeTransformer):
    def preprocess(self, mol):
        if isinstance(mol, str):
            mol = dm.to_mol(mol)
        mol = dm.standardize_mol(mol)
        mol = dm.remove_salts(mol)
        return mol

featurizer = CleanTransformer(FPCalculator("ecfp"), n_jobs=-1)
```

For 3D descriptors, generate conformers first:

```python
import datamol as dm
from molfeat.calc import RDKitDescriptors3D

mol = dm.conformers.generate(dm.add_hs(dm.to_mol("CC(C)Cc1ccc(C)cc1C")), n_confs=1)
desc = RDKitDescriptors3D()(mol)
```

---

## Scale: chunked featurization

Bound memory on very large libraries.

```python
import numpy as np

def featurize_in_chunks(smiles, featurizer, chunk_size=10_000):
    out = []
    for i in range(0, len(smiles), chunk_size):
        out.append(featurizer(smiles[i:i + chunk_size]))
        print(f"{min(i + chunk_size, len(smiles))}/{len(smiles)}")
    return np.vstack(out)
```

---

## Troubleshooting

**Invalid SMILES.** Enable tolerance and filter, keeping `X`/`y` aligned:

```python
featurizer = MoleculeTransformer(FPCalculator("ecfp"), ignore_errors=True, verbose=True)
feats = featurizer(smiles)                     # failures come back as None
mask  = [f is not None for f in feats]
X = np.stack([f for f in feats if f is not None])
smiles_ok = [s for s, keep in zip(smiles, mask) if keep]
```

**Missing pretrained dependency.** Import/load errors for ChemBERTa/GIN/Graphormer
usually mean the extra is not installed — `uv pip install "molfeat[transformer]"`
(or `[dgl]`, `[graphormer]`, `[fcd]`, `[map4]`).

**3D descriptor returns nothing / errors.** The molecule has no conformer —
generate one (see custom preprocessing above) before calling `desc3D`, `cats3D`,
`usr`, or `electroshape`.

**Reproducibility.** Pin the featurizer and record the version:

```python
import molfeat
featurizer.to_state_yaml_file("config.yml")
print("molfeat", molfeat.__version__)
```
