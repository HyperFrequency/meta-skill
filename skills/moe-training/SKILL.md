---
name: moe-training
description: Train and serve Mixture of Experts (MoE) models with DeepSpeed, Megatron-DeepSpeed, or HuggingFace Transformers. Use when scaling model capacity without proportional compute (sparse top-k activation, ~5x training cost reduction vs dense), implementing sparse architectures like Mixtral 8x7B, DeepSeek-V3, or Switch Transformers, configuring routing/load-balancing/expert-parallelism, or optimizing MoE inference (vLLM, FP8/INT8, expert parallelism). Not for dense model training (use standard transformers/pytorch-lightning), generic distributed data-parallel training without experts, fine-tuning an existing dense checkpoint, or non-LLM/quant-strategy work. Routes to references/ for architectures, training configs, and inference tuning.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Emerging Techniques, MoE, Mixture Of Experts, Sparse Models, DeepSpeed, Expert Parallelism, Mixtral, DeepSeek, Routing, Load Balancing, Efficient Training]
dependencies: [deepspeed, transformers, torch, accelerate]
---

# MoE Training: Mixture of Experts

A Mixture of Experts model replaces dense FFN layers with many parallel expert FFNs plus a learned router that activates only the top-k experts per token. This decouples total parameter count (capacity) from active parameters (compute): Mixtral 8x7B has 47B total params but activates only ~13B per token.

This file is a navigator. Deep content lives in `references/`. Read the reference that matches your task rather than loading everything.

## When to Use

- Scaling model capacity without a proportional compute increase (~5x training cost reduction vs an equivalent dense model)
- Implementing a SOTA sparse architecture: Mixtral 8x7B (Mistral), DeepSeek-V3, Switch Transformers / GLaM (Google), NLLB-MoE (Meta)
- Configuring routing (top-1 / top-2 / expert-choice), load balancing, capacity factors, or expert parallelism across GPUs
- Optimizing MoE inference and serving (vLLM expert parallelism, FP8/INT8 quantization, expert pruning)

## When NOT to Use

- Training or fine-tuning a **dense** model — use the standard `transformers` / `pytorch-lightning` paths; MoE adds routing/balancing complexity with no benefit
- Plain distributed data-parallel scale-up without experts — that is a DeepSpeed/ZeRO or FSDP concern, not MoE
- Small datasets where many experts will overfit — see expert-count guidance in `references/training.md`
- Non-LLM or trading-strategy work

## Installation

```bash
# DeepSpeed with MoE support (large-scale training)
pip install "deepspeed>=0.6.0"
git clone https://github.com/microsoft/Megatron-DeepSpeed   # training scripts

# Or HuggingFace path (loading/fine-tuning released MoE checkpoints)
pip install transformers accelerate
```

## Core Concepts (at a glance)

- **Experts**: parallel FFN networks (typically 8-128). Total params scale with expert count.
- **Router / gate**: a learned `Linear(hidden, num_experts)` that scores experts per token.
- **Top-k routing**: activate only k experts per token (k=1 Switch, k=2 Mixtral). Active compute scales with k, not total expert count.
- **Load balancing**: an auxiliary loss (and optional router z-loss for stability) keeps token assignment roughly uniform across experts so capacity is not wasted.
- **Capacity factor**: per-expert token budget = `(tokens_per_batch / num_experts) * capacity_factor`. Tokens over budget are dropped (training) or buffered (eval).
- **Expert parallelism**: experts are sharded across GPUs (`expert_parallel_size`), distinct from tensor/data parallelism.

Minimal top-2 routing core (full, production-grade implementations are in `references/architectures.md`):

```python
router_logits = gate(hidden)                                  # (tokens, num_experts)
weights = torch.softmax(router_logits, dim=-1)
weights, experts = torch.topk(weights, k=2, dim=-1)           # top-2 selection
weights = weights / weights.sum(dim=-1, keepdim=True)         # renormalize
# dispatch each token to its 2 experts, combine outputs weighted by `weights`
```

## Where to Go Next

| Your task | Read |
|-----------|------|
| Understand a specific model (Mixtral 8x7B, DeepSeek-V3 / MLA / shared-expert, Switch top-1), pick a routing pattern, or see full `MoEBlock` code | `references/architectures.md` |
| Set up DeepSpeed/Megatron MoE training, config JSON, CLI flags, LR / capacity-factor / loss-coeff tuning, PR-MoE, MoS distillation, monitoring, troubleshooting | `references/training.md` |
| Optimize inference/serving: vLLM expert parallelism, FP8/INT8 quantization, expert pruning, speculative decoding, deployment configs, benchmarks | `references/inference.md` |

## Resources

- DeepSpeed MoE tutorial: https://www.deepspeed.ai/tutorials/mixture-of-experts-nlg/
- Mixtral paper: https://arxiv.org/abs/2401.04088
- Switch Transformers: https://arxiv.org/abs/2101.03961
- HuggingFace MoE guide: https://huggingface.co/blog/moe
- NVIDIA MoE in LLM architectures: https://developer.nvidia.com/blog/applying-mixture-of-experts-in-llm-architectures/
