---
name: smiles-validation
version: 0.1.0
description: >-
  Strictly validate machine-generated SMILES with RDKit, compare a proposed
  molecule against an original (Tanimoto similarity, Murcko scaffold
  preservation, maximum common substructure), and verify that a claimed edit
  ("added a hydroxyl", "removed the nitro group") actually happened in the
  structure. Use after any step that emits or mutates a molecule — LLM
  molecule generation, lead-optimization loops, reaction/library enumeration,
  batch QC of a generated set — to reject un-parseable or chemically
  impossible structures and self-inconsistent edits before they flow
  downstream. Not for docking, ADMET/property prediction, 3D conformer
  generation, retrosynthesis, or authoring general RDKit pipelines: see the
  `rdkit`, `datamol`, `admet-prediction`, and `deepchem` skills.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (RDKit)"
---

# SMILES Validation

## Overview

Generative models and LLMs routinely emit SMILES that either fail to parse,
encode chemically impossible valences, or do not match the change the model
*said* it made. This skill is a strict, deterministic gate that catches those
failures before they contaminate a screening set, a training corpus, or an
optimization loop. It wraps RDKit and does three things:

- **Parse + sanitize validation** — reject strings RDKit cannot read, catch
  valence errors, unbalanced parentheses/brackets, and flag out-of-range size
  or molecular weight. Emit the canonical SMILES, formula, MW, and atom counts.
- **Structural comparison** — quantify how far a proposed molecule sits from
  an original via Tanimoto similarity (Morgan fingerprints), generic Murcko
  scaffold identity, and maximum common substructure (MCS).
- **Modification verification** — take a natural-language claim about an edit
  and confirm the corresponding substructure was actually added, removed, or
  is present, using SMARTS matching on both molecules.

The gate is intentionally conservative: an ambiguous result is surfaced as a
warning or `INCONCLUSIVE`, never silently passed.

## When to Use This Skill

- **Immediately after molecule generation** — validate every SMILES an LLM or
  generative model produces before reporting, storing, or scoring it.
- **Inside optimization / editing loops** — confirm each proposed analogue is
  valid *and* that the intended modification is really present.
- **Batch library QC** — screen a CSV/list of generated structures and get a
  valid/invalid tally with per-row diagnostics.
- **Reproducibility checks** — canonicalize SMILES so two representations of
  the same molecule compare equal.

## When NOT to Use This Skill

- **Property, activity, or ADMET prediction** — this skill judges structural
  validity, not whether a molecule is good. Use `admet-prediction`,
  `admet-reasoning`, or `deepchem`.
- **Docking, pose generation, or binding scoring** — out of scope entirely.
- **3D conformer generation, retrosynthesis, or reaction planning.**
- **General-purpose RDKit / cheminformatics authoring** — if you need
  descriptors, transforms, standardization pipelines, or plotting, reach for
  the `rdkit` or `datamol` skills. This skill is the narrow validation gate
  they can call.
- **Non-SMILES inputs** (InChI, MOL blocks, SELFIES) — convert to SMILES with
  `rdkit` first, then validate here.

## Setup

```bash
pip install rdkit          # official wheels (RDKit >= 2022.09); do NOT use the
                           # unmaintained "rdkit-pypi" package
# or: conda install -c conda-forge rdkit
```

Batch mode also needs `pandas` (`pip install pandas`).

## Core Capabilities

### 1. Validate a single SMILES

Parses, sanitizes, canonicalizes, and reports diagnostics. A string is
**VALID** only if RDKit both parses *and* sanitizes it. Warnings (tiny/huge
molecule, MW > 1000) do not fail validation but are surfaced.

```bash
python scripts/validate.py --smiles "c1ccccc1"
```

### 2. Compare original vs proposed

Reports Tanimoto similarity, whether the generic Murcko scaffold is preserved,
MCS atom count, and atom-count delta, then classifies the relationship:

| Tanimoto | Classification            |
| -------- | ------------------------- |
| >= 0.6   | `lead_optimization`       |
| 0.4-0.6  | `significant_modification`|
| < 0.4    | `de_novo_design`          |

```bash
python scripts/validate.py --original "c1ccccc1" --proposed "c1ccc(O)cc1"
```

### 3. Verify a claimed modification

Given a claim like `"Added hydroxyl group"`, matches the relevant SMARTS on
both molecules and confirms the add/remove/replace direction. Returns
`VERIFIED`, `FAILED`, or `INCONCLUSIVE` (no structural check maps to the
claim).

```bash
python scripts/validate.py --original "c1ccccc1" --proposed "c1ccc(O)cc1" \
  --check-modification "Added hydroxyl group"
```

### 4. Batch validation

Validate a column of SMILES from a CSV and write a JSON report.

```bash
python scripts/validate.py --input generated.csv --smiles-col SMILES \
  --output validation_report.json
```

## Reference Material

- **`references/rdkit-api.md`** — the exact RDKit calls behind each check
  (parsing, sanitization, descriptors, the modern `rdFingerprintGenerator`
  Morgan API vs the legacy `AllChem` call, Murcko scaffolds, `rdFMCS`,
  SMARTS substructure matching), their parameters, and the chemistry gotchas
  (aromaticity, stereochemistry, salts/fragments, isotopes, tautomers).
- **`references/cli-reference.md`** — full `validate.py` flag reference, the
  JSON output schema for each mode, the functional-group SMARTS table used by
  modification verification, classification thresholds, failure modes, and
  troubleshooting.
