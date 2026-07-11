---
name: admet-reasoning
version: 0.1.0
description: >-
  Turn ADMET liabilities into mechanistic explanations for a small molecule
  (SMILES): map each flagged risk to its structural cause, the biological
  mechanism it drives (hERG cation-pi block, CYP heme coordination,
  nitrenium-ion DNA adducts, epoxide bioactivation), and a concrete structural
  fix — alongside physicochemical checks (LogP, MW, TPSA, QED, ESOL solubility).
  Combines an RDKit SMARTS structural-alert catalogue with property thresholds
  and a chain-of-thought reasoning template (after CoTox / DrugR). Use to
  interpret flagged liabilities, plan lead optimization, or write
  medchem-readable tox rationale. Do NOT use to compute raw ADMET scores or
  probabilities (use `admet-prediction`), to run the optimization itself (use
  `molecular-optimization`), for biologics or macromolecules, or as a
  regulatory-grade validated tox predictor — the alerts are high-recall
  heuristics that generate hypotheses, not verdicts.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (RDKit)"
---

# ADMET Reasoning

## Overview

Most ADMET tools emit bare scores — `hERG = 0.85`, `DILI = high` — with no
account of *why*. This skill adds the missing layer: for each liability it names
the **structural cause**, explains the **biological mechanism**, and proposes a
**structural fix**. It works from two evidence streams, both computed with
RDKit:

1. **Structural alerts** — a SMARTS substructure catalogue where each pattern is
   annotated with the endpoint it flags (hERG, DILI, CYP inhibition, AMES
   mutagenicity, aqueous solubility), the mechanism, and a remediation.
2. **Physicochemical thresholds** — property ranges (LogP, MW, TPSA, QED, HBA,
   HBD, rotatable bonds, ESOL-estimated LogS) whose violation implies an
   absorption, permeability, or developability risk.

The output is a structured liability report you can hand to a medicinal chemist
or feed into an optimization loop. The reasoning method follows chain-of-thought
toxicity interpretation as described in CoTox (Park et al., 2025) and explicit
liability reasoning before optimization as in DrugR (Liu et al., 2026): grounding
each prediction in structural and biological context, rather than a raw label,
is what makes the assessment actionable.

**This file is a router.** Depth lives in `references/`:

- `references/structural-alerts.md` — the full SMARTS alert catalogue (pattern →
  endpoint, cause, mechanism, fix), how to extend it, and false-positive caveats.
- `references/physchem-liabilities.md` — property thresholds, severities, the
  ESOL solubility equation, and the physicochemical rationale.
- `references/reasoning-workflow.md` — the cause→mechanism→fix method, an LLM
  reasoning-prompt template, integration with lead optimization, and citations.
- `references/reference-implementation.md` — a runnable RDKit reference script
  (single molecule + batch CSV) that emits the JSON report.

## When to Use This Skill

- **After ADMET prediction.** A model flagged a liability; you need to know the
  responsible substructure and how to fix it.
- **Lead-optimization planning.** Decide *which* structural features to modify
  and *why*, before proposing analogues.
- **Toxicity write-ups.** Produce medchem-readable rationale ("this aniline is
  the AMES risk because CYP1A2 N-hydroxylation forms a nitrenium ion") instead
  of an opaque score.
- **Design review.** Check whether a proposed modification actually neutralizes
  the flagged mechanism rather than a cosmetic change elsewhere in the molecule.

## When NOT to Use This Skill

- **Computing raw ADMET scores / probabilities.** This skill *interprets*
  liabilities; it does not train or run QSAR/ML predictors. Use `admet-prediction`.
- **Running the optimization itself.** For generating and scoring analogues, use
  `molecular-optimization`; this skill supplies the reasoning that steers it.
- **Automated alert filtering at library scale** (PAINS/BRENK/NIH sweeps) — use a
  curated filter library such as `medchem`; this catalogue is a small, mechanism-
  annotated subset, not an exhaustive screening ruleset.
- **Biologics / macromolecules.** The SMARTS patterns and descriptors assume
  drug-like small molecules.
- **Regulatory or safety decisions.** Alerts are high-recall, low-precision
  heuristics that generate *hypotheses*. They are not validated predictions and
  carry real false-positive rates — never treat a flag as a verdict.

## How the Reasoning Works

For every input SMILES the skill:

1. Parses and canonicalizes the molecule (RDKit `Chem.MolFromSmiles`).
2. Computes physicochemical descriptors and checks them against thresholds
   (`references/physchem-liabilities.md`).
3. Runs each SMARTS alert as a substructure match; every hit contributes a
   `{endpoint, structural_cause, mechanism, suggested_fix}` record
   (`references/structural-alerts.md`).
4. Aggregates into an overall assessment (CLEAN / MINOR / MODERATE / SIGNIFICANT
   by liability count) and emits a JSON report.

The value is in step 3's annotations. A raised hERG flag becomes: *basic
piperazine (pKa ~8.5) → protonated amine engages the channel inner vestibule via
cation-pi interaction → replace with morpholine to keep the H-bond acceptor while
dropping basicity.* That is a hypothesis a chemist can act on and a reviewer can
falsify. See `references/reasoning-workflow.md` for the chain-of-thought template
and how to wire the report into an LLM optimization loop.

## Quick Start

The reference implementation (full source in
`references/reference-implementation.md`) wraps RDKit:

```bash
pip install rdkit numpy pandas   # modern wheels ship as `rdkit`, not `rdkit-pypi`

# single molecule -> JSON + human-readable summary
python reason_admet.py --smiles "Nc1ccc(cc1)[N+](=O)[O-]" --output report.json

# focus specific endpoints
python reason_admet.py --smiles "CCN1CCN(CC1)c1ccccc1" --endpoints hERG,CYP

# batch a CSV (column defaults to SMILES)
python reason_admet.py --input compounds.csv --output liabilities.json
```

A report for `Nc1ccc(cc1)[N+](=O)[O-]` (p-nitroaniline) surfaces an AMES alert
(aromatic amine + nitro → nitroreduction and N-hydroxylation give DNA-reactive
species) and a DILI alert on the nitro group.

## Liability Coverage

| Endpoint | Detected via | Example alert |
|----------|-------------|---------------|
| **hERG** (cardiotox) | structural alerts | basic piperazine / piperidine, electron-rich azoles |
| **DILI** (hepatotox) | structural alerts | nitro group, fused PAH, reactive dione scaffolds |
| **CYP inhibition** | structural alerts | heme-coordinating azoles, planar biphenyls |
| **AMES** (mutagenicity) | structural alerts | aromatic amines, para-nitroaniline |
| **Aqueous solubility** | alerts + ESOL LogS | fused aromatics; LogP / LogS thresholds |
| **Absorption / developability** | physchem thresholds | MW, TPSA, HBD/HBA, RotBonds, QED |

The catalogue is deliberately small and mechanism-annotated; extend it in
`references/structural-alerts.md`.

## Failure Modes & Boundaries

- **False positives are expected.** SMARTS alerts fire on the substructure
  regardless of local context (steric shielding, deactivating substituents,
  metabolic soft spots elsewhere). Treat every hit as a hypothesis to confirm,
  not a rejection. A benzene ring in `c1ccc2ccccc2c1` matches "fused aromatic"
  even when the real molecule is highly soluble.
- **Over-broad SMARTS.** Some patterns (e.g. the pyrimidinedione DILI alert)
  match endogenous or benign scaffolds. Tighten SMARTS before using a report to
  kill a series.
- **Coverage is partial.** Absence of alerts is *not* a clean bill — the
  catalogue covers common liabilities, not all of ADMET (no PK/PBPK, no BBB, no
  transporter, no CYP-isoform selectivity).
- **ESOL LogS is an estimate.** The Delaney regression is a rough solubility
  proxy, not a measurement; use it for triage only.
- **Invalid SMILES** return an `{"error": ...}` record rather than crashing the
  batch — check for it before aggregating.

## Related Skills

- `admet-prediction` — compute the ADMET scores this skill interprets (run first).
- `molecular-optimization` — iterative analogue generation steered by this
  skill's liability reasoning.
- `medchem` — library-scale structural-alert / PAINS filtering.
- `rdkit` — the underlying cheminformatics engine for descriptors and SMARTS.
