---
name: prime-intellect-lab
version: 0.1.0
description: >-
  Hosted reinforcement-learning post-training on Prime Intellect's managed-GPU
  platform via the `prime` CLI: environments (dataset + harness + rubric),
  verifiable rewards, GRPO with LoRA on open-weight models (Qwen3, INTELLECT-3),
  agentic multi-turn training, the Environments Hub, custom environments built
  with the `verifiers` library, and GEPA gradient-free prompt optimization. Use
  when you want managed RL post-training without owning GPUs, verifiable-reward
  training on math/code/reasoning/agentic tasks, or to evolve a system prompt
  without gradient updates. Do NOT use for supervised fine-tuning (use `tinker`),
  local/on-prem RL on your own GPUs, raw GPU rental (use `tensorpool`), custom
  serverless compute (use `modal-ml-training`), or inference serving/deployment.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Prime Intellect Lab — Hosted RL Post-Training

## Overview

Prime Intellect Lab runs reinforcement-learning post-training on managed GPU
infrastructure, driven by the `prime` command-line tool. You supply two things —
an **environment** (what the model practices and how each rollout is scored) and
a **base model** — and the platform runs the trainer/inference/orchestrator loop
for you. Training is **GRPO** producing a **LoRA adapter** on an open-weight
model. Pre-built environments come from the Environments Hub; you can also author
your own with the `verifiers` library, or skip gradients entirely and refine a
system prompt with **GEPA**.

Hosted training may require beta access — check `primeintellect.ai`. CLI flags and
the supported-model list change over time; confirm specifics with `prime --help`,
`prime <subcommand> --help`, and `prime models list` rather than trusting a
memorized signature.

## When to Use This Skill

- You want managed-GPU GRPO/RL post-training without provisioning hardware.
- You are training against a **verifiable reward** — math, code execution,
  reasoning, or agentic tasks with a programmatic rubric.
- You need **agentic multi-turn** training (tool-use, code execution, browsing).
- You want a LoRA adapter on an open-weight model (Qwen3 family, INTELLECT-3).
- You want to reuse a pre-built environment, or author a custom one with
  `verifiers`.
- You want **GEPA** — gradient-free, genetic-Pareto system-prompt optimization.

## When NOT to Use This Skill

- **Supervised fine-tuning / instruction tuning** → use `tinker`.
- **Local / on-prem RL on your own GPUs** → self-hosted `prime-rl`, or TRL / verl
  directly.
- **Raw GPU rental or on-demand clusters** → use `tensorpool` (or Prime's own
  Compute API, covered in `references/models-and-compute.md`).
- **Custom serverless compute or non-standard architectures** →
  `modal-ml-training`, `modal-research-gpu`.
- **Inference serving / deployment** → vLLM, SGLang, and similar.

See the full platform decision matrix in `references/models-and-compute.md`.

## Core Concepts

- **Environment** — the fundamental training unit, `owner/name` (e.g.
  `primeintellect/alphabet-sort`). It bundles a **dataset** (the problems), a
  **harness** (execution sandbox: code runner, tool loop), and a **rubric**
  (reward function scoring each output in `[0.0, 1.0]`).
- **Hosted training loop** — `prime rl run` orchestrates a **trainer** (GRPO with
  LoRA), an **inference** service (generates rollouts at scale), and an
  **orchestrator** (routes data between them). You never manage these directly.
- **Environments Hub** — pre-built envs for math, code, reasoning, and agentic
  tasks; browse with `prime env list`, add with `prime env install`.
- **`verifiers` library** — the Python building blocks (rubrics, harness
  wrappers, dataset adapters) for authoring custom environments.
- **GEPA** — Genetic-Pareto prompt optimization. A teacher LLM reflects on
  evaluation failures and evolves the environment's system prompt across
  generations; no gradient training. Run with `prime gepa run <config.toml>`.

## Setup

```bash
uv tool install prime          # install the CLI (uv recommended)
prime login                    # authenticate (or: prime config set-api-key)
prime config view              # verify configuration

mkdir -p ~/dev/my-lab && cd ~/dev/my-lab
prime lab setup                # scaffold configs/, environments/, example TOMLs
```

`prime lab setup --prime-rl` additionally clones the self-hosted `prime-rl`
trainer. Authentication is read from `PRIME_API_KEY`; check it is present with
`[ -n "$PRIME_API_KEY" ] && echo set || echo missing` — never echo the value.

## Training Workflow (at a glance)

1. **Install an environment** — `prime env install primeintellect/<name>`.
2. **Baseline eval first** — `prime eval run <env> -m <model> -n 20 -r 1`. Always
   measure before training so you can prove the run moved the metric.
3. **Write a config** — a `.toml` with `model`, step/batch fields, and one or more
   `[[env]]` blocks. Use `[[env]]` (double brackets) — single `[env]` silently
   fails. See `references/config-reference.md`.
4. **Launch** — `prime rl run configs/rl/<name>.toml` (hosted) or
   `uv run prime-rl <config>` (self-hosted).
5. **Monitor** — `prime rl status`, `prime rl logs --follow`, plus W&B if enabled.
6. **Review** — `prime rl list`, `prime rl download <run-id> --output ./adapter`,
   then re-run eval with `--adapter ./adapter` to confirm the gain.

Full commands, flags, and the eval/download details are in
`references/training-workflow.md`.

## Operational Guardrails

- **Baseline before you train.** A run with no pre-training number is unfalsifiable.
- **Start small.** Prototype with `Qwen/Qwen3-4B-Instruct-2507` and
  `max_steps=50` before scaling model size or steps.
- **Estimate cost and get approval before large runs.** Check the projected spend
  (e.g. `prime rl estimate --config <config>`; verify the exact flag with
  `prime rl --help`) and present it before launching an expensive job.
  For budgeting hosted training economics, see `tinker-training-cost`.
- **Diagnose flat reward early.** Reward stuck at 0.0 usually means the rubric
  never fires or the model can't produce valid outputs; stuck at 1.0 means the
  task is too easy. Test the rubric with a small `prime eval run` before blaming
  the trainer — see `references/troubleshooting.md`.

## Reference Files

- `references/config-reference.md` — full `.toml` field reference, size presets,
  `[[env]]` array-of-tables syntax, and multi-environment weighting.
- `references/training-workflow.md` — step-by-step commands for install, eval,
  launch, monitor, and adapter download.
- `references/environments-and-gepa.md` — building custom environments with
  `verifiers`, and GEPA prompt-optimization configs.
- `references/models-and-compute.md` — supported models, the platform decision
  matrix, and the Compute API for direct GPU provisioning.
- `references/troubleshooting.md` — common failure modes and a command
  quick-reference.
