---
name: colab-finetuning
version: 0.1.0
description: >-
  Fine-tuning LLMs inside the Google Colab notebook, where the runtime is ephemeral and the free
  GPU is a single 16 GB T4. Owns the Colab-specific layer around a trainer: persisting
  adapters/checkpoints to Google Drive or the HF Hub before a disconnect wipes /content, surviving
  the ~90-min idle timeout and 12-h cap (resume-from-checkpoint), secrets via userdata.get, !pip
  install pitfalls, T4 VRAM budgeting (QLoRA 4-bit, batch/grad-accum, seq length), GPU tiers (free
  T4 vs Pro A100/L4), and exporting merged/GGUF weights. Use WHEN fine-tuning on Colab or hitting
  OOM / session-death / Drive-mount / disk-full there. NOT the trainer internals — model loading,
  LoRA/QLoRA, SFTTrainer, GRPO (use unsloth, trl-fine-tuning, peft); NOT disconnect-safe training
  on Modal serverless GPU (use modal-ml-training); NOT multi-GPU/FSDP (use distributed-training);
  NOT the build-vs-buy cost call (use model-economics).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Colab Fine-Tuning

## Overview

Fine-tuning on Google Colab fails in ways that fine-tuning on a real machine does not, and none of
those failures are about the training code. The runtime is **ephemeral** (everything under
`/content` vanishes on disconnect), the free GPU is a single **16 GB T4**, and the session is
**time-boxed** (idle-reclaimed after ~90 min, hard-recycled at ~12 h). This skill is the discipline
for that environment. Three habits carry most of the weight:

1. **Persist before you disconnect** — checkpoints and the final adapter go to Google Drive or the
   HF Hub, never to `/content`.
2. **Budget for 16 GB** — QLoRA 4-bit, batch size 1-2 + grad accumulation, gradient checkpointing.
3. **Make the run resumable** — `output_dir` on Drive + `save_steps`, so a mid-run recycle costs
   one interval, not the whole job.

The *trainer* — how you load a model, attach LoRA adapters, and call `SFTTrainer`/`GRPOTrainer` —
is **not** in this skill. Use `unsloth` (fast single-GPU QLoRA, the usual Colab choice),
`trl-fine-tuning`, or `peft`. This skill is the notebook envelope those run inside.

## When to Use This Skill

- Fine-tuning any LLM in a Colab notebook (free T4, or Pro L4/V100/A100).
- Deciding what fits in 16 GB and how to configure batch/seq/grad-accum for it.
- Persisting adapters and checkpoints so a disconnect does not lose the run.
- Recovering a run after the session died, timed out, or was preempted.
- Debugging Colab-specific breakage: OOM on T4, forced restart after `pip install`, Drive mount
  hang, `SecretNotFoundError`, `No space left on device`, CPU-fallback.
- Exporting the result off Colab: merged 16-bit or GGUF, pushed to the Hub.

## When NOT to Use This Skill

- **Trainer internals** — model loading, LoRA/QLoRA config, `SFTTrainer`, chat templates,
  `train_on_responses_only`, RL (GRPO/DPO) → use `unsloth`, `trl-fine-tuning`, or `peft`.
- **Disconnect-safe training on Modal serverless GPU** — deploy+spawn, volume checkpointing →
  use `modal-ml-training`. (Same *idea*, different platform; that skill owns Modal.)
- **Multi-GPU / multi-node / FSDP / DeepSpeed** — Colab free is single-GPU → use
  `distributed-training`.
- **Squeezing throughput out of the GPU** (kernels, precision, packing) → use `optimize-for-gpu`.
- **Whether to fine-tune at all / where it is cheapest** (build-vs-buy, ROI) → use
  `model-economics`.
- Any run that needs > 12 h unattended, a guaranteed card, or more than one GPU — leave Colab
  (see the last section).

## The three non-negotiables

### 1. Persist to Drive or the Hub — `/content` is ephemeral

Everything under `/content` is wiped on disconnect. Only Google Drive (mounted) and the HF Hub
survive. Mount Drive and point durable output at it:

```python
from google.colab import drive
drive.mount("/content/drive")
OUT = "/content/drive/MyDrive/finetune/run"      # survives disconnect
```

Save **LoRA adapters** (tens of MB) as intermediate checkpoints, not merged weights (many GB) —
and push the final adapter to the Hub the instant training finishes, before any export step that
could crash. Full patterns — Drive I/O speed trap, merged 16-bit vs GGUF export, `push_to_hub_*`
— are in `references/persistence-and-checkpointing.md`.

### 2. Resume from checkpoint — beat the 12-h cap

```python
args = TrainingArguments(output_dir=OUT, save_strategy="steps", save_steps=50,
                         save_total_limit=2, ...)      # rest of config: see the trainer skill
trainer.train(resume_from_checkpoint=True)             # no-ops cold, resumes warm
```

If the VM recycles at hour 6, a fresh session re-runs install/mount/secrets, rebuilds the trainer
with the **same `output_dir`**, and resumes. Max lost progress = one `save_steps` interval. The
full cold-vs-warm resume flow is in `references/persistence-and-checkpointing.md`.

### 3. Budget for 16 GB — QLoRA is mandatory on T4

Confirm the GPU, then load 4-bit and keep batches small:

```python
!nvidia-smi                                            # empty output = no GPU; fix runtime type
# load_in_4bit=True, per_device_train_batch_size=1-2, gradient_accumulation_steps=8-16,
# use_gradient_checkpointing="unsloth", max_seq_length 1024-2048   (details in the unsloth skill)
```

Rough T4 ceiling: ~8-9B model in 4-bit at seq ≤ 2048. The GPU-tier table, the VRAM-sizing
heuristic, secrets via `userdata.get`, and the `!pip install` restart trap are in
`references/session-and-runtime.md`.

## Secrets — never hardcode a token in a shared notebook

Notebooks get shared and committed. Put tokens in the Colab **Secrets** panel (key icon) and read
them at runtime; do not paste `hf_...` into a cell:

```python
from google.colab import userdata
import os
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")      # for gated repos + push_to_hub
```

## When something breaks

Colab has a small, recurring set of failures — OOM, session-death, forced restart after
`pip install`, Drive-mount hang, disk full, CPU-fallback. The full symptom→fix table is in
`references/failure-modes.md`. The two-line summary: put `output_dir` on Drive with `save_steps`
set, and push the adapter to the Hub the moment training finishes.

## Leaving Colab

Colab free is right for learning, small QLoRA jobs (≤ ~8B, a few hours), and prototyping. Move off
it when a run needs > 12 h unattended, multiple GPUs, or a guaranteed card, or when Pro+ costs more
than a spot A100 hour elsewhere. Route to `modal-ml-training` (disconnect-safe serverless GPU) or
`distributed-training` (multi-GPU), and check the economics with `model-economics`.

## References

- `references/session-and-runtime.md` — runtime-type setup, GPU-tier table, idle/12-h/preemption
  timeouts, Pro+ background execution, `!pip install` restart pitfalls, secrets via `userdata`,
  and the full T4 VRAM-budgeting guide.
- `references/persistence-and-checkpointing.md` — Drive mount + I/O speed trap, checkpoint +
  `resume_from_checkpoint` (cold vs warm), saving adapters, merged 16-bit and GGUF export,
  `push_to_hub_*`, and the ordered per-run checklist.
- `references/failure-modes.md` — the complete Colab symptom→fix table and the "when to leave
  Colab" decision.
