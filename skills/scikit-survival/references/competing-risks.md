# Competing Risks Analysis

Competing risks arise when a subject can experience one of several **mutually
exclusive** events, and the occurrence of one prevents the others — death from
cancer vs. cardiovascular vs. other causes; relapse vs. death in remission;
retirement vs. resignation vs. dismissal.

The **cumulative incidence function (CIF)** gives the probability of a specific
event type occurring by time *t* **in the presence of the competing events**:

**CIF_k(t) = P(T ≤ t, event type = k)**

A Kaplan-Meier estimate applied to one cause (treating the others as censoring)
**overstates** that cause's probability. Use CIF instead.

## When to use it

Use competing-risks methods when multiple mutually exclusive event types exist,
one event blocks the others, and you need per-event-type probabilities. Skip it
if there is only one event of interest (standard survival analysis), events are
recurrent rather than exclusive, or the competing event is negligibly rare
(<~10%), in which case treating it as censoring is acceptable.

## Estimating the CIF

`cumulative_incidence_competing_risks` takes an **integer status array** (0 =
censored, 1..k = event type) and the observed **time** array — **not** a `Surv`
structured array — and returns `(times, cif_estimates)`:

```python
sksurv.nonparametric.cumulative_incidence_competing_risks(
    event_status, time, conf_type="none", n_bootstraps=1000)
# returns:
#   times          -> shape (n_times,)
#   cif_estimates  -> shape (n_event_types + 1, n_times)
#                     cif_estimates[0] = total risk (all causes)
#                     cif_estimates[i] = CIF for event type i  (i = 1..k)
# with conf_type != "none", also returns confidence intervals
```

```python
import matplotlib.pyplot as plt
from sksurv.datasets import load_bmt
from sksurv.nonparametric import cumulative_incidence_competing_risks

bmt_features, bmt_outcome = load_bmt()
# bmt_outcome fields: "status" (0=censored, 1/2 = competing events), "ftime" (time)
times, cif = cumulative_incidence_competing_risks(bmt_outcome["status"], bmt_outcome["ftime"])

plt.step(times, cif[0], where="post", label="Total risk")
plt.step(times, cif[1], where="post", label="Event type 1")
plt.step(times, cif[2], where="post", label="Event type 2")
plt.xlabel("time t"); plt.ylabel("P(event before t)"); plt.ylim(0, 1); plt.legend()
```

Interpretation: `cif[i][-1]` is the estimated long-run incidence of event type
*i*; `cif[0]` (total) is the probability of experiencing **any** event; `1 -
cif[0]` is the probability of remaining event-free.

## Building the status array

sksurv models want a boolean `event` for cause-specific fits, but the CIF
estimator wants the integer status. Keep both:

```python
import numpy as np
import pandas as pd
from sksurv.util import Surv

df = pd.read_csv("competing_risks_data.csv")   # columns: time, event_type (0/1/2/...)
status = df["event_type"].to_numpy(dtype=int)   # for cumulative_incidence_*
time   = df["time"].to_numpy(dtype=float)

times, cif = cumulative_incidence_competing_risks(status, time)
```

## Comparing groups

Estimate the CIF within each stratum and overlay:

```python
for group, mask in {"treatment": df["arm"] == "A", "control": df["arm"] == "B"}.items():
    t, cif_g = cumulative_incidence_competing_risks(status[mask.values], time[mask.values])
    print(group, "event-1 incidence:", round(float(cif_g[1][-1]), 3))
```

For a formal test of CIF equality (Gray's test), use `lifelines` or R's
`cmprsk` — sksurv does not provide it.

## Cause-specific hazard models

To study covariate effects, fit a **separate Cox model per event type**,
treating the other event types as censored:

```python
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.util import Surv
import numpy as np

X = df[["age", "treatment_A"]]

for k, label in [(1, "relapse"), (2, "death")]:
    y_k = Surv.from_arrays(event=(status == k), time=time)   # other events -> censored
    cox = CoxPHSurvivalAnalysis().fit(X, y_k)
    print(label, "hazard ratios:", np.exp(cox.coef_))
```

Each model's coefficients describe the effect on the **cause-specific hazard**
for that event. A covariate can raise the hazard of one event while lowering
another's.

## Cause-specific vs. sub-distribution

- **Cause-specific hazards** (fit-able in sksurv): interpretable, good for
  understanding etiology; other events treated as censored.
- **Fine-Gray sub-distribution hazards**: model the CIF directly, better for
  prediction and clinical risk stratification. **Not in sksurv** — use
  `lifelines` or R's `cmprsk`.

## Common mistakes

- Kaplan-Meier for a single cause with competing events treated as censoring →
  overstates incidence; use the CIF.
- Passing a `Surv` structured array to `cumulative_incidence_competing_risks` →
  it expects the integer status array and time separately.
- Ignoring competing events when they are substantial (>10–20%).
- Conflating cause-specific and sub-distribution hazards — they answer different
  questions; pick the one matching your goal.
