# Training, Evaluation, Calibration, and Interpretability

The `Trainer` runs the loop; `get_metrics_fn` / the `*_metrics_fn` family score
predictions; `pyhealth.calib` makes probabilities trustworthy. For clinical use,
calibration and fairness are not optional extras.

## Trainer

Construct with the model and the metrics to track, then call `train`:

```python
from pyhealth.trainer import Trainer, get_metrics_fn

trainer = Trainer(model=model, metrics=["pr_auc", "roc_auc", "f1", "accuracy"])
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=50,
    monitor="pr_auc",                 # metric used to pick the best checkpoint
    monitor_criterion="max",          # "max" for AUC/F1, "min" for loss/error
    optimizer_params={"lr": 1e-3},    # optimizer kwargs go in this dict
)
```

Notes that differ from naive expectations:

- Metrics are passed to the **constructor**; `monitor` selects which one drives
  checkpointing.
- Learning rate lives inside **`optimizer_params`**, not as a top-level `lr=`
  kwarg. The optimizer class is configurable (Adam by default in most versions).
- The Trainer checkpoints the best model by `monitor`, supports early stopping,
  and handles device placement. Confirm the exact keyword names against your
  version for anything you script.

### Inference returns a tuple

```python
y_true, y_prob, loss = trainer.inference(test_loader)
```

`inference` returns `(y_true, y_prob, loss)`, or a 4-tuple
`(y_true, y_prob, loss, extra_output)` when you request extras:

```python
y_true, y_prob, loss, extra = trainer.inference(
    test_loader, additional_outputs=["y_predset"]     # e.g. conformal sets
)
```

It does **not** return a dict keyed by `y_pred` — index the tuple positionally.

## Metrics

Compute metrics with the mode-appropriate function. `get_metrics_fn(model.mode)`
returns the right one; the family members can also be imported directly.

```python
from pyhealth.metrics import binary_metrics_fn
print(binary_metrics_fn(y_true, y_prob, metrics=["pr_auc", "roc_auc", "f1"]))
```

| mode | function | representative metric keys |
|---|---|---|
| binary | `binary_metrics_fn` | `pr_auc`, `roc_auc`, `f1`, `accuracy`, `precision`, `recall`, `cohen_kappa` |
| multiclass | `multiclass_metrics_fn` | `accuracy`, `f1_macro`, `f1_micro`, `f1_weighted`, `cohen_kappa` |
| multilabel | `multilabel_metrics_fn` | `pr_auc_samples`, `jaccard_samples`, `f1_samples`, `hamming_loss` |
| regression | `regression_metrics_fn` | `mae`, `mse`, `rmse`, `r2` |

The metric keys are bare names (`pr_auc`, `roc_auc`, `f1`) — **not**
`pr_auc_score` / `roc_auc_score`. If no `metrics` list is given, binary defaults
to `["pr_auc", "roc_auc", "f1"]`. Exact multilabel/multiclass key spellings vary
by version; check the metrics module docstring.

**Which to trust:** for imbalanced binary outcomes lead with **AUPRC**
(`pr_auc`) — AUROC looks deceptively high when positives are rare. For imbalanced
multiclass use `f1_macro`. Report a confidence interval (bootstrap) rather than a
point estimate.

## Calibration (`pyhealth.calib`)

A raw 0.8 output is a score, not an 80% risk. Calibrate by wrapping the trained
model, calibrating on a held-out set, then running inference through the wrapper:

```python
from pyhealth.calib import calibration
from pyhealth.trainer import Trainer, get_metrics_fn

cal_model = calibration.KCal(model, debug=True, dim=32)   # or TemperatureScaling, etc.
cal_model.calibrate(cal_dataset=val_dataset)

y_true, y_prob = Trainer(model=cal_model).inference(test_loader)[:2]
print(get_metrics_fn(cal_model.mode)(y_true, y_prob,
      metrics=["accuracy", "f1_macro", "cwECEt_adapt"]))   # ECE-style calibration metric
```

`pyhealth.calib.calibration` offers several methods (temperature scaling,
histogram binning, Dirichlet, KCal, ...). The calibration set should be
exchangeable with the test set and separate from any set used to pick the
checkpoint.

## Conformal Prediction Sets

For coverage guarantees (return a *set* of labels that contains the truth with,
say, 90% probability), use `pyhealth.calib.predictionset`:

```python
from pyhealth.calib.predictionset import LABEL
from pyhealth.trainer import Trainer, get_metrics_fn

cal_model = LABEL(model, [0.15, 0.15, 0.15, 0.15, 0.15])   # per-class miscoverage
cal_model.calibrate(cal_dataset=cal_data)

y_true, y_prob, _, extra = Trainer(model=cal_model).inference(
    test_loader, additional_outputs=["y_predset"])
print(get_metrics_fn(cal_model.mode)(
      y_true, y_prob, metrics=["accuracy", "miscoverage_ps"],
      y_predset=extra["y_predset"]))
```

Coverage is evaluated with `miscoverage_ps` (and set-size metrics), passing the
prediction sets back into the metrics function via `y_predset`.

## Uncertainty (model-agnostic)

- **MC dropout** — keep dropout active at inference, run N forward passes, use the
  mean as the prediction and the standard deviation as uncertainty.
- **Deep ensemble** — train several models with different seeds; disagreement is
  the uncertainty. More reliable than MC dropout, N× the cost.

## Fairness

Evaluate metrics **within** demographic subgroups; a strong aggregate can hide a
subgroup failure. Compare true-positive rate, PPV, and prevalence-of-positive
prediction across groups (gender, race, age band):

```python
from sklearn.metrics import recall_score
male, female = demo == "male", demo == "female"
tpr_gap = abs(recall_score(y_true[male], y_pred[male])
              - recall_score(y_true[female], y_pred[female]))
```

Meaningful gaps (demographic-parity, equalized-odds, equal-opportunity
disparities) are a deployment blocker, not a footnote.

## Interpretability

- **RETAIN** exposes visit-level and feature-level attention — request the extra
  outputs at inference and read off which visits and codes drove a score. This is
  PyHealth's most clinically legible explanation.
- **Attention** from `Transformer` gives a coarser view of which positions
  mattered.
- For everything else, use post-hoc, model-agnostic explanations via `shap`
  (see the `shap` skill) or permutation importance from `scikit-learn`. Prefer a
  natively interpretable model (`RETAIN`, `AdaCare`, `LogisticRegression`) when a
  clinician must sign off, rather than bolting on explanations after the fact.

## Deployment Checklist

1. **Split by patient** and validate externally (different site or time period).
2. **Calibrate** and confirm ECE is low before quoting probabilities as risk.
3. **Quantify uncertainty** so low-confidence cases can defer to a human.
4. **Audit fairness** across subgroups.
5. **Explain** predictions (attention / `shap`).
6. **Respect privacy** — de-identified data only, HIPAA/GDPR compliant.

## Troubleshooting

- **Metric key error** — you used `pr_auc_score`; the key is `pr_auc`.
- **`inference()` unpacking error** — it returns a tuple, not a dict; use
  `y_true, y_prob, loss = trainer.inference(...)`.
- **AUROC high, model useless** — imbalanced data; switch to AUPRC and tune the
  threshold.
- **OOM in training** — lower batch size, cap sequence length, or use a lighter
  model (`CNN` over `Transformer`).
- **Probabilities look wrong as risk** — you skipped calibration.
