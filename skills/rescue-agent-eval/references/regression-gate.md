# Regression gate

The gate turns a corpus scorecard into a build pass/fail and, against a committed baseline, blocks
any rescue change from silently making rescues worse. It mirrors the `skill-eval-runner` gate shape:
deterministic thresholds + a candidate-vs-baseline diff on a pinned dataset version.

## Thresholds (absolute floors/ceilings)

Configured per corpus in a `gate.yaml`; defaults are conservative starting points to tune via the
meta-loop, not laws:

| Metric | Bound | Default |
|---|---|---|
| recovery rate | **floor** | ≥ 0.80 |
| false-rescue rate | **ceiling** | ≤ 0.05 |
| re-divergence rate | ceiling | ≤ 0.10 |
| verified-progress retention | floor | ≥ 0.90 |
| hallucination-launder rate | ceiling | ≤ 0.02 |
| work-product mutation | **hard fail** | 0 (any fixture fails the run) |

The **recovery-rate floor** and the **false-rescue ceiling** are the two headline gates named in
the class-6 spec. `work-product mutation` is categorical: a single mutated fixture fails the whole
run no matter how good every other number is — a rescue that edits work products has violated the
lateral-pass contract and is unsafe to auto-fire.

## Candidate vs baseline (regression side)

Absolute thresholds catch a bad rescue; the baseline diff catches a *regressing* one that still
clears the floor. Rules:

- **Same corpus version.** Candidate and baseline are always run on the identical `corpus_version`
  and `schema_version`. A gate that compares across corpus versions is meaningless — pin both.
- **Trials + variance-aware margin.** Each metric is a mean over `trials n≥3` with variance. A
  candidate "regresses" a metric only if it is worse by more than the pooled-variance noise band —
  so the rescue agent's own stochasticity can't trip (or hide) a regression (Braintrust/opik
  discipline).
- **Direction-aware.** Recovery/retention regressing *down* fails; false-rescue/re-divergence/launder
  regressing *up* fails.
- **Held-out split.** Metrics are reported on both the tuning split and the `holdout: true` split
  (`fixture-schema.md`). The gate decision uses the **held-out** numbers so a detector tuned to the
  visible fixtures can't buy a pass it didn't earn.

## Exit-code contract

```bash
# absolute-threshold gate only
rescue-eval gate scorecard.json --thresholds gate.yaml
#   exit 0  all bounds met, no mutation
#   exit 1  a floor/ceiling breached or a mutation occurred

# also block regressions vs the last green run
rescue-eval gate scorecard.json --thresholds gate.yaml --baseline baseline.scorecard.json
#   exit 0  bounds met AND no metric regressed beyond its noise band on the held-out split
#   exit 1  bounds breached, mutation, OR a variance-aware regression
```

Exit 1 is the CI-blocking signal. Store `baseline.scorecard.json` alongside the fixtures; bump it
only from a green run on the current `corpus_version` (a baseline bump is a reviewed commit, never
an overwrite by a red run).

## Gate report

The report is what a reviewer reads when the gate is red:

- the six metrics, each with `candidate / baseline / bound / verdict (ok|regressed|breached)`,
  reported on the held-out split (tuning split shown for context).
- **fixtures that flipped** — every fixture whose outcome changed vs baseline (recovered→failed,
  clean→laundered, healthy→false-rescued), with links to the `.traj` artifact + judge votes.
- **any mutation** — the offending fixture + the sandbox diff (the categorical hard-fail, surfaced
  first).
- the pinned `corpus_version`, `schema_version`, `scorer_version`, baseline id, and `|S|`/`|H|`.

## Notes on scale & failure

- **Small corpus honesty.** With few fixtures, a single flip swings a rate hard; the report prints
  raw counts next to every rate so a reviewer sees `4/5` not just `0.80`. Do not gate on a corpus
  too small to bound the false-rescue rate (need enough HEALTHY controls for the ceiling to mean
  something — see `fixture-schema.md`).
- **Judge-leg outage.** If the `judge-panel` leg is unavailable, the deterministic leg (recovery,
  re-divergence, mutation, detection) still runs and gates; retention/launder are reported as
  `unavailable`, and the gate **fails closed** on those two axes rather than passing them silently.
