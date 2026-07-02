---
name: slime
description: Guidance for LLM RL post-training with slime, THUDM's Megatron-LM + SGLang framework (powers GLM-4.5/4.6/4.7). Use when training GLM/Qwen3/DeepSeek-V3/Llama-3 models with GRPO/GSPO/PPO, building custom data-generation or multi-turn agentic rollout workflows, or needing native Megatron-LM parallelism (TP/PP/DP/SP) with high-throughput SGLang rollout. NOT for enterprise-grade stability features (use miles), flexible backend swapping (use verl), PyTorch-native abstractions (use torchforge), or lightweight single-GPU SFT/DPO without Megatron (use trl-fine-tuning or openrlhf).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Reinforcement Learning, Megatron-LM, SGLang, GRPO, Post-Training, GLM]
dependencies: [sglang-router>=0.2.3, ray, torch>=2.0.0, transformers>=4.40.0]
---

# slime: LLM Post-Training Framework for RL Scaling

slime is an LLM post-training framework from Tsinghua's THUDM team, powering
GLM-4.5/4.6/4.7. It connects **Megatron-LM** for training with **SGLang** for
high-throughput rollout generation, orchestrated by Ray.

## When to use slime

**Choose slime when you need:**
- Megatron-LM native training with SGLang inference and full parallelism (TP, PP, DP, SP)
- Custom data-generation workflows with flexible data buffers
- Training GLM-4.x, Qwen3, DeepSeek V3/R1, or Llama 3 models
- A research-grade framework with production backing (Z.ai)

**Choose a sibling skill instead when:**
- You need enterprise-grade stability features → **miles**
- You want flexible backend swapping → **verl**
- You need PyTorch-native abstractions → **torchforge**
- You want lightweight single-GPU SFT/DPO without Megatron → **trl-fine-tuning** / **openrlhf**

## Architecture

```
            ┌────────────────────────────────┐
            │          Data Buffer           │
            │  prompt mgmt · custom gen/filter│
            │  · rollout sample storage       │
            └───────┬────────────────┬────────┘
        ┌───────────▼──────┐ ┌───────▼──────────────┐
        │ Training         │ │ Rollout              │
        │ (Megatron-LM)    │ │ (SGLang + Router)    │
        │ actor · critic   │ │ generation · reward  │
        │ · weight sync ──►│ │ · multi-turn         │
        └──────────────────┘ └──────────────────────┘
```

## Three argument categories

slime composes three arg namespaces on one command line:

1. **Megatron args** — passed directly (`--tensor-model-parallel-size`, `--num-layers`, ...)
2. **SGLang args** — prefixed `--sglang-` (`--sglang-mem-fraction-static`, `--sglang-context-length`, ...)
3. **slime args** — resource/data/loop/algorithm (`--actor-num-gpus-per-node`, `--prompt-data`, `--advantage-estimator`, ...)

Per-rollout batch constraint:

```
rollout_batch_size × n_samples_per_prompt = global_batch_size × num_steps_per_rollout
```

## Quick start

Run from the root of a cloned [`THUDM/slime`](https://github.com/THUDM/slime)
checkout (the `scripts/` paths below live in that repo, not in this skill):

```bash
source scripts/models/qwen3-4B.sh   # repo-relative; sets MODEL_ARGS / CKPT_ARGS
python train.py \
    --actor-num-gpus-per-node 4 --rollout-num-gpus 4 \
    --advantage-estimator grpo --use-kl-loss --kl-loss-coef 0.001 \
    --rollout-batch-size 32 --n-samples-per-prompt 8 --global-batch-size 256 \
    --num-rollout 3000 --prompt-data /path/to/data.jsonl \
    ${MODEL_ARGS[@]} ${CKPT_ARGS[@]}
```

## Supported models

GLM (4.5/4.6/4.7, Z1-9B) · Qwen (Qwen3 4B/8B/30B-A3B, Qwen3-MoE, Qwen2.5) ·
DeepSeek (V3, V3.1, R1) · Llama 3 (8B, 70B) · Kimi K2 · Moonlight-16B.
Each has a pre-configured script under `scripts/models/` in the slime repo.

## References

- **`references/workflows.md`** — installation, GRPO quick start, and the three core
  workflows (standard GRPO, async, multi-turn agentic) plus co-location, custom reward
  model, and multi-task eval recipes.
- **`references/api-reference.md`** — full argument tables, Sample/Status data
  structures, data-buffer classes, custom generate/reward function signatures, and
  model-script structure.
- **`references/troubleshooting.md`** — SGLang crashes, weight-sync timeouts, OOM,
  data-loading, stability (NaN / reward collapse), async, multi-turn, and checkpoint issues.

## Resources

- Docs: https://thudm.github.io/slime/
- GitHub: https://github.com/THUDM/slime
- Blog: https://lmsys.org/blog/2025-07-09-slime/
- Examples: `examples/` directory in the repo (14+ worked examples)
