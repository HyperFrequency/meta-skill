# DeepChem Workflows

End-to-end recipes for common tasks. Each follows the same pipeline —
**load → featurize → split → train → evaluate/predict** — and only swaps the
class at each stage. Verify constructor keywords against the DeepChem docs for
anything version-sensitive (pretrained models and materials loaders especially).

## 1. Property prediction from a custom CSV

Input CSV needs a SMILES column plus one or more target columns:

```csv
smiles,solubility
CCO,-0.77
CC(=O)OC1=CC=CC=C1C(=O)O,-1.19
```

```python
import deepchem as dc

# 1. load + featurize
featurizer = dc.feat.CircularFingerprint(radius=2, size=2048)
loader = dc.data.CSVLoader(tasks=["solubility"], feature_field="smiles", featurizer=featurizer)
dataset = loader.create_dataset("data.csv")

# 2. split without structural leakage
train, valid, test = dc.splits.ScaffoldSplitter().train_valid_test_split(
    dataset, frac_train=0.8, frac_valid=0.1, frac_test=0.1
)

# 3. normalize the target (fit on train, apply to all, keep for inverse-transform)
transformers = [dc.trans.NormalizationTransformer(transform_y=True, dataset=train)]
for t in transformers:
    train, valid, test = t.transform(train), t.transform(valid), t.transform(test)

# 4. train
model = dc.models.MultitaskRegressor(
    n_tasks=1, n_features=2048, layer_sizes=[1000, 500], dropouts=0.25, learning_rate=1e-3
)
model.fit(train, nb_epoch=50)

# 5. evaluate (pass transformers so scores are in real units)
metric = dc.metrics.Metric(dc.metrics.r2_score)
print("test R^2:", model.evaluate(test, [metric], transformers))
```

### Predicting new molecules

Featurize with the **same** featurizer and apply the **same** transformers:

```python
X = featurizer.featurize(["CCO", "c1ccccc1", "CC(C)O"])
new = dc.data.NumpyDataset(X=X)
for t in transformers:
    new = t.transform(new)
preds = model.predict(new, transformers)   # inverse-transformed back to real units
```

## 2. Benchmark evaluation with a graph neural network

```python
tasks, datasets, transformers = dc.molnet.load_tox21(featurizer="GraphConv", splitter="scaffold")
train, valid, test = datasets

model = dc.models.GCNModel(n_tasks=len(tasks), mode="classification", batch_size=128, learning_rate=1e-3)
model.fit(train, nb_epoch=50)

metric = dc.metrics.Metric(dc.metrics.roc_auc_score)
print("test ROC-AUC:", model.evaluate(test, [metric], transformers))
```

Swap `GCNModel` for `GATModel`, `AttentiveFPModel`, or `DMPNNModel` to compare
architectures. For regression benchmarks use `mode="regression"` and an
`r2_score`/`mean_absolute_error` metric on `load_delaney`, `load_freesolv`, etc.

## 3. Hyperparameter search

```python
tasks, datasets, transformers = dc.molnet.load_bbbp(featurizer="ECFP", splitter="scaffold")
train, valid, test = datasets

params = {
    "layer_sizes": [[1000], [1000, 500]],
    "dropouts": [0.25, 0.5],
    "learning_rate": [1e-3, 1e-4],
}

def model_builder(model_params, model_dir):
    return dc.models.MultitaskClassifier(n_tasks=len(tasks), n_features=1024, **model_params)

metric = dc.metrics.Metric(dc.metrics.roc_auc_score)
opt = dc.hyper.GridHyperparamOpt(model_builder)
best_model, best_params, all_results = opt.hyperparam_search(
    params, train, valid, metric, transformers=transformers
)
print(best_params)
```

## 4. Transfer learning with a pretrained chemical LM

Fine-tuning a model pretrained on millions of molecules often beats training from
scratch on a small or novel dataset. Use a low learning rate and few epochs, and
feed raw SMILES (let the model tokenize):

```python
loader = dc.data.CSVLoader(
    tasks=["activity"], feature_field="smiles", featurizer=dc.feat.DummyFeaturizer()
)
dataset = loader.create_dataset("small_dataset.csv")
train, test = dc.splits.ScaffoldSplitter().train_test_split(dataset)
```

DeepChem exposes ChemBERTa / MoLFormer through `HuggingFaceModel` and dedicated
classes (`Chemberta`, `MoLFormer`). The constructor takes a Hugging Face model
object and tokenizer plus a `task`, and the exact signature changes between
releases — **check the DeepChem source/docs and the `transformers` sibling skill
before wiring it**, rather than assuming a name-string API. Once constructed, the
training loop is the usual `model.fit(train, nb_epoch=10)` /
`model.predict(test)`.

Use transfer learning when: the labeled set is small (<~1K), the chemistry is
novel, or you need a quick prototype.

## 5. Molecular generation with MolGAN

```python
import deepchem as dc

tasks, datasets, _ = dc.molnet.load_qm9(featurizer="GraphConv", splitter="random")
train, _, _ = datasets

gan = dc.models.BasicMolGANModel(learning_rate=1e-3, vertices=9)   # vertices = max atoms
gan.fit_gan(train, nb_epoch=100, generator_steps=0.2, checkpoint_interval=10)

generated = gan.predict_gan_generator(1000)   # sample new molecular graphs
```

`vertices`/`edges`/`nodes` and the conditional-generation options vary by version
— confirm before relying on specific keywords. Post-process generated graphs back
to valid molecules (RDKit sanitization) before using them.

## 6. Materials property prediction

Crystal/materials models (`CGCNNModel`, `MEGNetModel`) consume structure-based
representations rather than SMILES. The concrete loader/featurizer for CIF or
Materials-Project structures differs across DeepChem versions, so consult the
current materials tutorial before building the input pipeline. The training shape
is unchanged:

```python
model = dc.models.CGCNNModel(n_tasks=1, mode="regression", batch_size=32, learning_rate=1e-3)
model.fit(train, nb_epoch=100)
score = model.evaluate(test, [dc.metrics.Metric(dc.metrics.mean_absolute_error)])
```

MoleculeNet also offers ready materials datasets: `load_bandgap`,
`load_perovskite`, `load_mp_formation_energy`, `load_mp_metallicity`.

## 7. Protein sequence analysis

```python
loader = dc.data.FASTALoader()
dataset = loader.create_dataset("proteins.fasta")
train, test = dc.splits.RandomSplitter().train_test_split(dataset)

# ProtBERT via the Hugging Face wrapper (verify constructor as in workflow 4)
model = dc.models.HuggingFaceModel(model=..., tokenizer=..., task="classification", n_tasks=1)
model.fit(train, nb_epoch=5)
preds = model.predict(test)
```

For richer protein modeling (generation, embeddings, structure), prefer the `esm`
sibling skill; DeepChem's protein path is convenient mainly when you want it in
the same dataset/metric harness as your molecular models.

## 8. Wrapping your own model

### scikit-learn

```python
from sklearn.ensemble import RandomForestRegressor
model = dc.models.SklearnModel(model=RandomForestRegressor(n_estimators=100, random_state=42))
model.fit(train)
model.evaluate(test, [dc.metrics.Metric(dc.metrics.r2_score)])
```

### custom PyTorch module

```python
import torch.nn as nn

net = nn.Sequential(nn.Linear(2048, 512), nn.ReLU(), nn.Dropout(0.2), nn.Linear(512, 1))
model = dc.models.TorchModel(model=net, loss=nn.MSELoss(), output_types=["prediction"])
model.fit(train, nb_epoch=50)
```

## Recurring pitfalls

- **Random split on molecules** inflates metrics — default to `ScaffoldSplitter`.
- **Imbalanced classification** — apply `BalancingTransformer(dataset=train)` or a
  balanced metric.
- **Out-of-memory** — use `DiskDataset.from_numpy(...)` and a smaller `batch_size`.
- **GNN worse than fingerprints** — usually too little data (<10K) or too few
  epochs; try `AttentiveFPModel`/`DMPNNModel` or a pretrained model.
- **Errors reported in normalized space** — pass `transformers` into
  `evaluate`/`predict`.
