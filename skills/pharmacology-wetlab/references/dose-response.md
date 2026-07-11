# Dose-Response Fitting, Selectivity, and Combination Index

Fit concentration-response data to a 4-parameter logistic (4PL), extract
IC50/EC50 with a confidence interval, and extend to multi-compound selectivity
and Chou-Talalay synergy.

## Input schema

A tidy CSV / DataFrame with at least:

| column | meaning |
| --- | --- |
| `concentration` | drug concentration, linear scale, **> 0** (e.g. µM) |
| `response` | measured readout (% viability, % activity, signal) |
| `compound` | *(optional)* compound name for multi-compound runs |
| `replicate` | *(optional)* replicate id; replicates are averaged per concentration |

## The 4PL model (log-concentration form)

Fit in log10-concentration space — it is far better conditioned than
linear-space fitting because the sigmoid is symmetric in `log(conc)`.

```python
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist

def four_pl(log_conc, bottom, top, log_ec50, hill):
    """y = bottom + (top - bottom) / (1 + 10^((log_ec50 - log_conc) * hill))"""
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((log_ec50 - log_conc) * hill))

def fit_dose_response(concentrations, responses, response_type="inhibition"):
    """Return (popt=[bottom, top, log_ec50, hill], pcov, r_squared)."""
    conc = np.asarray(concentrations, float)
    resp = np.asarray(responses, float)
    mask = conc > 0                      # log transform requires positive conc
    log_conc = np.log10(conc[mask])
    resp = resp[mask]

    hill0 = -1.0 if response_type == "inhibition" else 1.0
    p0 = [resp.min(), resp.max(), np.median(log_conc), hill0]
    popt, pcov = curve_fit(four_pl, log_conc, resp, p0=p0, maxfev=20000)

    pred = four_pl(log_conc, *popt)
    ss_res = np.sum((resp - pred) ** 2)
    ss_tot = np.sum((resp - resp.mean()) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    return popt, pcov, r2
```

For `response_type="inhibition"` the response falls with dose (Hill < 0) and the
midpoint is the **IC50**; for `"activation"` it rises (Hill > 0) and the midpoint
is the **EC50**. In both cases `EC50 = 10 ** popt[2]`.

## 95% confidence interval (delta method)

The fit gives the standard error of `log_ec50` directly; exponentiate the
t-interval so the CI is asymmetric on the linear scale (correct for a log-normal
parameter):

```python
def ec50_ci(log_ec50, pcov, n_points, alpha=0.05):
    se_log = np.sqrt(pcov[2, 2])
    dof = max(n_points - 4, 1)           # 4 fitted parameters
    t_val = t_dist.ppf(1 - alpha / 2, dof)
    return 10.0 ** (log_ec50 - t_val * se_log), 10.0 ** (log_ec50 + t_val * se_log)
```

## Selectivity / therapeutic index

Across compounds (or the same compound in two cell lines / target vs off-target),
selectivity is the ratio of IC50s to a reference:

```python
selectivity_index = ic50_compound / ic50_reference
```

A *therapeutic index* is the same ratio between a toxicity IC50 and an efficacy
IC50. Only compare IC50s obtained under matched assay conditions and readouts.

## Chou-Talalay combination index (synergy)

Measure each drug's IC50 alone and the concentration of each drug present in a
fixed-ratio combination that produces the same effect level (Fa), then:

```python
def combination_index(ic50_d1, ic50_d2, combo_d1, combo_d2):
    """CI < 1 synergistic, ~1 additive, > 1 antagonistic."""
    ci = combo_d1 / ic50_d1 + combo_d2 / ic50_d2
    verdict = "synergistic" if ci < 0.9 else "antagonistic" if ci > 1.1 else "additive"
    return ci, verdict
```

Caveats: CI is only interpretable at (or near) the fraction-affected you actually
measured — pick the fixed ratio so the combination lands near Fa ≈ 0.5. For a
full CI-vs-Fa curve, fit each drug's median-effect equation and evaluate CI
across effect levels rather than at a single point.

## Failure modes

- **Unreasonable IC50 far outside the tested range** — your concentrations do not
  bracket the inflection. Responses should run from roughly 10% to 90% effect;
  add points around the midpoint and re-fit.
- **`curve_fit` raises `RuntimeError` / does not converge** — improve `p0`
  (set `bottom`/`top` to observed plateaus, `log_ec50` to the median log-conc),
  raise `maxfev`, or add gentle bounds. If the data are not sigmoidal, a 4PL is
  the wrong model.
- **Hill slope implausibly steep/shallow** — often noisy plateaus or too few
  points; constrain `hill` only as a last resort and report that you did.
- **Non-positive concentrations** — a `0 µM` vehicle point cannot be log-
  transformed; keep it for plotting/normalization but drop it from the fit
  (the code above masks it out).
