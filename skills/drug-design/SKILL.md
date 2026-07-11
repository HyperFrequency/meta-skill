---
name: drug-design
version: 0.1.0
description: >-
  Orchestrate an end-to-end structure-based drug discovery campaign by chaining
  the sibling chemistry skills into a deterministic, reproducible pipeline:
  structure prediction, pocket detection, druggability, de novo design,
  drug-likeness filtering, docking, interaction scoring, binding-affinity
  prediction, MM/GBSA rescoring, consensus ranking, and 3D visualization —
  across five modes (full, lead-opt, screen, assess, denovo). Use WHEN planning
  or running a whole campaign from a target (PDB or sequence), optimizing a hit,
  screening a library, or assessing druggability, and you want guaranteed stage
  order, validated inter-stage I/O contracts, and a provenance log. Do NOT use
  for a single stage — call the specific sibling skill directly
  (`pocket-detection`, `molecular-docking`, `binding-affinity`,
  `denovo-design`, `admet-prediction`); nor for wet-lab execution or any
  clinical/therapeutic claim. Every output is a computational estimate for
  prioritization only.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Drug Design Pipeline

## Overview

This skill is the **orchestration layer** for structure-based drug discovery
(SBDD). A real campaign is not one tool call — it is a chain of ten-plus stages
that must run in the right order, hand validated data to each other, and leave a
trail you can audit. This skill tells you how to compose the individual sibling
skills into that chain, which chain to pick for a given goal, and how to keep the
run reproducible instead of a pile of ad-hoc manual invocations.

The transferable idea is **deterministic orchestration**: fix the stage order,
validate the I/O contract between every pair of stages, log each invocation to a
provenance manifest, and stop on the first failure with a clear diagnostic. That
turns a fragile 11-step manual process into a workflow a reviewer can replay and
critique.

Each stage is owned by a focused sibling skill — this skill does not re-implement
docking, scoring, or generation. It decides *what runs, in what order, on what
data*, and enforces the contracts between them.

Deep material is split out:
- Full per-mode stage tables, inter-stage I/O contracts (JSON schemas), and the
  output directory layout → [references/modes-and-stages.md](references/modes-and-stages.md).
- The deterministic orchestration pattern (recommended CLI contract, stage-runner
  design, schema validation, provenance manifest, skip/non-fatal handling) and the
  failure-recovery playbook → [references/orchestration.md](references/orchestration.md).

## When to Use This Skill

Reach for `drug-design` when the request spans **multiple stages** of a campaign:

- "Find drug candidates for this target" (a PDB file or a bare sequence).
- "Optimize this hit compound" — generate and rank analogs against the target.
- "Screen this compound library" against a pocket and rank the survivors.
- "Is this target druggable?" — pocket + druggability + a visual report.
- "Design novel molecules for this pocket" de novo, then dock and rank them.

Trigger phrases: "drug discovery pipeline", "find/design drugs for target",
"screen compounds", "druggability assessment", "de novo design campaign",
"lead optimization", "run the whole SBDD workflow".

## When NOT to Use This Skill

- **A single stage.** If the user only needs one step, call that sibling skill
  directly — do not spin up the whole pipeline. Pockets → `pocket-detection`;
  poses → `molecular-docking`; affinity/ranking → `binding-affinity`; molecule
  generation → `denovo-design`; drug-likeness/tox → `admet-prediction`;
  structure from sequence → `structure-prediction`; rendering →
  `molecule-visualization`.
- **Ligand-based work with no protein structure** (QSAR, similarity search,
  property models on SMILES alone) — use the property/generation skills directly.
- **Wet-lab execution or assay design** — this is a computational triage layer.
- **Any quantitative, regulatory, or clinical claim.** Predicted affinities,
  druggability scores, and generated molecules are hypotheses to test, never
  evidence of efficacy or safety.

## The Five Workflow Modes

Pick the mode from the user's intent; each is a fixed stage chain.

| Intent | Mode | Key inputs | Chain (abbreviated) |
|--------|------|------------|---------------------|
| Find candidates for a target | `full` | PDB **or** sequence | structure? → pockets → druggability → de novo → filter → dock → score → affinity → rescore → consensus → 3D |
| Improve an existing hit | `lead-opt` | PDB + hit ligand | analogs → filter → dock → affinity → consensus |
| Rank a compound library | `screen` | PDB + library | pockets → batch score → dock top hits → affinity → consensus |
| Assess druggability | `assess` | PDB **or** sequence | structure? → pockets → druggability → visualization |
| Generate novel molecules | `denovo` | PDB (+ pocket) | pockets → SBDD gen → fragment gen → filter → dock → affinity → consensus |

`structure?` runs only when the input is a sequence rather than a PDB. Full stage
tables (stage → owning sibling skill → input → output) for every mode are in
[references/modes-and-stages.md](references/modes-and-stages.md).

## Stage Sequence and Data Flow

The canonical `full` campaign is a linear DAG; other modes are subsets of it:

```
sequence ─(structure-prediction)─► structure.pdb
structure.pdb ─(pocket-detection)─► pockets.json ─► druggability.json
pockets.json ─(denovo-design)─► candidates.sdf ─(filter)─► filtered.sdf
filtered.sdf + structure.pdb ─(molecular-docking)─► poses.sdf ─► interactions.json
poses.sdf ─(binding-affinity)─► affinity.json ─► mmgbsa.json ─► consensus.json
consensus.json + poses.sdf ─(molecule-visualization)─► complex_3d.html
```

Data crosses stage boundaries as files with a defined shape. The three contracts
that actually break pipelines if malformed are `pockets.json` (its
`center: [x,y,z]` field feeds docking), `affinity.json` (`predictions[]`), and
`consensus.json` (`rankings[]`, the final artifact). Validate these between
stages — full JSON schemas are in
[references/modes-and-stages.md](references/modes-and-stages.md).

## Orchestrate Deterministically

Whether you drive the stages by hand or wrap them in a small orchestrator script,
enforce four guarantees so the run is reproducible and reviewable:

1. **Fixed order.** Stages run in the DAG order above; nothing is skipped or
   reordered silently. Expose an explicit `--skip` list when a stage must be
   bypassed (e.g. the user supplies a pre-computed pocket).
2. **Contract validation.** After each stage, check the output file exists and
   matches the expected schema *before* feeding it downstream. Fail fast with the
   offending file named — a bad `center` field caught here saves a wasted dock.
3. **Provenance.** Append every invocation (stage, arguments, output path,
   timestamp) to a manifest so a reviewer can replay or critique the whole trace.
4. **Stop on first fatal failure;** mark cosmetic stages (visualization) non-fatal
   so a missing plotting dependency does not sink an otherwise-complete run.

A recommended orchestrator CLI contract (`--mode`, `--protein`/`--sequence`,
`--ligand`, `--library`, `--pocket`, `--output-dir`, `--skip`, `--top-n`,
`--docking-method`) and a stage-runner design that implements all four guarantees
are in [references/orchestration.md](references/orchestration.md).

## Failure Modes and Recovery

Common breakages and the first thing to try:

| Symptom | Likely cause | First move |
|---------|-------------|------------|
| "No pockets detected" | small protein / no clear cavity | pass a manual `--pocket` and skip detection |
| Docking fails | missing engine or malformed PDB | switch `--docking-method` (vina ↔ diffdock); re-clean the PDB |
| Schema validation fails | upstream stage emitted an unexpected shape | inspect that stage's output file directly |
| "No analogs generated" | invalid/over-complex input ligand | verify the SMILES parses before rerunning |

The full recovery table, edge cases, and scaling boundaries are in
[references/orchestration.md](references/orchestration.md).

## Related Skills

- `structure-prediction` — sequence → 3D structure (stage 1 when no PDB).
- `pocket-detection` — locate and score binding sites; owns druggability.
- `denovo-design` — generate SBDD, fragment, and analog molecules; drug-likeness filter.
- `molecular-docking` — produce and interaction-score docked poses.
- `binding-affinity` — pKd/ΔG prediction, MM/GBSA rescore, consensus ranking.
- `admet-prediction` — filter candidates by drug-likeness and safety.
- `molecule-visualization` — 2D/3D rendering of complexes and reports.

## References

- Eberhardt, J. et al. "AutoDock Vina 1.2.0." *J. Chem. Inf. Model.* 61, 3891-3898 (2021).
- Corso, G. et al. "DiffDock: Diffusion Steps, Twists, and Turns for Molecular Docking." *ICLR* (2023).
- Le Guilloux, V. et al. "Fpocket: an open source platform for ligand pocket detection." *BMC Bioinformatics* 10, 168 (2009).
- Wang, R. et al. "The PDBbind database." *J. Med. Chem.* 47, 2977-2980 (2004).
