# Troubleshooting

Diagnose from the logs first — most failures state their cause:
`fetch_job_logs(job_id=...)` / `hf jobs logs <id>`, or open the job URL. Logs
can lag 30–60s after a job starts; check `inspect_job(...).status.stage` if none
appear.

## Out of memory (OOM)

```
RuntimeError: CUDA out of memory
```

- Reduce batch size (down to 1 if needed).
- Process data in chunks / stream instead of loading all at once.
- Use quantization (8-bit/4-bit) or LoRA for large models.
- Upgrade the flavor: `cpu → t4 → a10g → a100 → h200`, or go multi-GPU with tensor parallelism.

## Job timeout

Status shows `TIMEOUT`/killed with only partial output.

- Default is **30 minutes**; long jobs need an explicit `timeout`.
- Read logs for the real runtime, then set `timeout` to that plus a 20–30% buffer.
- Optimize or chunk the work; checkpoint so a re-run resumes.

## Missing dependencies

```
ModuleNotFoundError: No module named 'X'
```

- Add the package to the PEP 723 header:
  ```python
  # /// script
  # dependencies = ["package>=1.0.0"]
  # ///
  ```
- Or pass `dependencies=[...]` to `run_uv_job`.
- Check the package name/spelling; pin a version if a resolver conflict appears.
- For heavy stacks, use a pre-built `image=` instead of installing at runtime.

## Script not found

```
FileNotFoundError: script.py
```

- The **Python API / MCP wrapper** cannot see local paths — pass inline code or a URL.
- The **`hf jobs uv run` CLI** does upload local files, so paths work there.
- If using a URL, make sure it is publicly reachable (a raw Hub/GitHub URL).

## Hub push / auth failures

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` | Add `secrets={"HF_TOKEN": "$HF_TOKEN"}`; re-`hf auth login`; token expired |
| `403 Forbidden` | Use a **write** token; check scope; verify repo/org access |
| `404 Not Found` | Create the repo first, or fix the `username/name` namespace |
| Results missing after "success" | No persistence ran — add push/upload/bucket code and wrap it in try/except |

Verify inside the script: `assert "HF_TOKEN" in os.environ`. See
`references/auth-and-secrets.md`.

## GPU not available

```
CUDA not available / No GPU found
```

- You are on a CPU flavor — set a GPU `flavor` (e.g. `a10g-large`).
- The image lacks CUDA — use a CUDA-enabled image (e.g. `pytorch/pytorch:...-cuda...-devel`).

## Slow / underutilized

- Wrong flavor or a data-loading bottleneck — profile, increase batch size, or upgrade.
- Low GPU utilization often means CPU-bound preprocessing; overlap I/O with compute.

## Cost higher than expected

- Job ran to a long/absent `timeout`, or an over-provisioned flavor was used.
- Set a tight `timeout`, right-size the flavor, and check `hf jobs hardware` prices before launching.

## Debugging tactics

1. **Test locally first**: `uv run script.py` catches most errors before you pay for compute.
2. **Log the environment** at startup:
   ```python
   import os, torch
   print("CUDA:", torch.cuda.is_available(),
         "| HF_TOKEN set:", "HF_TOKEN" in os.environ,
         "| accelerator:", os.environ.get("ACCELERATOR"))
   ```
3. **Wrap the body** in try/except with `traceback.print_exc()` and re-raise, so failures land in the logs.
4. **Inspect programmatically**:
   ```python
   info = inspect_job(job_id=job.id)
   if info.status.stage == "ERROR":
       print(info.status.message)
       for line in fetch_job_logs(job_id=job.id): print(line)
   ```

## Error code quick reference

| Code | Meaning | First move |
|------|---------|-----------|
| 401 | Unauthorized | Add/refresh `HF_TOKEN` secret |
| 403 | Forbidden | Check token permissions/scope |
| 404 | Not found | Verify repo exists / namespace |
| 500 | Server error | Retry; check https://status.huggingface.co |

More help: [HF forums](https://discuss.huggingface.co),
[huggingface_hub issues](https://github.com/huggingface/huggingface_hub/issues).
