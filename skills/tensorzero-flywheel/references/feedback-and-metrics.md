# Feedback, Metrics, Episodes & Datapoint Curation — the `feedback-store` plane

Behavioral spec for the storage + feedback layer, distilled from TensorZero-core `endpoints/feedback`,
`config/mod.rs` (MetricConfig), `db/feedback.rs`, `db/variant_statistics.rs`, `stored_inference.rs`, and
`db/stored_datapoint.rs` at pinned SHA `62eb8f63e`. **Postgres migrations are canonical; ClickHouse is
skipped entirely.** Where the donor names a ClickHouse table, translate to the Postgres table.

## 1. The metric definition (the reward triple)

Every metric declared in `flywheel-config` is exactly three orthogonal choices plus an optional description:

```
MetricConfig {
  type:     Boolean | Float          // what kind of value feedback carries
  optimize: Min | Max                // which direction is "better" (loss vs. reward)
  level:    Inference | Episode      // what the feedback attaches to
  description: Option<String>
}
```

- **type** picks the storage table: boolean → `tensorzero.boolean_metric_feedback`, float →
  `tensorzero.float_metric_feedback` (donor Postgres names; keep or re-namespace consistently).
- **optimize** tells the experiment/optimization planes how to rank variants (max reward or min loss). It is
  metadata the loop *reads* — it does not change storage.
- **level** decides the join key: `Inference` joins on the inference `id`; `Episode` joins on `episode_id`.
  This is the single most important field for the flywheel — see §3.

## 2. The four feedback types

The feedback endpoint accepts a `metric_name` + a `target_id` (an inference id or an episode id) + a value,
and dispatches on the metric's declared type. There are four `FeedbackType`s:

| FeedbackType | Value | Table / storage | Role in the flywheel |
|---|---|---|---|
| **Boolean** | `true/false` | `boolean_metric_feedback` | pass/fail signals (task solved?, gate passed?) |
| **Float** | `f64` | `float_metric_feedback` | graded reward (judge score, latency, cost proxy) |
| **Comment** | free text | comment feedback (target = Inference or Episode) | human notes; not directly optimized |
| **Demonstration** | a gold output | demonstration feedback (Inference level **only**) | gold labels → SFT training rows |

Rules from the donor worth preserving:

- **Demonstrations are inference-level only.** The endpoint hard-codes `MetricConfigLevel::Inference` for
  demonstrations — a demonstration is "here is the correct output for *this call*", which has no meaning at
  episode granularity. Enforce this.
- **A demonstration is validated against the function's contract.** For a Chat function the demo is content
  blocks / tool calls matched against the tool config (`DynamicDemonstrationInfo`); for a Json function it is
  a schema-valid object. Reject demos that don't type-check — a malformed gold label silently poisons every
  downstream SFT job.
- **Metric name must be declared.** Feedback for an unknown `metric_name` is rejected (except the two
  built-in comment/demonstration channels). The config is the source of truth for what can be measured.

Edge cases to handle explicitly: unknown metric name (reject, don't create-on-write); type mismatch (float
value on a boolean metric → reject); target id that doesn't exist yet (the donor allows feedback to arrive
before/independently of the inference write — decide your ordering and make it idempotent); duplicate
feedback on the same (metric, target) — decide last-write-wins vs. append and document it.

## 3. Episodes — the reward model for multi-step work

An **episode** is a UUIDv7 `episode_id` that spans many inferences belonging to one logical task/workflow.
UUIDv7 is time-ordered, so episodes sort chronologically for free and range-scan efficiently on Postgres.

Why this is the heart of the flywheel: a single inference's boolean/float feedback only rewards one call.
But most real work is a **trajectory** — plan, call tool, revise, answer. Attaching an **episode-level**
metric (`level: Episode`) lets you reward the *outcome of the whole trajectory* and propagate that signal
to every variant that participated. This is the credit-assignment substrate:

- Inference-level feedback → per-call supervised signal (good for SFT/prompt tuning of one step).
- Episode-level feedback → outcome reward for the trajectory (good for RFT/RL-style optimization and for
  judging whether a *workflow* change helped, not just a prompt).

When you design a function, decide up-front which metrics live at which level. A judge that scores "did the
final answer solve the user's task" is episode-level; a judge that scores "was this individual step's tool
call well-formed" is inference-level. Getting the level wrong makes the optimizer chase the wrong target.

## 4. Inference storage schema

Three canonical row shapes (donor `stored_inference.rs`, `db/inferences.rs`, `db/model_inferences.rs`):

- **ChatInference** — a Chat-function call: input messages + output content blocks + variant + episode_id.
- **JsonInference** — a Json-function call: input + schema-validated output object.
- **ModelInference** — the raw per-provider-call record beneath a variant (a best_of_n variant produces many
  ModelInference rows for one ChatInference). This is where token counts, latency, and **raw failed-provider
  capture** live, feeding cost/usage tracking.

Keep the ClickHouse latency/TTFT quantile columns as **`None` on Postgres** (the donor's variant-statistics
row already models this: `processing_time_ms_quantiles` / `ttft_ms_quantiles` are ClickHouse-only). Don't
fabricate quantiles you can't compute cheaply in Postgres — compute mean/count there, defer quantiles.

## 5. Datapoint curation — closing the loop into training data

The bridge from "logged traffic" to "training set" is `into_datapoint_insert` (donor `stored_inference.rs`):
a stored inference is promoted into a **datapoint** in a named, versioned **dataset**. Datapoints come in
`StoredChatInferenceDatapoint` / `StoredJsonInferenceDatapoint` shapes and become the input corpus for both
GEPA minibatches and SFT/RFT jobs.

Curation sources, in priority order:
1. **Demonstrations** — human-provided gold outputs are the highest-quality datapoints (direct SFT rows).
2. **High-reward inferences** — inferences whose metric feedback clears a threshold become positive examples.
3. **Filtered live traffic** — sampled real inferences, optionally judge-scored, for coverage.

### DPO / preference pairs — `dispreferred_outputs`

`RenderedSample` carries `dispreferred_outputs: Vec<Vec<ContentBlockChatOutput>>` — the **rejected** side of
a preference pair. A DPO datapoint = one preferred output (the demonstration or high-reward output) + one or
more dispreferred outputs (lower-reward variant outputs on the same input). Curate these by pairing, for a
fixed input, the best-scoring output against worse-scoring outputs from other variants/samples.

- **Schema is phase-1** (store the `dispreferred_outputs` column now); **consumption is phase-2** (a DPO
  fine-tune job reads it once `model-optimizer` lands). Don't block phase-1 on the trainer.
- A preference pair with an empty or identical dispreferred set is not a valid DPO row — filter those out at
  curation time, not at train time.

## 6. What you hand downstream

The feedback-store's contract to the rest of the flywheel:
- `experiment-tracker` reads **per-variant aggregates** (see `experimentation.md` — mean/variance/count/cost).
- `prompt-evolver` reads **pinned-version dataset minibatches** + **reflective failure traces**.
- `model-optimizer` reads **curated datasets** (demonstrations, high-reward, DPO pairs).

Keep dataset **versions immutable and pinned** — a GEPA run or SFT job must reference the exact datapoint set
it trained on, or lineage and regression comparisons become meaningless.
