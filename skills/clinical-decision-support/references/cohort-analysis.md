# Cohort Analysis: Stratification, Endpoints, and Statistics

Depth reference for `clinical-decision-support`. Covers how to split a cohort, what to
measure, and how to analyze it with standard scientific Python.

## 1. Stratification

Pick the axis before you look at outcomes; post-hoc grouping invites false positives.

**Biomarker axes**
- Genomic: driver mutations (EGFR, KRAS, BRAF), resistance mutations (T790M), CNVs
  (HER2/MET amplification, PTEN loss), fusions (ALK, ROS1, NTRK, RET), TMB (high ≥10
  mut/Mb), MSI-H vs MSS.
- Expression / IHC: PD-L1 TPS (<1%, 1-49%, ≥50%), HER2 (0/1+/2+/3+), Ki-67, ER/PR.
- Molecular subtypes: breast (Luminal A/B, HER2-enriched, TNBC), GBM (proneural, neural,
  classical, mesenchymal), CRC (CMS1-4).

**Clinical / risk axes**: TNM stage, grade, histology, ECOG or Karnofsky performance
status, Charlson comorbidity, prior lines of therapy, and disease-specific prognostic
scores (Child-Pugh, MELD, CHA2DS2-VASc, TIMI).

**Cut-point discipline**: prefer literature-validated cut-points; if data-driven
(maximally selected rank statistics, ROC), state it as exploratory and validate in an
independent cohort. Dichotomizing a continuous marker loses information — also report it
continuous (HR per SD) where possible.

## 2. Outcome endpoints

| Endpoint | Definition | Notes |
|----------|------------|-------|
| OS | Randomization/treatment start → death (any cause) | Regulatory gold standard; censor at last-alive date |
| PFS | Start → progression or death | RECIST 1.1 / iRECIST; earlier readout than OS |
| DFS/RFS/EFS | CR → recurrence/death | Adjuvant/curative setting |
| ORR | CR + PR proportion | Report with 95% CI |
| DOR | First response → progression | Responders only |
| DCR | CR + PR + SD (SD ≥6-8 wk) | Broader clinical-benefit measure |

Grade adverse events with CTCAE v5.0; capture dose reductions, delays, discontinuations,
and relative dose intensity for the safety section.

## 3. Survival analysis (`lifelines`)

```python
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

# Kaplan-Meier per group
kmf = KaplanMeierFitter()
kmf.fit(durations=df["time"], event_observed=df["event"], label="PD-L1 >=50%")
kmf.median_survival_time_          # median OS/PFS
kmf.plot_survival_function()       # step curve with CI band

# Two-group comparison
res = logrank_test(
    df_hi["time"], df_lo["time"],
    event_observed_A=df_hi["event"], event_observed_B=df_lo["event"],
)
res.p_value, res.test_statistic

# Adjusted hazard ratios (multivariable)
cph = CoxPHFitter()
cph.fit(model_df, duration_col="time", event_col="event")
cph.print_summary()                # exp(coef) column = HR with 95% CI
cph.check_assumptions(model_df)    # Schoenfeld-residual PH check
```

- Report **median survival with 95% CI** ("NR" if <50% events reached), landmark rates
  (6/12/24-month), and a **number-at-risk** table under every curve.
- Log-rank assumes proportional hazards. If PH fails (Schoenfeld test, crossing curves),
  report restricted mean survival time (RMST) or a time-varying model instead of a single
  HR, and say so.

## 4. Group comparisons (`scipy.stats`)

| Data | Test | Call |
|------|------|------|
| Continuous, ~normal, 2 groups | Independent t-test | `stats.ttest_ind(a, b)` |
| Continuous, skewed, 2 groups | Mann-Whitney U | `stats.mannwhitneyu(a, b)` |
| Continuous, >2 groups | ANOVA / Kruskal-Wallis | `stats.f_oneway` / `stats.kruskal` |
| Categorical | Chi-square | `stats.chi2_contingency(table)` |
| Categorical, small cells (<5 expected) | Fisher exact | `stats.fisher_exact(table)` |

Report continuous variables as mean±SD (normal) or median [IQR] (skewed), categorical as
n (%). Do **not** correct baseline Table-1 p-values for multiple testing.

## 5. Effect sizes and multiple testing

- **Hazard ratio**: HR 0.65 (0.52-0.81), p<0.001 — HR<1 means reduced hazard.
- **Odds / risk ratio**: OR for case-control/logistic; RR for cohort/trial (more
  intuitive). **NNT** = 1/absolute risk reduction, for communicating benefit.
- **Multiple subgroups**: Bonferroni (α/n, conservative) or Benjamini-Hochberg FDR
  (`from statsmodels.stats.multitest import multipletests`). Pre-specify to avoid
  data-dredging.
- **Statistical vs clinical significance**: pair every p-value with an effect size and CI;
  a significant result under the minimal clinically important difference (MCID) is not
  actionable.

## 6. Tables and figures

**Table 1 (baseline)**: characteristic × group with n (%), median [IQR], and comparison
p-values. **Efficacy table**: ORR/DCR with 95% CI, DOR, then survival rows with HR (95%
CI). **Safety table**: any-grade and grade 3-4 AE counts per group.

**Figures** (`matplotlib`, colorblind-safe palette, high contrast):
- **Kaplan-Meier**: curves + CI bands + log-rank p + HR + number-at-risk.
- **Waterfall**: per-patient best % change from baseline, sorted, colored by
  CR/PR/SD/PD, annotated with biomarker status.
- **Forest**: subgroup HRs with 95% CI + interaction test; overall effect at the bottom.
- **Swimmer**: per-patient time on treatment, response duration, ongoing arrows.

## 7. Reporting standards

Follow the checklist matching the design: CONSORT (RCT), STROBE (observational), REMARK
(prognostic marker), TRIPOD (prediction model). Report missing-data handling and median
follow-up. For manuscript prose and structured abstracts, hand off to `scientific-writing`
and `venue-templates`.
