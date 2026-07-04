# Regression gate — tiered core, budgets, rollups, anti-gaming

The gate answers one question: **may this candidate agent config be promoted over
the current baseline?** It compares a candidate rollup against a **pinned baseline
experiment** on the **same pinned dataset version**, with trials + variance so a
"regression" has to beat LLM noise rather than being noise itself.

## Inputs the gate needs

- **Candidate rollup** — per-tier mean/std across trials for every metric (from the
  runner, [runner.md](runner.md)).
- **Baseline experiment** — a stored `experiment-tracker` record: the previous
  green run on the same dataset version + criteria version. The baseline is a
  *frozen artifact*, not a re-run — you compare against recorded numbers so the bar
  cannot drift under you.
- **Pinned dataset version + criteria version** — both must match between candidate
  and baseline, or the comparison is void (a mismatch is a hard error, not a warn).

## The three gate conditions

A candidate **passes** only if all three hold:

### 1. No tier-1 solve-rate drop

Tier-1 is the **exact-match core**: `tool_correctness` + `argument_correctness` on a
**gated held-out split** (GAIA design — ungameable graders, contamination-controlled).
The candidate's tier-1 solve-rate must not fall below the baseline's by more than the
declared `solve_rate_noise_band` (default 0.03). This is the ungameable floor: a
judge can be flattered, an exact-match tool-call check cannot.

### 2. No cost / step blow-up

Per-thread **cost** and **step** budgets versus the baseline experiment (default:
cost ≤ 1.25× baseline, steps ≤ 1.5× baseline). An agent that "solves more" by
burning 4× the tokens is a regression, not an improvement — Class 3 explicitly
gates the *efficiency* dimension, not just correctness. Cost comes from `llm-router`
usage tracking; steps from the `.traj` action count.

### 3. Judge-panel score floors + no model-graded regression

The model-graded metrics (task completion, plan adherence, coherence, knowledge
retention, trajectory_accuracy) roll up as opik-style **AssertionResult / Test-Suite
status**: each thread's weighted score vs `threshold` → PASS/FAIL, aggregated to a
suite pass-rate per tier. The candidate's per-tier suite pass-rate must not regress
beyond the noise band, and any absolute score floors in the criteria schema must
hold.

Because judges are noisy, condition 3 is always **variance-aware**: the comparison
is `candidate_mean − baseline_mean` against a band derived from the trial std, not a
bare point comparison (Braintrust/opik variance-aware compare).

## Rollup mechanics

- **Trials → item**: mean/max/min/std across the N trials of one item.
- **Items → tier**: suite pass-rate + mean metric scores per tier (Easy/Med/Hard
  reported separately — never blended, see runner.md).
- **Tiers → experiment**: the gate decision is a per-tier AND (a Hard-only win with
  an Easy regression fails).

The whole rollup is one `experiment-tracker` record with a config-snapshot hash, so
a passing candidate becomes the *next* baseline and the lineage is queryable.

## Anti-metric-gaming: disjoint write scope

The single most important invariant. **The agent config under evaluation can never
edit its own gate.** Concretely:

- The criteria schema (`criteria_version`) and the tier-1 held-out split are
  **write-locked** to the eval track; the agent/prompt-evolution track (Loop 1) has
  read-only access to them.
- A criteria-version bump (new judge prompt, new threshold, new metric) is a
  separate, HITL-or-calibration-gated operation (see [meta-loop.md](meta-loop.md)),
  gated on the class's *own held-out calibration set* — you cannot loosen the gate
  to pass a candidate.
- This is the swe-loop disjoint-write-scope pattern + the ce-harness-engineering
  surface lock. Without it, an autonomous loop learns to edit the rubric instead of
  improving the agent.

## Contamination control

The tier-1 core lives on a **gated held-out split** that is never shown to the
agent under development and never used to *tune* the agent. Dataset promotion from
production traces (meta-loop) must route new items away from the frozen held-out
split, or the split silently contaminates and the floor becomes meaningless.

## Hard-fail conditions (short-circuit, no promotion)

- Dataset-version or criteria-version mismatch between candidate and baseline.
- A tier-1 exact-match grader that cannot resolve its gold (unresolvable artifact).
- The deterministic pre-gate tripped on the whole tier (e.g. the agent emitted no
  valid tool calls at all) — that is a broken candidate, reported as such, not a
  score.
