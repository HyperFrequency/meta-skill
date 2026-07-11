# Common Workload Patterns

Reusable shapes for the jobs people actually run. Before writing a script from
scratch, check the community
[`uv-scripts` organization](https://huggingface.co/uv-scripts) on the Hub — it
hosts ready-to-run UV scripts for OCR, classification, synthetic data, vLLM
generation, and dataset creation. You can run one directly from its URL:

```python
run_uv_job("https://huggingface.co/datasets/uv-scripts/<collection>/resolve/main/run.py",
           flavor="a10g-large", secrets={"HF_TOKEN": "$HF_TOKEN"})
```

Discover collections with the Hub search MCP tools (e.g. `hub_repo_search` for
author `uv-scripts`) or on the website.

## Pattern 1 — Batch inference / generation with vLLM

Load a Hub dataset (a `messages` chat column or a `prompt` column), apply the
model chat template, generate with vLLM, and push the results back as a new
dataset. Needs a GPU and a **write** token.

- Use a pre-built image to skip dependency install: `image="vllm/vllm-openai:latest"`.
- Size the flavor to the model (`references/hardware.md`); use a multi-GPU flavor with tensor parallelism for large models.
- Set a generous `timeout` (generation over many rows is slow) and push incrementally or at the end.

```python
run_uv_job(
    "generate.py",                       # your vLLM generation script (or a uv-scripts URL)
    script_args=[
        "username/input-dataset", "username/output-dataset",
        "--model-id", "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "--max-tokens", "2048",
    ],
    image="vllm/vllm-openai:latest",
    flavor="a10g-large",
    timeout="4h",
    secrets={"HF_TOKEN": "$HF_TOKEN"},
)
```

## Pattern 2 — Synthetic data generation

Generate prompts/answers with an LLM (e.g. chain-of-thought self-instruct),
optionally filter for answer consistency, then push the dataset + a dataset card
to the Hub. GPU + write token. This is the same launch shape as Pattern 1 with a
generation-and-filter script; scale the flavor and `timeout` to the sample
count (tens of thousands of samples can run for hours — checkpoint if possible).

## Pattern 3 — Streaming dataset statistics (CPU, no full download)

Scan large parquet datasets directly from the Hub with a streaming engine
(e.g. Polars `scan_parquet` over `hf://` paths) so you never download the full
corpus. CPU flavors are usually enough; a token is only needed if you upload
results.

```python
run_uv_job(
    "stats.py",
    script_args=["--limit", "10000", "--output-repo", "username/dataset-stats"],
    flavor="cpu-upgrade",
    timeout="2h",
    env={"HF_XET_HIGH_PERFORMANCE": "1"},   # faster Hub streaming reads
    secrets={"HF_TOKEN": "$HF_TOKEN"},      # only if uploading
)
```

## Pattern 4 — Fan-out / parallel sweeps

Launch many jobs (e.g. one per hyperparameter) and wait on the batch. Mount a
shared read-only input volume once so every job reuses the same uploaded data.

```python
from huggingface_hub import run_uv_job, wait_for_job, sync_job_volume

data = sync_job_volume("./training-data", "/data")
jobs = [run_uv_job("train.py", script_args=["--lr", str(lr)], volumes=[data],
                   flavor="a10g-small", secrets={"HF_TOKEN": "$HF_TOKEN"})
        for lr in (0.01, 0.03, 0.05)]
finished = wait_for_job(job_id=[j.id for j in jobs], timeout=7200)
for j in finished:
    print(j.id, j.status.stage)
```

## Pattern 5 — Recurring / event-driven jobs

Use `create_scheduled_uv_job(script, schedule="@daily")` for CRON-style
recurrence, or `create_webhook(...)` to trigger a job when a watched repo
changes (payload delivered in `WEBHOOK_PAYLOAD`). Details in
`references/python-api.md`.

## Note on model training

This skill *launches* compute; it is not a training-recipe authoring guide. For
fine-tuning, point the job at a TRL training script (e.g. `trl/scripts/sft.py`
via `run_uv_job` with `dependencies=["trl"]`) and follow the
[TRL Jobs Training docs](https://huggingface.co/docs/trl/main/en/jobs_training)
for recipes, hardware, and hyperparameters.
