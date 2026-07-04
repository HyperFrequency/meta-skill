# The re-execution runner

Once `references/reproduction-contract.md` confirms the record is complete and
every reference resolves, re-execute the experiment under the resolved provenance
and capture a fresh result to diff. This file is the runner mechanics.

## Runner contract

Re-execution reuses the shared `harness_eval` chassis — the same
`task / solver / scorer` traits every class runs on (Inspect AI pattern) — so
repro-eval is not a bespoke path: it replays the *original* task/solver/scorer,
pinned to the *original* provenance. The system-under-test stays hidden behind a
completion-function-style trait, so the same re-execution works whether the
logged experiment tested a bare prompt, a graph agent, or a full Temporal
workflow.

Re-execution runs as **durable activities on the first-party spine** (opik
`evaluate()` shape: dataset × task × metrics, reconciled onto Temporal). Two
properties are load-bearing:

- **Single execution owner per item.** One item = one activity invocation that
  owns the model call, exactly as the original run did. Do not fan a single
  logged item across competing executors — that manufactures ordering
  nondeterminism the original never had.
- **Resumable via durable execution, not bespoke checkpoints.** Keep the
  pinned-inputs state shape (opik resumable-eval pattern) — a re-execution that
  is interrupted resumes from the same pinned inputs and produces the same result
  as an uninterrupted one. This resume-equivalence is itself a class-5 invariant;
  here it guarantees the *runner* does not inject nondeterminism.

## Step 1 — Reconstruct the exact config

From `config_snapshot_hash`, rehydrate the `StoredConfig` (see the snapshot-hash
section of `reproduction-contract.md`) and re-derive its structural hash. Assert
equality with the logged hash. This is not a formality: it proves the config you
are about to run under is byte-for-byte logically identical to the one the
original run used. A mismatch aborts as `unresolvable`.

Load the resolved config into `flywheel-config` in a **read-only** mode — the
re-execution must not mutate any registry (a repro run that writes back a new
config version has corrupted its own experiment).

## Step 2 — Pin dataset + restore seeds

- **Dataset:** load the exact `dataset_version` (immutable). Do not re-sample or
  re-shuffle unless the original recorded a shuffle seed — in which case restore
  that seed so the item order matches.
- **Seeds:** restore **each** recorded seed to its source (sampler seed, dataset
  shuffle seed, any stochastic solver seed, and the provider `seed` param where
  the provider honors it). A single global seed is insufficient — different
  stochastic sources must each be re-seeded from the record.
- **Sampling params:** apply the recorded `temperature / top_p / max_tokens /
  seed` per model call verbatim. If the original ran at `temperature = 0`, the
  target is (near-)deterministic and the delta gate uses exact/near-exact match;
  if `> 0`, the target is stochastic and needs the trial protocol below.

## Step 3 — Re-execute

- **Deterministic targets** (`temperature = 0`, no stochastic tools, seeds fully
  pin the sampler): run **once**. Pair with a **ScriptedJudge** control — a
  fixed-response scorer whose output is known — to prove the runner harness
  itself is deterministic (byte-identical control output every invocation). If
  the control drifts, the runner is broken; stop before blaming the experiment.
- **Stochastic targets** (`temperature > 0`, sampled tools, provider ignores
  seed): run **`n ≥ 3` trials** and collect the score distribution. Compute
  `mean`, `std_deviation`, and a `wilson_confint`-style interval over the trials
  (tensorzero evaluations `stats` shape). The gate compares distributions, not
  single points.
- Each re-execution **emits its own `.traj` trajectory + OTel trace** into
  `trace-store`, and writes fresh scores to `_llm_scores` with `source_type`
  distinguishing a reproduction run from the original — so the audit trail of the
  reproduction is itself queryable and never overwrites the original record.

## Step 4 — Capture the fresh result

Produce a `FreshResult` mirroring the recorded result's shape: the per-item
scores (or per-item trial distributions), the aggregate metric(s), realized cost,
and the fresh trace/trajectory ids. Hand this plus the recorded result to
`references/delta-gate.md`.

## What the runner must NOT do

- **No registry writes.** Config, prompt, scorer, dataset registries are
  read-only during re-execution.
- **No provenance widening.** If a field is under-specified (e.g. provider seed
  absent because the provider ignores it), record that the target is stochastic
  and route to the trial protocol — do not invent a seed to force determinism.
- **No silent model substitution.** If the recorded provider/model is
  unavailable, that is a `determinism-sources.md` "model-version drift" condition,
  surfaced to the gate — not a swap to a "close enough" model.
- **No sharing an execution owner across items.** One item, one owner, as
  originally logged.

## Determinism plumbing to respect

The runner inherits the harness's replay-safety guards (lightspeed, Apache-2.0 —
referenced): **`workflow_time` only** (no wall-clock reads in workflow code),
**`request_fingerprint` = sha256** of the request so identical requests are
detectable, and **opaque `ProviderParams`**. These exist precisely so a
re-execution on a different worker at a different time is not perturbed by clock,
retry, or param-ordering differences. If the original experiment was authored
against these guards, its non-model surface is deterministic and any residual
delta is isolated to the model/provider layer — which is exactly what the delta
gate wants to measure.
