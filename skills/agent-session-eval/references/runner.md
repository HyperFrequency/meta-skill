# Runner design — sources, thread-level scoring, tiering, artifacts

The runner sits on the shared `harness_eval` chassis and is shaped like
`opik.evaluate()`: **`dataset × agent × metrics`**, realized as a Temporal
workflow where items fan out to activities and scores stream back. What Class 3
adds is the **session** dimension — the "agent" under test is driven through a
*multi-turn thread*, and scoring happens at thread level.

## The chassis triad (what it inherits)

- **`task / solver / scorer` traits + registry** (Inspect AI shape). The
  system-under-test is hidden behind a **completion-function-style trait**, so the
  identical Class 3 run works against a raw prompt agent, a graph agent, or a full
  Temporal-hosted agent. The runner never hard-codes the agent — it holds a
  `Solver`.
- **Dual API**: a declarative batch runner (for the gate) and an
  EvaluationLogger-style incremental score emitter (Weave shape) so long-running
  session activities can stream partial scores instead of blocking to the end.
- **Determinism / resume**: Temporal durable execution *is* the checkpoint
  mechanism — opik's resumable-eval state collapses into workflow history. Keep the
  pinned-inputs state shape (dataset version, criteria version, seeds) so a resumed
  run is byte-identical to an uninterrupted one.

## Session source 1 — recorded-session REPLAY

A recorded thread is re-driven through the candidate agent. Two replay modes:

- **Cached / deterministic replay** — provider calls are served from a
  MITM/cache (tensorzero provider-proxy caching pattern) so the same session
  reproduces exactly. Use for the gate: no provider nondeterminism, no spend, no
  contamination drift.
- **Live re-run** — the recorded *user turns* are replayed but the agent's provider
  calls are re-issued. Use to test a new model/agent config against the same task
  the recorded session faced.

Replay inputs are any of: a first-party `.traj` artifact, an OTel trace pulled from
`trace-store`, a production session promoted into the dataset (see meta-loop), or a
hand-authored fixture. The recorded **user turns** and (for scoring) the **expected
tool-call set / gold** ride on the dataset item.

Determinism guardrails carried from lightspeed replay-safety: `workflow_time` only,
`request_fingerprint` sha256 on every provider call, opaque `ProviderParams`. A
replay that diverges on a fingerprint is a flagged nondeterminism event, not a
silent pass.

## Session source 2 — SimulatedUser personas

When there is no recorded corpus (or you want adversarial/edge coverage), generate
threads on demand. This is the opik multi-turn simulation shape, run as a
`harness_worker` **session-simulation activity**:

```
SimulatedUser {
  persona        # role/tone/knowledge-level; also adversarial personas (terse, contradictory, hostile)
  goal           # what this user is trying to get done (the task_completion gold)
  max_turns      # hard cap on thread length
  thread_id      # UUID; threaded through every Temporal activity boundary (opik @track/distributed shape)
  script?        # optional fixed user turns for a fully deterministic thread (ScriptedJudge discipline)
}
```

A simulated user is itself an LLM call at temperature > 0 for realism — which makes
the *thread* nondeterministic. That is why **trials (N≥3)** and variance are
mandatory here: one simulated thread is an anecdote, three+ are a measurement. For
gate-critical items, prefer a **scripted** SimulatedUser (fixed user turns) so only
the agent varies.

`thread_id` is the spine: it threads through every activity so all spans, `.traj`
events, and `_llm_scores` rows for one session join back to one thread — honoring
the LangSmith **run-vs-thread** distinction (a *run* is one activity/agent step; a
*thread* is the whole conversation; Class 3 scores threads, and rolls runs up
underneath).

## Thread-level scoring

Scoring uses the opik `evaluate_threads` shape: the scorer receives the **whole
ordered message list** for a `thread_id`, not a single turn. Deterministic
assertions (tool/argument correctness, step efficiency) are computed over the
recorded action sequence; conversational + trajectory metrics are handed to
`judge-panel` with the full thread as the candidate. See
[criteria-schema.md](criteria-schema.md) for the metric definitions and
[regression-gate.md](regression-gate.md) for how thread scores roll into a gate.

## N-trial + Easy/Med/Hard tiering

Every dataset item is run **N times** (N≥3) and its scores are reduced to
mean/max/min/std across trials (opik trial statistics). This is what lets a
candidate-vs-baseline comparison beat LLM noise.

Items are tagged **Easy / Medium / Hard** (GAIA tiering / meta-harness-tbench2
N-trial-with-splits protocol). Reporting is **per tier**, never a single blended
number — a candidate can improve on Hard while quietly regressing Easy, and a
blended score hides it. Tier-1 (the exact-match core) is reported and gated
separately (see regression-gate.md).

## Artifacts (every run emits three)

1. **`.traj` trajectory artifact** — the proto trajectory schema on the contract
   plane (SWE-agent shape). One per run; this is the exact artifact
   **`trajectory-miner`** later ingests, so a scored session feeds the loop-3
   corpus for free.
2. **One OTel trace** — gen_ai spans into `trace-store`; the DAG-endpoint query
   contract makes the session inspectable in the Dev-Ai UI.
3. **`_llm_scores` rows** — one per assertion, at thread level, pinned to
   `criteria_version` (schema in [criteria-schema.md](criteria-schema.md)).

The **judge runs self-trace** (openobserve evaluator-self-tracing): a judge-panel
call is itself a set of spans + scores, so the *evaluation* is as auditable and
regression-gateable as the thing it evaluated.

## Workflow sketch

```
AgentSessionEvalWorkflow(spec{dataset_version, criteria_version, solver, baseline_experiment, trials})
  for item in dataset:                         # fan out; Temporal activities
    for trial in 1..=N:
      thread = drive_session(solver, item)     # replay OR SimulatedUser activity; emits .traj + OTel
      pre_gate(thread, criteria)               # deterministic core; hard-fail short-circuits judges
      scores = judge_panel(thread, criteria)   # model-graded metrics -> Verdicts
      emit _llm_scores(thread_id, scores, criteria_version)
  rollup per tier (mean/std across trials)      # experiment-tracker
  gate(candidate_rollup, baseline_experiment)   # see regression-gate.md
```
