# Failure patterns — fingerprints and remediation mappings

Pass 3 (failure logs) and Pass 6 (upstream doc drift) of `/neuro-scan` recognize
recurring failures and route each to the right remediation task type. This
reference lists the common fingerprints and the task they map to. A fingerprint
is `command + exit code + first line of stderr`; the same fingerprint seen more
than once in 24h is reported as a recurring failure with a count
(see `scripts/scan_failures.sh`).

## Hook failures (`state/hooks/*.log`)

| Fingerprint                                   | Likely cause                          | Task type | Priority |
| --------------------------------------------- | ------------------------------------- | --------- | -------- |
| non-zero `exit_code` on a PostToolUse hook    | hook script bug or missing dependency | `repair`  | 1        |
| `command not found`                           | tool not installed on this harness    | `repair`  | 1        |
| hook timeout                                  | slow external call / network          | `repair`  | 2        |

## LLM failures (`state/llm_logs/<token>/<date>.jsonl`)

| Fingerprint                          | Likely cause                  | Task type | Priority |
| ------------------------------------ | ----------------------------- | --------- | -------- |
| `"error"` with HTTP 429              | rate limit                    | `repair`  | 2        |
| `"error"` with HTTP 5xx              | provider outage / transient   | `repair`  | 3        |
| `"error"` with auth/401              | bad or expired API key        | `repair`  | 1        |
| repeated empty/`null` completions    | prompt or model-id regression | `repair`  | 2        |

## Cron failures (`state/cron/*.log`)

| Fingerprint                  | Likely cause                     | Task type | Priority |
| ---------------------------- | -------------------------------- | --------- | -------- |
| `ERROR`/`FAIL` in cron job   | scheduled job broke              | `repair`  | 2        |
| job never ran (no log)       | cron entry missing/disabled      | `repair`  | 2        |

## Harness-to-harness comms

`06-Recursive/harness-to-harness-comms/*.json` with `status: failed` means one
harness handed work to another and the handoff did not complete. Report the
message id and both endpoints. Task type `repair`, priority 1 — a dropped
handoff stalls the whole pipeline.

## Upstream doc drift (Pass 6)

Not a failure per se, but a freshness gap. For each repo in
`08-code-docs/toolbox/` and `08-code-docs/forked-up/`, compare upstream's latest
release date to `last_synced`.

| Condition                                  | Task type | Routed to                          |
| ------------------------------------------ | --------- | ---------------------------------- |
| upstream released after `last_synced`      | `curate`  | `/adjacent-tools-code-docs`        |
| forked repo has upstream changes to pull   | `curate`  | `/forked-repos-with-changes`       |

## Routing note

`/neuro-scan` only *queues* these tasks — it never fixes them. Repair execution
goes to `/neuro-surgery` (HITL) or `/hyper-sleep` (non-HITL). Always set
`source: neuro-scan` and `scan_date` on the queued task so the failure is
traceable back to the scan that found it, and de-dupe against existing pending
repair tasks with the same fingerprint.
