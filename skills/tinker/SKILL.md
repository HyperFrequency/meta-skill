---
name: tinker
version: 0.1.0
description: >-
  Fine-tune LLMs on Thinking Machines Lab's managed Tinker cloud training API — you write the
  training loop (supervised SFT, RL/GRPO/PPO, DPO preference learning, distillation) and Tinker
  provisions GPUs, hosts weights, and runs the forward/backward passes. Every run is LoRA on a
  fixed roster of Qwen / Llama / DeepSeek / GPT-OSS / Kimi models (up to 235B), driven through a
  four-primitive API (ServiceClient → TrainingClient → SamplingClient → forward_backward/optim_step)
  or the higher-level tinker-cookbook recipes. Use when you want managed cloud LoRA training without
  owning GPUs, need fine control over the sampling → reward → gradient loop for RL, or want ready
  recipes for SFT/preference/distillation. Do NOT use for full-parameter (non-LoRA) fine-tuning,
  custom or unsupported architectures, air-gapped/offline training, or training on your own hardware
  — use the local `axolotl`, `unsloth`, `llama-factory`, or `peft` skills instead; to serve trained
  weights see the `inference-serving` skills.
metadata: { skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)", source-license: "Apache-2.0" }
---

# Tinker — Cloud LLM Fine-Tuning

## Overview

Tinker is a managed training API from Thinking Machines Lab. It hosts a fixed roster of open-weight
base models on cloud GPUs and exposes a small set of primitives — `forward_backward`, `optim_step`,
`sample`, and `save_state` — so you supply the training *logic* while Tinker owns hardware
provisioning, distribution, and weight hosting. Two layers exist:

- **Low-level `tinker` SDK** — raw clients and `Datum`/`ModelInput` types. Maximum control; you build
  the sampling → reward → gradient loop yourself (essential for custom RL).
- **`tinker-cookbook`** — opinionated recipes and dataset/renderer helpers (`chz.Blueprint` configs)
  for standard SFT, RL, DPO, and distillation without wiring the loop by hand.

All training is **LoRA** — Tinker never does full-parameter fine-tuning. This is a deliberate scope
choice, not a limitation to fight.

> This skill is adapted from an openscience skill (Apache-2.0). Tinker itself (`tinker`,
> `tinker-cookbook`) is a third-party product of Thinking Machines Lab; consult its own license and
> docs at https://tinker-docs.thinkingmachines.ai before use.

## When to Use This Skill

- Fine-tune models up to 235B parameters without provisioning or managing GPUs.
- Run LoRA SFT on Qwen, Llama, DeepSeek, GPT-OSS, or Kimi families.
- Implement custom RL loops (GRPO-style advantage centering, PPO, importance sampling) where you
  control sampling, reward computation, and the training step.
- Train vision-language models (Qwen3-VL) with image chunks.
- Run DPO / RLHF / prompt-distillation pipelines from the cookbook recipes.
- Iterate fast when your bottleneck is hardware access, not training code.

## When NOT to Use This Skill

- **Full-parameter fine-tuning** — Tinker is LoRA-only. Use `distributed-training` (DeepSpeed/FSDP)
  for full FT.
- **Your own GPUs / on-prem / air-gapped** — use the local `axolotl`, `unsloth`, `llama-factory`,
  or `peft` skills.
- **Custom or unsupported architectures** — Tinker serves specific model families only (see
  [Models & LoRA](references/models-and-lora.md)).
- **Quantized (QLoRA / bitsandbytes) local training** — use `unsloth`.
- **Serving or deploying finished weights** — use the `inference-serving` skills (`vllm`, `sglang`).

## Core Mental Model

```python
import tinker
from tinker import types

service_client  = tinker.ServiceClient()
training_client = service_client.create_lora_training_client(base_model="Qwen/Qwen3-30B-A3B", rank=32)

# One training step = submit both, then wait (overlaps on the same clock cycle)
fwd_bwd = training_client.forward_backward(datums, loss_fn="cross_entropy")
optim   = training_client.optim_step(types.AdamParams(learning_rate=get_lr(model_name)))
fwd_bwd.result(); optim.result()

# Snapshot weights, then sample from them
path            = training_client.save_weights_for_sampler(name="step-0").result().path
sampling_client = service_client.create_sampling_client(model_path=path)
```

Every call returns a **future** — submit work, then block on `.result()` (or `await` the
`*_async` variant). A `Datum` pairs a `ModelInput` (the token sequence) with `loss_fn_inputs`
(targets, weights, logprobs, advantages — whichever the loss function needs). Full signatures and
types: [API Reference](references/api-reference.md).

## Capability Map

| Topic | Reference |
|-------|-----------|
| Clients, `Datum`/`ModelInput`/`AdamParams`/`SamplingParams`, sampling, logprobs, async | [API Reference](references/api-reference.md) |
| Supervised fine-tuning: cookbook + HF/streaming/custom datasets, checkpoints | [Supervised Learning](references/supervised-learning.md) |
| RL: env classes, custom GRPO loop, completers, off-policy, extension property | [Reinforcement Learning](references/reinforcement-learning.md) |
| Built-in loss math (`cross_entropy`, `importance_sampling`, `ppo`, `cispo`, `dro`) + custom | [Loss Functions](references/loss-functions.md) |
| Model roster, LoRA behavior, learning-rate scaling | [Models & LoRA](references/models-and-lora.md) |
| Renderers, `TrainOnWhat`, chat formats, vision inputs | [Rendering](references/rendering.md) |
| DPO, full RLHF pipeline, prompt distillation, LR sweeps | [Preference & Distillation](references/preference-and-distillation.md) |
| Inline + offline (Inspect AI) evals, custom evaluators | [Evaluations](references/evaluations.md) |
| Runnable example scripts (`sl_basic`, `sl_loop`, `rl_basic`, `rl_loop`, ...) | [Recipes](references/recipes.md) |

## Installation & Authentication

```bash
pip install tinker tinker-cookbook           # requires Python 3.10–3.13 (NOT 3.14+)
export TINKER_API_KEY=...                      # obtain from the Tinker console
[ -n "$TINKER_API_KEY" ] && echo set || echo "not set"
```

## Supervised Fine-Tuning (fastest path)

Prepare JSONL chat data (`{"messages": [{"role": ..., "content": ...}, ...]}`), then drive the
cookbook trainer via a `chz.Blueprint`:

```python
model_name = "meta-llama/Llama-3.1-8B"
common  = ChatDatasetBuilderCommonConfig(
    model_name_for_tokenizer=model_name, renderer_name=get_recommended_renderer_name(model_name),
    max_length=2048, batch_size=128,
    train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,   # ALWAYS set explicitly; default is LAST only
)
builder = FromConversationFileBuilder(common_config=common, file_path="data.jsonl")
config  = chz.Blueprint(train.Config).apply({
    "log_path": "/tmp/sft-run", "model_name": model_name, "dataset_builder": builder,
    "learning_rate": get_lr(model_name), "lr_schedule": "linear", "num_epochs": 3, "lora_rank": 32,
}).make()
asyncio.run(train.main(config))   # from tinker_cookbook.supervised import train
```

Watch `train_mean_nll` and `test/nll` in `log_path/metrics.jsonl`. Full imports, HF/streaming/custom
datasets, and checkpoints: [Supervised Learning](references/supervised-learning.md).

## Reinforcement Learning (GRPO-style)

Standard reward-driven training via the cookbook is one config away:

```python
from tinker_cookbook.rl import train
from tinker_cookbook.recipes.math_rl.math_env import Gsm8kDatasetBuilder
# builder = Gsm8kDatasetBuilder(batch_size=128, group_size=16, renderer_name=..., model_name_for_tokenizer=...)
# blueprint sets learning_rate=4e-5, max_tokens=256, then asyncio.run(train.main(config))
```

For full control, run the loop yourself: `save_weights_for_sampler` → `create_sampling_client` →
`sample(num_samples=group_size)` → compute rewards → center advantages (`r - mean(r)`, skip groups
where all advantages are 0) → build `Datum`s with `logprobs`+`advantages` → `forward_backward(...,
loss_fn="importance_sampling")`. Keep sampler↔learner KL below **0.01**. Env classes, the complete
loop, off-policy/streaming config, and the O(T) vs O(T²) sequence-extension property:
[Reinforcement Learning](references/reinforcement-learning.md).

## DPO & Preference Learning

Align to preference pairs without a separate reward model. Use a lower LR than SFT (1e-5 to 1e-6)
and keep the base model in-distribution with the preference data:

```bash
python -m tinker_cookbook.recipes.preference.train \
    log_path=/tmp/dpo model_name=meta-llama/Llama-3.2-1B \
    dataset=hhh renderer_name=role_colon learning_rate=1e-5 dpo_beta=0.1
```

Datasets `hhh` / `helpsteer3` / `ultrafeedback`; three-step SL → preference-model → RL pipeline and
prompt distillation: [Preference & Distillation](references/preference-and-distillation.md).

## Models, LoRA & Hyperparameters

Base models (no chat template) suit post-training research; Instruction/Hybrid/Reasoning/Vision
variants each fit different needs. MoE models (e.g. Qwen3-30B-A3B) are the most cost-efficient.
Full roster: [Models & LoRA](references/models-and-lora.md).

**LoRA needs 20–100× the LR of full fine-tuning** — never hand-pick it. Use
`get_lr(model_name)` (or `get_lora_lr_over_full_finetune_lr`). Optimal LR is independent of rank.
Train **all** weight matrices (attention + MLP), not attention-only.

| Parameter | SFT | RL | Notes |
|-----------|-----|----|-------|
| `learning_rate` | `get_lr(model)` | 4e-5 (Llama-8B) | Model-dependent; scale `LR ∝ √batch_size` |
| `batch_size` | 128 | 128 | Aim for 100+ steps/epoch; smaller helps FT |
| `lora_rank` | 32 | 32 (small ranks fine for RL) | LoRA params ≥ completion tokens for SFT |
| `group_size` | — | 16 | Rollouts per problem (variance reduction) |
| `max_length` / `max_tokens` | 2048–32768 | 256 | Sequence / generation length |
| `num_epochs` | 1–3 | — | — |
| `lr_schedule` | `linear` | — | Only `linear` and `constant` exist — `cosine` fails |

## Cost Estimation

Estimate before launching and confirm with the user:
`cost ≈ (total_tokens × num_epochs × price_per_M) / 1e6`. Get `total_tokens` by tokenizing the
dataset with `get_tokenizer(model_name)` (SFT) or `batch_size × group_size × max_tokens × num_batches`
(RL). Per-model prices: [Models & LoRA](references/models-and-lora.md). For cross-provider $/token
modeling see the `model-economics` skill.

## Common Failure Modes

| Symptom | Cause / Fix |
|---------|-------------|
| `TINKER_API_KEY` not set | `export TINKER_API_KEY=...` before any client call |
| `Unknown learning rate schedule` | Only `linear` / `constant` are valid — `cosine` does not exist |
| pydantic errors on import | Tinker requires Python 3.10–3.13; v1 pydantic breaks on 3.14+ |
| Only 1 step per epoch | `batch_size` too large for dataset — target 100+ steps/epoch |
| KL > 0.01 in RL | Lower LR; check `group_size`; go off-policy carefully |
| Reward stuck at 0 | Debug the reward fn in isolation; verify answer extraction |
| All advantages = 0 | No reward variance in the group — raise `group_size` |
| OOM loading dataset | Use `StreamingSupervisedDatasetFromHFDataset` |
| Model trains on wrong tokens | Set `TrainOnWhat` explicitly; default is `LAST_ASSISTANT_MESSAGE` |
| Generation never stops | Pass `renderer.get_stop_sequences()` into `SamplingParams` |

## Saving & Resuming

```python
sampling_path = training_client.save_weights_for_sampler(name="final").result().path  # inference only
resume_path   = training_client.save_state(name="checkpoint").result().path            # + optimizer state
training_client.load_state(resume_path)
```

## Related Skills

- `axolotl`, `unsloth`, `llama-factory`, `peft` — local/on-prem fine-tuning alternatives.
- `distributed-training` — full-parameter FT (DeepSpeed / FSDP).
- `inference-serving` (`vllm`, `sglang`) — serve the weights you trained here.
- `fireworks-ai` — another managed fine-tuning + inference provider.
- `arbor` — autonomous optimization loops that can wrap a Tinker training run as the inner objective.
- `model-economics` — cross-provider cost modeling.

## External Resources

- Docs: https://tinker-docs.thinkingmachines.ai
- Cookbook: https://github.com/thinking-machines-lab/tinker-cookbook
- Console: https://tinker-console.thinkingmachines.ai
