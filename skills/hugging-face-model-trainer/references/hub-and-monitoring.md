# Hub Persistence and Trackio Monitoring

The two things that make an ephemeral-runner job worthwhile: the model ends up
on the Hub, and you can watch it train.

## Why Hub push is mandatory

The Jobs runner is temporary — its disk is wiped when the job ends, with no local
persistence and no way to retrieve files afterward. **A model that is not pushed
to the Hub during the job is permanently lost.** This is the single most
important configuration in the whole workflow.

## The three required pieces

1. **In the config** — enable push and name the target repo:

   ```python
   SFTConfig(
       push_to_hub=True,
       hub_model_id="username/model-name",   # MUST include a namespace
       hub_strategy="every_save",             # optional: push each checkpoint
   )
   ```

2. **In the script** — call the final push (belt and suspenders):

   ```python
   trainer.train()
   trainer.push_to_hub()
   ```

3. **On the job** — supply the write token so the runner can authenticate:

   ```bash
   hf jobs uv run ... --secrets HF_TOKEN "https://.../train.py"
   ```

   With an `hf_jobs` MCP wrapper the equivalent is
   `"secrets": {"HF_TOKEN": "$HF_TOKEN"}` — the `$HF_TOKEN` placeholder is
   substituted with your actual token at submission. Prefer `secrets` over a
   plain `env` value so the token isn't exposed in job metadata.

**Pre-submit checklist:** `push_to_hub=True` ✔ · `hub_model_id` has
`namespace/name` ✔ · token secret attached ✔ · you have **write** access to that
namespace ✔.

## What gets saved

With `push_to_hub=True`: final weights, tokenizer, `config.json`, the training
arguments, and an auto-generated model card. With checkpointing enabled, the
intermediate checkpoints land in the **same repo**.

## Checkpointing (resume + safety)

Long runs should checkpoint so a timeout or crash doesn't cost everything:

```python
SFTConfig(
    save_strategy="steps",
    save_steps=100,
    save_total_limit=3,          # keep only the last 3
    hub_strategy="every_save",   # push each checkpoint to the Hub
)
```

Resume by pointing the trainer at a pushed checkpoint:

```python
trainer.train(resume_from_checkpoint="username/model-name/checkpoint-1000")
```

## Auth failures at push time

| Error | Cause | Fix |
|-------|-------|-----|
| **401 Unauthorized** | token missing/invalid | attach the `HF_TOKEN` secret; `hf auth whoami`; re-login |
| **403 Forbidden** | no write access to the namespace | check `hub_model_id` matches your user, or that you're an org member with write; ensure the token has **write** scope |
| **Repository not found** | auto-create failed / bad name | pre-create with `HfApi().create_repo(...)`; use lowercase `namespace/name`, no spaces |
| **Push fails mid/after training** | network/Hub hiccup | checkpoints may still be saved; re-push manually before the job's files are gone |

Valid repo IDs look like `username/my-model` or `org/my-model`; invalid:
`my-model` (no namespace), `username/my model` (space), `username/MODEL`
(uppercase discouraged).

## Trackio (real-time metrics)

Trackio streams metrics from the cloud runner to a Hugging Face **Space** so you
can watch loss, learning rate, GPU utilization, memory, and throughput live —
and the Space persists them after the job ends. Without a Space, metrics vanish
with the runner.

**Wire-up (four steps):**

```python
# 1. dependency
# /// script
# dependencies = ["trl>=0.12.0", "trackio"]
# ///

import trackio

# 2. init with a space_id — Trackio auto-creates the Space if missing
trackio.init(
    project="my-sft",
    space_id="username/trackio",     # default convention: {username}/trackio
    config={                          # keep minimal — hyperparams + model/dataset only
        "model": "Qwen/Qwen2.5-0.5B",
        "dataset": "trl-lib/Capybara",
        "learning_rate": 2e-5,
    },
)

# 3. tell TRL to report to Trackio (via the config)
#    SFTConfig(report_to="trackio", run_name="baseline-run")

# 4. flush at the end
trainer.train()
trackio.finish()                      # final sync
```

`HF_TOKEN` (the same job secret) authorizes Space creation and metric writes.
Metrics buffer to a local SQLite DB and sync to a Hub dataset roughly every
5 minutes, with a final sync on `trackio.finish()`. View at
`https://huggingface.co/spaces/username/trackio`.

**Grouping runs** (optional) for sweeps/experiments — pass a `group` so related
runs cluster in the dashboard:

```python
trackio.init(project="lr-sweep", run_name="lr-1e-4", group="lr_1e-4")
trackio.init(project="lr-sweep", run_name="lr-3e-4", group="lr_3e-4")
```

Use sensible defaults (`{username}/trackio` Space, a recognizable `run_name`,
minimal config) unless the user asks for a specific setup. Trackio is best for
solo real-time monitoring; Weights & Biases is the alternative for team
collaboration (`report_to="wandb"`, requires an account).

## See also

- [jobs-and-hardware.md](jobs-and-hardware.md) — attaching secrets, submitting
- [training-methods.md](training-methods.md) — templates that already wire these in
- [troubleshooting.md](troubleshooting.md) — "model not on Hub" diagnosis
