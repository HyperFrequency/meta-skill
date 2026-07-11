# Submitting Jobs, Choosing Hardware, and Sizing Cost

How to get a training script onto Hugging Face Jobs, on the right GPU, with a
timeout that won't kill it. Jobs run **asynchronously** — submission returns
immediately and training continues for hours. Report the job ID + monitoring URL
and let the user ask for status; do not poll.

## Four ways to submit

**1. Inline uv script (most control).** The script declares its own dependencies
with a [PEP 723](https://docs.astral.sh/uv/guides/scripts/) header so the runner
resolves them with `uv` — no requirements file:

```python
# /// script
# dependencies = ["trl>=0.12.0", "peft>=0.7.0", "trackio"]
# ///

from trl import SFTTrainer, SFTConfig
# ... training code ...
```

Submit its content via the CLI (from a URL) or, if present, an `hf_jobs` MCP
wrapper whose JSON fields mirror the CLI flags (`script`, `flavor`, `timeout`,
`secrets`, `env`).

**2. `hf jobs uv run` CLI.** Flag order is strict:

```bash
# CORRECT — flags BEFORE the script URL, --secrets is plural, "uv run" not "run uv"
hf jobs uv run --flavor a10g-large --timeout 2h --secrets HF_TOKEN \
  "https://huggingface.co/user/repo/resolve/main/train.py"
```

Common mistakes that silently misbehave: `hf jobs run uv ...` (wrong order),
flags placed **after** the URL (ignored), `--secret` singular (wrong flag).

**3. TRL maintained scripts.** Battle-tested, no code to write — run them by URL
and pass `script_args`:

```bash
hf jobs uv run --flavor a10g-large --timeout 2h --secrets HF_TOKEN \
  "https://raw.githubusercontent.com/huggingface/trl/main/trl/scripts/sft.py" \
  --model_name_or_path Qwen/Qwen2.5-0.5B --dataset_name trl-lib/Capybara \
  --output_dir my-model --push_to_hub --hub_model_id username/my-model
```

Catalog: https://github.com/huggingface/trl/tree/main/examples/scripts.

**4. `trl-jobs` package.** Opinionated one-liners with auto Trackio + Hub push,
ideal from a terminal:

```bash
pip install trl-jobs
trl-jobs sft --model_name Qwen/Qwen2.5-0.5B --dataset_name trl-lib/Capybara
```

## Script source rules (important)

The runner executes in an isolated container with **no access to your local
filesystem**. The script must be one of:

- **Inline code** (recommended for custom training),
- a **public URL** (Hub `resolve/main/...`, GitHub `raw...`, or a raw Gist), or
- a **private Hub URL** (authenticated via the `HF_TOKEN` secret).

Local paths (`train.py`, `./scripts/train.py`, `/abs/path/train.py`) **all
fail**. To use a local script, upload it first:

```bash
hf repo create my-training-scripts --repo-type model
hf upload my-training-scripts ./train.py train.py
# then use: https://huggingface.co/USER/my-training-scripts/resolve/main/train.py
```

## Hardware flavors

| Flavor | GPU | VRAM | Sweet spot | ~$/hr |
|--------|-----|------|-----------|-------|
| `cpu-basic` / `cpu-upgrade` | — | — | dataset validation, preprocessing (not training) | low |
| `t4-small` | T4 | 16 GB | <1B models, demos (skip eval) | ~$0.5–1 |
| `t4-medium` | T4 | 16 GB | 1–3B dev | ~$1–2 |
| `l4x1` | L4 | 24 GB | 3–7B efficient training | ~$2–3 |
| `l4x4` | 4× L4 | 96 GB | multi-GPU | ~$8–12 |
| `a10g-small` | A10G | 24 GB | 3–7B production | ~$3–4 |
| `a10g-large` | A10G | 24 GB | 7–13B (LoRA) | ~$4–6 |
| `a10g-largex2` / `x4` | 2–4× A10G | 48–96 GB | multi-GPU, large models | ~$8–24 |
| `a100-large` | A100 | 40 GB | 13B+ fast, LoRA | ~$8–12 |

Flavor names and prices change — treat these as approximate and confirm against
the current Jobs docs. Rule of thumb: start on the smallest flavor that fits, use
**LoRA/PEFT for anything ≥7B**, and let TRL/Accelerate handle multi-GPU (no code
change; `per_device_train_batch_size` is per-GPU).

## Memory sizing

Rough VRAM budget:

```
full fine-tune  ≈  params(B) × 20 GB
LoRA fine-tune  ≈  params(B) × 4  GB
```

So Qwen2.5-7B full (~140 GB) is infeasible on a single GPU, but 7B LoRA
(~28 GB) fits an `a10g-large`. If you OOM, walk the ladder in
[troubleshooting.md](troubleshooting.md) (smaller batch → grad accumulation →
LoRA → gradient checkpointing → bigger GPU).

## Timeouts

Default is **30 min — too short for real training.** Formats: `"90m"`, `"2h"`,
`"1.5h"`, or integer seconds. Set estimated time **+ 20–30% buffer** for
model/dataset loading, checkpoint saving, and Hub push. On timeout the job is
killed immediately and unsaved progress is lost; save checkpoints
(`save_strategy="steps"`, `hub_strategy="every_save"`) so you can resume.

| Scenario | Timeout |
|----------|---------|
| Quick demo (50–100 examples) | 10–30 min |
| Development (small dataset) | 1–2 h |
| Production 3–7B, full dataset | 4–6 h |
| Large model + LoRA | 3–6 h |

## Cost & time estimate

`cost = hours × $/hr`. A quick heuristic for training hours: for a ~1B model on
`a10g-large`, budget roughly **0.1 h per 1K examples per epoch**, then scale
linearly by model size and by a hardware multiplier (t4-small ≈ 2×, a100-large
≈ 0.7×, a10g-largex2 ≈ 0.6× relative to a10g-large). Offer an estimate whenever
a job will run >1 h or cost >$5, and add the 30% timeout buffer on top.

Before spending, **verify inputs exist** — a typo'd model/dataset name fails the
job seconds in but only after you've paid to spin it up:

```python
hub_repo_details(["Qwen/Qwen2.5-0.5B"], repo_type="model")
hub_repo_details(["trl-lib/Capybara"], repo_type="dataset")
```

## Job status (on request only)

```bash
hf jobs ps                 # list jobs
hf jobs logs <job-id>      # stream logs (initial logs can lag 30–60 s)
hf jobs inspect <job-id>   # full details
hf jobs cancel <job-id>    # stop a job
```

## See also

- [training-methods.md](training-methods.md) — what to put in the script
- [hub-and-monitoring.md](hub-and-monitoring.md) — persistence + Trackio
- [troubleshooting.md](troubleshooting.md) — OOM/timeout/hang remedies
- Jobs docs: `hf_doc_fetch("https://huggingface.co/docs/huggingface_hub/guides/jobs")`
