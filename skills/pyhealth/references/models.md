# Models

PyHealth ships 30+ models behind one constructor contract. General-purpose nets
cover most tasks; healthcare-specific models add interpretability, DDI-aware drug
safety, or stage/signal structure.

## Shared Constructor Contract

Every model reads its inputs from the `SampleDataset` by name:

```python
model = ModelClass(
    dataset=sample_dataset,      # the SampleDataset from set_task
    feature_keys=["conditions", "procedures", "drugs"],  # keys the task emitted
    label_key="label",           # the task's label key
    mode="binary",               # binary | multiclass | multilabel | regression
    # ...model-specific hyperparameters (embedding_dim, hidden_dim, ...)
)
```

`mode` must match the task's label type — it selects the output head, loss, and
metric family. Omitting `label_key` (as some older snippets do) fails on models
that need it; always pass it.

## General-Purpose Models

- **`LogisticRegression`** — linear classifier over pooled embeddings. Your
  first baseline; fast and interpretable.
- **`MLP`** — feedforward net (`hidden_dim`, `num_layers`, `dropout`, pooling).
  Baseline for structured features.
- **`CNN`** — 1D convolutions for local temporal/spatial patterns; parameter
  efficient (`num_filters`, `kernel_size`, `num_layers`).
- **`TCN`** — dilated causal convolutions for long sequences without RNN cost.
- **`RNN`** — LSTM/GRU/RNN variants (`rnn_type`, `hidden_dim`, `bidirectional`);
  strong on variable-length clinical event sequences.
- **`Transformer`** — multi-head self-attention; good default for long-range
  dependencies (`embedding_dim`, `num_heads`, `num_layers`, `dropout`). Memory is
  quadratic in sequence length.
- **`GNN`** — graph learning (GAT/GCN) for drug interactions, patient-similarity,
  or knowledge-graph structure.

For clinical **text**, PyHealth integrates pretrained language models (BERT /
ClinicalBERT-family) for coding and classification. Exact class name and the
`pretrained_model` argument vary by version — verify in `pyhealth.models`; for
standalone LLM fine-tuning use `transformers`.

## Healthcare-Specific Models

### Interpretable EHR

- **`RETAIN`** — reverse-time two-level attention; exposes **visit-level** and
  **feature-level** attention so you can point at the codes driving a risk score.
  Strong default when a clinician must trust the output.
- **`AdaCare`** — adaptive feature calibration with disease-specific attention;
  handles irregular intervals.
- **`ConCare`** — cross-visit convolutional/self-attention for longitudinal EHR.

### DDI-aware drug recommendation (all `mode="multilabel"`)

- **`GAMENet`** — graph + memory network over drug knowledge and patient history,
  drug-drug-interaction aware.
- **`SafeDrug`** — molecular-structure encoding plus a DDI constraint to trade
  efficacy against interaction risk.
- **`MICRON`** — medication change modeling with interaction constraints.
- **`MoleRec`** — molecular-substructure-level recommendation.

These consume additional resources (DDI adjacency, molecule graphs). Argument
names for those paths differ across versions — check the model's docstring.

### Stage / sequence / signal

- **`StageNet`** — stage-aware LSTM with time decay; chronic-disease progression
  and ICU mortality.
- **`Deepr`**, **`GRASP`**, **`Agent`** — additional sequential / graph / RL-style
  architectures.
- **`SparcNet`** — the standard net for biosignal tasks (e.g. sleep staging with
  `feature_keys=["signal"]`).
- **`ContraWR`** — contrastive self-supervised pretraining for limited-label
  signal data.

### Generative

- **`GAN`**, **`VAE`** — synthetic-EHR generation and representation learning.

Treat this list as a map; confirm each class exists in your installed version
before relying on it.

## Selecting a Model

By **task**:

- Binary (mortality, readmission): `LogisticRegression` baseline -> `RNN` /
  `Transformer` -> interpretable `RETAIN` / `AdaCare` -> `StageNet`.
- Multilabel (drug recommendation): `GAMENet`, `SafeDrug`, `MICRON`, `MoleRec`,
  or `GNN`.
- Regression (length of stay): `MLP` baseline -> `RNN` / `TCN` / `Transformer`.
- Multiclass (coding, specialty, sleep stage): `CNN` / `RNN` / `Transformer`;
  `SparcNet` for signals; pretrained text models for notes.

By **data type**: sequential events -> RNN / Transformer / RETAIN; time-series
signals -> CNN / TCN / SparcNet; text -> pretrained transformers; graphs ->
GNN / GAMENet / SafeDrug; images -> CNN / vision transformers.

By **interpretability need**: high -> `LogisticRegression`, `RETAIN`, `AdaCare`,
`SparcNet`; moderate (post-hoc attention or `shap`) -> `CNN`, `Transformer`,
`GNN`; black-box acceptable -> deep RNN / ensembles.

## Hyperparameter Starting Points

- `embedding_dim`: 64-128 (small data), 128-256 (large), up to 512 (complex).
- `hidden_dim`: ~1-2x `embedding_dim`.
- `num_layers`: start 2-3; go deeper only if val metrics improve.
- `dropout`: start 0.5; lower (0.1-0.3) if underfitting, raise if overfitting.

Always establish a `LogisticRegression` or `MLP` baseline before a deep model —
if the baseline is competitive, the extra capacity is not earning its keep. See
`references/training-evaluation.md` for training and evaluation.
