# Clinical Prediction Tasks

A task is the contract between a dataset and a model: it walks each patient and
emits samples with named feature fields and a label, and it decides the
prediction `mode`. Pick a predefined task for standardized benchmarking; write a
custom one when your outcome or feature window differs.

## Applying a Task

```python
from pyhealth.tasks import mortality_prediction_mimic4_fn
sample_dataset = dataset.set_task(mortality_prediction_mimic4_fn)
```

Recent PyHealth versions also expose task **classes** (e.g. a
`MortalityPrediction*` class you instantiate and pass to `set_task`) alongside
the `*_fn` functions. Both express the same contract; check which your version
ships and keep the code and the model's `mode` consistent.

## Predefined EHR Tasks and Their Mode

| Task family | Example function | mode | Label |
|---|---|---|---|
| Mortality (next visit) | `mortality_prediction_mimic3_fn`, `mortality_prediction_mimic4_fn`, `mortality_prediction_eicu_fn`, `mortality_prediction_omop_fn` | binary | deceased / alive |
| In-hospital mortality | `inhospital_mortality_prediction_mimic4_fn` | binary | dies this stay |
| 30-day readmission | `readmission_prediction_mimic3_fn` / `_mimic4_fn` / `_eicu_fn` / `_omop_fn` | binary | readmitted |
| Length of stay | `length_of_stay_prediction_mimic3_fn` / `_mimic4_fn` / `_eicu_fn` / `_omop_fn` | regression (or binned multiclass) | days |
| Drug recommendation | `drug_recommendation_mimic3_fn` / `_mimic4_fn` / `_eicu_fn` / `_omop_fn` | multilabel | set of drug codes |
| ICD coding from notes | `icd9_coding_mimic3_fn` | multilabel | set of ICD codes |

Function names track dataset and version; confirm the exact symbol in
`pyhealth.tasks` for your install.

## Signal, Imaging, and Text Tasks

- **Sleep staging** — `sleep_staging_isruc_fn`, `sleep_staging_sleepedf_fn`,
  `sleep_staging_shhs_fn`. `multiclass` over Wake / N1 / N2 / N3 / REM, one label
  per 30-second epoch. Feature key is typically `"signal"`.
- **EEG** — abnormality detection (`abnormality_detection_tuab_fn`, binary),
  event detection (`event_detection_tuev_fn`, multiclass), seizure detection
  (`seizure_detection_tusz_fn`, binary).
- **Imaging** — `covid_classification_cxr_fn` (multiclass over COVID / pneumonia
  / normal).
- **Text** — `medical_transcription_classification_fn` (specialty, multiclass);
  ICD coding above.

## Writing a Custom Task

A task function takes one patient and returns a list of sample dicts. Each dict
carries `patient_id`, an optional `visit_id`, one key per feature you want the
model to read, and one label key. Filter out patients without enough history.

```python
def my_readmission_task_fn(patient):
    samples = []
    visits = patient.visits
    for i in range(1, len(visits)):          # need >= 1 prior visit
        prior = visits[:i]
        conditions, drugs = [], []
        for v in prior:
            for e in v.events:
                if e.vocabulary == "ICD10CM":
                    conditions.append(e.code)
                elif e.vocabulary == "NDC":
                    drugs.append(e.code)
        if not conditions:                    # skip empty inputs
            continue
        label = 1 if readmitted_within(visits[i], days=30) else 0
        samples.append({
            "patient_id": patient.patient_id,
            "visit_id": visits[i].visit_id,
            "conditions": conditions,          # -> feature_keys=["conditions", ...]
            "drugs": drugs,
            "label": label,                    # -> label_key="label"
        })
    return samples

sample_dataset = dataset.set_task(my_readmission_task_fn)
```

The feature dict keys you emit are exactly the strings you later pass as
`feature_keys`, and your label key is the model's `label_key`. Exact sample-dict
conventions differ slightly across versions — mirror a shipped `*_fn` for your
version.

### Design checklist

1. **Temporal window** — only use events available at prediction time; leaking a
   future visit's codes into the input inflates every metric.
2. **Inclusion filter** — drop patients/visits with insufficient history and
   document the rule (it defines your cohort).
3. **Label type fixes `mode`** — binary flag, mutually exclusive class,
   multi-hot set, or continuous value.
4. **Preserve ids** — keep `patient_id` so `split_by_patient` works and you can
   trace a prediction back to a record.

## Class Imbalance

Mortality and readmission are rare-positive. This is a task-level fact with
downstream consequences: monitor `pr_auc`, not `accuracy` (see
`references/training-evaluation.md`), and consider class weighting. Do not "fix"
imbalance by oversampling across the patient-split boundary.
