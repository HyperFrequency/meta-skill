---
name: openrlhf
description: High-performance Ray + vLLM RLHF framework for distributed PPO, GRPO, RLOO, REINFORCE++, and DPO training of large models (7B-70B+) on multi-node GPU clusters, with a Hybrid Engine that colocates models for ~2x speedups over DeepSpeedChat. Use when post-training large LLMs with RL across many GPUs/nodes and you want vLLM-accelerated rollouts. NOT for single-node/simple RLHF (use trl-fine-tuning), GRPO-on-TRL recipes (grpo-rl-training), reference-free preference tuning (simpo), Megatron+SGLang GLM training (slime/miles), PyTorch-native agentic RL (torchforge), or 100B+ FSDP/Megatron scale (verl).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Post-Training, OpenRLHF, RLHF, PPO, GRPO, RLOO, DPO, Ray, vLLM, Distributed Training, Large Models, ZeRO-3]
dependencies: [openrlhf, ray, vllm, torch, transformers, deepspeed]
---

# OpenRLHF — High-Performance RLHF Training

Ray-based RLHF framework optimized for distributed training with vLLM rollout
acceleration. Entry modules: `openrlhf.cli.train_ppo_ray` (PPO/GRPO/RLOO/REINFORCE++),
`train_rm`, `train_dpo`, `train_sft`. Paper: arXiv 2405.11143.

## When to use this skill

Reach for OpenRLHF when **all** of these hold:
- Training large models (7B-70B+) with RL, not just preference tuning.
- You have a multi-GPU / multi-node cluster and want Ray scheduling.
- You want vLLM-accelerated generation and the Hybrid Engine (GPU colocation).
- You need PPO, GRPO, RLOO, REINFORCE++(-baseline), or DPO in one framework.

Pick a sibling skill instead when:
- **trl-fine-tuning** — single-node or simpler HF-native SFT/DPO/PPO/GRPO.
- **grpo-rl-training** — GRPO specifically on TRL (reward-fn design, LoRA/Unsloth).
- **simpo** — reference-free preference optimization (no reward model, no DPO ref).
- **slime** / **miles** — Megatron-LM + SGLang RL for GLM/Qwen3/DeepSeek (miles = FP8/MoE prod fork).
- **torchforge** — PyTorch-native agentic RL (Monarch + TorchTitan).
- **verl** — Volcano Engine RL at the largest (100B-671B) FSDP/Megatron scale.

## Algorithm selection

| Algorithm      | When                                         | Estimator flag                          |
|----------------|----------------------------------------------|-----------------------------------------|
| PPO            | Max control, complex rewards (needs critic)  | *(default)*                             |
| GRPO           | Memory-efficient, no critic model            | `--advantage_estimator group_norm`      |
| RLOO           | Per-token KL, critic-free                     | `--advantage_estimator rloo`            |
| REINFORCE++    | More stable than GRPO, faster than PPO        | `--advantage_estimator reinforce`       |
| DPO            | Simplest, no reward model, no rollouts        | `openrlhf.cli.train_dpo`                |

## Quick start

```bash
pip install openrlhf[vllm]          # inside the NVIDIA PyTorch 25.02+ container

# PPO with the Hybrid Engine (8 GPUs, all models colocated)
ray start --head --node-ip-address 0.0.0.0 --num-gpus 8
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json='{"working_dir": "/openrlhf"}' \
  -- python3 -m openrlhf.cli.train_ppo_ray \
  --pretrain OpenRLHF/Llama-3-8b-sft-mixture \
  --reward_pretrain OpenRLHF/Llama-3-8b-rm-700k \
  --save_path ./output/llama3-8b-rlhf \
  --colocate_all_models --vllm_num_engines 4 --vllm_tensor_parallel_size 2 \
  --zero_stage 3 --bf16 --vllm_enable_sleep --deepspeed_enable_sleep
# GRPO: add  --advantage_estimator group_norm  and drop the critic allocation.
```

Full copy-paste recipes (reward model, PPO, GRPO, DPO), troubleshooting, and the
stable-vs-main flag-namespace mapping: **[references/training-recipes.md](references/training-recipes.md)**.

> Version note: OpenRLHF's `main` refactored the CLI to nested flags
> (`--algo.advantage.estimator`, `--train.colocate_all`, `--train.async_enable`,
> `--train.agent_func_path`). The recipes above use the flat-flag form from
> released versions — see the mapping table in the recipes reference.

## Deeper references

- **[references/hybrid-engine.md](references/hybrid-engine.md)** — vLLM/DeepSpeed sleep mode, GPU colocation, node allocation.
- **[references/algorithm-comparison.md](references/algorithm-comparison.md)** — PPO vs GRPO vs RLOO vs REINFORCE++ benchmarks and hyperparameters.
- **[references/multi-node-training.md](references/multi-node-training.md)** — Ray cluster setup and fault tolerance.
- **[references/custom-rewards.md](references/custom-rewards.md)** — reinforced fine-tuning, async/agent RLHF (`--train.agent_func_path`).

## Hardware

- GPU: NVIDIA A100/H100. 7B ≈ 8x A100 40GB (Hybrid Engine); 70B ≈ 48x A100 80GB
  (vLLM:Actor:Critic = 1:1:1). Multi-node: InfiniBand recommended.
- Container: NVIDIA PyTorch 25.02+. ~2x faster than DeepSpeedChat via vLLM +
  Hybrid Engine GPU sharing.

## Resources

- Repo/docs: https://github.com/OpenRLHF/OpenRLHF
- Examples: https://github.com/OpenRLHF/OpenRLHF/tree/main/examples/scripts
- Paper: https://arxiv.org/abs/2405.11143
