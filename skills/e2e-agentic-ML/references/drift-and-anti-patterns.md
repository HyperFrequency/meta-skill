# Drift Detection + Anti-Patterns — Detailed Reference

Referenced from `SKILL.md`.

## Drift Detection Skeleton

A minimal drift monitor for Stage 11. Uses KS test for continuous features and PSI for distribution shift.

```python
# stage11_drift.py — daily drift check on a deployed model's features.
import numpy as np, polars as pl
from scipy.stats import ks_2samp

def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index. > 0.25 = significant shift, action required."""
    cuts = np.quantile(reference, np.linspace(0, 1, bins + 1))
    cuts[0], cuts[-1] = -np.inf, np.inf
    ref_pct = np.histogram(reference, cuts)[0] / len(reference) + 1e-6
    cur_pct = np.histogram(current,   cuts)[0] / len(current)   + 1e-6
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

def drift_report(ref_df: pl.DataFrame, cur_df: pl.DataFrame, features: list[str]):
    rows = []
    for f in features:
        r, c = ref_df[f].to_numpy(), cur_df[f].to_numpy()
        ks_stat, ks_p = ks_2samp(r, c)
        rows.append({"feature": f, "psi": psi(r, c), "ks_stat": ks_stat, "ks_p": ks_p,
                     "flag": "RED" if psi(r, c) > 0.25 or ks_p < 0.01 else "OK"})
    return pl.DataFrame(rows).sort("psi", descending=True)

# Usage in the heartbeat:
# rep = drift_report(training_features, this_week_features, FEATURES)
# if (rep["flag"] == "RED").any(): trigger_retrain_or_rollback()
```

The thresholds (PSI > 0.25, KS p < 0.01) are conservative defaults. Tune per project; document the tune.

## Anti-Patterns

The agent **will refuse** the following without explicit user override:

1. **Auto-deploy without human approval.** Stage 10 always routes through `AskUserQuestion`. Even with full automation enabled. The kill-switch and the deploy switch are human-only.
2. **Skipping purged CV.** Plain K-fold on time series leaks labels across folds via temporal autocorrelation. The agent will refuse `cross_val_score` with `KFold(shuffle=True)` on any returns-derived target.
3. **Reporting raw Sharpe without DSR + PBO.** Stage 8 enforces this. A Sharpe number without (a) the trials count and (b) the deflated value is not a result.
4. **Random train/test split on prices.** Same failure mode as #2. `train_test_split(shuffle=True)` is banned on temporal data.
5. **Look-ahead leakage in features.** Stage 4 enforces this via the leakage_check_passed manifest. The agent will not pass the gate without it.
6. **Going live off a vectorbt-only backtest.** Stage 9 requires the NautilusTrader event-driven confirmation. The agent will refuse to skip it.
7. **Picking a multiple-testing correction after seeing results.** Stage 5 locks it; once committed it is immutable for the project.
8. **Training before tracking is wired.** `mlflow.set_experiment(...)` must succeed before `.fit()` is called.
9. **One-off `.fit()` calls without a config.** All training goes through Hydra. The agent rewrites stray calls into config-driven invocations.
10. **Silently picking a model when candidates are within tolerance.** Use `AskUserQuestion`. The agent will not gamble with the team's bankroll.

## What the Agent Does NOT Decide Alone

Three classes of decision are reserved for the human:

1. **Capital allocation.** The agent designs strategies; the human funds them.
2. **Stage 10 deploy.** Always routed through `AskUserQuestion`.
3. **Stage 1 frame override.** If the agent's framing of a fuzzy goal doesn't match the human's intent, the human's intent wins. The agent surfaces its frame as a one-pager and asks for sign-off before Stage 2 begins.

Everything else (CV scheme, hyperparameter prior, feature pruning threshold, retrain frequency) the agent picks defensibly and reports.
