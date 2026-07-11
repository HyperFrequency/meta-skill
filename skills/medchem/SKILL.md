---
name: medchem
version: 0.1.0
description: >-
  Medicinal-chemistry filtering and triage of small-molecule libraries with the
  `medchem` Python library (wraps RDKit + datamol). Apply drug-likeness,
  lead-like, fragment, and CNS rules (Lipinski Ro5, Veber, Oprea, Rule of Three,
  REOS, golden triangle), PAINS and structural-alert sets (Common Alerts, NIBR,
  Lilly demerits), chemical-group / SMARTS detection, molecular-complexity
  metrics, and property constraints — all with built-in parallelization. Use to
  prioritize or triage compound collections, flag reactive or assay-interfering
  structures, gate hits by discovery stage (screening → hit-to-lead → lead
  optimization), or detect functional groups and warheads. NOT for full ADMET /
  PK prediction (use `admet-prediction`), plain descriptor / fingerprint
  calculation or standardization (use `rdkit` / `datamol`), docking or scoring,
  ML-model training, or biologics / peptides / PROTACs.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (medchem, datamol-io)"
---

# Medchem

## Overview

`medchem` is a Python library for triaging and prioritizing small molecules in
drug-discovery workflows. It bundles hundreds of published and industrial
medicinal-chemistry filters — property rules, structural-alert sets, PAINS
patterns, complexity metrics, and functional-group queries — behind a uniform,
parallelized interface. It sits on top of RDKit (via `datamol`), so molecules
are native `rdkit.Chem.Mol` objects and results interoperate with the rest of a
cheminformatics stack.

This skill is a **router**. It gives you the quick-start path, a capability map,
and the judgment calls that filters do not encode for you, then delegates the
full rule catalog and per-module API to `references/`. The one rule to keep in
mind everywhere: **these filters are guidelines, not verdicts.** Roughly 10% of
marketed drugs fail the Rule of Five; natural products, antibiotics, and
prodrugs routinely violate standard rules by design. Combine filters with the
biological context and domain judgment — never auto-reject on a single flag.

## When to Use This Skill

Trigger when the user wants to:
- Apply drug-likeness / lead-like / fragment / CNS rules to a compound set
- Flag PAINS, reactive groups, or other assay-interfering / problematic
  substructures before spending assay or compute budget
- Triage a large library down to a prioritized shortlist
- Gate candidates by discovery stage (HTS screening, hit-to-lead, lead-opt)
- Score molecules with industrial alert sets (NIBR, Lilly demerits)
- Detect specific chemical groups, warheads, or scaffolds (hinge binders,
  Michael acceptors, custom SMARTS)
- Compute molecular-complexity metrics as a synthetic-accessibility proxy
- Combine several of the above with a boolean query in one pass

## When NOT to Use This Skill

- **Full ADMET / PK prediction.** For absorption, metabolism, hERG/AMES/DILI
  toxicity, or clearance calls, use `admet-prediction` — `medchem` only does
  rule/alert filtering, not learned endpoint prediction.
- **Plain descriptor or fingerprint calculation, parsing, standardization.** Use
  `rdkit` for low-level descriptors/substructure search and `datamol` for
  SMILES↔Mol conversion, sanitization, and standardization. Standardize inputs
  in `datamol` *before* filtering here.
- **Docking, scoring, or generative design.** Out of scope.
- **Training QSAR / ML models.** Filter first, then hand the survivors to
  `scikit-learn` / `deepchem`; `medchem` does not train models.
- **Biologics, peptides, oligonucleotides, PROTACs, inorganics.** These rules
  were derived for conventional small molecules and do not transfer.

## Install and Import

```bash
uv pip install medchem      # pulls rdkit + datamol as dependencies
```

```python
import datamol as dm
import medchem as mc
```

The idiomatic pipeline is always: parse strings to `Mol` objects with `datamol`,
drop the ones that fail to parse, standardize, then filter.

## Capability Map

Each row is an entry point; follow the reference link for signatures,
thresholds, return shapes, and worked examples.

| Task | Entry point | Depth |
|---|---|---|
| Single named rule on one molecule | `mc.rules.basic_rules.rule_of_five(mol)`, `...rule_of_cns`, `...rule_of_veber` | `references/rules-catalog.md` |
| Many rules over a library | `mc.rules.RuleFilters(rule_list=[...])` | `references/api.md` |
| Common structural alerts (ChEMBL/literature) | `mc.structural.CommonAlertsFilters()` | `references/api.md` |
| Novartis NIBR filter set | `mc.structural.NIBRFilters()` | `references/api.md` |
| Eli Lilly demerit scoring | `mc.structural.LillyDemeritsFilters()` | `references/api.md` |
| High-level one-shot filters | `mc.functional.*` | `references/api.md` |
| Chemical-group / SMARTS detection | `mc.groups.ChemicalGroup(groups=[...])` | `references/rules-catalog.md` |
| Named substructure catalogs | `mc.catalogs.NamedCatalogs` | `references/api.md` |
| Molecular complexity metrics | `mc.complexity.*` | `references/api.md` |
| Property-range constraints | `mc.constraints.Constraints(...)` | `references/api.md` |
| Boolean query language | `mc.query` | `references/api.md` |

> Verify exact function names, keyword arguments, and return shapes against the
> official docs (https://medchem-docs.datamol.io) before relying on them — the
> library's surface evolves across releases, and the signatures in `references/`
> are documented at capability level, not pinned to one version.

## Minimal Recipes

**Parse, drop failures, then apply one rule** (always guard the parse):

```python
mols = [dm.to_mol(smi) for smi in smiles_list]
mols = [m for m in mols if m is not None]   # a single None poisons batch steps

passes = mc.rules.basic_rules.rule_of_five("CC(=O)Oc1ccccc1C(=O)O")  # aspirin -> True
```

**Apply several rules across a library in parallel:**

```python
rfilter = mc.rules.RuleFilters(rule_list=["rule_of_five", "rule_of_veber"])
results = rfilter(mols=mols, n_jobs=-1, progress=True)   # n_jobs=-1 = all cores
```

**Screen for structural alerts:**

```python
alert_filter = mc.structural.CommonAlertsFilters()
alerts = alert_filter(mols=mols, n_jobs=-1, progress=True)
clean = [m for m, a in zip(mols, alerts) if not a["has_alerts"]]
```

**Detect a chemical group / warhead:**

```python
group = mc.groups.ChemicalGroup(groups=["hinge_binders", "michael_acceptors"])
hits = group.has_match(mols)   # one boolean per molecule
```

Extended pipelines — library triage, stage-gated lead filtering, DataFrame
integration, and batch CLI-style scripts — are in
[references/api.md](references/api.md).

## Choosing Filters by Stage

Filter strictness should track the discovery stage — broad early, tight late:

- **HTS screening:** Rule of Five + PAINS + Common Alerts (catch obvious junk).
- **Hit-to-lead:** Rule of Oprea or lead-like (soft) + NIBR + Lilly demerits
  (leave "room to grow" during optimization).
- **Lead optimization:** Rule of Drug + lead-like (strict) + full alert analysis
  + a complexity ceiling.
- **CNS targets:** Rule of CNS + tight TPSA/HBD constraints for BBB penetration.
- **Fragment-based discovery:** Rule of Three + low complexity ceiling.

Per-stage recommended filter stacks, with the exact rule thresholds and literature
citations, are in [references/rules-catalog.md](references/rules-catalog.md).

## Failure Modes and Gotchas

- **`None` molecules poison batches.** `dm.to_mol` returns `None` on unparseable
  SMILES; filter them out before any `medchem` call.
- **Sign of the PAINS/alert result.** `pains_filter` returns **True when NO
  PAINS is found** (i.e. True = clean). Structural-alert filters instead report
  `has_alerts=True` for problematic molecules. Read each direction carefully
  before combining flags.
- **Alerts are necessary-not-sufficient.** A SMARTS match means resemblance to a
  liability class, not confirmed activity — high sensitivity, low specificity,
  expect false positives. Michael acceptors flagged as "reactive" may be the
  *intended* warhead in a covalent inhibitor.
- **Lilly demerits accumulate.** A molecule is rejected at **>100 demerits**;
  several minor patterns can sum past the threshold even with no single fatal
  group. Inspect `matched_patterns`, not just the pass/fail bit.
- **Standardize first.** Salts, mixed protonation states, and tautomers make
  rule and alert results inconsistent — run `datamol` standardization upstream.
- **Marketed-drug exceptions are real.** ~10% of approved oral drugs fail Ro5;
  gate, do not delete. Preserve the reason a molecule was filtered for
  reproducibility and later review.
- **Use parallelization on large sets.** Pass `n_jobs=-1` for libraries beyond a
  few hundred molecules; the per-molecule SMARTS matching is the bottleneck.

## References

- [references/rules-catalog.md](references/rules-catalog.md) — every rule,
  structural-alert set, and chemical-group pattern: criteria, thresholds,
  literature citations, per-stage recommended stacks, and the false-positive /
  false-negative caveats.
- [references/api.md](references/api.md) — module-by-module API
  (`rules`, `structural`, `functional`, `groups`, `catalogs`, `complexity`,
  `constraints`, `query`, `utils`), return-shape reference, DataFrame
  integration, and a batch-filtering CLI pattern.

## Related Skills

- `datamol` — parse, sanitize, and standardize structures before filtering; the
  I/O and Mol-object layer this skill sits on.
- `rdkit` — low-level descriptors, fingerprints, substructure search.
- `admet-prediction` — learned ADMET/PK/tox endpoint prediction (the prediction
  counterpart to these rule-based filters).
- `admet-reasoning` — LLM-driven mechanistic interpretation of liabilities.
- `deepchem` / `scikit-learn` — train models on the surviving, filtered set.
