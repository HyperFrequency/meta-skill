# The meta-class duty

Class 8 is the **meta-class**: "it audits ALL other classes' runs (it is the
meta-class)." Every other eval class (1 skill, 2 prompt/workflow, 3 agent/session,
4 market rewards, 5 graph workflows, 6 rescue, 7 context/compaction, 9 temporal
authoring, 10 accuracy) produces logged experiment records; repro-eval samples
those records, re-executes them (`references/re-execution-runner.md`), and gates
on the delta (`references/delta-gate.md`). If a class's own runs do not reproduce,
its gates are decorative — a green result you cannot re-obtain gates nothing.

This file covers the responsibilities that only the meta-class carries.

## What the audit covers

- **Cross-class sampling.** Periodically (and in CI) draw a deterministic
  `trace_id`-hash head sample across every class's recent records and re-execute
  them. Deterministic sampling means the audit slice is itself reproducible —
  the reproducibility auditor must not be a source of nondeterminism.
- **Completeness lint on every class.** Each class emits the class-8
  completeness fields (`reproduction-contract.md`); the audit fails a class whose
  records are structurally un-reproducible (missing snapshot hash, unpinned
  dataset, absent scorer version) even before any numeric drift.
- **Rollup integrity.** Leaderboard and rollup values are only as trustworthy as
  the runs beneath them; the audit re-derives sampled rollup inputs and raises a
  drift alarm when a historical run no longer reproduces (see delta-gate).

## CI provenance-lint contract

"Provenance lint runs in CI on every eval PR." Wire it as a required check:

- On any PR that adds or changes an eval class, a scorer, a criteria schema, or a
  dataset, run the provenance lint over the **new/changed** records' shapes:
  every completeness-checklist field must be populated and every reference
  resolvable.
- The lint is deterministic (no model calls) so it is fast and cannot flake — it
  checks *structure and resolvability*, not numeric reproduction. Numeric
  reproduction (actual re-execution) runs on a schedule / nightly against sampled
  historical records, because it costs model calls.
- A PR that regresses provenance completeness (drops a logged field, makes a
  reference danglable, mutates a dataset in place) fails the check.

## Methodology-drift visibility

The meta-class also makes *methodology* drift visible, not just numeric drift:

- **Feedback-type ablation matrices (Reflexion).** When an eval's methodology
  changes which feedback signal it uses, record the ablation so a later
  reproduction knows which methodology produced the logged number — a result
  reproducible under one feedback design but not another is a documented,
  not silent, difference.
- **Preregistration records.** For classes with a preregistered design (notably
  class 4 market rewards — power analysis, multiple-testing corrections applied
  to the eval suite itself), the prereg record is part of provenance; a
  reproduction confirms the analysis was run as registered, catching
  after-the-fact metric shopping.
- **K/B/I epistemic tags** travel with every record so the audit can tell which
  components were claimed deterministic vs distributional, and hold each to the
  right tolerance.

## Anti-gaming: disjoint write scope

The single hardest rule, because the meta-class is the ultimate gate:

- **The run under audit can never edit its own reproduction gate.** Reproduction
  tolerances, the completeness schema, and the provenance lint live in the scorer/
  criteria registry with their own versions; a class (or a Loop-1 optimizer
  evolving that class) has **disjoint write scope** — it cannot widen its own
  reproduction band to pass (swe-loop disjoint-write pattern;
  ce-harness-engineering surface locks).
- Tightening the reproduction schema or a tolerance is a **criteria-version bump**
  (`contract-rfc`-style), gated on the class's own held-out calibration set — not
  an ad-hoc edit. Every scorecard records the schema version it was graded under
  so historical reproduction verdicts stay interpretable.
- Reproduction verdicts (including drift root causes) are written to `_llm_scores`
  with `source_type = annotation`; judge-vs-human agreement on reproduction calls
  is itself a regression-gated metric (Align-Evals), so the auditor is audited.

## Relationship to the ancestor gate

`neuro-quant-research-proof` is the quant-monorepo instance of this duty — a
verify-before-claiming gate over repo-local research/Modal/strategy/release
evidence. repro-eval is the harness-wide generalization: same "prove it before
you claim it" doctrine, but the artifact under proof is any logged harness
experiment and the proof is *re-execution within tolerance*, not repo-local
artifact validation. When an audited experiment IS a quant artifact (a nautilus
backtest, an Optuna study), hand the repo-local evidence checks back to
`neuro-quant-research-proof` and keep the re-execution/delta gating here.
