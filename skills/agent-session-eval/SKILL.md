---
name: agent-session-eval
version: 0.1.0
description: "D13 CLASS 3 RUNNER for whole agent SESSIONS/threads (not skills, prompts, or graphs). Runs recorded-session REPLAY plus SimulatedUser-persona sessions against a versioned criteria schema — agentic metrics (task completion, tool/argument correctness, step efficiency, plan adherence), conversation metrics (coherence, retention, frustration), and a trajectory judge — scored at THREAD level via judge-panel over Easy/Med/Hard tiers, N trials, gating regressions (no tier-1 solve-rate drop, no cost blow-up) vs a pinned baseline. Use to score or regression-gate an agent's multi-turn behavior, replay production traces, or benchmark a harness config. NOT for one SKILL.md (skill-eval-runner), a prompt A/B (class 2), graph checkpoint fidelity (graph-workflow-eval class 5), market/PnL rewards (class 4), mining a corpus for anti-patterns (trajectory-miner), rescuing a live stuck node (background-rescue), or designing a judge (ce-advanced-evaluation); this is the runner, ce-evaluation/-advanced-evaluation are guidance-only."
allowed-tools: Read Write Edit Bash
license: HyperFrequency original. Behavioral patterns described (never copied) from Apache-2.0/MIT donors — opik (SimulatedUser, evaluate_threads shape), DeepEval (agentic + conversational metric sets), tensorzero (workflow-evaluation, functions-with-variants), lightspeed (deterministic replay). GAIA tiering + LangSmith run/thread vocabulary referenced conceptually.
---

# Agent Session Eval

The **D13 Class 3 runner**: it scores an *agent's end-to-end behavior across a
whole multi-turn session*, and gates regressions on it. Where sibling runners
score a static artifact — one `SKILL.md` (class 1), one prompt variant (class 2),
one graph's transition fidelity (class 5) — this one puts a **live agent** through
a task and judges *how it got there*: did it finish, did it call the right tools
with the right arguments, did it waste steps, did it follow its plan, and was the
conversation coherent rather than a frustrated loop.

It is a **runner**, not guidance and not a primitive. `ce-evaluation` and
`ce-advanced-evaluation` tell you *how to think about* agent evaluation and judge
design; this skill is the executable thing that produces scores and a gate
decision. It does not invent its own judges — it **calls `judge-panel`** for every
model-graded metric.

It runs on the shared `harness_eval` chassis (§c of the autoresearch PRD): a
`task / solver / scorer` trait triad with the system-under-test hidden behind a
completion-function-style trait, so the same run works against a raw prompt, a
graph agent, or a full Temporal workflow. What Class 3 adds on top of the chassis
is the **session** dimension: threads, personas, replay, and thread-level scoring.

## When to use

- **Regression-gate an agent/harness config** before promotion: does this change
  keep tier-1 solve-rate and not blow up cost/steps versus the pinned baseline?
- **Replay recorded production sessions** (or a fixed benchmark corpus) through a
  candidate agent and score the resulting threads.
- **Generate fresh sessions on demand** via `SimulatedUser` personas when you lack
  (or want to augment) a recorded corpus — multi-turn, scripted or persona-driven.
- **Benchmark two agent configs** head-to-head across Easy/Med/Hard splits with N
  trials and variance, producing an auditable per-thread scorecard.

## When NOT to use (anti-triggers)

- **Scoring one `SKILL.md` against the frontier rubric** → `skill-eval-runner`
  (class 1). Same chassis, different system-under-test.
- **A/B-ing a prompt/variant on a dataset** → class-2 prompt/workflow eval.
- **Graph state-transition coverage, checkpoint/resume, replay-equivalence** →
  `graph-workflow-eval` (class 5).
- **Trade/PnL or verifiable-market rewards** → class-4 market-reward eval /
  `strategy-verify`.
- **Mining a *corpus* of past runs for systemic anti-patterns** → `trajectory-miner`
  (loop 3). It is read-only and corpus-level; this scores *one agent config* on a
  *dataset* and returns a gate. (They share the `.traj` schema and the
  session-quality gate — see meta-loop.)
- **Rescuing one live stuck node** → `background-rescue`. **Scoring** rescue
  quality → `rescue-agent-eval` (class 6).
- **Designing the individual judge** (rubric, scale, bias mitigation) →
  `ce-advanced-evaluation`. You author judges there, then this runner panels them.

## The two session sources

Class 3 evaluates *threads*, and a thread comes from one of two places. Full
mechanics — replay determinism, persona schema, `max_turns`, `thread_id`
threading through Temporal activity boundaries — are in
[references/runner.md](references/runner.md).

| Source | What it is | Use when |
|---|---|---|
| **Replay** | A recorded session (production trace, `.traj` artifact, or fixture) re-driven through the candidate agent; provider calls may be cached (MITM) for determinism, or re-issued for a live re-run. | You have real traces or a frozen benchmark and want reproducible, contamination-controlled scoring. |
| **SimulatedUser** | Persona-driven multi-turn sessions generated on demand (`{persona, goal, max_turns, thread_id}`, opik shape), run as a `harness_worker` session-simulation activity. | You lack a corpus, need adversarial/edge personas, or want to stress a specific capability. |

## The criteria schema (versioned)

Class 3 criteria are a **versioned YAML schema** registered in the scorer registry
(openobserve `_llm_scores` + ScoreConfig). Three families combine by per-assertion
weight into a test-level threshold = the regression gate. Deterministic assertions
run first (cheap, ungameable); judge-panel metrics run only on what survives.
Metric definitions, weights, the evidence-before-score verdict shape, and a full
example live in [references/criteria-schema.md](references/criteria-schema.md) and
[references/class3-criteria.example.yaml](references/class3-criteria.example.yaml).

| Family | Metrics | Grading |
|---|---|---|
| **Agentic** | task completion, tool correctness, argument correctness, step efficiency, plan adherence | tool/argument correctness are deterministic (compare against an expected tool-call set); task completion + plan adherence are judge-panel; step efficiency is a metric (steps/tokens vs a per-tier budget) |
| **Conversational** | coherence, knowledge retention, user frustration | judge-panel over the whole thread (opik `evaluate_threads` shape); frustration is a degeneration signal, not just a rubric axis |
| **Trajectory** | `trajectory_accuracy` | judge-panel over the ordered action/observation sequence vs an ideal-path reference |

## Runner design

The runner is an `opik.evaluate()`-shaped Temporal workflow — `dataset × agent ×
metrics`, items fan out to activities, scores stream back via an
EvaluationLogger-style incremental emitter. It scores at **thread level** (not
turn level) and honors the LangSmith **run-vs-thread** distinction. Each item is
run **N times** (trials, N≥3) so variance is measured, across **Easy/Med/Hard**
tiers (GAIA / meta-harness-tbench2 tiering). Every run emits one `.traj`
trajectory artifact + one OTel trace, and the judge runs self-trace. Determinism,
resume (Temporal durable execution replaces bespoke checkpoints), the score-record
shape, and the tiering protocol: [references/runner.md](references/runner.md).

## Regression gate

Candidate-vs-baseline on the **same pinned dataset version** with trials + variance
so a regression must beat LLM noise. Two hard conditions, plus the tiered core:

1. **No tier-1 solve-rate drop** — the exact-match core set (gated held-out split,
   GAIA-style, ungameable graders) must not regress beyond the noise band.
2. **No cost/step blow-up** — per-thread cost and step budgets versus the baseline
   experiment.
3. Judge-panel scores rolled up as opik-style AssertionResult / Test-Suite status.

The candidate under evaluation can **never edit its own gate** — criteria-version
bumps are a disjoint-write-scope operation. Full mechanics, held-out split
handling, and rollup rules: [references/regression-gate.md](references/regression-gate.md).

## Meta-loop (how the eval itself improves)

Per the shared §c meta-loop, specialized for sessions: production traces flow into
the dataset via **trace→dataset promotion** (LangSmith backtesting vocabulary);
`trajectory-miner`'s **session-quality gate + phase segmentation** validate that
judged sessions are *representative* (junk filtered before expensive judging); the
judge panel is calibrated via the shared ledger + Align-Evals loop. Details and the
anti-metric-gaming discipline: [references/meta-loop.md](references/meta-loop.md).

## Cross-links

- **`judge-panel`** — the multi-judge verdict primitive this runner calls for every
  model-graded metric (task completion, plan adherence, conversational, trajectory).
- **`skill-eval-runner`** — sibling class-1 runner on the same chassis; use it for
  `SKILL.md`, this for sessions.
- **`trajectory-miner`** — loop-3 corpus miner; consumes the `.traj` artifacts this
  runner emits and lends its session-quality gate. Corpus-level and read-only; this
  is dataset-level and returns a gate.
- **`ce-evaluation` / `ce-advanced-evaluation`** — guidance-only: agent-eval theory
  and judge design. This is the runner that executes it.
- **`recursive-batch-eval`** — the outer stage-graded orchestrator that loops this
  runner across rounds under a budget.
- **`background-rescue` / `rescue-agent-eval`** — rescuing vs *scoring rescue* (class 6).

## References

- [references/criteria-schema.md](references/criteria-schema.md) — the three metric families, deterministic-vs-judge split, weights, verdict shape.
- [references/class3-criteria.example.yaml](references/class3-criteria.example.yaml) — a complete registered criteria schema.
- [references/runner.md](references/runner.md) — replay + SimulatedUser sources, thread-level scoring, N-trial tiering, `.traj`/`_llm_scores` artifacts, determinism/resume.
- [references/regression-gate.md](references/regression-gate.md) — tiered core, held-out splits, cost/step budgets, AssertionResult rollups, disjoint-write-scope.
- [references/meta-loop.md](references/meta-loop.md) — trace→dataset promotion, representativeness gate, judge calibration, anti-gaming.
- [references/boundaries.md](references/boundaries.md) — class-3 vs classes 1/2/5/6, edge cases, failure modes.
