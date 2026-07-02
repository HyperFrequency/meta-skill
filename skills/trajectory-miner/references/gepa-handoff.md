# GEPA handoff — mined failures → reflective dataset

Optional step 7. When the caller wants to *drive* prompt/harness evolution (not
just read a report), convert the mined failing trajectories into a **GEPA
reflective dataset** that the user's MIT-licensed `gepa`/gepars crate consumes.
The reflection LM reads the failure feedback and proposes an improved instruction
for the component that failed.

> License: gepars (crate name `gepa`) is **MIT** — wrap it freely. This doc
> describes its *public* API; write your own glue, don't copy its internals.

---

## What GEPA expects

Verified against the crate:

- `pub type ReflectiveDataset = HashMap<String, Vec<serde_json::Value>>` —
  keyed by **component name** (the prompt/instruction slot you want to improve,
  e.g. `"planner"`, `"bash_agent"`, `"system_prompt"`), value = a list of
  per-example records.
- Each record is a JSON object with exactly these keys (GEPA's reflection
  meta-prompt renders them as `## Inputs`, `## Generated Outputs`, `## Feedback`):

  ```json
  { "Inputs": "…", "Generated Outputs": "…", "Feedback": "…" }
  ```

- The reflection loop that consumes it:
  `gepa::proposer::reflective_mutation::ReflectiveMutationProposer` (re-exported
  as `gepa::ReflectiveMutationProposer`). It calls a
  `reflection_lm: Arc<dyn gepa::LanguageModel>` on a rendered meta-prompt to
  produce a new component text. A full run goes through `gepa::optimize(...)`
  with `gepa::{GEPAAdapter, LMConfig, OptimizeConfig}`.

Relevant public exports (from `src/lib.rs`): `optimize`, `Candidate`,
`EvaluationBatch`, `GEPAAdapter`, `ReflectiveDataset`, `LMConfig`,
`OptimizeConfig`, `LanguageModel`, `OpenAICompatibleLM`,
`ReflectiveMutationProposer`, `PromptTemplateConfig`.

---

## Mapping mined incidents → records

For each cluster (or each representative incident), map:

| GEPA field          | Source from a mined incident                                        |
|---------------------|---------------------------------------------------------------------|
| `Inputs`            | the session `goal_text` + the state at the diverging turn (the ask). |
| `Generated Outputs` | the agent's actual (bad) behavior at `turn_range` — the loop, the fabricated claim, the refusal, the cascade. |
| `Feedback`          | why it's wrong + the fix direction — the cluster `name`, `mode`, and `recommended_fix`. This is the signal GEPA optimizes against; make it specific and actionable. |

Bucket records under the **component** responsible for that failure. Infer the
component from the incident: a `Bash` error cascade → the tool-using executor
prompt; a `refusal` → the system prompt; a `goal_drift` → the planner. If the
harness has no named components, use a single `"system_prompt"` key.

Emit `reflective-dataset.json`:

```json
{
  "planner": [
    { "Inputs": "Goal: ship the parser. State: 3 tests failing.",
      "Generated Outputs": "Re-ran `git status` 6x, never touched the failing test.",
      "Feedback": "loop / no-progress. Add a stop rule: after 2 identical Bash calls, switch to editing the failing test. See cluster loop-bash-git-status." }
  ],
  "system_prompt": [
    { "Inputs": "Goal: refactor auth module.",
      "Generated Outputs": "\"I'm unable to help with that.\"",
      "Feedback": "refusal on a benign task. Constrain the refusal policy so ordinary code refactors are not declined." }
  ]
}
```

This file is already in GEPA's `ReflectiveDataset` shape — it deserializes
directly into `HashMap<String, Vec<Value>>`.

---

## Feeding it into gepars

Two integration depths:

1. **Dataset only (recommended default).** Emit `reflective-dataset.json` and
   stop. The caller's existing GEPA pipeline — or `recursive-self-improvement` /
   `autonomous-orchestrator` — loads it and runs the optimizer. This skill stays
   read-only and does not need to build or run Rust.

2. **Direct wrap.** When the caller wants trajectory-miner to trigger the run:
   implement `gepa::GEPAAdapter` whose `make_reflective_dataset(candidate,
   eval_batch, components_to_update)` returns the mined records for exactly the
   requested `components_to_update` (it filters by component name), configure a
   `reflection_lm` via `gepa::LMConfig` (an `OpenAICompatibleLM` against your
   OpenRouter/local endpoint), and call `gepa::optimize(...)`. The proposer
   mutates the failing component's instruction and Pareto-selects candidates.

Keep the boundary clean: trajectory-miner **produces the failure signal**; GEPA
**proposes the fix**; a graded HITL loop (`recursive-self-improvement`) or the
harness owner **decides whether to apply it**. This skill never applies a
mutation itself.

---

## Notes / gotchas

- `make_reflective_dataset` **silently skips** components absent from the dataset
  — so only the components you populate get improved. Populate every component
  you have evidence for.
- `Feedback` quality is the whole game: a vague "this was wrong" teaches the
  reflection LM nothing. Carry the concrete `mode` + `recommended_fix` + the
  cluster id so the proposal is grounded.
- Do not over-weight rare failures: records should mirror cluster `count` /
  `priority`, or GEPA optimizes for a one-off at the expense of the systemic mode.
- The dataset carries raw (scrubbed) trajectory text — treat it as sensitive,
  same as the source transcripts (see redaction in `clustering-and-report.md`).
