# Xenograft Tumor Growth Inhibition

Reduce in-vivo tumor-volume time courses to TGI%, per-group growth kinetics, and
an endpoint statistical comparison.

## Input schema

| column | meaning |
| --- | --- |
| `day` | measurement day (0 = randomization / treatment start) |
| `volume` | tumor volume in mm³ (typically `L * W² / 2` from calipers) |
| `group` | treatment arm; one value must denote control (e.g. `"Vehicle"`, `"control"`) |
| `mouse_id` | *(optional)* per-animal id; enables individual spider traces |

## TGI%

Tumor Growth Inhibition compares net growth of a treatment arm to the control
arm over the study window:

```
TGI% = (1 - (Tt - T0) / (Ct - C0)) * 100
```

where `T`/`C` are treatment/control mean volumes and `0`/`t` are the first/last
day. 100% = complete stasis, >100% = regression below baseline, <0% = treatment
grew faster than control.

```python
import numpy as np

def compute_tgi(df, control_name="Vehicle"):
    t0, tf = df["day"].min(), df["day"].max()
    ctrl = df[df["group"] == control_name]
    treat = df[df["group"] != control_name]
    c0 = ctrl[ctrl["day"] == t0]["volume"].mean()
    cf = ctrl[ctrl["day"] == tf]["volume"].mean()
    denom = cf - c0
    if denom == 0:
        return float("nan")
    t0v = treat[treat["day"] == t0]["volume"].mean()
    tfv = treat[treat["day"] == tf]["volume"].mean()
    return (1.0 - (tfv - t0v) / denom) * 100.0
```

For multiple treatment arms, loop over `df["group"].unique()` and compute TGI%
per arm against the shared control.

## Growth kinetics and doubling time

Fit exponential growth `V(t) = V0 · exp(k·t)` per group; fall back to a
log-linear OLS fit when the nonlinear solver diverges (common with noisy or
regressing tumors). Doubling time is `ln(2) / k`.

```python
from scipy.optimize import curve_fit

def fit_exponential(days, volumes):
    d = np.asarray(days, float); v = np.asarray(volumes, float)
    m = v > 0; d, v = d[m], v[m]
    if len(d) < 2:
        return np.nan, np.nan, np.nan
    try:
        (v0, k), _ = curve_fit(lambda t, v0, k: v0 * np.exp(k * t), d, v,
                               p0=[v[0], 0.05], maxfev=10000)
    except RuntimeError:                     # log-linear fallback
        k, b = np.polyfit(d, np.log(v), 1)
        v0 = np.exp(b)
    pred = v0 * np.exp(k * d)
    ss_tot = np.sum((v - v.mean()) ** 2)
    r2 = 1.0 - np.sum((v - pred) ** 2) / ss_tot if ss_tot else np.nan
    return v0, k, r2

doubling_days = np.log(2) / k if k > 0 else np.nan
```

## Growth delay

An alternative efficacy metric: median time for each arm to reach a target
volume (e.g. 2× or 4× baseline). Per animal, take the first day at/above the
target; report the group median (censoring animals that never reach it).

## Endpoint statistics

Compare endpoint (`day == max`) volumes between arms. Tumor volumes are typically
non-normal, so use a rank test for two groups and one-way ANOVA for more:

```python
from scipy.stats import mannwhitneyu, f_oneway

def endpoint_test(df):
    endpoint = df[df["day"] == df["day"].max()]
    arms = [endpoint[endpoint["group"] == g]["volume"].values
            for g in endpoint["group"].unique()]
    arms = [a for a in arms if len(a) > 0]
    if len(arms) < 2:
        return np.nan, "insufficient_data"
    if len(arms) == 2:
        _, p = mannwhitneyu(arms[0], arms[1], alternative="two-sided")
        return p, "Mann-Whitney U"
    _, p = f_oneway(*arms)
    return p, "One-way ANOVA"
```

For repeated measures over time (not just endpoint), a mixed-effects model is
more appropriate — hand that off to `statsmodels`.

## Best practices and failure modes

- Aim for **≥8–10 animals/group**; underpowered arms make TGI% and its p-value
  unreliable.
- Measure with calipers consistently (same operator/formula); volume is the
  dominant noise source.
- **Negative TGI%** means the treatment arm out-grew control — verify group
  labels and randomization, and consider growth-factor/hormone effects rather
  than reporting a spurious "harm."
- Dropouts / sacrifices bias late-timepoint means; note the effective `n` at the
  endpoint and consider growth delay, which tolerates censoring better.
- Survival endpoints (time to a size threshold, overall survival) are
  time-to-event analyses — use the `lifelines` library, not this skill.
