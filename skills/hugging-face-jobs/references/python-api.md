# Python API and `hf jobs` CLI Reference

All functions live in `huggingface_hub` (Apache-2.0). Import them directly, e.g.
`from huggingface_hub import run_job`. Every launcher returns a `JobInfo` with
`.id`, `.url`, and `.status` (a `JobStatus` with `.stage` and `.message`).

## Interface cheat sheet

| Operation | CLI | Python API |
|-----------|-----|------------|
| Run Docker job | `hf jobs run <image> <cmd>` | `run_job(image, command)` |
| Run UV script | `hf jobs uv run script.py` | `run_uv_job("script.py")` |
| List jobs | `hf jobs ps` / `hf jobs ls` | `list_jobs(status=..., labels=...)` |
| Inspect one | `hf jobs inspect <id>` | `inspect_job(job_id=...)` |
| Logs | `hf jobs logs <id>` | `fetch_job_logs(job_id=...)` |
| Metrics | — | `fetch_job_metrics(job_id=...)` |
| Wait for terminal | `hf jobs wait <id>` | `wait_for_job(job_id=...)` |
| Cancel | `hf jobs cancel <id>` | `cancel_job(job_id=...)` |
| List hardware | `hf jobs hardware` | `list_jobs_hardware()` |
| SSH in | `hf jobs ssh <id>` | pass `ssh=True` to `run_job` |
| Schedule Docker | `hf jobs scheduled run ...` | `create_scheduled_job(...)` |
| Schedule UV | `hf jobs scheduled uv run ...` | `create_scheduled_uv_job(...)` |
| Labels | `hf jobs labels <id> --label k=v` | `update_job_labels(job_id, labels=...)` |

## `run_job` / `run_uv_job` parameters

Shared, commonly used keyword arguments:

- `flavor` — hardware string (see `hardware.md`); default `cpu-basic`.
- `timeout` — seconds (`7200`) or string (`"90m"`, `"2h"`, `"1d"`); default 30 min.
- `env` — dict of plain env vars (visible in logs).
- `secrets` — dict of encrypted secrets (use for `HF_TOKEN`).
- `namespace` — run under an org you have write access to.
- `image` — Docker image; for `run_uv_job` this overrides the default UV image.
- `volumes` — list of `Volume(...)` mounts (see `persistence.md`).
- `ssh=True` — expose an SSH endpoint on the container.
- `expose` — list of container ports to publish through the jobs proxy, e.g.
  `expose=[8000]`; reachable at `job.status.expose_urls` (needs a read token).
- `labels` — dict of key/value labels for filtering in `list_jobs`.

`run_uv_job`-specific:

- `script` — a local file path, a URL, or (via the API/MCP wrapper) inline code.
- `dependencies` — extra packages added on top of the PEP 723 header.
- `python` — Python version, e.g. `"3.11"`.
- `script_args` — list passed as CLI args to the script.

```python
from huggingface_hub import run_uv_job

job = run_uv_job(
    "sft.py",
    script_args=["--model_name_or_path", "Qwen/Qwen2-0.5B"],
    dependencies=["trl"],
    flavor="a10g-small",
    timeout="90m",
    secrets={"HF_TOKEN": "$HF_TOKEN"},
)
```

`run_uv_job` can also run an inline command:
`run_uv_job("python", script_args=["-c", "import lighteval"], dependencies=["lighteval"])`.

## Monitoring

```python
from huggingface_hub import (
    list_jobs, inspect_job, fetch_job_logs, fetch_job_metrics,
    wait_for_job, cancel_job,
)

# list_jobs returns a paginated iterator of JobInfo
for job in list_jobs(status=["RUNNING", "SCHEDULING"], labels={"env": "prod"}):
    print(job.id, job.status.stage)

info = inspect_job(job_id=job_id)          # JobInfo
for line in fetch_job_logs(job_id=job_id): # logs may lag 30-60s after start
    print(line)
for m in fetch_job_metrics(job_id=job_id): # cpu/mem/gpu/net usage dicts
    print(m)
cancel_job(job_id=job_id)
```

### Waiting for completion

`wait_for_job` blocks until a job reaches a terminal stage (`COMPLETED`,
`CANCELED`, `ERROR`, `DELETED`). It **always returns the final `JobInfo`** — a
failed job does not raise — so branch on `.status.stage`. Pass a list of IDs to
wait on a batch:

```python
from huggingface_hub import run_job, wait_for_job

jobs = [run_job(image=img, command=cmd) for img, cmd in workloads]
finished = wait_for_job(job_id=[j.id for j in jobs], timeout=3600)
```

CLI: `hf jobs wait <id>` exits 0 only if the job(s) succeeded, so
`hf jobs wait <id> && next-step` chains correctly. A non-detached
`hf jobs run` also exits non-zero on failure.

## Built-in container environment variables

Available inside every job:

| Variable | Meaning |
|----------|---------|
| `JOB_ID` | Unique job id — use it to name output repos uniquely |
| `ACCELERATOR` | Accelerator type (e.g. `a10g-small`); empty on CPU |
| `CPU_CORES` | CPU cores available |
| `MEMORY` | Memory available (e.g. `16Gi`) |

## Scheduled jobs

```python
from huggingface_hub import create_scheduled_job, create_scheduled_uv_job

create_scheduled_job(
    image="python:3.12",
    command=["python", "-c", "print('hourly')"],
    schedule="@hourly",          # or CRON, e.g. "0 9 * * 1"
)
create_scheduled_uv_job("my_script.py", schedule="@daily", flavor="a10g-small")
```

Schedules: `@annually`/`@yearly`, `@monthly`, `@weekly`, `@daily`, `@hourly`,
or any CRON expression. Scheduled launchers take the same params as
`run_job`/`run_uv_job`. Manage with `list_scheduled_jobs`,
`inspect_scheduled_job`, `suspend_scheduled_job`, `resume_scheduled_job`,
`trigger_scheduled_job` (run now without changing the schedule), and
`delete_scheduled_job`.

## Webhooks

```python
from huggingface_hub import create_webhook

create_webhook(
    job_id=job_id,
    watched=[{"type": "user", "name": "your-username"},
             {"type": "org", "name": "your-org"}],
    domains=["repo", "discussion"],
    secret="your-secret",
)
```

The triggered job receives the event JSON in the `WEBHOOK_PAYLOAD` env var:
`json.loads(os.environ.get("WEBHOOK_PAYLOAD", "{}"))`.

## SSH into a running job

Pass `ssh=True` to `run_job`/`run_uv_job`; the endpoint appears at
`job.status.ssh_url`. Connect with `hf jobs ssh <id>` (or
`ssh <id>@ssh.hf.jobs`). Requires write access to the job's namespace and an
SSH key registered at https://huggingface.co/settings/keys.

> API surface verified against the huggingface_hub Jobs guide
> (https://huggingface.co/docs/huggingface_hub/guides/jobs). Confirm exact
> keyword signatures against your installed version, as the Jobs API is still
> marked experimental.
