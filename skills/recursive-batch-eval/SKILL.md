---
name: recursive-batch-eval
description: Stage-graded recursive batch evaluation orchestrator. Uses multi-turn Opus 4.7 max + GPT-5.5 xhigh ideation to design tests + scaffolding, mirrors local dev or simulated cloud, runs concurrent parallel tests with extensive logs, grades rigorously, infers changes, runs the next round, and keeps staging improvements while within budget. Hard $200/day API ceiling by default. Outputs to ~/Desktop/recursive-batch-eval-<run_id>/ with tearsheet + full logs in the same artifact pattern as /gigaprompt and /exaflop. Trigger on `/recursive-batch-eval`, "recursive batch eval", "stage-graded batch verify", or when the user wants systematic improvement-under-budget rather than one-shot completion. Distinct from /batch-create-eval (which ships units) and /exaflop (which picks between persona proposals) — this one iterates on a working artifact, grading and improving in stages. Explicit daily budget. Do NOT fire on single-shot tasks.
---

# recursive-batch-eval

Stage-graded, recursive improvement orchestrator. Given a working (or mostly-working) artifact and a goal, it runs rounds of: test ideation → scaffolding → parallel execution → grading → inferred changes → next round. Each round ends with a recorded tearsheet. Loops as long as progress is measurable and budget remains.

Where `/gigaprompt` says "ship it with proof" and `/exaflop` says "pick the best of three proposals", this says **"keep grading it and making it better until the money runs out or the metric stops moving."**

## When to fire

- User has a working (or partially working) monorepo/service/model and wants it *better*, not *done*.
- Performance, robustness, coverage, or evaluation quality is the actual goal.
- The improvement surface is large enough that one-shot work won't find the best version.
- User says "recursive batch eval", "stage-graded", "keep iterating within budget", or drops this skill name directly.

## When NOT to fire

- Single-shot build tasks — use `/gigaprompt` or `/batch-create-eval`.
- Picking between mutually exclusive design proposals — use `/exaflop`.
- Tasks without a quantifiable grading metric — this skill needs a number to optimize.

## Flags

```
/recursive-batch-eval <goal>
  [--artifact <path>]               (default: cwd)
  [--metric <name>]                 (required — e.g. sharpe, rmse, p99-latency, coverage-pct)
  [--metric-direction <max|min>]    (required)
  [--budget-usd-daily <n>]          (default: 200; see §Budget)
  [--max-rounds <n>]                (default: unbounded — budget is the guard)
  [--concurrency <n>]               (default: 6; concurrent eval units)
  [--cloud <modal|ray|k8s|local>]   (default: local with cloud auto-fallback)
  [--ideation-model <id,id,...>]    (default: claude-opus-4-7[1m],gpt-5.5-xhigh)
  [--run-root <path>]               (default: ~/Desktop/recursive-batch-eval-<run_id>)
  [--seed-tests <path>]             (optional — skip initial ideation for round 0)
  [--stop-on-regression <n>]        (default: 2 — halt after N consecutive rounds with worse metric)
  [--dry-run]                       (plan only, no execution)
```

## Round loop

```
Round N:
  1. Ideate       opus-4-7[1m] max + gpt-5.5 xhigh brainstorm new test cases +
                  inferred changes from Round N-1 grading. Multi-turn — each
                  model sees the other's most recent round artifacts.
                  Output:  ideation/round-N/proposals.md,  tests.yaml
  2. Scaffold     Generate test harness code from tests.yaml.
                  Mirror: local dev OR simulated cloud (modal stub / ray stub / k8s stub).
                  Output:  scaffolding/round-N/
  3. Execute      Fan out --concurrency units in parallel. Capture stdout/stderr,
                  metric values, artifact checksums, wall time, token usage,
                  cost estimate per unit.
                  Output:  logs/round-N/unit-<i>.{log,metrics.json}
  4. Grade        Rigorous scoring against --metric. Multi-rubric:
                  a) raw metric value
                  b) regression vs. round N-1 and vs. best-ever round
                  c) variance across units (high variance = weak scaffolding)
                  d) cost efficiency: metric delta per $ spent
                  e) failure modes — categorized (flaky / deterministic / infra)
                  Output:  grading/round-N/{scorecard.json, tearsheet.html, findings.md}
  5. Infer        opus-4-7[1m] max reads grading + prior rounds, proposes changes
                  to both artifact and test suite. Ranks by expected metric delta /
                  expected cost.
                  Output:  inferred-changes/round-N/plan.md
  6. Apply        Apply top-K inferred changes to artifact (worktree merge) if
                  confidence >= 0.6. Else write as pending.
                  Output:  patches/round-N/ + artifact updated
  7. Loop gate    Continue if:
                    (budget_remaining > per-round-floor) AND
                    NOT (last --stop-on-regression rounds all worse) AND
                    NOT (metric plateau — delta < 1% for 3 consecutive rounds)
                  Halt otherwise.
```

Each round writes a top-level `rounds/round-N/` dir with everything above.

## Budget

- `--budget-usd-daily 200` by default. Reset at midnight local time (tracked in `budget.jsonl`).
- Per-round floor: `$5` (if remaining budget < $5, halt).
- Budget accounting fields (one line per event):

```json
{"ts":"...", "round":3, "phase":"ideate",   "model":"claude-opus-4-7[1m]", "input_tokens":84000, "output_tokens":9200, "est_usd":2.15}
{"ts":"...", "round":3, "phase":"execute",  "unit":7, "runtime":"modal", "gpu":"8xB200", "minutes":4.2, "est_usd":8.40}
{"ts":"...", "round":3, "phase":"grade",    "model":"claude-opus-4-7[1m]", "est_usd":0.95}
```

### Budget override

The user can raise the ceiling mid-run with:

```bash
~/.claude/skills/recursive-batch-eval/scripts/set-budget.sh <run_id> <new_usd_daily>
```

which writes the new ceiling to `budget.json` and surfaces it in the next round's tearsheet. No silent extensions.

## Output layout

All artifacts go to the Desktop so they're visible without digging:

```
~/Desktop/recursive-batch-eval-<run_id>/
├── mission.md                       # goal, metric, direction, constraints
├── budget.json                      # ceiling + spent + remaining
├── budget.jsonl                     # append-only event log
├── tearsheet.html                   # LIVE — updated after every round
├── tearsheet-round-N.html           # frozen snapshot per round
├── rounds/
│   ├── round-00/                    # seed / baseline
│   │   ├── ideation/
│   │   ├── scaffolding/
│   │   ├── logs/
│   │   ├── grading/
│   │   ├── inferred-changes/
│   │   └── patches/
│   ├── round-01/ ...
│   └── round-N/ ...
├── ideation/                        # aggregated ideation across rounds
├── patches/                         # consolidated patch timeline
├── adversarial-reviews/             # /codex:adversarial-review per round
└── .done                            # written when loop terminates cleanly
```

Matches the directory shape of `.batch-runs/exaflop-<run_id>/` and `.batch-runs/gigaprompt-<run_id>/` so tearsheet viewers already in the repo work unchanged.

## Ideation — multi-turn opus + gpt-5.5

Round 0: each model independently proposes baseline tests + metric instrumentation.

Round N (N≥1): models do **three** turns each per round:

```
Turn 1 → read Round N-1 grading + inferred-changes, propose 3-5 new tests
Turn 2 → critique each other's Turn 1 proposals (write-then-read)
Turn 3 → merge into consolidated tests.yaml with a rationale per test
```

The consolidation is adversarial — if one model flags another's test as redundant, weak, or unmeasurable, it must be justified or cut. The GPT-5.5 side is invoked via `/codex:gpt-5-5-prompting` contract at `xhigh` effort. The Claude side is `claude -p --model claude-opus-4-7[1m]` at max effort.

Both sides' transcripts are written to `ideation/round-N/transcripts/`.

## Grading rigor

Each round's scorecard is a structured JSON + a human-readable tearsheet row:

```json
{
  "round": 3,
  "metric": "sharpe",
  "direction": "max",
  "best_ever": 1.42,
  "this_round_mean": 1.38,
  "this_round_median": 1.41,
  "this_round_min": 0.92,
  "this_round_max": 1.58,
  "delta_vs_prev_round": -0.03,
  "delta_vs_best": -0.04,
  "variance_units": 0.18,
  "cost_usd": 23.40,
  "metric_per_usd": 0.059,
  "failure_modes": {"flaky": 1, "deterministic": 0, "infra": 0},
  "verdict": "plateau"
}
```

`verdict` is one of: `improvement`, `plateau`, `regression`, `infra-failure`. The loop's stop rules key off these.

## Cloud fallback

If local resources saturate during Phase 3 (Execute), the skill invokes the same cloud order as `--inception-perfect`:

1. Modal (GPU) — default 8xB200 / 8xB300
2. Ray (CPU cluster for parallel trials, or GPU trials that fan out)
3. Kubernetes (CPU pools)
4. Local Docker / Cursor dev container (only with explicit flag)

Preflights in `references/cloud-preflight.md`.

## Adversarial review cadence

`/codex:adversarial-review --effort xhigh` fires at the end of every round, reading:

- `rounds/round-N/grading/scorecard.json`
- `rounds/round-N/inferred-changes/plan.md`
- `rounds/round-N/patches/`

Output appended to `adversarial-reviews/round-N.md`. A round is not eligible to produce a patch-apply unless the adversarial review does not return a CRITICAL finding.

## Scripts

- `scripts/orchestrate.sh` — main entry; drives the round loop.
- `scripts/ideate.sh` — invokes opus + gpt-5.5 per round.
- `scripts/scaffold.sh` — generates harness code from tests.yaml.
- `scripts/execute.sh` — fans out --concurrency units; handles cloud fallback.
- `scripts/grade.sh` — computes scorecard.json + tearsheet row.
- `scripts/infer.sh` — proposes next-round changes.
- `scripts/apply-patches.sh` — worktree-merges accepted patches.
- `scripts/tearsheet.sh` — updates HTML tearsheet after each round.
- `scripts/set-budget.sh` — raise ceiling mid-run.

All scripts are idempotent and safe to re-run.

## References

- `references/round-template.md` — directory + file shapes for each round.
- `references/tearsheet-template.html` — Desktop-facing tearsheet.
- `references/cloud-preflight.md` — modal/ray/k8s preflight commands.
- `references/grading-rubric.md` — multi-rubric scoring spec.
- `references/ideation-contract.md` — opus + gpt-5.5 multi-turn protocol.

## Anti-patterns

- Running without `--metric` + `--metric-direction`. This skill optimizes a number; without one it's just a vibe loop.
- Accepting inferred changes when the adversarial review found a CRITICAL. The loop halts or restarts that round.
- Applying patches with confidence < 0.6 silently. They go to `pending/`, not `patches/`.
- Exceeding daily budget. The ceiling is a hard stop, not a soft warning.
- Using this skill on single-round tasks — that's `/batch-create-eval`.

## Interaction with other skills

- **`/gigaprompt --inception-perfect`** can spawn `/recursive-batch-eval` for performance optimization phases after the two-consecutive-pass rule is met. The inception loop keeps correctness green; recursive-batch-eval pushes the metric.
- **`/exaflop`** can seed a winning persona's branch into `/recursive-batch-eval` to squeeze additional quality before merge.
- **`/batch-create-verify`** produces the artifact; `/recursive-batch-eval` polishes it.
