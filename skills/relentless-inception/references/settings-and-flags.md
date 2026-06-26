# Settings and flags

This file documents every knob the skill exposes. Most users will never touch these — the defaults are tuned for "I won't be watching" runs.

---

## Model + effort defaults (per role)

These are the defaults applied when no flag overrides them. Each model name is the canonical 1M-context variant; the router resolves provider routing.

| Role                      | Model              | Effort      | Notes                                       |
|---------------------------|--------------------|-------------|---------------------------------------------|
| planner                   | opus-latest        | xhigh       | always xhigh, no degradation                |
| architecture-analyzer     | gpt-pro-latest     | xhigh       | via openrouter                              |
| orchestrator              | opus-latest        | xhigh       | never below xhigh                           |
| dev-worker                | opus-latest        | xhigh       | overridable to high for cost                |
| adversarial-review        | gpt-5.5            | high        | xhigh in rescue mode                        |
| nexus-graph-writer        | opus-4.7           | high        | one-per-graph-write                         |
| nexus-graph-synthesizer   | gpt-latest         | xhigh       | one-per-merge-batch                         |
| uv-dagger-deploy          | opus-latest        | high        |                                             |
| uv-package                | opus-latest        | high        |                                             |
| uv-workspaces             | opus-latest        | high        |                                             |
| test-harness-designer     | gpt-5.5            | xhigh       | always xhigh                                |
| temporal-tester           | opus-4.7           | high        |                                             |
| test-evaluator            | opus-4.7           | xhigh       | always xhigh                                |
| background-agent          | codex-latest       | medium      | watchdog mode, doesn't write code           |
| rescue-agent              | gpt-latest         | xhigh       | forced xhigh; no degradation                |

## Fallback policy

When the router can't satisfy a request:

1. Retry once with a 30-second backoff.
2. If still failing, try the named fallback (e.g., gpt-5.5 → gpt-latest; opus-latest → opus-4.7).
3. If the fallback fails, **pause the run** with a clear error. **Never silently degrade to a smaller model.**

The exception: `--allow-degradation` flag turns step 3 into "drop one effort level and continue." Use deliberately; surfaced as a warning at every gate.

---

## Entrypoint flags

```
/relentless-inception "<task>" \
  --plan=staff-up|kitchen-sink-monorepo|lawyer-up \
  --exec=gigaprompt|proof-loops|skynet|exaflop-infiniloop \
  --intensity=1|2|3 \
  --orchestrator-review-style=code-function-nexus|adversarial-review|simulate-users-harness \
  --subagent-review-style=verify-proof|adversarial-pass-fail \
  --budget-soft-hours=N \
  --budget-hard-usd=N \
  --allow-degradation \
  --resume=<run_id>
```

Defaults:

- `--plan=staff-up`
- `--exec=proof-loops`
- `--intensity=3`
- `--orchestrator-review-style=adversarial-review`
- `--subagent-review-style=verify-proof`
- `--budget-soft-hours=40`
- `--budget-hard-usd=50`
- `--allow-degradation` off

## Budget caps

| Cap                    | Default | What happens when hit                              |
|------------------------|---------|----------------------------------------------------|
| `--budget-soft-hours`  | 40 h    | Run pauses for user review                          |
| `--budget-hard-usd`    | $50     | Run pauses; no further router calls until raised    |
| Per-unit retries       | 3       | Escalate to rescue                                  |
| Per-gate iterations    | 3       | Escalate to rescue                                  |
| Per-run rescue cycles  | 3       | Pause for human intervention                        |

The kill switch — `~/.claude/relentless-inception/KILL` — bypasses none of these; it's an *additional* stop.

---

## Environment

The skill reads these env vars (or `~/.claude/.env` as a fallback):

- `OPENROUTER_API_KEY` — required for gpt-5.5, gemini-latest, gpt-pro-latest routes
- `ANTHROPIC_API_KEY` — required for opus-* routes if you're not in Claude Code already (Claude Code provides routing in-process)
- `CODEX_HOME` — defaults to `~/.codex`
- `RELENTLESS_INCEPTION_HOME` — defaults to `~/.claude/relentless-inception`; the runs/rescues/logs root
- `STALL_MINUTES` — default 12; watchdog threshold

---

## Run state directories

```
~/.claude/relentless-inception/
├── runs/
│   └── <run_id>/
│       ├── plan.md
│       ├── manifest.json
│       ├── cycle-<N>/
│       │   ├── tearsheet.html
│       │   ├── tool-calls.jsonl
│       │   ├── reasoning-traces/
│       │   ├── adversarial-verdicts/
│       │   └── ship-report.json
│       └── rescues/
│           └── <cycle>/
│               ├── diagnosis.md
│               ├── {lead,copilot}-proposal.md
│               └── approved.md
├── lateral-pass/
│   ├── pending-relentless.md
│   └── archive/
├── triggers/
│   └── rescue-<run_id>-<timestamp>.json
└── KILL                       <-- create this to stop all running orchestrators
```
