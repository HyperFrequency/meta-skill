# Grading rubric — recursive-batch-eval

Each round's `grading/scorecard.json` is scored across five rubrics. The `verdict` field summarizes them into one of: `improvement`, `plateau`, `regression`, `infra-failure`.

## Rubric 1 — Raw metric

The metric named by `--metric`, averaged across all `--concurrency` units in this round.

Fields:
- `this_round_mean`
- `this_round_median`  
- `this_round_min`
- `this_round_max`

## Rubric 2 — Deltas

Relative to the two reference points:

- `delta_vs_prev_round` — round N mean minus round N-1 mean
- `delta_vs_best` — round N mean minus best-ever mean across all rounds

Sign interpreted per `--metric-direction`:
- `max` → positive delta is improvement.
- `min` → negative delta is improvement.

## Rubric 3 — Variance

Spread of metric values across units in the round.

- `variance_units` — population variance of per-unit metric values
- **Interpretation:** high variance with high mean = unstable scaffolding (suspect the harness, not the artifact). High variance with low mean = mixed failures. Low variance + low mean = stable-but-bad.

## Rubric 4 — Cost efficiency

- `cost_usd` — total $ spent this round
- `metric_per_usd` — `(delta_vs_prev_round) / cost_usd` (sign-adjusted for direction)

Negative metric_per_usd means the round regressed AND cost money. Two of these in a row triggers halt.

## Rubric 5 — Failure modes

Categorize every non-passing unit:

- `flaky` — passes on retry (or: unit-to-unit variance > 3σ on same code path)
- `deterministic` — fails reproducibly on the artifact (genuine regression)
- `infra` — failure in harness, network, cloud, disk (not the artifact's fault)

Counts stored as `{"flaky": <n>, "deterministic": <n>, "infra": <n>}`.

## Verdict decision table

| Condition | Verdict |
|---|---|
| `delta_vs_best` favorable AND `deterministic == 0` | `improvement` |
| `\|delta_vs_prev_round\| / \|prev_mean\| < 0.01` for 3 rounds | `plateau` |
| `delta_vs_prev_round` unfavorable OR `deterministic > 0` | `regression` |
| `infra > 0.5 * concurrency` | `infra-failure` |

Ties break toward the worse verdict (precautionary).

## Loop gate consumption

The main loop reads `verdict` + budget + history:

- `improvement` → continue, apply top-K patches
- `plateau` (3-in-a-row) → halt, write `.done`, surface tearsheet
- `regression` (2-in-a-row per `--stop-on-regression`) → halt, mark best-ever round as winner
- `infra-failure` → do NOT count toward regression streak, retry with cloud fallback
