---
name: hugging-face-jobs
version: 0.1.0
description: >-
  Run arbitrary Python and Docker workloads on Hugging Face Jobs — managed cloud
  CPU / GPU / multi-GPU compute — through the huggingface_hub Python API
  (run_job, run_uv_job) or the `hf jobs` CLI. Covers UV inline-dependency
  scripts, flavor/hardware selection and cost, HF_TOKEN secrets, timeouts,
  volume/bucket mounts, scheduled and webhook-triggered jobs, monitoring, and
  Hub result persistence. Use when you need cloud GPUs without local setup:
  batch inference, synthetic-data generation, large dataset processing,
  reproducible experiments, or recurring jobs — and results must be persisted
  because the environment is ephemeral. Do NOT use for work that fits on your
  own machine, for interactive step-through debugging (use a Space/Sandbox),
  for authoring a full training recipe (see TRL jobs docs / a training skill),
  or as a scheduler for non-Hugging-Face infrastructure.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (huggingface_hub)"
---

# Hugging Face Jobs

## Overview

Hugging Face Jobs runs a command on managed HF infrastructure, defined by three
things: a **command** (e.g. a Python invocation), a **Docker image** (from
Docker Hub or an HF Space), and a **hardware flavor** (CPU, GPU, or multi-GPU).
Jobs are fire-and-forget and pay-as-you-go — you are billed per second of
runtime. Because the container is destroyed when the job ends, **nothing you
write to local disk survives** unless you push it to the Hub or a mounted
bucket.

Two canonical, portable interfaces exist, both from `huggingface_hub`:

- **`hf jobs` CLI** — `hf jobs run` (Docker-style) and `hf jobs uv run` (UV scripts).
- **Python API** — `run_job(...)` and `run_uv_job(...)`, plus monitoring and
  scheduling helpers.

Some agent harnesses also surface these as an `hf_jobs` MCP tool (e.g.
`hf_jobs("uv", {...})`) whose parameters mirror the options below. Prefer the
CLI or Python API as the ground truth; the MCP wrapper is a convenience layer.

## When to Use This Skill

Use this skill when the user wants to:

- Run GPU/CPU workloads **without** provisioning or configuring local hardware.
- Do batch inference over thousands of samples, or generate synthetic data with an LLM.
- Process or scan large Hub datasets (often streaming, no full download).
- Run reproducible ML experiments/benchmarks on consistent hardware.
- Persist model/dataset/artifact results to the Hugging Face Hub.
- Schedule recurring jobs (CRON) or trigger jobs from repo webhooks.

Jobs require a positive [credit balance](https://huggingface.co/settings/billing)
(Pro/Team/Enterprise) and a logged-in machine (`hf auth login`; verify with
`hf_whoami()` or `huggingface_hub.whoami()`).

## When NOT to Use This Skill

- The workload fits comfortably on the local machine — running it locally is cheaper and faster to iterate.
- You need an **interactive** REPL/shell to poke at code — use a Space or a Sandbox (built on Jobs), not a fire-and-forget Job.
- You are authoring a full fine-tuning/training recipe — that is a training-skill/TRL concern; this skill only *launches* the compute (see `references/workload-patterns.md`).
- You want to orchestrate jobs on non-HF infrastructure (AWS Batch, SLURM, your own cluster).

## Two Ways to Run a Job

### UV scripts (recommended for Python)

UV scripts declare their dependencies inline via a PEP 723 header, so they are
self-contained — no environment setup.

```python
from huggingface_hub import run_uv_job

script = '''
# /// script
# dependencies = ["transformers", "torch"]
# ///
from transformers import pipeline
clf = pipeline("sentiment-analysis")
print(clf("I love Hugging Face!"))
'''
job = run_uv_job(script, flavor="a10g-small", timeout="30m")
print(job.url, job.id)
```

CLI equivalent (local file paths and URLs both work):

```bash
hf jobs uv run my_script.py --flavor a10g-small --timeout 30m
hf jobs uv run --flavor a10g-large --image vllm/vllm-openai:latest gen.py
```

Default UV image is `ghcr.io/astral-sh/uv:python3.12-bookworm`. Override with
`--image` / `image=` for framework images (vLLM, PyTorch) to cut startup time.
Add extra deps with `dependencies=[...]`, pin Python with `python="3.11"`, and
pass CLI args to the script with `script_args=[...]`.

### Docker jobs

```python
from huggingface_hub import run_job

run_job(
    image="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
    command=["python", "-c", "import torch; print(torch.cuda.get_device_name())"],
    flavor="a10g-small",
    timeout="1h",
)
```

Use any Docker Hub image or an HF Space as an image
(`image="hf.co/spaces/lhoestq/duckdb"`). Run under an org with
`namespace="my-org"`.

### Passing the script correctly

There are two "script path" stories — this is a common failure:

- **Python API / MCP wrapper**: the `script` value must be **inline code** (a
  string) or a **URL**. A local path like `"./foo.py"` does not exist inside
  the remote container. Read the file first: `Path("foo.py").read_text()`.
- **`hf jobs uv run` CLI**: local file paths **do** work — the CLI uploads the
  script for you.

## Authentication and Secrets

Any Hub interaction (push, private repo, authenticated API) needs `HF_TOKEN`.
Always pass it as a **secret** (encrypted server-side), never as `env`
(visible in logs), and never hardcode it:

```python
run_uv_job(script, secrets={"HF_TOKEN": "$HF_TOKEN"})
```

`$HF_TOKEN` is a placeholder replaced with your logged-in token. In the script,
read it with `os.environ["HF_TOKEN"]` or let `huggingface_hub`/`datasets`
auto-detect it. Full guidance, token types, and 401/403 fixes:
`references/auth-and-secrets.md`.

## Hardware and Cost

Pick the smallest flavor that fits, test there, then scale up. Common choices:

| Workload | Flavor | Notes |
|----------|--------|-------|
| Data processing, testing | `cpu-basic`, `cpu-upgrade` | ~$0.01–0.03/hr |
| <7B model inference | `t4-small`, `l4x1`, `a10g-small` | 16–24 GB |
| 7–13B inference / batch | `a10g-large` | 24 GB |
| 13B+ / fastest single GPU | `a100-large` | 1× A100 80 GB |
| Multi-GPU / tensor-parallel | `a10g-largex4`, `l4x4`, `a100x4`, `h200x2` | large models |

Cost ≈ runtime × per-hour rate. Get the live, authoritative flavor list and
prices with `hf jobs hardware` or `list_jobs_hardware()`. Full table, memory
sizing, and budget guidance: `references/hardware.md`.

## Persisting Results (Ephemeral Environment)

**All local files are deleted when the job ends.** Persist explicitly:

- **Push to Hub**: `model.push_to_hub(...)`, `dataset.push_to_hub(...)`, or `HfApi().upload_file(...)` (needs `HF_TOKEN` secret).
- **Mount a bucket/volume**: `Volume(type="bucket", source="user/bucket", mount_path="/out")` gives fast mutable storage; `sync_job_volume(...)` uploads local data in, `sync_bucket(...)` pulls results back.
- **External store / API**: S3, GCS, or POST to your endpoint.

Details and examples: `references/persistence.md`.

## Timeouts

Default timeout is **30 minutes** — jobs are killed at the limit and unsaved
progress is lost. Set `timeout=` explicitly for anything longer. Accepts
seconds (`7200`) or a string (`"90m"`, `"2h"`, `"1.5h"`, `"1d"`). Add a
20–30% buffer for setup and upload.

## Monitoring

```python
from huggingface_hub import list_jobs, inspect_job, fetch_job_logs, wait_for_job, cancel_job

list_jobs(status="RUNNING")             # iterator of JobInfo
inspect_job(job_id=job.id).status.stage # COMPLETED | RUNNING | ERROR | ...
for line in fetch_job_logs(job_id=job.id): print(line)
wait_for_job(job_id=job.id)             # blocks until terminal; never raises
cancel_job(job_id=job.id)
```

CLI: `hf jobs ps`, `hf jobs logs <id>`, `hf jobs wait <id>`, `hf jobs cancel <id>`.
Jobs are asynchronous — do not poll in a tight loop; report the `job.url` and
check status when the user asks. Resource metrics (`fetch_job_metrics`), SSH
(`ssh=True`), labels, and built-in container env vars (`JOB_ID`,
`ACCELERATOR`, `CPU_CORES`, `MEMORY`): `references/python-api.md`.

## Scheduled and Webhook Jobs

`create_scheduled_job` / `create_scheduled_uv_job` accept `@hourly`, `@daily`,
etc. or a CRON expression (`"0 9 * * 1"`), plus the same params as `run_job`.
Manage with `list_scheduled_jobs`, `suspend_scheduled_job`,
`resume_scheduled_job`, `trigger_scheduled_job`, `delete_scheduled_job`.
`create_webhook(...)` triggers a job on repo changes, exposing the event as
`WEBHOOK_PAYLOAD`. Full API: `references/python-api.md`.

## Common Failure Modes

- **OOM** → reduce batch size, chunk the data, or upgrade flavor (cpu → t4 → a10g → a100).
- **Timeout** → check logs for real runtime, raise `timeout` with buffer.
- **401/403 on Hub** → missing/insufficient `HF_TOKEN` secret; verify permissions.
- **Results missing after success** → no persistence code ran; push or mount a bucket.
- **`ModuleNotFoundError`** → add the package to the PEP 723 header or `dependencies`.
- **Script not found** → passed a local path to the Python API; use inline code or a URL.

Full diagnostics: `references/troubleshooting.md`.

## References

- `references/python-api.md` — complete Python API + `hf jobs` CLI reference (run, monitor, wait, metrics, SSH, labels, scheduled jobs, webhooks, env vars).
- `references/hardware.md` — current flavor table with per-hour cost, memory sizing, multi-GPU, and selection by model size/budget.
- `references/persistence.md` — Hub push, `upload_file`, volume/bucket mounts, and external storage.
- `references/auth-and-secrets.md` — token types, `secrets` vs `env`, verification, and 401/403 fixes.
- `references/workload-patterns.md` — batch inference (vLLM), synthetic-data generation, streaming dataset stats, and the community `uv-scripts` collection.
- `references/troubleshooting.md` — OOM, timeouts, dependency, push, GPU, and cost issues with fixes.

### External docs

- [HF Jobs guide](https://huggingface.co/docs/huggingface_hub/guides/jobs) · [Hub Jobs + pricing](https://huggingface.co/docs/hub/jobs) · [`hf jobs` CLI](https://huggingface.co/docs/huggingface_hub/guides/cli#hf-jobs) · [UV scripts (PEP 723)](https://docs.astral.sh/uv/guides/scripts/) · [uv-scripts org](https://huggingface.co/uv-scripts)
