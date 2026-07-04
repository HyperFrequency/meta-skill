---
name: rescue-agent-eval
version: 0.1.0
description: "D13 class-6 evaluator for RESCUE quality: scores whether a rescue agent (background-rescue) un-sticks diverged runs safely. Grades two subjects over a versioned corpus — the STUCK-PATTERN DETECTOR (doom loops, monologue/ping-pong StuckDetector, context-degradation) and the RESCUE re-grounding prompt. Metrics: recovery rate, re-divergence rate, false-rescue rate (fires on HEALTHY control runs), progress-retention, hallucination-launder rate; work-product mutation is a HARD FAIL (a rescue must only re-ground, never edit state). Runs scripted stuck fixtures through background-rescue as an activity, drives a deterministic resumption oracle plus a judge-panel prompt-quality leg, gates candidate-vs-baseline with trials/variance. Use to gate background-rescue or any re-grounding agent, or build a regression suite. NOT the rescue agent itself (background-rescue), the stall-miner that feeds fixtures (trajectory-miner), the judge primitive it calls (judge-panel), or general agent/session scoring (agent-session-eval)."
license: HyperFrequency original. Detection heuristics re-implemented from behavioral descriptions of forgecode DoomLoopDetector (Apache-2.0) and the OpenHands StuckDetector algorithm (described, not copied). Runner/gate patterns from Inspect AI / promptfoo / opik (patterns only). No code copied from PolyForm-NC, BUSL, AGPL, or Anthropic-proprietary sources.
---

# Rescue Agent Eval

`background-rescue` is the agent that re-grounds a stalled, context-rotted, hallucinating, or
looping node. **Nothing scores it.** This skill is that scorer: the D13 **class-6** runner that
proves a rescue agent actually un-sticks diverged runs — and, just as importantly, that it does
so *without harm* (no false alarms on healthy runs, no mutation of real work).

A rescue is worthless if it fires on a run that was fine, and dangerous if it "fixes" a node by
editing its work products instead of handing back a clean context. So this eval grades **two
subjects at once** over a labeled fixture corpus:

- **The stuck-pattern DETECTOR** — did it flag the diverged runs and, critically, *not* flag the
  healthy ones? (precision/recall; the **false-rescue rate** is the specificity number that matters
  most).
- **The RESCUE re-grounding prompt** — given a genuinely stuck run, does `background-rescue`'s one
  prompt get the resumed run to the goal, carry forward the *real* progress, quarantine the
  hallucinations, and touch nothing? (recovery / re-divergence / retention / no-mutation).

Scope is narrow: **one rescue agent, one corpus, one gate decision.** It is not the rescue agent,
the stall-miner, or a general session evaluator — see [Cross-links](#cross-links).

## When to use

- **Gate `background-rescue`** (or any re-grounding agent) before it ships or after it changes —
  prove recovery rate holds and false-rescue rate stays under ceiling.
- **Build / run a rescue regression suite** so a prompt or detector edit can never silently make
  rescues worse than a pinned baseline.
- **Turn mined real stalls into fixtures** — take stall clusters surfaced by `trajectory-miner` and
  materialize them as scored fixtures (the meta-loop; see [references/meta-loop.md](references/meta-loop.md)).
- **Tune detector thresholds** (doom-loop count, monologue/ping-pong windows) and measure the
  precision/false-rescue trade-off on the corpus.

## When NOT to use (anti-triggers)

- **Rescuing a live stuck node** → `background-rescue`. That *is* the agent under test here; this
  skill only measures it, it never re-grounds anything itself.
- **Mining a corpus of past runs for systemic failures / new stall classes** → `trajectory-miner`.
  It *feeds* fixtures into this eval; it does not score rescue quality.
- **Getting a multi-judge verdict on one candidate** → `judge-panel`. This skill *calls* it for the
  prompt-quality leg; it is not a judge primitive.
- **Scoring general agent/session behavior** (task completion, tool correctness, plan adherence) →
  `agent-session-eval` (D13 class 3). Rescue is a narrow slice, not whole-session quality.
- **Scoring context-compaction / token budget** → `compaction-eval` (D13 class 7). Related failure
  family (context rot), different subject.
- **Designing the shared eval chassis** (runner traits, `_llm_scores` table, criteria registry) →
  `skill-eval-runner` / the `harness_eval` chassis. This class plugs into that chassis; it does not
  reinvent it.

## What it measures (the heart)

Six numbers per corpus run. Precise formulas, numerator/denominator edge cases, and the
`_llm_scores` record shape (level, `scorer_id`+version, `source_type`) are in
[references/metrics.md](references/metrics.md).

| Metric | Over which fixtures | Definition | Gate role |
|---|---|---|---|
| **recovery rate** | correctly-flagged STUCK | resumed run reaches the goal after the re-grounding prompt | **floor** |
| **re-divergence rate** | rescued STUCK | resumed run diverges *again* (stalls/loops/hallucinates) post-rescue | ceiling |
| **false-rescue rate** | HEALTHY controls | detector/rescue fires on a run that was making legitimate progress | **ceiling** |
| **verified-progress retention** | rescued STUCK | fraction of ground-truth real progress carried forward (recall) | floor |
| **hallucination-launder rate** | rescued STUCK | fraction of fabricated results restated as fact in the prompt | ceiling |
| **work-product mutation** | ALL | did the rescue edit any file/state instead of only re-grounding? | **HARD FAIL** |

Detection also yields precision/recall and **stuck-class accuracy** (was the *primary* divergence
type — stalled / context-rot / hallucinated / looped — labeled correctly). The two headline gates
are the **recovery-rate floor** and the **false-rescue ceiling**; `work-product mutation` on *any*
fixture fails the whole run — a rescue must be a pure lateral pass (`background-rescue`'s own
guardrail, mechanically enforced by a diff-tracked sandbox, not the agent's self-report).

## The fixture corpus

Every fixture is a scripted, replayable case — no live nondeterminism. Two disjoint sets:

- **STUCK** — genuinely diverged runs, each labeled with `primary_stuck_class`, `verified_progress[]`,
  `hallucination[]`, a reachable goal, and a **resumption oracle** (a scripted continuation that
  deterministically completes iff the re-grounding prompt is clean and correct).
- **HEALTHY controls** — runs still making legitimate progress, deliberately built to *resemble*
  stuck runs (a closing monologue in WrapUp, a legitimate retry, a long research read) so the
  detector's specificity is actually tested. Any fire here is a false-rescue.

Fixtures use ScriptedJudge-style transcripts (WS9-T2 discipline) + fixed-response `SimulatedUser`
scenarios. Full `RescueFixture` schema, specificity traps, provenance / versioning:
[references/fixture-schema.md](references/fixture-schema.md).

## The detection schema (versioned SUT)

The detector is graded against a **versioned stuck-pattern criteria schema** — the same one
`trajectory-miner` scans with, so detection stays consistent across mine-time and eval-time:

- **doom loops** — `[A,A,A]` consecutive-identical and `[A,B,C][A,B,C]` repeating tool-signature
  cycles (forgecode `DoomLoopDetector`, default threshold 3).
- **stuck patterns** — `monologue` (≥3 consecutive assistant turns with no action), `ping_pong` (≥6
  action↔observation with no progress), repeated `context_window_error` (OpenHands StuckDetector,
  re-implemented from the algorithm).
- **context-degradation** — the five `ce-context-degradation` modes (lost-in-middle, poisoning,
  distraction, confusion, clash) at versioned thresholds.
- **degeneration metric** — repetition/entropy collapse in generated text.

Every run pins the `schema_version` it graded under. Details + why the version pin is load-bearing
for anti-gaming: [references/detection-schema.md](references/detection-schema.md).

## The runner

`task / solver / scorer` decomposition (Inspect AI). The **solver** is `background-rescue` run as
an activity: feed it the fixture transcript + goal, capture its `Diagnosis` line + re-grounding
prompt, and assert it wrote nothing. The **scorer** is hybrid:

1. **Deterministic leg** — drive the fixture's resumption oracle with the emitted re-grounding
   prompt; the oracle deterministically reaches goal / re-diverges → the hard **recovery** and
   **re-divergence** signals, free of LLM noise.
2. **Judge-panel leg** — call `judge-panel` to grade the softer sub-scores (retention recall,
   hallucination-launder, class-label correctness) with an evidence-before-score rubric.

Runs **trials n≥3** with variance stats so a rescue's stochasticity can't sneak a regression past
the gate. Each fixture run emits a `.traj` artifact + one OTel trace; judge runs self-trace. Full
runner design, the resumption-oracle contract, and an end-to-end fixture walkthrough:
[references/runner.md](references/runner.md).

## The regression gate

Candidate rescue vs a pinned **baseline** on the **same fixture-corpus version**, trials +
variance-aware margins so regressions must beat noise. Fails (exit 1) if: recovery rate < floor,
false-rescue rate > ceiling, re-divergence > ceiling, retention < floor, launder > ceiling, **or**
any fixture shows work-product mutation. A held-out fixture split guards against overfitting the
detector to the visible corpus. Exit-code contract, baseline semantics, and the gate report:
[references/regression-gate.md](references/regression-gate.md).

## How this class is itself evaluated (meta-loop)

Anti-gaming is structural: **the rescue agent under test may never edit the detector schema, the
fixtures, or the gate** (disjoint-write-scope, swe-loop pattern). Improvement comes from outside —
`trajectory-miner` mines real stalls into new fixtures; new stuck classes → `schema_version` bump;
thresholds tuned by **TPE/CMA-ES** within gate bounds. The judge-panel leg carries its own
calibration ledger + Align-Evals agreement. See [references/meta-loop.md](references/meta-loop.md).

## Cross-links

- **`background-rescue`** (neuro-code) — **the agent this skill evaluates.** It produces the
  re-grounding prompt; this skill scores whether that prompt actually works. They are a matched
  pair: never one without the other in the harness.
- **`trajectory-miner`** (neuro-code) — the loop-3 corpus miner that shares this skill's versioned
  detection schema and **feeds real stalls in as new fixtures**. Upstream of the meta-loop.
- **`judge-panel`** (neuro-centrifuge) — the multi-judge primitive this skill *calls* for the
  prompt-quality leg (retention, launder, class-label). This skill owns fixtures/gate; it owns the
  verdict math.
- **`skill-eval-runner`** (neuro-centrifuge) — sibling class runner; source of the
  versioned-criteria-schema + deterministic-then-judge + regression-gate pattern reused here.
- **`agent-session-eval`** (class 3) / **`compaction-eval`** (class 7) — adjacent D13 classes on
  the same chassis; whole-session and context-budget scoring respectively.

## References

- [references/metrics.md](references/metrics.md) — every metric's formula, edge cases, `_llm_scores` record shape.
- [references/fixture-schema.md](references/fixture-schema.md) — `RescueFixture` schema, STUCK vs HEALTHY controls, specificity traps, versioning.
- [references/detection-schema.md](references/detection-schema.md) — the versioned stuck-pattern schema (doom loops, StuckDetector, context-degradation, degeneration).
- [references/runner.md](references/runner.md) — task/solver/scorer design, resumption oracle, hybrid deterministic + judge-panel legs, walkthrough.
- [references/regression-gate.md](references/regression-gate.md) — floors/ceilings, hard-fail, baseline + held-out semantics, exit codes, report.
- [references/meta-loop.md](references/meta-loop.md) — fixture mining, schema versioning, threshold tuning, disjoint-write-scope anti-gaming.
