# Round directory template

Every round produces the same directory tree:

```
rounds/round-<N>/
├── README.md                     # 1-para summary + verdict + metric delta
├── ideation/
│   ├── opus-turn-1.md            # claude-opus-4-7[1m] turn 1
│   ├── opus-turn-2.md
│   ├── opus-turn-3.md
│   ├── gpt-5-5-turn-1.md         # via /codex:gpt-5-5-prompting
│   ├── gpt-5-5-turn-2.md
│   ├── gpt-5-5-turn-3.md
│   ├── transcripts/              # raw model I/O
│   ├── tests.yaml                # consolidated test spec (input to scaffolding)
│   └── proposals.md              # human-readable merge of both sides
├── scaffolding/
│   ├── harness/                  # generated test runner code
│   ├── mirror/                   # local-dev OR simulated-cloud shims
│   └── fixtures/                 # data fixtures per test
├── logs/
│   ├── unit-01.log
│   ├── unit-01.metrics.json
│   ├── ...
│   └── unit-<K>.metrics.json
├── grading/
│   ├── scorecard.json            # machine-readable (see grading-rubric.md)
│   ├── findings.md               # flaky/deterministic/infra breakdown
│   └── tearsheet-row.html        # appended to top-level tearsheet.html
├── inferred-changes/
│   ├── plan.md                   # ranked proposals from opus-4-7[1m]
│   └── expected-deltas.json      # per-proposal expected metric + $ cost
├── patches/
│   ├── applied/                  # successfully worktree-merged
│   └── pending/                  # confidence < 0.6, waiting for user
└── adversarial-review.md         # /codex:adversarial-review --effort xhigh output
```

## Cross-round aggregation

After every round, `scripts/tearsheet.sh` folds round-N artifacts into:

- `~/Desktop/recursive-batch-eval-<run_id>/tearsheet.html` — live view, all rounds
- `~/Desktop/recursive-batch-eval-<run_id>/ideation/cumulative.md` — merged ideation across rounds
- `~/Desktop/recursive-batch-eval-<run_id>/patches/timeline.md` — patch chronology

## Naming rules

- Round numbers are zero-padded to 2 digits: `round-00`, `round-01`, ..., `round-99`.
- Run IDs: `YYYYMMDD-<slug>-<4-char-hash>` (same shape as batch runs elsewhere).
- Metric deltas recorded as raw float AND percentage vs. prior round AND percentage vs. best-ever.
