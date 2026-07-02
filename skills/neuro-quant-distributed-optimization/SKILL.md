---
name: neuro-quant-distributed-optimization
version: 0.1.0
description: >
  Distributed HPO and sweep infrastructure for the neuro-quant monorepo:
  Optuna, Ray, Dask, MLflow, PostgreSQL-backed Optuna, and GNU parallel.
  Routes a tuning or fan-out request to the right scheduler, study storage,
  and tracking surface, then proves the run can persist and resume. Use when
  the user asks for "scalable HPO", "distributed optuna", "ray/dask cluster",
  "study storage", "make the study resumable", "fan out a sweep", "parallelize
  this backtest", "track this with MLflow", or "launch a GNU parallel sweep".
  For walk-forward EPOCH selection use adaptive-wfo-epoch; for is-the-Sharpe-real,
  PBO, or purged-CV use model-evaluation; for comparing a backtest to an Optuna
  baseline use strategy-verify. NOT for single-trial local optimization or backtest
  statistical analysis.
allowed-tools: Read, Grep, Glob, Bash
---

# Distributed Optimization

## Scope

Coordinate Optuna, Ray, Dask, MLflow, PostgreSQL storage, and local fan-out for
long sweeps. The default path is one deterministic trial, one persisted study,
then parallel scale.

This family owns these tools:

- `optuna`: samplers, pruners, objective functions, study lifecycle, dashboard handoff.
- `postgresql-optuna`: PostgreSQL/RDB storage for concurrent and resumable studies.
- `ray`: Ray Core and Ray Tune style execution for Python-native task and trial fan-out.
- `dask`: Dask Distributed for DataFrame/array workloads and task graphs.
- `mlflow`: experiment tracking, parameters, metrics, artifacts, and run provenance.
- `gnu-parallel`: shell-level batch fan-out for independent commands and fixture sweeps.

Use this skill when the task matches one of these signals:
- long Optuna workflow
- distributed backtest sweep
- Ray or Dask optimization
- MLflow experiment tracking
- PostgreSQL Optuna storage
- GNU parallel batch

## Trigger Phrases

Use this skill for requests like:

- "run Optuna across workers"
- "use PostgreSQL for Optuna"
- "make the study resumable"
- "parallelize this backtest"
- "Ray Tune or Dask"
- "track this with MLflow"
- "launch a GNU parallel sweep"
- "optuna dashboard"
- "distributed HPO proof"

Ask one clarifying question if the request does not say whether the workload is
a Python objective, a shell command, a DataFrame graph, or a long-running
external backtest.

## Boundary

- For walk-forward EPOCH selection, use `adaptive-wfo-epoch`.
- For is-the-Sharpe-real, PBO, or purged-CV questions, use `model-evaluation`.
- For comparing a backtest to an Optuna baseline, use `strategy-verify`.

## Required Workflow

1. Restate the goal, target repo/tool, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Open `references/verification-checklist.md` for the smallest relevant proof path.
4. Use `references/handoff-template.md` when a long workflow should move to another family skill.
5. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or `neuro-link/02-KB-main/<tool>/index.md`.
6. Separate verified facts, assumptions, missing resources, and blocked checks in the final answer.

## Operating Rules

- Never scale an objective before a single deterministic trial passes.
- Pick storage before picking worker count. In-memory storage is for single-process smoke only.
- Use PostgreSQL or another RDB backend for real multi-process or multi-node Optuna. Treat SQLite as a local smoke path, not production concurrency.
- Keep secrets and database URLs out of committed files. Use env vars or local runtime config.
- MLflow is tracking, not scheduling. Ray, Dask, Optuna workers, or GNU parallel still need their own execution plan.
- Before giving current API signatures or code examples, use the docs-dual-lookup path (Context7 plus Auggie) so signatures match the local fork.

## Tool Routing

| Workload | Primary route | Why | Verification |
| --- | --- | --- | --- |
| Single-machine adaptive HPO | `optuna` | Fastest path from objective to best trial | Deterministic objective smoke and persisted study |
| Multi-process or multi-node HPO | `postgresql-optuna` plus `optuna` | Shared trial state, crash recovery, concurrent workers | Two workers complete trials in the same study |
| Python task fan-out or cluster burst | `ray` | Dynamic scheduling, actors, object store, Ray Tune integration | `ray.init`, resource view, bounded remote task smoke |
| DataFrame/array graph compute | `dask` | Native graph execution for partitioned data workloads | scheduler/client starts, tasks complete, graph size sane |
| Run provenance and artifacts | `mlflow` | Params, metrics, artifacts, run IDs | run appears with metric and artifact |
| Shell command matrix | `gnu-parallel` | Lowest overhead for independent CLI sweeps | dry run, exit codes, joblog, output paths |

## Progressive Disclosure Resource Map

| Level | Load only this much | Use when | Stop when |
| --- | --- | --- | --- |
| 0 | User request, `git status --short`, objective type, target metric | Every task | Intent, write boundary, and workload shape are clear |
| 1 | `toolbox/docs/tools/optuna-family.md` and local venv requirements | Choosing the optimization stack | Local install expectations are known |
| 2 | `deep-tool-wiki/optuna/wiki.md`, `ray-distributed`, `dask-distributed`, `mlflow`, `gnu-parallel`, `postgresql-optuna` | Explaining known local patterns | Existing wiki coverage answers the task |
| 3 | Current objective code, caller scripts, compose files, Ray configs, MLflow paths | Runtime changes or proof | Objective entry point and side effects are understood |
| 4 | Fresh smoke command output and study/tracking artifacts | Verification | One persisted run can be resumed or inspected |
| 5 | Context7 plus Auggie, then upstream docs | Local coverage is stale, ambiguous, or missing | Source gap is captured for deep-tool-wiki |

This skill keeps local resources in its own folder for immediate operation, but
the full documentation belongs in deep-tool-wiki and the navigable leaf docs
belong in 02-KB-main. Do not duplicate long API docs here. If a full doc is
missing, use the generated stub path from the resource map and mark the lookup
incomplete.

## Verification Gates

1. Objective gate: one trial or command runs locally with fixed seed and returns the target metric.
2. Persistence gate: study or run metadata is saved outside process memory and can be reopened.
3. Concurrency gate: two workers can execute without duplicate trial ownership or corrupt artifacts.
4. Resume gate: an interrupted run can continue from the same study, run directory, or joblog.
5. Tracking gate: MLflow or the selected artifact store contains params, metrics, and key output files.
6. Scale gate: CPU, memory, object-store, database connection, and disk-spill limits are named before increasing worker count.
7. Cleanup gate: local clusters, H2O/Ray/Dask processes, Docker containers, and temp DBs are stopped or explicitly left running.

## Storage Decision Points

- Use `InMemoryStorage` only for a single-process smoke.
- Use local SQLite only for a small single-host proof where write contention is not the question.
- Use PostgreSQL for concurrent process or node fan-out.
- Use connection pooling when worker count exceeds safe direct database connections.
- Use MLflow artifact storage separately from Optuna storage; do not overload the Optuna DB with large artifacts.
- Use GNU parallel joblogs for shell sweeps so failed rows can be resumed without rerunning all jobs.

## Local Docker and Eval Personas

- `single-trial-smoke`: one objective call, no cluster, no database beyond memory or temp file. Required before every larger run.
- `postgres-optuna-local`: local Docker or local service PostgreSQL plus two Optuna workers against the same study. Use for concurrency and resume proof.
- `ray-localcluster`: local Ray head with bounded CPU count and a tiny remote-task or Tune smoke. Use before any cloud or multi-node run.
- `dask-localcluster`: local Dask scheduler/client with a small partitioned workload. Use when graph scheduling or DataFrame behavior is the risk.
- `mlflow-file-smoke`: local file store or local tracking server with one metric and one artifact. Use before long HPO.
- `gnu-parallel-dryrun`: command matrix rendered with `--dry-run`, then a tiny two-job run with `--joblog`.

## Common Failure Modes

- SQLite locking or slow writes when multiple Optuna workers share one file.
- Orphaned running trials after worker death when heartbeat or cleanup behavior is not configured.
- Ray object store spills because large market data was copied per trial instead of shared.
- Dask graph explosion when every trial is materialized up front.
- MLflow artifacts missing because each worker writes relative paths from different working directories.
- GNU parallel hides partial failure unless joblogs and exit handling are checked.
- PostgreSQL max connection exhaustion when every worker opens a direct connection.

## Covered Tools

| Tool | Source | Full docs | KB lookup |
| --- | --- | --- | --- |
| Optuna | `deep-tool-wiki/optuna` | `deep-tool-wiki/optuna/wiki.md` | `neuro-link/02-KB-main/optuna/index.md` |
| Ray | `deep-tool-wiki/ray-distributed` | `deep-tool-wiki/ray-distributed/wiki.md` | `neuro-link/02-KB-main/ray-distributed/index.md` |
| Dask Distributed | `deep-tool-wiki/dask-distributed` | `deep-tool-wiki/dask-distributed/wiki.md` | `neuro-link/02-KB-main/dask-distributed/index.md` |
| MLflow | `deep-tool-wiki/mlflow` | `deep-tool-wiki/mlflow/wiki.md` | `neuro-link/02-KB-main/mlflow/index.md` |
| PostgreSQL Optuna | `deep-tool-wiki/postgresql-optuna` | `deep-tool-wiki/postgresql-optuna/wiki.md` | `neuro-link/02-KB-main/postgresql-optuna/index.md` |
| GNU Parallel | `deep-tool-wiki/gnu-parallel` | `deep-tool-wiki/gnu-parallel/wiki.md` | `neuro-link/02-KB-main/gnu-parallel/index.md` |

## Local Resources

- `references/resource-map.md`: relevant repos, local docs, deep-tool-wiki targets, and missing-doc status.
- `references/verification-checklist.md`: proof gates for this family.
- `references/handoff-template.md`: structured handoff for multi-step workflows.
- `evals/evals.json`: trigger, false-positive, and missing-resource cases.
- `agents/openai.yaml`: minimal UI metadata for skill discovery.

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Done Criteria

A distributed optimization task is done when the response names:

- The selected scheduler, storage backend, and tracking surface.
- The objective entry point and target metric.
- The verification gate reached and the exact evidence command or artifact.
- The worker count and resource limits used.
- Any deep-tool-wiki gap discovered during the work.

For draft-only work, list the proposed Markdown or JSON files and say no runtime
optimization state was changed.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and
the next verification step.
