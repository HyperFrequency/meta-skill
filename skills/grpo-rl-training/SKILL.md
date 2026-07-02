---
name: grpo-rl-training
description: Expert guidance for GRPO (Group Relative Policy Optimization) RL fine-tuning with HuggingFace TRL — reward function design, GRPOConfig/GRPOTrainer setup, LoRA/Unsloth/vLLM acceleration, training-metric monitoring, and deployment. Use when fine-tuning a causal LM with custom reward functions for verifiable tasks (math, code), strict output formats (XML/JSON), or reasoning, without preference pairs or a separate reward model. Do NOT use for plain supervised fine-tuning (use SFT/trl-fine-tuning), preference-pair alignment with existing pairs (use DPO/simpo), or large-scale distributed RL frameworks (use verl/openrlhf/slime/torchforge).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Post-Training, Reinforcement Learning, GRPO, TRL, RLHF, Reward Modeling, Reasoning, DPO, PPO, Structured Output]
dependencies: [transformers>=4.47.0, trl>=0.14.0, datasets>=3.2.0, peft>=0.14.0, torch]
---

# GRPO/RL Training with TRL

Router for implementing Group Relative Policy Optimization (GRPO) with HuggingFace TRL.
GRPO generates multiple completions per prompt, scores them with custom reward functions,
and updates the policy to favor higher-rewarded completions *relative to their group* — no
separate reward model required.

## When to Use This Skill

Use GRPO training when you need to:
- **Enforce specific output formats** (XML tags, JSON, structured reasoning).
- **Teach verifiable tasks** with objective correctness metrics (math, coding, fact-checking).
- **Improve reasoning** by rewarding chain-of-thought patterns.
- **Align to domain-specific behaviors** without labeled preference data.
- **Optimize multiple objectives** simultaneously (format + correctness + style).

**Do NOT use GRPO for:**
- Plain supervised fine-tuning → use SFT (sibling `trl-fine-tuning`).
- Tasks without a clear, programmable reward signal.
- You already have high-quality preference pairs → use DPO (sibling `simpo`).
- Large-scale / multi-node distributed RL → siblings `verl`, `openrlhf`, `slime`, `torchforge`, `miles`.

## Core Algorithm (the one thing to internalize)

For each prompt: generate N completions (group size 4-16) → compute a reward per completion →
increase the probability of above-average completions and decrease below-average ones *within
the group*. Differs from PPO: no separate reward/value model, more sample-efficient, simpler to
debug. Counterintuitively, **training loss INCREASES** — it tracks KL from the initial policy, so
watch reward metrics, not loss (see `references/training-insights.md`).

## Start Here: Bundled Code

| File | Use for |
|------|---------|
| [`templates/basic_grpo_training.py`](templates/basic_grpo_training.py) | Copy as your starting training script (model + LoRA + 3 rewards + GRPOConfig). |
| [`examples/reward_functions_library.py`](examples/reward_functions_library.py) | Pick/adapt reward functions (20+: correctness, format, length, style, combined). |

## Reference Map (read the page you need, not all of them)

| Topic | Reference |
|-------|-----------|
| Reward function philosophy, types, templates, dataset prep | [`references/reward-design.md`](references/reward-design.md) |
| `GRPOConfig` (small-GPU & large-GPU), hyperparameter tuning, model setup (Transformers/PEFT, Unsloth, vLLM) | [`references/training-config.md`](references/training-config.md) |
| Loss behavior, reward/KL metrics, pitfalls, debugging, checklists | [`references/training-insights.md`](references/training-insights.md) |
| Multi-stage training, adaptive reward scaling, custom datasets, deployment/inference, DAPO variant | [`references/advanced-patterns.md`](references/advanced-patterns.md) |

## Recommended Workflow

1. Prepare a chat-format dataset (prompts as `List[Dict]`; carry ground truth as an extra column).
   See `references/reward-design.md`.
2. Pick/write reward functions; **test each in isolation** before training.
   Use `examples/reward_functions_library.py`.
3. Configure `GRPOConfig` + load the model from `templates/basic_grpo_training.py`;
   tune per `references/training-config.md`.
4. Train, then **monitor `reward` / `reward_std` / `kl` (not loss)** per `references/training-insights.md`.
5. Merge LoRA and deploy per `references/advanced-patterns.md`.

**Critical reminders:** compose 3-5 reward functions; start small (`num_generations=4`) and scale;
test rewards before training; save checkpoints every ~100 steps; monitor reward metrics, not loss.

## References & Resources
- TRL GRPO Trainer: https://huggingface.co/docs/trl/grpo_trainer
- Open R1 (reference implementation): https://github.com/huggingface/open-r1
- DeepSeek R1 paper: https://arxiv.org/abs/2501.12948
- Unsloth docs: https://docs.unsloth.ai/
