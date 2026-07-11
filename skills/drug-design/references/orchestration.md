# Deterministic Orchestration and Recovery

How to drive the multi-stage campaign so it is reproducible, reviewable, and
fails loudly instead of silently. This is the transferable engineering pattern —
independent of which library each sibling skill uses internally.

You can run the stages by hand (call each sibling skill in DAG order, validating
outputs as you go) or wrap them in a thin orchestrator script. Either way, the
four guarantees below are what separate a reproducible run from a fragile one.

---

## Why Orchestrate Instead of Chaining by Hand

Manually invoking 10+ stages in the right order is where campaigns go wrong:

- A skipped or reordered stage produces a plausible-looking but wrong result.
- A schema mismatch between two stages surfaces as a crash three stages later,
  far from the real cause.
- With no invocation log, the run cannot be replayed or critiqued.
- One missing optional dependency (e.g. a plotting library) aborts an otherwise
  complete run.

A deterministic orchestrator removes all four failure classes.

## The Four Guarantees

1. **Fixed stage order.** Build the stage list once from the mode; run it in
   order. Never let the model reorder or drop stages implicitly. Skipping is
   allowed only through an explicit, logged `--skip` list.
2. **Contract validation between stages.** After each stage: confirm the expected
   output file exists, then validate its schema (see the contracts in
   `modes-and-stages.md`). Only then feed it downstream. Catching a bad
   `pockets.json[0].center` here avoids a wasted docking run.
3. **Provenance manifest.** Append one JSON line per invocation to
   `_manifest.jsonl` (stage name, resolved arguments, output path, UTC
   timestamp). A reviewer replays or audits the full trace from this file.
4. **Fail fast, but tolerate cosmetics.** Stop the pipeline on the first *fatal*
   stage failure with the offending stage and file named. Mark purely cosmetic
   stages (visualization/reporting) **non-fatal** so a missing plotting
   dependency logs a warning and the run still completes.

## Recommended Orchestrator CLI Contract

If you wrap the stages in a script, this argument surface covers all five modes
cleanly. These names are a sound default interface, not a third-party API — adapt
as needed.

| Argument | Required | Purpose |
|----------|----------|---------|
| `--mode` | yes | `full` \| `lead-opt` \| `screen` \| `assess` \| `denovo` |
| `--protein` | yes* | input PDB (*or `--sequence`) |
| `--sequence` | no | protein sequence; triggers structure prediction when no PDB |
| `--ligand` | `lead-opt` | hit ligand `.sdf`/SMILES to optimize |
| `--library` | `screen` | compound library `.sdf` to screen |
| `--pocket` | no | pre-computed pocket JSON (skips pocket detection) |
| `--output-dir` | no | run directory (default `./pipeline_results/`) |
| `--skip` | no | comma-separated stages to bypass |
| `--top-n` | no | how many compounds to carry forward (default 10) |
| `--docking-method` | no | `vina` (default) or `diffdock` |

Validate at startup: exactly one of `--protein`/`--sequence` present; input files
exist; `--ligand` present for `lead-opt`; `--library` present for `screen`.
Contain `--output-dir` inside the working directory so a stage cannot write
outside the run tree.

## Stage-Runner Design

Model each stage as a small record: `{name, owning_skill, args, expected_output,
schema_check, fatal}`. The runner, per stage:

1. Resolve and invoke the owning sibling skill with `args`.
2. On non-zero exit, print the last lines of stderr, mark the stage failed, and
   stop (unless `fatal=False`, then warn and continue).
3. Assert `expected_output` exists; if `schema_check` is set, run it and stop on a
   validation error naming the file.
4. Append the invocation to `_manifest.jsonl`.
5. Record status + elapsed time into a `pipeline_report.json` accumulator.

At the end, write `pipeline_report.json` (per-stage status, timings, the failed
stage if any). Exit non-zero if the run did not complete, so callers can branch.

Selecting a stage subset per mode is just building this list differently — the
`full` list, minus generation/scoring for `assess`, minus pocket detection for
`lead-opt`, and so on (see `modes-and-stages.md` for each mode's stages).

---

## Failure Recovery Playbook

| Error | Cause | Recovery |
|-------|-------|----------|
| Stage script/skill not found | sibling skill not installed or misnamed | ensure the sibling skills are present; check the stage's owning-skill name |
| Schema validation failed | upstream stage emitted an unexpected shape | open that stage's output file and inspect the failing field before rerunning |
| "No pockets detected" | protein too small or no clear cavity | supply manual coordinates via `--pocket` and add `pocket-detection` to `--skip` |
| Docking failed | missing docking engine or malformed PDB | install/verify the engine, or switch `--docking-method` (vina ↔ diffdock); re-clean and re-protonate the PDB |
| "No analogs generated" | invalid or over-complex input ligand | verify the ligand SMILES parses (e.g. RDKit `Chem.MolFromSmiles`) before rerunning `lead-opt` |
| Empty consensus ranking | all upstream score files missing/empty | check that at least one of `affinity.json` / `mmgbsa.json` was produced |

## Edge Cases and Boundaries

- **Sequence-only input.** `full` and `assess` accept a raw sequence and prepend
  structure prediction. A predicted structure carries model error into every
  downstream stage — treat its pockets and scores as lower-confidence.
- **Pre-computed pocket.** When the user supplies `--pocket`, skip detection and
  feed those coordinates straight to docking; do not silently re-detect.
- **Docking is the cost bottleneck.** In `screen` mode never dock the full
  library — batch-score first and dock only the `--top-n` survivors. Docking cost
  scales with the number of ligands, so `--top-n` is the main scaling knob.
- **Non-fatal cosmetics.** Visualization/reporting stages must not abort a
  completed scientific run; downgrade their failures to warnings.
- **Everything is an estimate.** Druggability scores, predicted affinities
  (~1-2 log-unit pKd error), and generated molecules are prioritization
  hypotheses. Report raw values with their uncertainty; never rescale them to
  match expectations, and never present them as experimental or clinical evidence.
