# Distributed Optimization Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `optuna` | Optuna | `deep-tool-wiki/optuna` | `deep-tool-wiki/optuna/wiki.md` | `neuro-link/02-KB-main/optuna/index.md` | existing-deep-missing-kb |
| `ray-distributed` | Ray | `deep-tool-wiki/ray-distributed` | `deep-tool-wiki/ray-distributed/wiki.md` | `neuro-link/02-KB-main/ray-distributed/index.md` | existing-deep-missing-kb |
| `dask-distributed` | Dask Distributed | `deep-tool-wiki/dask-distributed` | `deep-tool-wiki/dask-distributed/wiki.md` | `neuro-link/02-KB-main/dask-distributed/index.md` | existing-deep-missing-kb |
| `mlflow` | MLflow | `deep-tool-wiki/mlflow` | `deep-tool-wiki/mlflow/wiki.md` | `neuro-link/02-KB-main/mlflow/index.md` | existing-deep-missing-kb |
| `postgresql-optuna` | PostgreSQL Optuna | `deep-tool-wiki/postgresql-optuna` | `deep-tool-wiki/postgresql-optuna/wiki.md` | `neuro-link/02-KB-main/postgresql-optuna/index.md` | existing-deep-missing-kb |
| `gnu-parallel` | GNU Parallel | `deep-tool-wiki/gnu-parallel` | `deep-tool-wiki/gnu-parallel/wiki.md` | `neuro-link/02-KB-main/gnu-parallel/index.md` | existing-deep-missing-kb |

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Storage Backend Selection

Pick storage before picking worker count.

- `InMemoryStorage`: single-process smoke only.
- Local SQLite: small single-host proof where write contention is not the question; not for multi-worker concurrency.
- PostgreSQL/RDB: concurrent process or node fan-out, crash recovery, resumable studies.
- Connection pooling: required when worker count exceeds safe direct database connections.
- MLflow artifact store: keep separate from Optuna storage; do not overload the Optuna DB with large artifacts.
- GNU parallel joblogs: enable resume of failed rows without rerunning every job.

## Eval / Docker Personas

| Persona | Surface | Use before |
| --- | --- | --- |
| `single-trial-smoke` | one objective call, memory/temp-file only | every larger run |
| `postgres-optuna-local` | local PostgreSQL + two Optuna workers, same study | concurrency/resume proof |
| `ray-localcluster` | local Ray head, bounded CPU, tiny task/Tune smoke | any cloud or multi-node run |
| `dask-localcluster` | local Dask scheduler/client, small partitioned workload | graph/DataFrame risk |
| `mlflow-file-smoke` | local file store, one metric + one artifact | long HPO |
| `gnu-parallel-dryrun` | `--dry-run` matrix, then two-job `--joblog` run | full shell sweep |

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.

Sibling routes: walk-forward EPOCH selection -> `adaptive-wfo-epoch`; is-Sharpe-real / PBO / purged-CV -> `model-evaluation`; backtest-vs-Optuna-baseline comparison -> `strategy-verify`.
