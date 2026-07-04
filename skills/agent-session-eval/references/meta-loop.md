# Meta-loop — how the Class 3 eval improves itself (without cheating)

Every D13 class carries a meta-loop: the eval's own scorers/criteria are versioned
registry entities, and they improve over time under discipline. Class 3's meta-loop
has three moving parts — a **dataset that refreshes from production**, a
**representativeness gate** on what gets judged, and **judge calibration** — all
fenced by the anti-gaming rule that the loop under evaluation can never edit its own
gate.

## 1. Dataset refresh — trace→dataset promotion (backtesting)

The Class 3 dataset is not frozen forever; it is **continuously refreshed from
historical production traces** (LangSmith "backtesting" vocabulary). Real sessions
in `trace-store` are promoted into the dataset via **trace→dataset promotion**
(opik shape), so the eval keeps facing the distribution the agent actually meets in
production rather than a stale hand-authored set.

Promotion is gated, not automatic:

- New items route **away from the tier-1 gated held-out split** (contamination
  control — see [regression-gate.md](regression-gate.md)).
- Promoted sessions pass the representativeness gate below before they can be
  judged, so junk traces don't pollute the dataset.
- Each promotion is a dataset-version bump (versioning/diff/restore), so any run is
  re-attributable to the exact dataset it faced.

## 2. Representativeness gate — reuse trajectory-miner's session-quality filter

A judged session is only meaningful if it is a *real* session. Class 3 reuses two
pieces of **`trajectory-miner`** (meta_skill donor lineage) as a pre-filter before
expensive judging:

- **Session-quality gate** (min_score 0.3): backtracking/abandonment/thrash
  penalties filter degenerate or truncated sessions out of the dataset before they
  cost judge tokens.
- **Phase segmentation** (Recon / Change / Validation / WrapUp): confirms a
  promoted session actually exercises the phases a representative task should, so
  the corpus isn't skewed toward trivial one-phase threads.

This is a *shared* mechanism, not a fork: the same code that mines a corpus for
anti-patterns validates that a promoted eval item is representative. The boundary
stays clean — trajectory-miner *mines*, agent-session-eval *scores* (see
[boundaries.md](boundaries.md)).

## 3. Judge calibration — ledger + Align-Evals

The model-graded metrics are only as trustworthy as their judges, so the panel is
continuously calibrated via the shared `judge-panel` machinery:

- **Calibration ledger** (tournament-autoresearch shape): each judge's predicted
  score is later paired with a realized outcome (a human label, or the downstream
  tier-1 exact-match result on the same thread) → per-judge reliability weights +
  bias offsets fed back into aggregation.
- **Align-Evals loop** (LangSmith pattern): human corrections on thread verdicts
  become few-shot exemplars spliced into the judge prompt, and **judge/human
  agreement is itself a regression-gated metric** — a judge-prompt change that drops
  agreement below its gate is rejected.

Both are logged to `_llm_scores` with `source_type = annotation`, so the
*calibration process* is as auditable as the evals it calibrates.

## The anti-gaming fence (why the loop can be trusted)

Criteria evolution is real but **disjoint-write-scoped**. Loop 1 may *propose* a new
judge prompt or threshold, but a `criteria_version` bump only lands when it passes on
the class's **own held-out calibration set** — a human-labeled thread set the
proposing loop cannot see or tune. The agent track and the criteria track have
disjoint write scopes (swe-loop pattern; ce-harness-engineering surface lock). So:

- You cannot loosen the gate to pass a weak agent.
- You cannot overfit the judge to the current candidate.
- Every gate change is traceable to a calibration-set win, not a convenience.

## K/B/I epistemic tagging

Following episteme, each metric's result carries a Known / Believed / Inferred tag:
tool-correctness is **Known** (deterministic), a task-completion judge score is
**Believed** (model-graded, calibrated), a trajectory judgment with no ideal-path
reference is **Inferred**. The gate weights Known evidence above Believed above
Inferred, and the tags make explicit *how much* of a promotion decision rests on
judgment versus fact.
