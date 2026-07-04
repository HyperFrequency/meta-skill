# The delta gate

Turn a `FreshResult` (from `references/re-execution-runner.md`) and the original
recorded result into one of three verdicts:

- **`reproduced`** — fresh result is within the declared tolerance of the record.
- **`drifted`** — fresh result is outside tolerance; must be root-caused
  (`references/determinism-sources.md`) before it is accepted as a real
  regression vs a provenance defect.
- **`unresolvable`** — a referenced artifact did not resolve (decided upstream in
  the contract; restated here because it is a gate outcome, always hard-fail).

The gate is the class-8 regression gate: "reproduction delta ≤ tolerance with
ScriptedJudge; any unresolvable artifact reference = hard fail; leaderboard/rollup
drift alarms."

## Tolerance is declared, per determinism class

The tolerance band is **read from the record**, never improvised. It is selected
by the result component's K/B/I determinism class (see
`reproduction-contract.md`):

| Class | Determinism | Match rule |
|---|---|---|
| **Known** | fully deterministic (temp 0, seeds pin sampler, no stochastic tools) | **exact match** (or bit-tolerance for documented float ordering) — any diff is `drifted` |
| **Believed** | stochastic but bounded (temp > 0, sampled tools) | **distributional**: fresh trial mean must fall within the recorded confidence band; overlap of Wilson intervals |
| **Inferred** | downstream computation of the above | propagate the tolerance of its inputs |

For deterministic (`Known`) targets the comparison is exact and the **ScriptedJudge
control must be byte-identical** — if the control drifts the gate is invalid
(runner defect), and the verdict is neither reproduced nor drifted but "runner
broken", reported as such.

For stochastic (`Believed`) targets, apply the variance-aware compare the other
classes use: trials `n ≥ 3`, compare fresh `mean` against the recorded
distribution with `std_deviation` / Wilson-interval overlap (tensorzero `stats`;
Braintrust/opik trial statistics) so reproduction noise does not read as
regression, and a true regression is not masked by noise. The tolerance band
width is a pinned number on the record — **widening it to make a failing run pass
is a provenance defect, not a fix**, and must be flagged, not applied.

## Hard-fail conditions (no tolerance applies)

These fail the experiment outright regardless of the numeric delta:

- **Any unresolvable artifact reference** (config/dataset/prompt/scorer/trace/
  CAS blob) — `unresolvable`.
- **Snapshot hash re-derivation mismatch** — the resolved config is not the
  logged config; identity is broken.
- **ScriptedJudge control drift** — the runner is nondeterministic; no result
  is trustworthy until fixed.
- **A registry write during re-execution** — the reproduction mutated state it
  was supposed to only read; the run is void.
- **K/B/I tag inconsistent with true determinism class** — e.g. a stochastic
  judge score tagged `Known`; a completeness defect that pre-empts the numeric
  gate.

## Drift alarms on rollups

Beyond a single experiment, the gate watches **leaderboard / rollup drift**: when
a re-execution of a sampled historical experiment lands `drifted`, and that
experiment feeds an aggregate leaderboard value, raise a drift alarm on the
rollup (openobserve alert-shape → HITL spine signal, clean-room). A silent
leaderboard whose underlying runs no longer reproduce is the exact failure this
class exists to catch.

## Gate contract (exit semantics)

Model the gate as a Test-Suite assertion rollup (opik `AssertionResult` shape) so
it drops into CI unchanged:

- **PASS (exit 0)** — verdict `reproduced` for the sampled experiment(s); every
  checklist reference resolved; controls byte-identical.
- **FAIL (exit 1)** — any `unresolvable`, any `drifted` not yet reconciled, any
  hard-fail condition, or a raised rollup drift alarm.
- **Sampling.** Auditing a *set* of past experiments uses deterministic
  `trace_id`-hash head sampling (openobserve pattern, clean-room) so the same
  audit slice is reproducible across CI runs — the reproducibility auditor must
  itself be reproducible.

## After a `drifted` verdict

`drifted` is **not** an accept and **not** an auto-reject. Route to
`references/determinism-sources.md` and run the elimination loop
(`anomaly-investigation` discipline): identify which single provenance dimension
leaked. Outcomes:

- Leak is a **provenance defect** (unpinned seed, unrecorded temperature,
  mutable dataset) → fix the *logging*, not the tolerance; the experiment is
  marked non-reproducible until re-logged completely.
- Leak is **external and expected** (provider model-version bump) → record the
  model drift as the cause; the original result is annotated as reproducible only
  under the pinned model, and the leaderboard entry is footnoted.
- No leak found and the delta is real → it is a genuine **regression** in the
  system under test; hand back to the owning eval class.

Every verdict — including the drift root cause — is written to `_llm_scores` with
`source_type = annotation` so the reproduction decision is itself regression-
gateable (the meta-loop: judge-vs-human agreement on reproduction calls is
tracked like any other metric).
