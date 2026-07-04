---
name: repro-eval
version: 0.1.0
description: >-
  Re-execute a previously logged harness experiment from its recorded
  config-snapshot hash, pinned dataset version, seeds, and artifacts, then GATE
  on the delta between the fresh and original recorded result. The
  reproducibility eval class (neuro-centrifuge D13 class 8): the meta-class that
  audits every other eval class's runs and fails when a result cannot be
  reproduced. Use when the user says "reproduce this experiment", "repro-eval",
  "is this result reproducible", "reproduction gate", before trusting a logged
  eval result, or for CI asserting every logged
  experiment resolves and re-runs within tolerance. Generalizes
  neuro-quant-research-proof beyond the quant monorepo to ANY harness
  experiment. Do NOT use to first-run or score a NEW candidate vs baseline (use
  skill-eval-runner) — repro-eval only re-runs already-logged experiments; nor
  to verify repo-local quant artifacts (neuro-quant-research-proof), compute
  PBO/deflated-Sharpe stats (model-evaluation), or check external claims
  (claim-verify).
---

# repro-eval

Re-run an experiment the harness already logged, from **only its recorded
provenance**, and decide whether it reproduces. The unit of work is one logged
experiment record; the output is a reproduction verdict — `reproduced` (fresh
result within tolerance), `drifted` (outside tolerance, root-caused), or
`unresolvable` (a referenced artifact no longer resolves — always a hard fail).

This is the neuro-centrifuge **D13 class 8** runner (experiment logging &
reproducibility). It is the *meta-class*: it audits the runs of every other eval
class (skill, prompt, agent-session, market-reward, graph, rescue, context,
temporal-authoring, accuracy) by re-executing sampled records and confirming the
logged number is the number you get back. If a class's own runs do not
reproduce, that class's gates cannot be trusted.

It generalizes `neuro-quant-research-proof` — the quant-monorepo verify-gate —
to **any** harness experiment: not just Modal/strategy/Optuna artifacts, but any
prompt/graph/workflow/skill run captured in `experiment-tracker`.

## What "reproducible" requires

An experiment is reproducible only if its record resolves to a **complete,
pinned provenance set** and re-executing under that set lands within tolerance.
The completeness checklist (config-snapshot hash, prompt versions, scorer
versions + `score_config` versions, dataset version, seeds, per-provider sampling
params, costs, trace ids, and K/B/I epistemic metadata) plus how to resolve each
artifact reference is in **`references/reproduction-contract.md`**. Any
unresolvable reference is a hard fail before re-execution even starts.

## The workflow

1. **Load the record** from `experiment-tracker` (its snapshot hash, dataset
   version, seeds, variant/prompt/scorer versions). → verify: every field in the
   completeness checklist is present and non-null.
2. **Resolve provenance** — reconstruct the exact config from its
   `config-snapshot` hash, pin the dataset version, restore seeds, resolve every
   trace/artifact reference. → verify: resolved config's re-derived structural
   hash equals the logged hash (content-addressed identity, not text identity).
3. **Re-execute** the same task under the resolved provenance — as durable
   activities, single execution owner per item, `n ≥ 3` trials for stochastic
   targets. Deterministic control pairs run under a ScriptedJudge. → verify: the
   fresh run emits its own trajectory + OTel trace and writes fresh scores.
4. **Compute the delta** between fresh and recorded results and apply the gate
   (exact-match for deterministic outputs; a variance-aware tolerance band for
   stochastic ones). → verify: verdict is one of reproduced / drifted /
   unresolvable, with the delta and tolerance recorded.
5. **Root-cause any drift** through the elimination loop (which provenance
   dimension leaked — see `references/determinism-sources.md`) before accepting
   or rejecting; record the verdict as an annotation score so the reproduction
   process is itself auditable.

Step-by-step re-execution mechanics (resolving a config from its snapshot hash,
restoring seeds, resume-state shape, durable single-owner execution) are in
**`references/re-execution-runner.md`**. The tolerance model, hard-fail
conditions, drift alarms, and the full gate contract are in
**`references/delta-gate.md`**.

## Why deltas happen — and which ones are real

A nonzero delta is not automatically a failure. Provenance leaks
(unpinned seed, unpinned dataset version, unrecorded sampling temperature),
model-version drift on the provider side, cache replay mismatches, and
floating-point / ordering nondeterminism each produce characteristic delta
signatures. Classifying a delta as **benign reproduction noise** vs a **real
regression or a provenance defect** is the skill's core judgment — the taxonomy
of nondeterminism sources and their fixes (provider sampling, banned clock/rand
in workflow code, `request_fingerprint` replay-safety, tool nondeterminism) is
in **`references/determinism-sources.md`**.

## The meta-class duty

Because class 8 audits all the others, it carries extra discipline: provenance
lint runs in CI on every eval PR; leaderboard/rollup values get drift alarms;
feedback-type ablation matrices and preregistration records make methodology
drift visible; and the **disjoint-write-scope** rule holds — the run under audit
can never edit its own reproduction gate. The audit responsibilities, CI
provenance-lint contract, and anti-gaming rules are in
**`references/meta-class-audit.md`**.

## Boundaries and cross-links

- **First-run vs re-run.** repro-eval never authors or first-runs an eval. It
  re-executes an **already-logged** experiment and checks it replays. To score a
  *new* candidate against a baseline, use `skill-eval-runner` (class 1) or the
  relevant class runner; repro-eval consumes the records those runners produce.
- **Harness experiment vs quant artifact.** `neuro-quant-research-proof` is the
  quant-monorepo-scoped ancestor (validate repo-local research/Modal/strategy/
  release evidence). repro-eval is its harness-wide generalization; hand quant
  repo-local proofs back to it, keep harness experiment re-execution here.
- **Reproduction vs overfit statistics.** Probability of Backtest Overfitting,
  deflated/probabilistic Sharpe, and multiple-testing corrections are
  `model-evaluation`; repro-eval asks only "does the logged number come back",
  not "is the number overfit".
- **Reproduction vs external claim.** Checking a claim against outside sources is
  `claim-verify`; repro-eval checks the harness's own logged runs against
  themselves.
- **Anomaly root-cause.** When a delta is real and needs diagnosis, the
  elimination discipline mirrors `anomaly-investigation`; repro-eval owns the
  reproduction gate, that skill owns the general single-anomaly hunt.

## Non-negotiables

- **Re-run from the record, not from memory.** Never assert a result reproduces
  without actually re-executing under the resolved provenance.
- **Unresolvable reference = hard fail.** A dangling config/dataset/trace/artifact
  reference fails the experiment outright; it is not "reproduced with a warning".
- **Tolerance is declared, not improvised.** The delta gate reads a pinned
  tolerance band; widening a band to make a run pass is a provenance defect, not
  a fix.
- **Original content only.** This skill is original work. It may read donor repos
  (tensorzero, lightspeed, gepars, episteme — Apache-2.0/MIT) for accuracy but
  copies no code or text; openobserve behaviors are described clean-room (no
  AGPL code lifted).
