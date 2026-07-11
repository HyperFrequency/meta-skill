# Biodistribution and MIRD Dosimetry

Two related radiopharmacology workflows: reducing tissue-count biodistribution
data to %ID/g plus clearance kinetics, and estimating absorbed organ dose with
the MIRD formalism.

## Part 1 — Biodistribution (%ID/g)

### Input schema

| column | meaning |
| --- | --- |
| `time_hours` | time post-injection |
| `organ` | tissue name (`tumor`, `blood`, `liver`, ...) |
| `counts_per_gram` | measured radioactivity per gram of tissue (e.g. CPM/g) |
| `injected_dose` | total injected dose in the same count units |

### Percent injected dose per gram

`%ID/g` normalizes tissue uptake to the injected dose so animals and time points
are comparable. Apply a decay-correction factor when counting spans multiple
half-lives of the isotope.

```python
def id_per_gram(counts_per_gram, injected_dose, decay_correction=1.0):
    """(%ID/g) = counts_per_gram * decay_correction / injected_dose * 100."""
    return counts_per_gram * decay_correction / injected_dose * 100.0
```

### Clearance kinetics and AUC

Fit each organ's %ID/g vs time. Blood and most tissues clear
mono-exponentially; organs that accumulate then wash out (many tumors, some
targets) follow a Bateman uptake-clearance form. Keep whichever fit has the
higher R².

```python
import numpy as np
from scipy.optimize import curve_fit

def mono_exponential(t, a, lam):           # A e^(-lam t)
    return a * np.exp(-lam * t)

def uptake_clearance(t, a, lam_up, lam_cl):  # Bateman: rise then fall
    return a * (np.exp(-lam_cl * t) - np.exp(-lam_up * t))

# half-life from the clearance rate:  t_half = ln(2) / lam_cl
# time-to-peak (Bateman):  t_peak = ln(lam_up / lam_cl) / (lam_up - lam_cl)
```

Integrate exposure with the trapezoidal rule (sort by time first):

```python
def auc(time, values):
    order = np.argsort(time)
    return float(np.trapz(np.asarray(values)[order], np.asarray(time)[order]))
```

### Tumor-to-blood ratio

At each shared time point, `T:B = %ID/g(tumor) / %ID/g(blood)`. A rising T:B over
time is the hallmark of successful tumor targeting with background clearance;
T:B > 1 means preferential tumor retention.

## Part 2 — MIRD absorbed-dose estimation

The MIRD (Medical Internal Radiation Dose) schema estimates mean absorbed dose to
a target organ as time-integrated activity × dose factor, summed over source
organs:

```
D(target) = Σ_source  Ã(source) · S(source ← target)
```

- **Ã (time-integrated activity, a.k.a. cumulated activity)** — area under the
  activity-vs-time curve for a source organ, in MBq·h. Integrate the measured
  activity trapezoidally (see `auc` above) and, for a complete Ã, add analytic
  tails for decay beyond the last measured point.
- **S-value** — absorbed dose to the target per unit cumulated activity in the
  source, in mGy/(MBq·h). These are **tabulated constants** for a given isotope,
  phantom, and source→target pair.

```python
def mird_dose(cumulated_activity, s_values):
    """cumulated_activity: {organ: A_tilde_MBq_h}
       s_values: {(source, target): S in mGy/(MBq*h)}
       returns {target: total absorbed dose (mGy)} = self-dose + cross-dose."""
    doses = {}
    for target in cumulated_activity:
        doses[target] = sum(a * s_values.get((source, target), 0.0)
                            for source, a in cumulated_activity.items())
    return doses
```

The `(target, target)` term is the **self-dose**; the rest are **cross-doses**
from other organs.

### Critical caveat — never invent S-values

S-values depend on isotope, organ geometry, and the reference phantom, and must
come from a validated source — **OLINDA/EXM**, the **IDAC-Dose** model, or
published MIRD pamphlet tables. Do not fabricate or interpolate them ad hoc.
Likewise, this mean-organ formalism does not capture intra-organ dose
heterogeneity or small-scale/voxel dosimetry (use dedicated Monte-Carlo tools
such as GATE for that).

## Failure modes

- **Missing decay correction** across long count sessions systematically
  under-reports late-time %ID/g — always correct to a common reference time.
- **Bateman fit refuses to converge** when the peak is at t=0 (pure clearance) —
  fall back to the mono-exponential model.
- **Truncated Ã** (integrating only to the last sample) underestimates dose for
  slowly clearing isotopes; add the analytic decay tail.
- **Divide-by-zero in T:B** when blood %ID/g is ~0 at late times — guard and
  report the ratio as undefined rather than infinite.
