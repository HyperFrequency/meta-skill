# DeepChem API Reference

Catalog of the core classes for each pipeline stage. Import everything from
`import deepchem as dc`. Class availability and constructor signatures shift
between releases — treat this as a map, and confirm exact keyword arguments
against the DeepChem docs (https://deepchem.readthedocs.io/) for anything
load-bearing.

## Data loaders (`dc.data`)

| Loader | Input | Notes |
|---|---|---|
| `CSVLoader` | CSV with a SMILES/id column | most common; `tasks=[...]`, `feature_field="smiles"`, `featurizer=...` |
| `UserCSVLoader` | CSV | user-specified column handling |
| `SDFLoader` | SDF structure files | 2D/3D molecular records |
| `JsonLoader` | JSON | structured records |
| `ImageLoader` | images | vision tasks |
| `FASTALoader` | FASTA | protein/DNA sequences |
| `FASTQLoader` | FASTQ | sequences with quality scores |
| `InMemoryLoader` | Python objects | featurize in-memory lists |

`loader.create_dataset(path)` returns a `Dataset`.

## Dataset classes

- `NumpyDataset` — in-memory arrays `(X, y, w, ids)`; convenient, memory-bound.
- `DiskDataset` — sharded on-disk storage for datasets that exceed RAM; build via
  `DiskDataset.from_numpy(X, y, w, ids)`.
- `ImageDataset` — image tensors.

`w` is the per-example/per-task weight matrix (used for masking missing labels in
multitask data and for class balancing).

## Splitters (`dc.splits`)

Molecule-aware (prevent structural leakage):

- `ScaffoldSplitter` — split by Bemis–Murcko scaffold. **Default for drug
  discovery.**
- `ButinaSplitter` — Butina fingerprint clustering.
- `FingerprintSplitter` — by fingerprint similarity.
- `MaxMinSplitter` — maximize train/test diversity.
- `MolecularWeightSplitter` — by molecular weight.

General:

- `RandomSplitter`, `IndexSplitter`, `SpecifiedSplitter`,
  `RandomStratifiedSplitter`, `SingletaskStratifiedSplitter`, `TaskSplitter`.

Each exposes `train_valid_test_split(dataset, frac_train=, frac_valid=, frac_test=)`
and `train_test_split(dataset)`.

## Transformers (`dc.trans`)

Fit on the training set, then apply to every split; pass the same list into
`evaluate`/`predict` so outputs are inverse-transformed.

- `NormalizationTransformer(transform_y=True, dataset=train)` — zero-mean/unit-std.
- `MinMaxTransformer`, `LogTransformer`, `PowerTransformer`, `CDFTransformer` —
  other feature/label scalings.
- `BalancingTransformer(dataset=train)` — reweight classes for imbalance.
- `FeaturizationTransformer`, `CoulombFitTransformer`, `DAGTransformer`,
  `RxnSplitTransformer` — task-specific.

## Featurizers (`dc.feat`)

### Fingerprints (traditional ML)

- `CircularFingerprint(radius=2, size=2048, useChirality=False)` — ECFP/Morgan.
- `MACCSKeysFingerprint` — 167 structural keys.
- `PubChemFingerprint` — 881-bit.
- `Mol2VecFingerprint` — learned embeddings.

### Descriptors

- `RDKitDescriptors` — ~200 physicochemical descriptors (MW, LogP, TPSA, H-donors/
  acceptors, …); interpretable.
- `MordredDescriptors` — very large descriptor set.
- `CoulombMatrix` — 3D interatomic-distance matrix.

### Graph (GNNs)

- `MolGraphConvFeaturizer` — graph-convolution inputs (GCN/GAT).
- `ConvMolFeaturizer` — classic GraphConv `ConvMol` objects.
- `WeaveFeaturizer` — Weave features.
- `DMPNNFeaturizer` — directed message-passing inputs.
- `EquivariantGraphFeaturizer` — geometry-aware.
- `GroverFeaturizer` — inputs for the pretrained GROVER transformer.

### Sequence / raw

- `SmilesToSeq`, `SmilesToImage`, `RawFeaturizer`, `DummyFeaturizer`
  (pass-through; use when the model tokenizes SMILES itself).

### Selection table

| Use case | Featurizer | Model family |
|---|---|---|
| Fast baseline | `CircularFingerprint` | RF, XGBoost, MLP |
| Interpretable | `RDKitDescriptors` | linear, RF |
| Graph neural net | `MolGraphConvFeaturizer` / `DMPNNFeaturizer` | GCN, GAT, DMPNN |
| Sequence model | `SmilesToSeq` / raw | LSTM, transformer |
| 3D / quantum | `CoulombMatrix` | specialized 3D nets |

## Models (`dc.models`)

All share `fit(dataset, nb_epoch=...)`, `predict(dataset)`,
`evaluate(dataset, metrics, transformers)`.

### Classical / boosting

- `SklearnModel(model=<any sklearn estimator>)` — wrap RF, SVM, Ridge, etc.
- `GBDTModel` — gradient-boosted trees (XGBoost/LightGBM backend).

### Fingerprint / descriptor nets

- `MultitaskRegressor`, `MultitaskClassifier` — shared-trunk MLPs over fixed-width
  features (`n_tasks`, `n_features`, `layer_sizes`, `dropouts`, `learning_rate`).
- `MultitaskFitTransformRegressor`.

### Graph neural networks

- `GCNModel`, `GATModel`, `AttentiveFPModel`, `DMPNNModel`, `MPNNModel`,
  `GraphConvModel` — most take `n_tasks`, `mode="classification"|"regression"`,
  `batch_size`, `learning_rate`.
- `GroverModel`, `MATModel` — graph transformers.

### Materials

- `CGCNNModel` (crystal graph conv), `MEGNetModel`, `LCNNModel`. Require
  structure-based featurization; check the docs for the current materials loaders/
  featurizers before wiring an input pipeline.

### Generative

- `BasicMolGANModel` (methods `fit_gan`, `predict_gan_generator`), `GANModel`,
  `WGANModel`, `SeqToSeqModel`, LSTM-based generators.

### Physics-informed / vision

- `PINNModel`, `HNNModel`, `FNOModel`; `CNN`, `UNetModel`, `InceptionV3Model`,
  `MobileNetV2Model`.

### Pretrained chemical / biological language models

- `HuggingFaceModel` — general wrapper; takes a Hugging Face model **object** plus
  a `tokenizer` and a `task`, not just a checkpoint name. Dedicated classes:
  `Chemberta`, `MoLFormer`, `ProtBERT`. Signatures change between releases —
  verify against the DeepChem source before use.

### Custom models

- `TorchModel(model=<nn.Module>, loss=..., output_types=["prediction"])` — wrap an
  arbitrary PyTorch module in the DeepChem training/eval interface.

## MoleculeNet datasets (`dc.molnet.load_*`)

Each returns `(tasks, (train, valid, test), transformers)` and accepts
`featurizer=` (`"ECFP"`, `"GraphConv"`, `"Weave"`, `"Raw"`, `"smiles2img"`),
`splitter=` (`"scaffold"`, `"random"`, `"stratified"`, `"butina"`), and
`reload=`.

- **Classification:** `load_tox21` (12 assays), `load_bbbp`, `load_bace`,
  `load_hiv`, `load_clintox`, `load_sider`, `load_muv`, `load_pcba`,
  `load_toxcast`.
- **Regression:** `load_delaney` (ESOL solubility), `load_freesolv`, `load_lipo`,
  `load_qm7` / `load_qm8` / `load_qm9` (quantum), `load_hopv`.
- **Binding:** `load_pdbbind`.
- **Materials:** `load_perovskite`, `load_mp_formation_energy`,
  `load_mp_metallicity`, `load_bandgap`.
- **Reactions:** `load_uspto`.

## Metrics (`dc.metrics`)

Wrap in `dc.metrics.Metric(fn, name=...)`.

- **Classification:** `roc_auc_score`, `prc_auc_score`, `accuracy_score`,
  `balanced_accuracy_score`, `recall_score`, `precision_score`, `f1_score`.
- **Regression:** `mean_absolute_error`, `mean_squared_error`,
  `root_mean_squared_error`, `r2_score`, `pearson_r2_score`,
  `spearman_correlation`.

Most metrics average over tasks for multitask datasets.

## Hyperparameter search (`dc.hyper`)

- `GridHyperparamOpt(model_builder)` — `model_builder(params, model_dir)` returns
  a fresh model; call `hyperparam_search(params_dict, train, valid, metric,
  transformers=...)` → `(best_model, best_params, all_results)`.
- `GaussianProcessHyperparamOpt` — Bayesian optimization alternative.
