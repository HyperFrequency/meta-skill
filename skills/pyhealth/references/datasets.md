# Datasets and the Data Model

PyHealth normalizes every source into one object graph, then converts it into
task-specific samples. Understand the graph first; the rest of the library reads
from it.

## The Patient / Visit / Event Graph

A dataset is a collection of **patients**; each patient holds ordered
**visits**; each visit holds **events**.

- **Event** — one atomic clinical occurrence. Core fields: `code` (the medical
  code), `vocabulary` / table (the coding system, e.g. `ICD9CM`, `NDC`,
  `LOINC`), a timestamp, and for measurements an optional numeric `value` and
  `unit`.
- **Visit** — one encounter: `visit_id`, admission/discharge times, encounter
  type (inpatient / outpatient / emergency), and the events recorded during it.
- **Patient** — `patient_id`, demographics (birth datetime, gender, ethnicity),
  and the chronological visit list.

Base-dataset methods you will use: iterate patients, fetch a single patient by
id, print `stats()` (patient / visit / event counts and code distributions), and
`set_task(task_fn)` to project the graph into model-ready samples.

```python
dataset = MIMIC4Dataset(root="/path/to/mimic4")
print(dataset.stats())                 # sanity-check scale + code coverage
```

Always run `stats()` before modeling — it exposes empty tables, unexpected code
vocabularies, and class-prevalence surprises early.

## Dataset Catalogue

### EHR (structured events)

| Class | Source | Notes |
|---|---|---|
| `MIMIC3Dataset` | Beth Israel ICU | ~40k critical-care patients |
| `MIMIC4Dataset` | Beth Israel ICU (v4) | larger, better coverage than v3 |
| `eICUDataset` | multi-center ICU | 200k+ admissions, hospital-level variation |
| `OMOPDataset` | OMOP CDM | standardized common data model, portable |
| `EHRShotDataset` | few-shot benchmark | for generalization / few-shot studies |
| `MIMICExtractDataset` | pre-extracted MIMIC features | reduced preprocessing |

### Physiological signals

- Sleep staging: `SleepEDFDataset`, `SHHSDataset`, `ISRUCDataset` (multi-channel
  EEG, standard sampling rates, expert stage annotations).
- Temple University EEG corpus: `TUABDataset` (abnormal vs normal),
  `TUEVDataset` (event types), `TUSZDataset` (seizure).

### Imaging and text

- `COVID19CXRDataset` — chest X-rays, multi-class (COVID / pneumonia / normal).
- `MedicalTranscriptionsDataset` — clinical notes for specialty classification.
- `CardiologyDataset` — cardiac records.

Dataset availability and exact constructor arguments vary by PyHealth version and
require the underlying data on disk (MIMIC/eICU are credentialed — you download
them yourself). Confirm the class exists in your installed version.

## From Raw Dataset to SampleDataset

`set_task` runs a task function over every patient and returns a
`SampleDataset` — a flat list of `{patient_id, visit_id, <feature_keys>, <label>}`
samples with an inferred input/output schema. Models read `feature_keys` and
`label_key` directly from this object, which is why constructing a model needs
`dataset=sample_dataset`.

```python
sample_dataset = dataset.set_task(mortality_prediction_mimic4_fn)
print(len(sample_dataset))             # number of generated samples
print(sample_dataset.samples[0])       # inspect one sample's shape
```

See `references/tasks.md` for the task functions and their emitted schema.

## Splitting — the Leakage Boundary

| Function | Guarantee | Use |
|---|---|---|
| `split_by_patient` | no patient spans splits | **default for clinical prediction** |
| `split_by_visit` | splits by encounter | same patient may recur — use with care |
| `split_by_sample` | random over samples | most leakage-prone; benchmarks only |

```python
from pyhealth.datasets import split_by_patient
train_ds, val_ds, test_ds = split_by_patient(sample_dataset, [0.7, 0.1, 0.2])
```

Some versions accept a `seed`; set it for reproducibility. For temporal
validation (train on earlier admissions, test on later), split by admission time
yourself rather than randomly — random splits overstate prospective performance.

## Batching

`get_dataloader` wraps a split in a PyTorch `DataLoader` with PyHealth's collate
(it pads variable-length event sequences for you):

```python
from pyhealth.datasets import get_dataloader
train_loader = get_dataloader(train_ds, batch_size=64, shuffle=True)
```

Shuffle **train** only; keep val/test unshuffled so predictions align with labels
and patient ids.

## Failure Modes

- **Empty `SampleDataset`** after `set_task` — the task's inclusion filter
  dropped every patient (e.g. it requires >= 2 visits and your cohort is
  single-visit). Print `stats()` and re-read the task's filter logic.
- **Out-of-memory on load** — large EHR sets are tens of GB; load a subset or use
  `MIMICExtractDataset`.
- **Wrong `vocabulary`** on events — downstream `medcode` maps will silently
  return nothing; verify with `stats()`.
