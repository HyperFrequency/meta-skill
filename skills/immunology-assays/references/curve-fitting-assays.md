# Curve-Fitting Plate Assays

ELISA (4PL), antibody titers / GMT, and multiplex cytokine (5PL) quantitation.
All fits use `scipy.optimize.curve_fit`; nothing here requires a vendor SDK.

## 1. ELISA — 4-Parameter Logistic

The 4PL is the standard sigmoid for immunoassay standard curves:

```
y = D + (A - D) / (1 + (x / C)^B)
```

`A` = lower asymptote (signal at zero analyte), `D` = upper asymptote
(saturation), `C` = EC50 (inflection concentration), `B` = Hill slope. It has a
closed-form inverse, which is what makes reading unknowns cheap.

```python
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

def four_pl(x, a, b, c, d):
    return d + (a - d) / (1 + (x / c) ** b)

def inverse_four_pl(y, a, b, c, d):
    # solve four_pl(x)=y for x; valid only for y strictly between a and d
    return c * ((a - d) / (y - d) - 1) ** (1 / b)

def fit_standard_curve(concentrations, ods, blank_od=0.0):
    """Fit a 4PL to (concentration, OD) standards. Drop the zero standard."""
    conc = np.asarray(concentrations, float)
    od = np.asarray(ods, float) - blank_od
    keep = conc > 0
    conc, od = conc[keep], od[keep]

    p0 = [od.min(), 1.0, np.median(conc), od.max()]
    popt, _ = curve_fit(four_pl, conc, od, p0=p0, maxfev=10000)

    pred = four_pl(conc, *popt)
    ss_res = np.sum((od - pred) ** 2)
    ss_tot = np.sum((od - od.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    return popt, r2

def interpolate_unknowns(unknowns, popt, blank_od=0.0):
    """unknowns: {sample_name: [od_replicate, ...]}. Gates to the curve range."""
    a, b, c, d = popt
    rows = []
    for name, ods in unknowns.items():
        corrected = np.asarray(ods, float) - blank_od
        vals = [inverse_four_pl(v, *popt) if a < v < d else np.nan for v in corrected]
        rows.append({
            "sample": name,
            "mean_od": float(np.mean(corrected)),
            "mean_conc": float(np.nanmean(vals)),
            "std_conc": float(np.nanstd(vals)),
            "n_in_range": int(np.sum(~np.isnan(vals))),
        })
    return pd.DataFrame(rows)
```

### Detection limits

Compute from the blank-well replicates, not the fit:

- **LOD** (limit of detection) = `mean(blank) + 3·SD(blank)`
- **LOQ** (limit of quantification) = `mean(blank) + 10·SD(blank)`

Convert those OD thresholds back to concentration with `inverse_four_pl` when
they fall inside `[A, D]`. Report any unknown whose OD is below LOQ as
"< LOQ", and any above `D` as needing dilution and re-run.

### Expected CSV schema (batch/CLI use)

A plate table with columns `well, concentration, od450, sample_type`, where
`sample_type ∈ {standard, unknown, blank}`. Group `standard` rows to fit,
average `blank` rows for subtraction and LOD/LOQ, and interpolate `unknown`
rows. Persist the fitted `A,B,C,D`, R², LOD, LOQ, and the per-sample
concentration table.

### When the fit misbehaves

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curve_fit` won't converge | curve doesn't span the analyte range, or bad `p0` | verify standards bracket the expected values; set `p0=[min_od, 1, median_conc, max_od]`; raise `maxfev` |
| R² < 0.99 | asymmetric curve, or an outlier standard | switch to 5PL (see §3); drop/replace the offending standard well |
| interpolated conc is `nan` | OD outside `[A, D]` | dilute and re-run; do not extrapolate past the asymptotes |
| negative or huge concentrations | OD near an asymptote where the inverse is unstable | keep unknowns to the ~20–80% signal band of the curve |

## 2. Antibody Titers and GMT

Endpoint titer = the **highest dilution** whose OD still exceeds a cutoff.

```python
import numpy as np
from scipy import stats

def endpoint_titer(dilutions, ods, negative_ods=None, k_sd=3, fixed_cutoff=0.1):
    """dilutions/ods are paired and ordered from least to most dilute.
    Cutoff defaults to mean(neg)+k_sd*SD(neg); falls back to fixed_cutoff."""
    if negative_ods is not None and len(negative_ods) > 1:
        cutoff = float(np.mean(negative_ods) + k_sd * np.std(negative_ods, ddof=1))
    else:
        cutoff = fixed_cutoff

    endpoint = None
    for dil, od in zip(dilutions, ods):
        if od > cutoff:
            endpoint = dil          # keep the last (most dilute) positive
    if endpoint is None:
        return {"titer": f"<{min(dilutions)}", "cutoff": cutoff}
    return {"titer": int(endpoint), "log2_titer": float(np.log2(endpoint)),
            "cutoff": cutoff}

def geometric_mean_titer(titers):
    """GMT with a 95% CI, computed in log2 space (titers are log-distributed)."""
    log_t = np.log2([t for t in titers if t and t > 0])
    lo, hi = stats.t.interval(0.95, df=len(log_t) - 1,
                              loc=log_t.mean(), scale=stats.sem(log_t))
    return {"gmt": float(2 ** log_t.mean()),
            "ci_lower": float(2 ** lo), "ci_upper": float(2 ** hi),
            "n": int(len(log_t))}
```

Notes:
- Always work in **log2** for group statistics — the arithmetic mean of raw
  titers is meaningless.
- Seroconversion is conventionally a **≥4-fold** (≥2 log2) rise between paired
  samples.
- CSV schema for batch runs: `dilution, od450, sample_id`, with negative-control
  rows carrying `sample_id = "negative"` so the cutoff is derived per plate.
- If a sample is positive at the most concentrated dilution, its true endpoint
  is beyond the plate — report as ">[max dilution]" and repeat with a higher
  starting dilution.

## 3. Multiplex Cytokines (Luminex / MSD) — 5PL

Bead/electrochemiluminescence assays report MFI and are usually asymmetric, so a
**5-parameter logistic** fits better than 4PL. There is no closed-form inverse —
solve numerically with `brentq`.

```python
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, brentq

def five_pl(x, a, b, c, d, g):
    return d + (a - d) / (1 + (x / c) ** b) ** g

def process_multiplex(plate_df, standard_curves):
    """plate_df: columns [sample, analyte, MFI].
    standard_curves: {analyte: (concentrations, mfi_values)}."""
    rows = []
    for analyte, (conc, mfi) in standard_curves.items():
        conc, mfi = np.asarray(conc, float), np.asarray(mfi, float)
        m = conc > 0
        try:
            popt, _ = curve_fit(five_pl, conc[m], mfi[m],
                                p0=[mfi.min(), 1, np.median(conc), mfi.max(), 1],
                                maxfev=10000)
        except RuntimeError:
            popt = None                      # curve failed; emit NaN below

        sub = plate_df[plate_df["analyte"] == analyte]
        for _, r in sub.iterrows():
            conc_val = np.nan
            if popt is not None:
                try:
                    conc_val = brentq(lambda x: five_pl(x, *popt) - r["MFI"],
                                      1e-2, 1e5)
                except ValueError:
                    conc_val = np.nan        # MFI outside the bracketed range
            rows.append({"sample": r["sample"], "analyte": analyte,
                         "MFI": r["MFI"], "concentration": conc_val})
    return pd.DataFrame(rows)
```

QC:
- Flag analytes whose replicate **CV > 15%**.
- Watch for cross-reactivity between panel members; a spike in one analyte
  bleeding into another is a classic multiplex artifact.
- `brentq` needs the target MFI to lie between the images of the bracket
  endpoints; widen `[1e-2, 1e5]` only if your standards genuinely extend
  further, otherwise treat it as out-of-range.
