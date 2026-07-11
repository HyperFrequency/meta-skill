---
name: admet-prediction
version: 0.1.0
description: >-
  Predict ADMET (absorption, distribution, metabolism, excretion, toxicity) and
  drug-likeness properties for small-molecule drug candidates from SMILES, using
  RDKit physicochemical descriptors and rules, SMARTS structural-alert libraries
  (PAINS, hERG, AMES, DILI), and ML models (PyTDC benchmark data, ADMET-AI). Each
  endpoint gets a GREEN / YELLOW / RED call so a series can be triaged at a glance.
  Use to rank hits from a screen, flag toxicity and PK liabilities, gate
  drug-likeness for a delivery route (oral / CNS / topical / injectable), or
  compare candidates against approved-drug statistics before committing to
  synthesis. NOT for biologics, peptides, PROTACs, or inorganics (outside the
  applicability domain); NOT a substitute for in vitro / in vivo assays; NOT for
  plain descriptor calculation (use `rdkit`) or training QSAR models from scratch
  (use `pytdc` / `deepchem`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: RDKit BSD-3-Clause; PyTDC MIT; ADMET-AI MIT
---

# ADMET Prediction

## Overview

ADMET liabilities — poor absorption, wrong distribution, fast clearance,
CYP-mediated interactions, cardiac (hERG) or genotoxic (AMES) risk — sink a large
fraction of clinical candidates. Computational ADMET lets you triage compounds
*before* synthesis, so scarce chemistry effort goes to molecules with a plausible
developability profile.

This skill computes a full ADMET + drug-likeness panel from a SMILES string using
three complementary tiers:

1. **Physicochemical descriptors + rules** — RDKit descriptors (MW, cLogP, TPSA,
   HBD/HBA, rotatable bonds, Fsp3) feed empirical rules (Lipinski, ESOL solubility,
   BBB score) and drug-likeness scores (QED, synthetic accessibility).
2. **SMARTS structural alerts** — curated substructure libraries flag hERG, AMES,
   DILI, PAINS, reactive/electrophilic groups, and metabolic soft spots.
3. **ML models** — `pytdc` benchmark datasets and the ADMET-AI package supply
   trained predictors for endpoints where descriptors alone are weak (Caco-2,
   CYP inhibition, clearance, hERG IC50).

Every endpoint is reduced to a **traffic light** — GREEN (favorable), YELLOW
(borderline), RED (liability) — so a hit list can be scanned quickly. Thresholds
and the clinical meaning of each endpoint live in
[references/endpoints.md](references/endpoints.md); runnable code for every tier
lives in [references/recipes.md](references/recipes.md).

## When to Use This Skill

- **Hit-to-lead triage** — rank HTS hits by predicted developability.
- **Lead optimization** — locate the specific liability (hERG alert? high cLogP?
  metabolic soft spot?) driving a series' problems and guide the next analog.
- **Virtual-screening filter** — drop compounds with fatal ADMET flags before
  spending compute on docking or scoring.
- **Toxicity flagging** — run a focused hERG / AMES / DILI / PAINS check before
  synthesis or before advancing a screening hit.
- **Delivery-route gating** — evaluate a molecule against an oral, CNS, topical,
  or injectable property profile.
- **Candidate comparison** — benchmark your molecules head-to-head or against
  FDA-approved-drug property distributions.

## When NOT to Use This Skill

- **Biologics and non-drug-like matter** — peptides, oligonucleotides, PROTACs,
  antibodies, inorganics, and metal complexes fall outside the applicability
  domain of these descriptors and models; results are unreliable.
- **As a replacement for assays** — these are predictions (typical classification
  AUC 0.7–0.85). Confirm any decision-critical finding in vitro / in vivo.
- **Plain descriptor calculation or SMILES parsing** — if you only need MW, cLogP,
  fingerprints, or standardization, use `rdkit` directly. Use `smiles-validation`
  to clean/canonicalize input structures first.
- **Training new QSAR/ADMET models** — for dataset loading, splits, and model
  fitting use `pytdc` (Therapeutics Data Commons) or `deepchem`.
- **Interpreting *why* a molecule is flagged, in depth** — for LLM-driven
  mechanistic ADMET reasoning and optimization suggestions, pair with
  `admet-reasoning`.

## Setup

```bash
pip install rdkit numpy pandas      # core: descriptors, alerts, QED, PAINS, SA score
pip install PyTDC                    # optional: benchmark datasets + admet_group
pip install admet-ai                 # optional: fast Chemprop-RDKit ADMET predictions
```

`rdkit` alone covers tiers 1 and 2. On conda, prefer `conda install -c conda-forge
rdkit`. The ML tier (`PyTDC`, `admet-ai`) is optional and only needed for the
learned endpoints noted in [references/endpoints.md](references/endpoints.md).

## Quick Start

Compute the physicochemical + drug-likeness core and a PAINS check for one
molecule (aspirin):

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, QED, rdMolDescriptors
from rdkit.Chem import FilterCatalog
from rdkit.Chem.FilterCatalog import FilterCatalogParams

mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
if mol is None:
    raise ValueError("unparseable SMILES")   # always guard the parse

panel = {
    "MW":       Descriptors.MolWt(mol),
    "cLogP":    Crippen.MolLogP(mol),
    "TPSA":     rdMolDescriptors.CalcTPSA(mol),
    "HBD":      rdMolDescriptors.CalcNumHBD(mol),
    "HBA":      rdMolDescriptors.CalcNumHBA(mol),
    "RotBonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
    "Fsp3":     rdMolDescriptors.CalcFractionCSP3(mol),
    "QED":      QED.qed(mol),
}

params = FilterCatalogParams()
params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
pains_hit = FilterCatalog.FilterCatalog(params).HasMatch(mol)
```

Map each value to a traffic light with the threshold table in
[references/recipes.md](references/recipes.md#traffic-light-thresholds), then read
the endpoint meaning in [references/endpoints.md](references/endpoints.md).

## Panel Coverage

| Category | Endpoints |
|----------|-----------|
| Absorption | Caco-2 permeability, HIA, P-gp substrate, aqueous solubility (LogS / ESOL) |
| Distribution | BBB penetration, plasma protein binding, volume of distribution |
| Metabolism | CYP3A4 / 2D6 / 2C9 liability, metabolic soft spots |
| Excretion | clearance route (hepatic vs renal) and rate class |
| Toxicity | hERG, AMES mutagenicity, DILI, skin sensitization, phospholipidosis, LD50 class, PAINS |
| Drug-likeness | Lipinski Ro5, QED, synthetic accessibility, Fsp3 |

Per-endpoint clinical significance, thresholds, applicability limits, and
therapeutic-area prioritization are in
[references/endpoints.md](references/endpoints.md). Concrete RDKit / PyTDC /
ADMET-AI code for each tier — descriptor panel, ESOL, SA score, structural-alert
matching, PAINS/Brenk catalogs, batch CSV scoring, ML predictions — is in
[references/recipes.md](references/recipes.md).

## Interpreting Results

- **GREEN** — within the favorable range; no action.
- **YELLOW** — borderline; optimize only if it stacks with other marginal flags.
- **RED** — likely liability; address it or justify why it is acceptable for the
  target.

Two cross-cutting rules the traffic lights do not encode for you:

- **Context flips the sign.** A RED for BBB penetration is *good* for a peripheral
  drug and *bad* for a CNS drug. Read every flag against your therapeutic goal.
- **Safety outranks polish.** A molecule with GREEN toxicity but YELLOW
  drug-likeness beats one with GREEN drug-likeness but RED hERG/AMES/DILI. See the
  prioritization ladder in
  [references/endpoints.md](references/endpoints.md#prioritization).

## Limitations

- Structural alerts are **necessary-not-sufficient**: a SMARTS match signals
  similarity to a known liability class, not confirmed activity (high sensitivity,
  low specificity — expect false positives).
- Descriptor-based PK endpoints (clearance, VDss, PPB) are the **least accurate**;
  treat them as directional, not quantitative.
- Predictions are reliable only for **drug-like small molecules** (roughly MW
  150–900, conventional heteroatom composition). Outside that, trust nothing.

## Related Skills

- `rdkit` — descriptor calculation, fingerprints, substructure search (the engine
  under tiers 1–2).
- `smiles-validation` — standardize / canonicalize / sanitize structures before
  scoring.
- `pytdc` — Therapeutics Data Commons datasets, splits, and the ADMET benchmark
  group for training or evaluating models.
- `deepchem` — deep-learning ADMET/tox models (GNNs, multitask).
- `medchem` — broader medicinal-chemistry alert/filter rule sets.
- `admet-reasoning` — LLM-driven mechanistic interpretation and optimization
  advice on top of a computed panel.
