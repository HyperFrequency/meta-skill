# Automated design gate (non-interactive scoring and regression gating)

This file adds a second execution path to the skill. The interactive review
(driven by [rubric.md](rubric.md), [checklist.md](checklist.md), and
[decision-guide.md](decision-guide.md)) produces a human-facing critique. This
path turns the **same rubric** into an automated gate that scores a Temporal
workflow design or authored workflow code **without a human in the loop** and
**fails a build** when a design regresses against a pinned baseline.

It is the design-critic half of an evaluation class for **Temporal workflow
authoring**: static and replay-based checks over authored workflows, gated on a
determinism-and-payload floor plus a rubric-judge score floor.

Nothing here replaces the interactive path — it reuses it. The rubric and
checklist are the source of truth; this path compiles them into machine-checkable
assertions and adds the runners that produce evidence non-interactively.

---

## When to take this path (vs. interactive review)

Take the **automated gate** path when the request is any of:

- "score this design non-interactively" / "give me a pass/fail, not a writeup"
- "gate this workflow in CI" / "block the PR if the design regresses"
- "run the replay corpus and tell me if anything is non-deterministic"
- "regression-test the authored workflow against last release's baseline"
- "check patch/versioning safety automatically"

Take the **interactive review** path (the rest of this skill) when the request
is a one-off critique, an architecture read, a fitness assessment, or a
thumbs-up/down with prose. When in doubt, run interactive review; the gate is
for repeatable, unattended scoring where a numeric verdict must beat noise.

The two paths share one rubric, so a design that passes interactive review with
no `critical`/`high` findings should also clear the gate's rubric floor. If they
disagree, the disagreement is a signal that the criteria schema drifted from the
rubric — reconcile before trusting the gate.

---

## Concept: rubric → versioned criteria schema

The interactive rubric is prose. The gate needs the same judgments expressed as
a **declarative, versioned criteria schema** so runs are reproducible and
comparable across time. The schema is a weighted list of two assertion kinds
plus a gate threshold:

1. **Deterministic assertions** — checks with a mechanical yes/no answer that
   need no model: does the workflow avoid `now()`/`rand()`/system I/O in workflow
   code; does every activity that mutates external state declare an idempotency
   key; does a `patch()`/`GetVersion` marker exist for the changed branch; is the
   largest encoded payload under the platform ceiling; does the authored workflow
   only use SDK primitives on the allowed-capability list. These map one-to-one to
   [checklist.md](checklist.md) items.

2. **Model-graded assertions** — the **rubric judge**: a model scores the design
   against a rubric-section prompt (e.g. "rate history-growth strategy 0-5 with
   evidence") and returns an *evidence-before-score* verdict. Use these only for
   judgments the deterministic checks cannot make (fit, granularity tradeoffs,
   compensation completeness).

3. **Weights + threshold** — each assertion carries a weight; the weighted score
   is compared to a per-schema **threshold**. Crossing the threshold, plus the
   hard-fail invariants below, is the gate.

A concrete, versioned example lives in
[gate-criteria-schema.yaml](gate-criteria-schema.yaml). The schema is an
**immutable version**: bumping any assertion, weight, or threshold mints a new
`schema_version`, so a score is only comparable to another score under the same
version. Store the version in every result (see the score record below).

**Hard-fail invariants** (override the weighted score — any one fails the gate):

- any nondeterminism error on the replay corpus
- any encoded payload over the single-payload hard limit, or any workflow-task
  transaction over the gRPC/transaction hard limit
- a workflow-logic change on an in-flight-reachable branch with **no** replay-safe
  versioning marker
- use of an SDK primitive outside the authored-workflow capability bound

These correspond to the `critical` severity band in the interactive rubric.

---

## Runner design

The gate is a sequence of runners. Earlier, cheaper, deterministic runners gate
the expensive rubric-judge run — do not spend judge tokens on a design that
already failed a static determinism check.

### 1. Static determinism analysis (deterministic)

Parse the authored workflow code (or design pseudocode) and flag, without
executing it, every construct the rubric's **Determinism** section forbids in
workflow code:

- wall-clock reads, random sources, UUID/time-based ID generation
- direct network/disk/env reads inside workflow code (must be in activities)
- iteration over unordered collections whose order drives control flow
  (language-specific — e.g. randomized map iteration)
- run-ID-based branching

Emit each hit as a deterministic assertion failure with a file/line pointer.
This is the first gate because it needs no model and no server.

### 2. Replay-history tests (deterministic, the core of the class)

Reuse the SDK's replay machinery (`WorkflowReplayer` / replay-from-history /
`Worker.runReplayHistories`, keyed to the SDK) **as an eval runner** rather than
as a one-off test:

- maintain a **replay corpus** — a pinned set of exported Event Histories
  (captured production histories plus synthesized adversarial ones)
- replay the *current* workflow code against every history in the corpus
- **any** nondeterminism error is a hard fail (invariant above)

The corpus is a versioned dataset; a new corpus version is a new baseline. This
runner is what makes the gate a *replay* gate and not just a lint.

### 3. Versioning / patch-safety checks (deterministic)

For a design that changes existing workflow logic:

- diff the changed branches against the prior version and require a replay-safe
  marker (`patch()` / `GetVersion`, or a Worker-Deployment version pin) on any
  branch reachable by an in-flight execution
- flag patch markers that have no retirement plan (accumulating forever)
- confirm the versioning approach matches the intent per the decision rule in
  [rubric.md](rubric.md) section 13 (inline `patch()` vs. Worker Deployments)

Missing a required marker is a hard fail; an un-retired patch is a weighted
deduction, not a hard fail.

### 4. Payload / wire-size assertions (deterministic)

Compute the maximum encoded size of every workflow/activity input and output
(run the design's data converter over representative fixtures) and assert
against the platform ceilings documented in [rubric.md](rubric.md) sections 2
and 4:

- single payload over the hard limit → hard fail
- single payload routinely over the self-hosted warning size → weighted deduction
- a workflow task that schedules enough commands to breach the transaction limit
  even with small individual payloads → hard fail

### 5. SDK capability bound (deterministic)

Authored workflows may only use SDK primitives on an explicit **capability
inventory** for the target SDK and pin (e.g. which of Nexus, Update-with-Start,
Worker Deployments, Sessions exist in that SDK version). Using a primitive
outside the inventory is a hard fail — it both breaks portability and signals the
author assumed a capability the target runtime lacks. Keep the inventory keyed to
the SDK pin so a version bump re-scopes it.

### 6. Rubric judge (model-graded)

Only after 1-5 pass, run the model-graded assertions. Each is a rubric-section
prompt that returns `{evidence, score 0-5, reasoning}`. Combine with the
deterministic-assertion results by weight into the final weighted score. For
noise control, run the judge for **N >= 3 trials** and take the median; report
variance. Judge prompts are themselves versioned inside the criteria schema.

---

## Regression gate mechanics

A single score is not a gate — a **comparison** is. The gate compares the
candidate design against a **pinned baseline** on the **same schema version and
same replay-corpus version**:

- run candidate and baseline through runners 1-6
- the candidate must clear every hard-fail invariant
- the candidate's weighted rubric score must be **>= the schema threshold** and
  **not lower than the baseline by more than the trial-variance noise band**
  (median over N trials; a drop inside noise is not a regression)
- no new nondeterminism error and no new payload-limit breach relative to baseline

Passing all three yields `gate: pass`; any failure yields `gate: fail` with the
failing assertions listed most-severe first. The baseline is typically the last
released version's design or the current `main` workflow; pin it explicitly so
the comparison is reproducible.

**Anti-gaming:** the design being evaluated must never be able to edit its own
gate. The criteria schema, replay corpus, and baseline are separate,
write-protected artifacts; changing any of them is itself a reviewed change
(bump the schema/corpus version), not something a candidate run can do. This
keeps a candidate from "passing" by weakening the rubric.

---

## Score record

Every gate run emits one machine-readable record so results are queryable and
comparable over time. It carries, at minimum:

- `subject`: what was scored (design id / workflow name / commit)
- `schema_version` and `corpus_version`: the pinned versions the score is under
- `level`: `design` for a whole design, or per-workflow when scoring code
- `assertions`: each deterministic and model-graded assertion with pass/fail,
  weight, and (for judge assertions) evidence + reasoning
- `weighted_score`, `threshold`, and each `hard_fail` invariant result
- `baseline_ref` and `delta_vs_baseline` (with the noise band)
- `trials` and score variance for model-graded assertions
- `gate`: `pass` | `fail`

The machine-readable shape is formalized in
[gate-output-schema.json](gate-output-schema.json); validate gate output against
it (for example `ajv validate -s gate-output-schema.json -d gate-result.json`) so
CI consumes a stable contract. This record is deliberately compatible with a
general score store (score level + scorer id/version + source type + reasoning)
so gate results sit alongside other evaluation classes.

---

## Determinism checklist (replay-safety guards)

The static and replay runners enforce these guards, drawn from the rubric's
determinism and versioning sections. A design that satisfies all of them clears
the determinism portion of the gate:

- workflow code reads time only through the workflow's own deterministic clock,
  never the system clock
- no randomness, UUID generation, or environment reads in workflow code — all in
  activities
- every externally-mutating activity has an idempotency key (at-least-once)
- request/side-effect identity is derived deterministically (e.g. a stable
  fingerprint), not from wall-clock or run ID
- payloads carry references/blob handles, not large inline blobs, and stay under
  the platform ceilings
- any logic change reachable by in-flight executions is guarded by a replay-safe
  version marker
- the whole replay corpus replays clean against the current code

---

## Meta-loop: keeping the gate honest over time

The gate is only as good as its corpus, schema, and calibration. Maintain it:

- **Corpus growth** — real harness/production workflows and their histories feed
  the replay corpus; each addition is a new corpus version (a new baseline).
- **SDK-pin drift detection** — when the target Temporal SDK pin changes, re-run
  the *entire* corpus. Newly-surfaced nondeterminism or newly-available/removed
  primitives (re-scope the capability inventory) are caught here, not in prod.
- **Rubric-judge calibration** — calibrate the judge against real outcomes:
  production incidents and post-mortems become rubric evidence, and human
  corrections on judge verdicts are stored and fed back (few-shot) so the judge's
  agreement with human reviewers is itself a tracked, gate-able metric. A schema
  version bump requires the judge to still agree with a held-out set of
  human-labeled designs before it is trusted.
- **Reconciliation with interactive review** — if the gate and an interactive
  review disagree on a design, treat it as schema drift and fix the criteria
  schema, not the design.

---

## Non-interactive invocation contract

When invoked as a gate, the skill consumes and produces fixed artifacts (no
prose, no questions):

**Inputs**

- authored workflow code and/or design spec (the subject)
- `schema_version` (criteria schema to score under)
- `corpus_version` (pinned replay-history corpus)
- `baseline_ref` (design/commit to compare against)
- target SDK + pin (selects the capability inventory and replay machinery)

**Outputs**

- a score record validating against
  [gate-output-schema.json](gate-output-schema.json)
- process exit status: non-zero on `gate: fail` (so CI blocks)

If a required input is missing, the gate **fails closed** with an explicit
`inconclusive` reason rather than guessing — an unattended gate must never
silently pass a design it could not fully evaluate.

---

## Cross-skill handoff

This path stays scoped to Temporal-authoring judgments and defers the rest:

- **skill-eval-runner** — owns the generic eval chassis: rubric-as-versioned-
  criteria-schema, deterministic-plus-model-graded assertion runners, trials +
  variance, and baseline regression gating as a reusable engine. This skill
  supplies the *Temporal-specific* criteria schema, replay-corpus runner, and
  capability inventory; hand the general runner mechanics to skill-eval-runner
  rather than re-implementing them here.
- **graph-workflow-eval** — owns scoring **dynamic state-based graph workflows**
  (state-transition coverage, checkpoint/resume fidelity, interrupt round-trip,
  fanout/join determinism, replay *equivalence*). If the subject is a graph state
  machine rather than a Temporal workflow, route there. The two are complementary:
  this gate proves Temporal-authoring determinism; graph-workflow-eval proves
  graph-execution determinism.
- **temporal-developer** — writes and debugs the actual workflow/activity code.
  When the gate fails and the fix requires editing the workflow (add a patch
  marker, move I/O into an activity, shrink a payload), hand the failing
  assertions to temporal-developer to implement, then re-run the gate.
