# Evidence Grading, Synthesis, and Treatment Recommendations

Depth reference for `clinical-decision-support`. Covers how to grade evidence, reconcile
guidelines, synthesize across trials, and structure line-of-therapy recommendations.

## 1. GRADE

**Quality of evidence** (confidence in the effect estimate):

| Rating | Symbol | Meaning |
|--------|--------|---------|
| High | ⊕⊕⊕⊕ | Further research very unlikely to change confidence |
| Moderate | ⊕⊕⊕○ | Further research likely to have important impact |
| Low | ⊕⊕○○ | Further research very likely to change the estimate |
| Very low | ⊕○○○ | Estimate very uncertain |

Start RCTs at **high**, observational studies at **low**. Then adjust:
- **Downgrade** for risk of bias, inconsistency (I² >50-75%), indirectness (surrogate
  endpoint, off-target population), imprecision (wide CI crossing the decision threshold),
  and publication bias.
- **Upgrade** (observational only) for large effect (RR >2 or <0.5), dose-response, or
  confounders that would bias toward the null.

**Strength of recommendation**: Grade 1 (strong, "we recommend") when benefits clearly
outweigh harms; Grade 2 (conditional, "we suggest") when trade-offs are close or values
vary. Combined notation: **1A** strong/high, **1B** strong/moderate, **2A** weak/high,
**2B** weak/moderate, **2C** weak/low.

## 2. Major guideline systems

Map recommendations to the systems the audience uses, and note the version/date:

- **NCCN**: Category 1 (high evidence + uniform consensus) → 2A → 2B → 3 (disagreement).
- **ASCO**: GRADE-style; frequently endorses NCCN/ESMO.
- **ESMO**: evidence levels I-V + recommendation grades A-E; ESMO-MCBS scores benefit
  magnitude 1-5.
- **AHA/ACC** (cardiology): Class of Recommendation (I / IIa / IIb / III-No-Benefit /
  III-Harm) × Level of Evidence (A / B-R / B-NR / C-LD / C-EO).
- **ESC, IDSA, ATS/ERS, ACR, KDIGO** for their specialties (mostly GRADE-based).

**Concordance**: tabulate the same clinical question across guidelines; where they
disagree, attribute it (geography, cost/HTA, evidence recency, methodology) and favor the
most rigorous, most recent GRADE-based source. Example discordance driver: a therapy is
NCCN Category 1 in the US but NICE-declined in the UK on cost-effectiveness (QALY), not
efficacy — record both and make the recommendation context-dependent.

## 3. Evidence synthesis and meta-analysis

**Systematic review (PRISMA)**: PICO-defined search across PubMed/Embase/Cochrane, dual
screening, RoB 2.0 (RCTs) or Newcastle-Ottawa (observational) quality assessment, and a
PRISMA flow diagram of records screened → included.

**Pooling**:
- Fixed-effect (Mantel-Haenszel) when heterogeneity is low (I² <25%); random-effects
  (DerSimonian-Laird) otherwise — wider CI, more conservative.
- Time-to-event: pool log(HR) by generic inverse variance.
- Binary: RR/OR/RD; continuous: mean difference (same scale) or standardized mean
  difference (different scales).
- Heterogeneity: I² (0-25 low, 25-50 moderate, 50-75 substantial, >75 considerable),
  Cochran's Q, τ². Explore with pre-specified subgroups.
- **Network meta-analysis** for indirect comparisons when no head-to-head trial exists;
  check the transitivity/consistency assumption and treat SUCRA rankings as probabilistic.

Present the result as a **forest plot** (per-study HR/CI + weight, pooled diamond,
heterogeneity stats) and an **evidence table** (study, design, n, PICO, result, GRADE
quality).

## 4. Treatment sequencing

Document therapy by line, each with evidence and grade:
- **First-line**: standard of care from phase 3 trials, filtered by performance status,
  organ function, molecular profile, and goal (cure vs control vs palliation).
- **Second-line+**: driven by prior response/duration, progression pattern
  (oligo- vs widespread), residual toxicity, acquired resistance, and trial availability.
- **Maintenance**: consolidation after induction response; requires a randomized PFS
  benefit and tolerable long-term profile.

## 5. Biomarker-guided selection

Link validated biomarkers to therapies and note companion-diagnostic status:
- Required (treatment-defining): ALK fusion → alectinib/brigatinib/lorlatinib; EGFR ex19
  del/L858R → osimertinib; BRAF V600E → dabrafenib+trametinib; HER2 3+/amplified →
  trastuzumab/pertuzumab; PD-L1 ≥50% → pembrolizumab monotherapy.
- Complementary (informative): PD-L1 1-49%, TMB-high, MSI-H/dMMR.
- Actionability tiers: I (FDA-approved targeted therapy), II (clinical-trial/off-label,
  e.g. NTRK/RET fusions), III (biological plausibility, trial enrollment strongly advised).

## 6. Special populations and monitoring

- **Elderly**: geriatric assessment (G8, CARG), dose reductions ~20-25%, longer intervals,
  polypharmacy/interaction review.
- **Renal impairment**: dose-adjust renally cleared agents by eGFR (carboplatin via
  Calvert AUC×[GFR+25]; reduce methotrexate/capecitabine).
- **Hepatic impairment**: reduce hepatically metabolized agents by Child-Pugh class
  (docetaxel, irinotecan, most CYP3A4 TKIs).
- **Pregnancy/fertility**: contraception during + after treatment; offer fertility
  preservation before gonadotoxic therapy; avoid first-trimester chemotherapy.
- **On-treatment monitoring**: pre-specify labs (CBC, chemistry, thyroid for
  immunotherapy), imaging cadence (every 6-9 weeks, RECIST 1.1), and grade-based dose
  modification rules. Add post-treatment surveillance and survivorship (late cardiac,
  pulmonary, neuropathy, second-malignancy screening).

## 7. Emerging evidence and updates

Weight by phase: phase 1 (safety, very low), phase 2 (signal, low-moderate), phase 3
(confirmatory, high), phase 4 (post-market). Accelerated-approval agents may enter
guidelines as NCCN 2A before OS matures; upgrade on confirmatory data. Trigger a
recommendation update within 3 months of a practice-changing phase 3 result, new FDA/EMA
approval, guideline change, or safety alert; keep a version/change log.
