---
name: microbial-dynamics
version: 0.1.0
description: >-
  Model and analyze microbial populations with SciPy/NumPy. Fit bacterial
  growth curves (logistic, Gompertz, Baranyi) from OD600 time-series to extract
  lag, mu_max, and carrying capacity; simulate multi-species communities with
  generalized Lotka-Volterra ODEs and test coexistence stability; run exact
  stochastic (Gillespie SSA) population and gene-expression simulations;
  quantify crystal-violet biofilm assays; enumerate CFU/mL from serial-dilution
  plate counts with confidence intervals; count colonies from agar-plate images
  by watershed segmentation; annotate bacterial genomes with Prokka and parse
  GFF statistics; and run a simplified ADM1 anaerobic-digestion/biogas model.
  Use when you have wet-lab microbiology or ecology data to fit or a
  population/community dynamics model to simulate. NOT for constraint-based
  metabolic flux modeling (use cobrapy), sequence/BLAST/phylogenetics (use
  biopython), single-cell omics (use scanpy/anndata), or general statistical
  tests (use statistical-analysis).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (SciPy, NumPy, pandas, scikit-image); Apache-2.0 (OpenCV); Prokka invoked as external CLI (GPL-3.0)"
---

# Microbial Dynamics: Population Modeling & Analysis

## Overview

This skill is a **router** for computational microbiology built on SciPy and
NumPy. It covers three families of task:

- **Fit** growth models to OD600 time-series and recover interpretable
  parameters (lag phase, maximum specific growth rate `mu_max`, carrying
  capacity `K`).
- **Simulate** population and community dynamics — deterministic ODE systems
  (Lotka-Volterra, simplified anaerobic digestion) and exact stochastic
  trajectories (Gillespie SSA).
- **Quantify** wet-lab readouts — crystal-violet biofilm assays, CFU
  enumeration from serial dilutions, colony counts from plate photos, and
  gene/feature statistics from an annotated bacterial genome.

The body below is a concise capability map with one runnable quick-start each.
Full model equations, function signatures, parameter tables, model-selection
guidance, and end-to-end scripts live in `references/`.

## When to Use This Skill

- You have OD600 (or other turbidity/biomass) time-series and want growth
  parameters, or want to compare conditions/strains by `mu_max` and lag.
- You want to model how two or more species interact (competition, mutualism,
  predation) and whether they coexist.
- You need exact stochastic simulation of a small population or a reaction
  network (birth-death, gene expression bursts) where mean-field ODEs miss the
  noise.
- You are processing crystal-violet biofilm plates, serial-dilution CFU counts,
  or agar-plate colony photos.
- You want to annotate a bacterial assembly and summarize its gene content.
- You are estimating biogas/methane yield from an anaerobic digester.

## When NOT to Use This Skill

- **Constraint-based / genome-scale metabolic modeling** (FBA, knockouts, flux
  sampling) — use `cobrapy`.
- **Sequence manipulation, BLAST, alignment, phylogenetics, Entrez** — use
  `biopython`.
- **Single-cell / omics count matrices** — use `scanpy` / `anndata`.
- **General statistical testing, GLMs, dose-response curve stats** — use
  `statistical-analysis`; for sample-size planning use `power-analysis`.
- **Heavy microscopy / fluorescence image analysis** beyond simple colony
  counting — use `bioimage-analysis`.
- **Plotting the results** — this skill computes; hand figures to
  `scientific-visualization` / `matplotlib`.

## Setup

```bash
uv pip install scipy numpy pandas          # core: all modeling capabilities
uv pip install scikit-image opencv-python  # optional: colony counting from images
# conda install -c bioconda prokka         # optional: genome annotation (GPL-3.0)
```

## Capabilities

### 1. Growth curve fitting

Fit OD600 data to logistic, modified-Gompertz, or Baranyi models with
`scipy.optimize.curve_fit`, returning each parameter with its standard error
and an R-squared. Parameters of interest: `y0`, `K` (carrying capacity),
`mu_max` (h^-1), and `lag` (h).

```python
import numpy as np
from scipy.optimize import curve_fit

def logistic(t, y0, K, r, lag):
    return K / (1 + ((K - y0) / y0) * np.exp(-r * (t - lag)))

time  = np.array([0, 2, 4, 6, 8, 10, 12, 16, 20, 24])
od600 = np.array([0.02, 0.03, 0.15, 0.72, 1.25, 1.42, 1.48, 1.51, 1.51, 1.52])
popt, _ = curve_fit(logistic, time, od600, p0=[0.02, 1.5, 0.5, 2.0], maxfev=10000)
print(f"K={popt[1]:.3f}  mu_max~{popt[2]:.3f} h^-1  lag={popt[3]:.2f} h")
```

Model equations, a reusable `fit_growth_curve(time, od, model=...)` helper with
bounds and R-squared, and model-selection guidance (AIC/BIC, when Baranyi is
worth the extra parameters) are in `references/growth-models.md`.

### 2. Community dynamics (Lotka-Volterra)

Integrate a generalized n-species Lotka-Volterra system with
`scipy.integrate.solve_ivp`, then inspect equilibria and test local stability
via the Jacobian eigenvalues.

```python
import numpy as np
from scipy.integrate import solve_ivp

def glv(t, N, r, K, alpha):        # alpha[i,j] = effect of species j on i
    return r * N * (1 - (alpha @ N) / K)

r = np.array([0.5, 0.4, 0.3]); K = np.array([1000, 800, 600])
alpha = np.array([[1.0, 0.5, 0.1], [0.3, 1.0, 0.4], [0.2, 0.6, 1.0]])
sol = solve_ivp(glv, [0, 200], [10, 10, 10], args=(r, K, alpha),
                t_eval=np.linspace(0, 200, 1000))
print("equilibrium:", sol.y[:, -1].round(1))
```

Stability analysis, solver choice for stiff systems, extinction `events`, and
the simplified ADM1 anaerobic-digestion model are in
`references/dynamics-simulation.md`.

### 3. Stochastic simulation (Gillespie SSA)

Exact discrete-molecule simulation for small populations or reaction networks
where demographic noise matters. Supply a propensity function and a
stoichiometry matrix; run an ensemble and summarize.

```python
# props(x) -> reaction rates ; stoich[reaction] -> state change vector
times, states = gillespie_ssa(props, stoich, x0=[10], t_end=50)
```

The full `gillespie_ssa` implementation, ensemble/summary patterns, and when to
switch to tau-leaping or a mean-field + noise approximation are in
`references/dynamics-simulation.md`.

### 4. Biofilm and CFU quantification

Crystal-violet biofilm assay (blank subtraction, per-condition mean/SEM,
fold-change vs control) and CFU/mL enumeration from serial-dilution plate counts
(with a t-based 95% confidence interval and log10 CFU).

```python
result = calculate_cfu(counts=[42, 38, 45], dilution_factor=1e-6,
                       volume_plated_ml=0.1)
print(f"{result['mean_cfu_per_ml']:.2e} CFU/mL  (log10 {result['log10_cfu']:.2f})")
```

Both helpers, the 30-300 countable-range rule, and biofilm normalization to
planktonic growth are in `references/lab-assays.md`.

### 5. Colony counting from plate images

Count colonies (including touching ones) from an agar-plate photo via Gaussian
blur, Otsu/adaptive thresholding, distance-transform watershed segmentation
(`skimage.segmentation.watershed` + `skimage.feature.peak_local_max`), and
morphological size filtering — returning a count plus a size distribution.
Approach, tunable parameters (min/max radius, sensitivity), and failure modes
(uneven lighting, plate-edge artifacts) are in `references/lab-assays.md`.

### 6. Genome annotation

Run Prokka on a bacterial assembly and parse the GFF3 output into a feature
table (CDS / tRNA / rRNA / tmRNA counts, mean CDS length, coding density).

```python
prefix = run_prokka('assembly.fasta', 'out', genus='Escherichia', species='coli')
genes  = parse_prokka_gff(f'{prefix}.gff')
```

Prokka CLI flags, the GFF parser, and interpretation are in
`references/lab-assays.md`. For downstream sequence work on the predicted genes,
hand off to `biopython`.

## Best Practices

- Fit each biological **replicate individually**, then report mean ± SEM of the
  parameters — do not average curves before fitting (it biases `mu_max`).
- Compare growth models by **AIC/BIC**, not R-squared alone; more parameters
  always raise R-squared.
- Run Gillespie ensembles of **>100 trajectories** before trusting means; a
  single trajectory is not a result.
- Count only plates with **30-300 colonies**; below 30 is statistically
  unreliable, above 300 is too dense to resolve.
- Normalize biofilm CV signal to **planktonic OD600** to separate
  biofilm-specific effects from plain growth differences.
- Use `RK45` for non-stiff ODEs; switch to `BDF` or `Radau` when a multi-species
  or digestion model integrates slowly or oscillates numerically.

## References

- `references/growth-models.md` — logistic / Gompertz / Baranyi equations, the
  `fit_growth_curve` helper, model selection, multi-condition workflow.
- `references/dynamics-simulation.md` — generalized Lotka-Volterra, stability,
  Gillespie SSA, tau-leaping notes, simplified ADM1 digestion model.
- `references/lab-assays.md` — biofilm CV assay, CFU enumeration, colony image
  counting, Prokka annotation + GFF parsing, troubleshooting.
