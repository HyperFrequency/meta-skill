# Meta-loop — how this class is itself evaluated and improved

Every D13 class is a versioned scorer that must itself be kept honest and current. For class 6 the
meta-loop answers three questions: where do new fixtures come from, how does the detection schema
evolve, and how do we keep the rescue agent under test from gaming its own gate.

## 1. Fixture mining (fresh cases from real stalls)

The corpus must not go stale against how runs actually fail in production. `trajectory-miner`
(neuro-code) scans harness OTel spans + `.traj` artifacts + Claude Code session logs for repeated
stall clusters. Each confirmed stall cluster is a candidate **new fixture**:

1. `trajectory-miner` surfaces a cluster (e.g. "apply_patch loop after a fabricated test pass") as
   an `AntiPattern` / `Issue`, scrubbed of secrets/PII.
2. This skill materializes it as a `RescueFixture`: replay the real transcript (trimmed), author the
   answer key (`primary_stuck_class`, `verified_progress`, `hallucination`), and write a resumption
   oracle. Provenance records the source trace id + cluster id (`fixture-schema.md`).
3. New fixtures land in the **held-out** split first, so they measure the current rescue agent
   before any threshold is tuned to them.

This is the loop-3 → class-6 handoff the class-6 spec names: *loop-3 scanners mine real production
stalls into new fixtures.* `trajectory-miner` and this skill deliberately share one versioned
detection schema so a stall the miner clusters is the same thing the detector fires on.

## 2. Detection-schema evolution (new stuck classes)

When failure-mode synthesis over the mined clusters names a **new kind of stall** not covered by the
existing scanners (`detection-schema.md`), that is a **`schema_version` bump**, not an ad-hoc edit:

- add the scanner (or tighten a threshold) → new `detection.vN+1`.
- re-run the whole corpus under both versions; the scorecard records which version it graded under,
  so historical results stay interpretable.
- a schema bump that changes detection metrics is reviewed like any released-artifact change — never
  slipped in to make a red gate green.

## 3. Threshold tuning (external optimizer only)

Detector thresholds — doom-loop count, monologue/ping-pong windows, degradation cutoffs — trade
detection recall against false-rescue rate. They are tuned by an **external optimizer** (TPE or
CMA-ES, the search strategies pinned in Loop 1) that searches thresholds to maximize recovery-rate
headroom subject to the false-rescue ceiling, **on the tuning split only**. The held-out split then
confirms the tuning generalized (`regression-gate.md`).

Critically: **the rescue agent under test never tunes these thresholds.** Tuning is a separate
process with write access to the schema; the subject being scored has none.

## 4. Anti-gaming — disjoint write scope

The structural guarantee that makes the gate trustworthy (swe-loop disjoint-write-scope pattern; the
class-6 spec's *"never by the rescue agent itself"*):

> The rescue agent under evaluation can never edit the detection schema, the fixtures, or the gate
> thresholds.

Concretely — three separated write scopes:

| Artifact | Written by | Never written by |
|---|---|---|
| detection schema (`detection.vN`) | schema owner + external optimizer | the rescue agent under test |
| fixtures + answer keys | fixture authors + trajectory-miner mining | the rescue agent under test |
| gate thresholds (`gate.yaml`) | reviewed commits | any automated rescue-improvement loop |

If a rescue-improvement loop (e.g. `prompt-optimize`/`gepa` breeding a better re-grounding prompt)
runs, it may only mutate the **rescue agent's own prompt** — its fitness signal is this eval's score,
and it has zero write access to the thing computing that score. This is the same disjoint-scope
discipline that keeps class 1's frontier-rubric gate ungameable.

## 5. Judge-leg calibration

The `judge-panel` leg (retention, launder, class-label) can itself drift. Two guards, both inherited
from `judge-panel`'s own machinery:

- **calibration ledger** — the panel's predicted retention/launder verdicts are paired with the
  deterministic oracle outcome (a laundered hallucination should predict re-divergence); persistent
  disagreement down-weights or flags the judge.
- **Align-Evals** — human corrections on a sampled set of judge verdicts become few-shot exemplars
  spliced into the judge prompt; judge-vs-human agreement is tracked as its own regression-gated
  metric. A judge-prompt change that drops agreement is rejected — the same bar every judge in the
  harness clears.

## Provenance / licensing

All content here is original. Detection heuristics are re-implemented from the *behavioral
descriptions* of forgecode `DoomLoopDetector` (Apache-2.0) and the OpenHands StuckDetector algorithm
— described, not copied. Runner/gate/scorer patterns follow Inspect AI, promptfoo, opik, and
Braintrust (patterns only). No code is copied from PolyForm-Noncommercial (gitnexus\*), BUSL-1.1
(copula-dependency), AGPL (openobserve), or Anthropic-proprietary sources; the meta_skill lineage is
clean-room behavioral spec only.
