---
name: hugging-face-trackio
version: 0.1.0
description: >-
  Trackio is Hugging Face's lightweight, free, local-first experiment tracker
  with a drop-in wandb-compatible API (init/log/finish) that stores runs in a
  local SQLite database and can sync to a Hugging Face Space for a shareable,
  real-time dashboard. Use when instrumenting ML training to log scalar metrics,
  media, and hyperparameters from Python, wiring automatic logging through
  TRL/Transformers `report_to="trackio"`, persisting metrics from cloud or
  remote-GPU jobs to a Space so they survive instance teardown, or querying
  logged projects/runs/metrics programmatically through the dashboard's HTTP
  `/api/*` endpoints or MCP server mode for automation and agent workflows. Not
  a full MLOps platform — for governed model registries with lineage, dataset
  and large-file versioning, managed sweep orchestration, or org-wide RBAC team
  dashboards use Weights & Biases or MLflow; for the training loop itself use
  `pytorch-lightning` or `transformers`.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Apache-2.0
---

# Hugging Face Trackio

## Overview

Trackio ([`gradio-app/trackio`](https://github.com/gradio-app/trackio),
[docs](https://huggingface.co/docs/trackio/index)) is a small experiment-tracking
library from Hugging Face. It exposes a **wandb-compatible** surface so existing
`wandb.init/log/finish` code runs unchanged, but it is **local-first**: metrics
land in a local SQLite database and the dashboard is a Gradio app you launch on
demand. Passing a `space_id` mirrors runs to a Hugging Face Space, giving a
persistent, shareable dashboard that outlives an ephemeral training instance.

Two interfaces, two directions of data flow:

| Direction | Interface | Reference |
|-----------|-----------|-----------|
| **Write** metrics during training | Python API (`import trackio`) | [references/logging-metrics.md](references/logging-metrics.md) |
| **Read** metrics after/during training | Dashboard HTTP `/api/*` endpoints + MCP server (`trackio show`) | [references/retrieving-metrics.md](references/retrieving-metrics.md) |

Install it with `pip install trackio` (or `uv pip install trackio`).

## When to Use This Skill

- You are instrumenting a training script and want to log loss, accuracy,
  learning rate, or any scalar metric plus a config of hyperparameters.
- You want zero-config, free tracking with no account or server to stand up.
- You have wandb code and want a drop-in local replacement (`import trackio as wandb`).
- You are training on a **remote/cloud GPU or HF Jobs** and need metrics to
  survive instance teardown — sync to a Space with `space_id`.
- You use a TRL or Transformers `Trainer` and want automatic logging via
  `report_to="trackio"`.
- You (or an agent) need to **read back** logged runs and metric series
  programmatically — via the dashboard's HTTP `/api/*` JSON endpoints or its MCP
  server — for scripting and agent workflows.

## When NOT to Use This Skill

- You need a **governed model registry with lineage, dataset or large-file
  versioning, or team collaboration UI** — use Weights & Biases or MLflow.
  (Trackio does log basic versioned artifacts via `log_artifact`/`use_artifact`,
  but it is not a full registry.)
- You need **managed hyperparameter-sweep orchestration** or org-wide team
  dashboards with RBAC — Trackio tracks runs but does not schedule sweeps.
- You are writing the **training loop itself** — use `pytorch-lightning` or
  `transformers`; Trackio only records the numbers those loops produce.
- You want a general-purpose metrics/observability backend for a running service
  (Prometheus/OpenTelemetry territory), not ML experiment runs.

## Core Mental Model

A **project** groups related **runs**; each run is a time series of logged
**metrics** keyed by step, plus a static `config`. You:

1. `init` a run (name it, attach a config, optionally give a `space_id`).
2. `log` metric dicts repeatedly through training.
3. `finish` to flush and close the run.

Read it back later through the dashboard's HTTP `/api/*` endpoints, or just view
it in the dashboard (`trackio show`) — there is no `list`/`get` query subcommand.

## Logging (Python API)

Minimal loop:

```python
import trackio

trackio.init(project="my-project", config={"learning_rate": 2e-5, "epochs": 3})
for epoch in range(3):
    trackio.log({"loss": train_epoch(), "epoch": epoch})
trackio.finish()
```

Remote-safe: pass `space_id` so metrics persist to a Space dashboard (the Space
is auto-created if missing). **Always do this for cloud/HF Jobs training** —
local SQLite is lost when the instance dies.

```python
trackio.init(project="sft-training", space_id="username/trackio",
             config={"model": "Qwen/Qwen2.5-0.5B"})
```

For TRL/Transformers, set `report_to="trackio"` on the trainer config and
logging is automatic. See **[references/logging-metrics.md](references/logging-metrics.md)**
for the full `init()` parameter list, wandb-compatibility, TRL integration,
run grouping, `trackio.sync()`, and embedding Space dashboards in a web page.

## Retrieving (Dashboard API)

Trackio has **no** `trackio list`/`trackio get` query subcommands. To read data
back, launch the dashboard — it serves each read tool as a `POST /api/{tool}`
HTTP endpoint returning `{"data": ...}`:

```bash
trackio show                      # serves http://127.0.0.1:7860 (+ /api/*)
BASE=http://127.0.0.1:7860
curl -s -X POST $BASE/api/get_all_projects -d '{}' -H "Content-Type: application/json"
curl -s -X POST $BASE/api/get_runs_for_project -H "Content-Type: application/json" \
  -d '{"project": "my-project"}'
curl -s -X POST $BASE/api/get_metric_values -H "Content-Type: application/json" \
  -d '{"project": "my-project", "run": "my-run", "metric_name": "loss"}'
```

For LLM-agent access, enable MCP mode: `pip install "trackio[mcp]"` then
`trackio show --mcp-server` (endpoint `http://127.0.0.1:7860/mcp/`). Push a local
project to a Space with `trackio sync` or `trackio.sync(project=..., space_id=...)`.

See **[references/retrieving-metrics.md](references/retrieving-metrics.md)** for
the full endpoint table, `httpx`/curl/`jq` patterns, system-metric queries,
write-gated mutation tools (`delete_run`, `rename_run`, `force_sync`), and MCP
client configuration.

## Failure Modes and Boundaries

- **Metrics vanished after a cloud run** — you did not pass `space_id`; local
  SQLite on the terminated instance is gone. Sync eagerly during remote training.
- **A run is missing from the dashboard/API** — the API reads the store the
  running server points at. A local `trackio show` reads the **local** SQLite
  database, so a run that lives only on a Space is invisible until you query that
  Space's own URL (`https://<space>.hf.space/api/…`) or sync it down first.
  Project/run names are case-sensitive.
- **wandb drop-in gaps** — the scalar `init/log/finish` path is compatible, but
  do not assume every advanced wandb feature (rich media, sweeps, artifacts) maps
  over; verify against the [Trackio docs](https://huggingface.co/docs/trackio/index).
- **Space auth** — syncing needs Hugging Face Hub credentials
  (`huggingface-hub`, e.g. `huggingface-cli login` or `HF_TOKEN`).
