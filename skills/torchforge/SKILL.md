---
name: torchforge
description: Router for PyTorch-native agentic RL with torchforge, Meta's library that separates infrastructure (Monarch + TorchTitan + vLLM) from algorithms (GRPO/DAPO/CISPO/GSPO/SAPO). Use when post-training LLMs with RL and you want clean algorithm/infra separation, no-Ray PyTorch-native abstractions, fast algorithm experimentation, or scalable multi-GPU training. Do NOT use for production-hardened RLHF (prefer verl or miles), Megatron-native training (prefer slime), supervised fine-tuning without RL, or non-PyTorch stacks. Routes to references/ for workflows, full API, and troubleshooting.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Reinforcement Learning, PyTorch, GRPO, SFT, Monarch, TorchTitan, Meta]
dependencies: [torch>=2.9.0, torchtitan>=0.2.0, vllm, monarch]
---

# torchforge: PyTorch-Native Agentic RL Library

torchforge is Meta's PyTorch-native RL library that separates infrastructure
concerns from algorithm concerns. It lets you focus on RL algorithms while it
handles distributed training, inference, and weight sync automatically. Both
torchforge and Monarch are experimental; APIs may change.

This file is a router. Detailed content lives in `references/`:

| Need | Reference |
|------|-----------|
| Step-by-step recipes (GRPO math, custom loss, multi-GPU, batch format) | `references/workflows.md` |
| Classes, methods, config schema, install, async patterns | `references/api-reference.md` |
| Errors: OOM, GPU shortage, weight sync, policy collapse, deadlocks | `references/troubleshooting.md` |

## When to Use

Choose torchforge when you need:
- Clean separation between RL algorithms and infrastructure
- PyTorch-native abstractions (no Ray dependency)
- Easy algorithm experimentation (GRPO, DAPO, SAPO in ~100 lines)
- Scalable training via the Monarch actor system
- TorchTitan integration for model parallelism

Use a sibling skill instead when:
- You need production-ready stability -> **verl** or **miles**
- You want Megatron-native training -> **slime**
- You are doing plain SFT without RL, or a non-PyTorch stack

## Key Components

- **Algorithm isolation**: implement RL algorithms without touching infra
- **Scalability**: single GPU to thousands via Monarch
- **Stack**: TorchTitan (training), vLLM (inference), TorchStore (weight sync)
- **Built-in losses**: GRPO, DAPO, CISPO, GSPO, SAPO

Service layers: Application (your rewards/loss/sampling) -> Forge API
(`ForgeActor`, `Service`, async interfaces) -> Distributed Services on Monarch
(`TitanTrainer` FSDP, `Generator` vLLM, `ReferenceModel` KL baseline, reward
actors). See `references/api-reference.md` for the full diagram and signatures.

## Install

```bash
conda create -n forge python=3.12 && conda activate forge
./scripts/install.sh          # ./scripts/install_rocm.sh on AMD
python -c "import torch, forge, vllm; print('OK')"
```

## Quick Start

```bash
# SFT (2+ GPUs)
python -m apps.sft.main --config apps/sft/llama3_8b.yaml
# GRPO (3+ GPUs)
python -m apps.grpo.main --config apps/grpo/qwen3_1_7b.yaml
```

For configuring your own GRPO run, custom losses, or scaling out, follow
`references/workflows.md`.

## Resources

- Docs: https://meta-pytorch.org/torchforge
- GitHub: https://github.com/meta-pytorch/torchforge
- Blog: https://pytorch.org/blog/introducing-torchforge/
- TorchTitan: https://github.com/pytorch/torchtitan | Monarch: https://github.com/meta-pytorch/monarch
- Discord: https://discord.gg/YsTYBh6PD9
