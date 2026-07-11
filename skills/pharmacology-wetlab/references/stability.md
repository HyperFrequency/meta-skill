# Pharmaceutical Stability and Shelf-Life Prediction

Predict a drug product's shelf life from accelerated (elevated-temperature)
stability data using degradation kinetics plus the Arrhenius relationship.

## Input schema

| column | meaning |
| --- | --- |
| `temperature_C` | storage temperature of the stability arm (°C) |
| `time_months` | time on stability |
| `potency_percent` | assayed potency as % of label (100 at t=0) |

Need **≥2 temperatures** to fit Arrhenius; ≥3 is strongly preferred so you can
verify linearity of `ln(k)` vs `1/T`.

## Step 1 — degradation kinetics per temperature

Fit each temperature arm to a kinetic order and keep the better R². Zero-order
(linear potency loss) and first-order (log-linear) cover most small molecules;
second-order (`1/C` linear) occurs for some bimolecular pathways.

```python
import numpy as np

def r_squared(obs, pred):
    ss_tot = np.sum((obs - obs.mean()) ** 2)
    return 1.0 - np.sum((obs - pred) ** 2) / ss_tot if ss_tot else float("nan")

def fit_zero_order(t, c):                 # C = C0 - k t
    slope, c0 = np.polyfit(t, c, 1)
    k = -slope
    return c0, k, r_squared(c, c0 - k * t)

def fit_first_order(t, c):                # ln C = ln C0 - k t
    m = c > 0; t, c = t[m], c[m]
    slope, b = np.polyfit(t, np.log(c), 1)
    k, c0 = -slope, np.exp(b)
    return c0, k, r_squared(c, c0 * np.exp(-k * t))
```

Pick the dominant order across all temperatures (e.g. by majority vote), then
re-fit every temperature with that single order so the rate constants are
comparable.

## Step 2 — Arrhenius fit

Linearize `k = A·exp(-Ea / RT)` as `ln(k) = ln(A) - (Ea/R)·(1/T)` and regress
`ln(k)` on `1/T` (Kelvin). The slope gives the activation energy.

```python
R_GAS = 8.314  # J/(mol*K)

def fit_arrhenius(temps_C, rate_constants):
    m = rate_constants > 0
    inv_T = 1.0 / (np.asarray(temps_C, float)[m] + 273.15)
    ln_k = np.log(rate_constants[m])
    slope, ln_A = np.polyfit(inv_T, ln_k, 1)
    Ea = -slope * R_GAS                    # J/mol  (divide by 1000 for kJ/mol)
    return Ea, ln_A, r_squared(ln_k, ln_A + slope * inv_T)

def predict_k(Ea, ln_A, target_C):
    return np.exp(ln_A - (Ea / R_GAS) / (target_C + 273.15))
```

Typical small-molecule Ea is ~50–120 kJ/mol; values far outside this range, or a
poor Arrhenius R², signal a changing degradation mechanism across temperatures.

## Step 3 — shelf life to a spec limit

Extrapolate the rate to the storage temperature (e.g. 25 °C, or 5 °C for
cold-chain) and solve for the time to hit the potency spec limit (commonly 90%).

```python
def shelf_life_months(c0, k_target, spec_limit, order):
    if k_target <= 0:
        return np.inf
    if order == 0:
        return (c0 - spec_limit) / k_target        # C = C0 - k t
    return np.log(c0 / spec_limit) / k_target      # first order
```

## Best practices and failure modes

- **Verify Arrhenius linearity before trusting the extrapolation.** A phase
  transition, melt, or moisture-driven pathway that only appears at high
  temperature breaks the single-Ea assumption — exclude those points.
- Accelerated extrapolation is a *prediction*, not a substitute for real-time
  data. Regulatory shelf life still requires long-term study at the labeled
  condition (ICH Q1A: 25 °C / 60% RH long-term, 40 °C / 75% RH accelerated;
  guidance Q1A–Q1E).
- Distinguish **potency loss** (degradation of active) from **impurity growth**;
  a product can fail on a specified degradant before potency drops below limit.
- Low Arrhenius R² with clean per-temperature fits usually means multiple
  mechanisms — do not force a single order across the whole temperature range.
