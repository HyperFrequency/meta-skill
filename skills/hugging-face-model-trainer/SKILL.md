---
name: hugging-face-model-trainer
version: 0.1.0
description: >-
  Fine-tune and align language models with TRL (SFT, DPO, GRPO, reward
  modeling) on Hugging Face Jobs' managed cloud GPUs — no local hardware.
  Submit self-contained uv / PEP-723 scripts (or the `trl-jobs` package) with
  `hf jobs uv run`, push results to the Hub off the ephemeral runner, monitor
  with Trackio, pick a GPU flavor + timeout, and export merged adapters to GGUF
  for Ollama / llama.cpp / LM Studio. Use WHEN you want cloud-GPU TRL training
  without owning infrastructure, need SFT/DPO/GRPO/reward jobs, or must convert
  a trained model to GGUF for local inference. NOT for a training loop you run
  on your own machine (use `unsloth`, `peft`, `axolotl`, `llama-factory`),
  Colab-notebook survival specifics (`colab-finetuning`), managed fine-tuning
  bundled with a serving vendor (`fireworks-ai`), multi-GPU / FSDP internals
  (`distributed-training`), or standing up an inference server
  (`inference-serving`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "TRL, transformers, peft, accelerate, datasets, huggingface_hub, trackio all Apache-2.0; llama.cpp / GGUF tooling MIT"
---

# Hugging Face Model Trainer (TRL on HF Jobs)

## Overview

Train and align language models with [TRL](https://huggingface.co/docs/trl)
(Transformer Reinforcement Learning) on **Hugging Face Jobs** — managed cloud
GPUs that you never provision. You write a self-contained training script,
submit it with `hf jobs uv run`, and the trained model is pushed to the Hub.
No local GPU, no CUDA install, no infrastructure.

The runner is **ephemeral**: everything on disk is destroyed when the job ends,
so a model that is not pushed to the Hub is lost. Three cross-cutting rules
therefore run through every job: (1) `push_to_hub=True` + a write token, (2) a
`timeout` longer than training (the default 30 min is too short), and (3) a
dataset whose format matches the trainer.

This file is a **router**. Each capability links to a focused reference with
runnable templates, parameter tables, and failure modes — read the one for the
task at hand rather than loading everything.

## When to Use This Skill

- You want to fine-tune or align an open model on cloud GPUs with no local
  setup, billed per job.
- You need a TRL method: **SFT** (instruction tuning), **DPO** (preference
  alignment), **GRPO** (online RL with verifiable rewards), or **reward
  modeling** for an RLHF pipeline.
- You want a one-liner (`trl-jobs`) or a fully custom inline training script run
  as a managed job.
- You need to convert a trained/merged model to **GGUF** for Ollama, llama.cpp,
  LM Studio, or edge/CPU inference.
- You want real-time metrics (Trackio) and guaranteed Hub persistence from an
  ephemeral runner.

## When NOT to Use This Skill

- **You own the training loop on your own machine or rented box** — use
  `unsloth`, `peft`, `axolotl`, or `llama-factory` directly.
- **Google Colab specifics** (Drive persistence, 90-min idle death, T4 VRAM
  budgeting) — use `colab-finetuning`.
- **Managed fine-tuning bundled with a serving vendor** (you never see a job) —
  use `fireworks-ai`.
- **Multi-GPU / FSDP / DeepSpeed sharding internals** — Jobs+Accelerate handle
  multi-GPU automatically; for the sharding mechanics use `distributed-training`.
- **Serving or benchmarking a finished model** — use `inference-serving`.
- **Generic Hub/CLI plumbing** (repos, uploads, auth) unrelated to training —
  use `hugging-face-cli`.

## Setup

Hugging Face Jobs requires a **paid plan** (Pro, Team, or Enterprise) — free
accounts cannot submit jobs.

```bash
pip install -U "huggingface_hub[cli]"   # provides the `hf` CLI (incl. `hf jobs`)
pip install -U trl-jobs                  # optional: one-liner training wrapper

hf auth login                            # or: export HF_TOKEN=hf_...  (WRITE scope)
hf auth whoami                           # verify identity + token
```

The token **must have write permission** — the job pushes the model back to the
Hub under your namespace. Confirm with `hf auth whoami`; a read-only token fails
at push time with 401/403.

## Quick Start

**Option A — `trl-jobs` one-liner** (opinionated defaults, auto Trackio + Hub
push; best from a terminal):

```bash
trl-jobs sft --model_name Qwen/Qwen2.5-0.5B --dataset_name trl-lib/Capybara
```

**Option B — custom inline uv script** (full control; the general path). The
script carries its own dependencies via a PEP 723 header, and the job config
sets the GPU flavor, timeout, and the token secret:

```bash
hf jobs uv run \
  --flavor a10g-large \
  --timeout 2h \
  --secrets HF_TOKEN \
  "https://huggingface.co/USER/REPO/resolve/main/train_sft.py"
```

`hf jobs` flags **must come before** the script argument, and the script must be
inline code, a public URL, or a Hub/Gist URL — **local file paths do not work**
(the runner has no access to your filesystem). If your environment exposes an
`hf_jobs` MCP wrapper, it takes the same fields (`script`, `flavor`, `timeout`,
`secrets`, `env`) as JSON; the semantics below are identical. See
[references/jobs-and-hardware.md](references/jobs-and-hardware.md) for the inline
`# /// script` template, URL rules, and CLI syntax gotchas.

## Capability Map

| Capability | What you get | Reference |
|------------|--------------|-----------|
| **Training methods** | SFT / DPO / GRPO / reward: when to use each, exact dataset formats, and complete runnable templates | [references/training-methods.md](references/training-methods.md) |
| **Jobs & hardware** | `hf jobs uv run` CLI + PEP 723 uv scripts, `trl-jobs`, TRL maintained scripts, GPU flavor table, timeouts, cost & memory sizing, multi-GPU | [references/jobs-and-hardware.md](references/jobs-and-hardware.md) |
| **Hub & monitoring** | Ephemeral-runner persistence, `push_to_hub` + checkpoints, Trackio real-time metrics, auth troubleshooting | [references/hub-and-monitoring.md](references/hub-and-monitoring.md) |
| **GGUF conversion** | Merge adapter + convert with llama.cpp, quantization table, Ollama/LM Studio usage, build pitfalls | [references/gguf-conversion.md](references/gguf-conversion.md) |
| **Troubleshooting** | Hang-on-eval, OOM ladder, timeouts, `max_length` vs `max_seq_length`, dataset-format failures, reliability rules | [references/troubleshooting.md](references/troubleshooting.md) |

## The Three Non-Negotiables

Verify all three before submitting **any** job — each has its own reference:

1. **Persist to the Hub.** `push_to_hub=True`, `hub_model_id="user/name"` in the
   config, and `--secrets HF_TOKEN` on the job. Without all three, training is
   thrown away. → [references/hub-and-monitoring.md](references/hub-and-monitoring.md)
2. **Set a real timeout.** Default is 30 min. Use estimated training time + a
   20–30% buffer for load/checkpoint/push overhead; on timeout the job is killed
   and unsaved progress is lost. → [references/jobs-and-hardware.md](references/jobs-and-hardware.md)
3. **Match the dataset format.** SFT wants `messages`/text/prompt-completion;
   DPO wants `prompt`/`chosen`/`rejected`; GRPO wants prompt-only. Validate
   unknown datasets on CPU (~$0.01) before burning GPU time — a format mismatch
   is the single most common cause of failed jobs.
   → [references/training-methods.md](references/training-methods.md)

## Workflow at a Glance

1. **Pick the method** (SFT → then optionally DPO; GRPO for verifiable-reward
   tasks) and confirm the dataset's columns match it.
2. **Choose hardware** by model size; use **LoRA/PEFT** for anything ≥7B.
   Estimate time and cost first.
3. **Write the script** with a PEP 723 header, Trackio reporting, an eval split,
   and Hub-push config — or reuse a TRL maintained script / `trl-jobs`.
4. **Submit**, then report the job ID, monitoring URL, and estimated time. Jobs
   run **asynchronously** for hours — do not poll; check status only on request
   (`hf jobs ps`, `hf jobs logs <id>`, `hf jobs inspect <id>`).
5. **(Optional) Convert to GGUF** once the model is on the Hub, for local
   inference.

## Notes on API stability

TRL's config field names drift across releases. Recent TRL uses `max_length`
(not `max_seq_length`) on `SFTConfig`/`DPOConfig`, with a default of `1024`;
older versions differ. Pin a TRL version in the PEP 723 header and confirm
current fields with `hf_doc_fetch("https://huggingface.co/docs/trl/sft_trainer")`
before scripting exotic parameters. GPU flavor names and per-hour prices change
— verify flavors at the Jobs docs and treat every cost figure in the references
as approximate.
