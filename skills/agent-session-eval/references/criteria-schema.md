# Class 3 criteria schema — metric families, grading, verdict shape

The Class 3 criteria schema is a **versioned YAML artifact** registered in the
scorer registry (`ScoreConfig` + `_llm_scores`, openobserve shape). It is *data*,
not code: bumping a threshold, a weight, or a judge prompt is a version bump, not a
recompile. Every run is scored against a pinned `criteria_version`, and the runner
records that version on every emitted score row so a result is always
re-attributable to the exact rubric that produced it.

A criteria schema is a weighted list of **assertions**. Two assertion kinds:

- **Deterministic assertions** — pure functions over the recorded thread (tool-call
  set membership, argument equality, step count, latency, cost, is-valid-JSON).
  They are cheap, ungameable, and run **first**. On the shared chassis these are
  the `equals / regex / is-json / levenshtein / latency / cost / is-valid-function-call`
  leaf metrics.
- **Model-graded assertions** — delegated to **`judge-panel`** (never a bespoke
  inline judge). The schema names a `rubric` + `judges[]` + `topology` +
  `aggregation`; the runner hands the thread to the panel and stores the returned
  `Verdict`. This keeps a single judge contract across all ten D13 classes.

Assertions combine by **per-assertion weight** into a test-level score; the
**threshold** on that score is the per-thread pass/fail. Assert-sets and derived
composite metrics follow the promptfoo taxonomy. Verdicts always use the
**evidence-before-score** JSON shape (ChatEval): the judge cites observable
features of the thread *before* emitting a number.

## The three metric families

Class 3 is distinguished from other classes by *what it measures*: not an
artifact's quality but an **agent's behavior over a multi-turn thread**. The
metric set is the DeepEval agentic + conversational families plus a trajectory
judge (pattern donors — described, not copied).

### 1. Agentic metrics (per-thread, mixed grading)

| Metric | Grading | Definition | Reference / gold needed |
|---|---|---|---|
| **task completion** | judge-panel | Did the thread achieve the user's stated goal? Judged against the goal statement + final state, not intermediate chatter. | goal statement (from the dataset item or persona) |
| **tool correctness** | deterministic | Set/sequence agreement between the tools the agent actually called and the expected tool-call set for the task. Score = F1 over `(tool_name)` tuples (order-sensitive variant available). | expected tool-call set |
| **argument correctness** | deterministic (+ optional judge for free-text args) | For each matched tool call, do the arguments match the expected arguments? Exact-match / schema-match for structured args; a judge leg for natural-language args. | expected arguments per call |
| **step efficiency** | metric | Steps (or tokens, or wall-cost) taken vs a **per-tier budget**. NOT raw minimization — a correct 6-step solve beats a wrong 3-step one; this only penalizes waste *above budget on solved threads*. | per-tier step/token budget |
| **plan adherence** | judge-panel | If the agent produced a plan (explicit plan step, TODO list), did its actions follow it? Judges the action sequence against the agent's own stated plan. | none (self-referential) |

Tool + argument correctness are the **exact-match, ungameable core** — they anchor
tier-1 (see [regression-gate.md](regression-gate.md)). Task completion and plan
adherence carry the model-graded weight.

### 2. Conversation metrics (whole-thread, judge-panel)

Scored at **thread level** using the opik `evaluate_threads` shape — the panel sees
the full ordered message list, not a single turn.

| Metric | Definition | Signal type |
|---|---|---|
| **coherence** | Does the thread stay on-topic and internally consistent turn-to-turn? Detects the degeneration failure where an agent contradicts or forgets its own earlier turns. | quality rubric |
| **knowledge retention** | Does the agent retain facts the user supplied earlier in the thread rather than re-asking or contradicting them? | retention rubric |
| **user frustration** | Rising frustration in the (real or simulated) user's turns — repeated re-statements, corrections, "no, I said…". Treated as a **degeneration signal**, not merely a rubric axis: a frustrated thread is a failing thread even if the task nominally completes. | degeneration signal |

### 3. Trajectory metric (judge-panel over the action sequence)

| Metric | Definition |
|---|---|
| **trajectory_accuracy** | Judges the ordered `(action, observation)` sequence against an *ideal-path* reference (when one exists) or against a rubric of "reasonable path" (when none does). This is the metric that catches an agent that reaches the right answer by an absurd or lucky route — right destination, wrong journey. |

## Weights and threshold

The schema assigns each assertion a weight; the weighted sum is the thread score;
`threshold` on that score is the per-thread pass. Recommended default posture (tune
per suite, and record the tuning — it is itself gated, see meta-loop):

- Deterministic core (tool + argument correctness) is a **hard pre-gate**: a thread
  that fails the core is scored 0 and skips the judges (cost control + ungameable
  floor). Frustration crossing a degeneration threshold is likewise a hard fail.
- Remaining weight splits across task completion, plan adherence, coherence,
  knowledge retention, trajectory_accuracy.

The complete registered form (all fields, judge references, tier splits) is in
[class3-criteria.example.yaml](class3-criteria.example.yaml).

## Score record shape

Every assertion result becomes one row in `_llm_scores`:

```
_llm_scores {
  level        "thread"            # class 3 scores at thread (also "session"/"experiment" rollups)
  thread_id                        # the evaluated thread
  scorer_id    "class3.tool_correctness"
  scorer_version                   # from criteria_version
  score_config_id + version        # the registered ScoreConfig
  value        0.83                 # numeric | categorical | boolean (Langfuse typing)
  source_type  "model" | "deterministic" | "human"
  reasoning                        # the evidence-before-score rationale (judge legs)
  criteria_version                 # pinned rubric that produced this
}
```

One table, all ten classes — a Class 3 thread score sits alongside a Class 1 skill
score and a Class 4 market score, queryable by the same experiment-tracker rollups.
