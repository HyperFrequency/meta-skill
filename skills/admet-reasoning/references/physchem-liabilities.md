# Physicochemical Liability Thresholds

Property-based liabilities complement the structural alerts: a molecule can be
alert-free yet still fail on absorption, permeability, or developability grounds.
Each property is checked against a range; a violation carries a severity used to
rank the report.

All descriptors are RDKit `Descriptors.*` (or `QED.qed`) calls — see the
Quick Start in `../SKILL.md` and the runnable code in
`reference-implementation.md`.

## Threshold table

| Property | RDKit call | Range | Severity | Rationale |
|----------|-----------|-------|----------|-----------|
| **LogP** | `Descriptors.MolLogP` | 1.0 – 3.0 | medium | The lipophilicity sweet spot; high LogP drives promiscuity, hERG, and poor solubility, low LogP hurts permeability |
| **LogS (ESOL est.)** | see equation below | ≥ -4.0 | medium | Below ~-4 log mol/L aqueous solubility becomes a formulation and absorption risk |
| **MW** | `Descriptors.MolWt` | 150 – 500 | medium | Lipinski upper bound; low MW often lacks potency, high MW hurts permeability/oral absorption |
| **TPSA** | `Descriptors.TPSA` | 20 – 130 | medium | >140 Å² blocks passive permeability and oral absorption; very low TPSA correlates with promiscuity |
| **QED** | `QED.qed` | ≥ 0.5 | low | Quantitative Estimate of Drug-likeness; a composite developability score |
| **HBA** | `Descriptors.NumHAcceptors` | ≤ 10 | low | Lipinski rule-of-five |
| **HBD** | `Descriptors.NumHDonors` | ≤ 5 | low | Lipinski rule-of-five; excess HBD hurts membrane permeability |
| **RotBonds** | `Descriptors.NumRotatableBonds` | ≤ 10 | low | Veber criterion for oral bioavailability |

Severities rank as `critical > high > medium > low`; the report sorts violations
by severity so the most consequential surface first.

## ESOL (Delaney) solubility estimate

LogS is estimated with the Delaney ESOL regression (Delaney, 2004):

```
LogS = 0.16 - 0.63*cLogP - 0.0062*MW + 0.066*RotBonds - 0.74*AP
```

where **AP is the aromatic proportion** = (number of aromatic heavy atoms) /
(number of heavy atoms). Compute it directly rather than approximating with a
ring ratio:

```python
aromatic_atoms = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic())
heavy_atoms    = mol.GetNumHeavyAtoms()
aromatic_proportion = aromatic_atoms / heavy_atoms if heavy_atoms else 0.0
```

ESOL is a rough triage proxy calibrated on a modest training set — treat a low
estimate as "flag for a measured solubility assay", not as a number to report.

## Overall assessment banding

The report rolls physchem violations and structural alerts into one count and
bands it:

| Total liabilities | Assessment |
|-------------------|-----------|
| 0 | CLEAN — no ADMET liabilities detected |
| 1 – 2 | MINOR CONCERNS — addressable with targeted modifications |
| 3 – 4 | MODERATE CONCERNS — optimization needed before advancement |
| 5+ | SIGNIFICANT CONCERNS — major redesign may be required |

The banding is a coarse triage signal. A single high-severity structural alert
(e.g. an Ames-positive aromatic amine) can matter far more than several low-
severity physchem violations, so read the itemized records — do not stop at the
headline band.

## Notes on the thresholds

- The ranges above are drug-likeness heuristics (rule-of-five, Veber, ESOL), not
  hard cutoffs. Successful drugs routinely violate one or more (β-lactams,
  macrocycles, kinase inhibitors). Use them to *prioritize attention*, not to
  reject.
- LogP here is RDKit's Crippen `MolLogP`; it differs from experimental logP and
  from other predictors — keep the estimator consistent across a series.
- TPSA uses RDKit's default (Ertl) topological polar surface area and does not
  count S/P polar contributions unless requested.
