---
name: constitutional-ai
description: Anthropic's method (arXiv 2212.08073) for training harmless AI via self-improvement. Two phases - supervised self-critique/revision, then RLAIF (RL from AI Feedback). Use WHEN you want safety alignment / harmlessness without human harm-labels, explainable refusals, or scalable preference data from a written constitution; implemented on transformers + trl (SFTTrainer, RewardTrainer, PPOTrainer). Do NOT use WHEN you have or need human-validated preferences (use RLHF/PPO or DPO/SimPO directly), you only need runtime content filtering (NeMo Guardrails) or a pre-trained moderation classifier (LlamaGuard), or you want general instruction-tuning rather than harmlessness.
version: 1.0.3
author: Orchestra Research
license: MIT
tags: [Safety Alignment, Constitutional AI, RLAIF, Self-Critique, Harmlessness, Anthropic, AI Safety, RL From AI Feedback, Claude]
dependencies: [transformers, torch, trl]
---

# Constitutional AI - Harmlessness from AI Feedback

## Quick start

Constitutional AI (CAI) trains models to be harmless through self-critique and AI
feedback, without human labels for harmful outputs. Models learn to critique and
revise their own responses against a "constitution" (a set of principles).

**Two phases**:
1. **Supervised Learning (SL)**: self-critique + revision, then SFT on revisions.
2. **Reinforcement Learning (RL)**: RLAIF — AI-generated preferences train a reward
   model, then PPO optimizes the policy against it.

**Constitution example** (principles the model self-critiques against): choose the
most helpful, honest, and harmless response; avoid toxic, racist, or sexist content;
prefer explaining objections over refusing; favor thoughtful, nuanced answers. Full
principle-design guidance is in
[references/constitution-design.md](references/constitution-design.md).

## Workflows

Full runnable code (transformers pipelines + trl trainers) lives in
[references/training-workflows.md](references/training-workflows.md). Summary:

**SL phase (self-critique + revision)** —
1. Generate initial responses to red-team prompts (`transformers.pipeline`).
2. Self-critique each against the constitution.
3. Revise based on the critique (optionally iterate several rounds).
4. SFT on the `(prompt, revised_response)` pairs (`trl.SFTTrainer`).

**RL phase (RLAIF)** —
1. Sample 2+ responses per prompt (`do_sample=True`, `temperature≈0.8`).
2. Get AI preferences A-vs-B from the constitution — no human labels.
3. Train a reward model on chosen/rejected pairs (`trl.RewardTrainer` + `RewardConfig`).
4. Optimize the policy with `trl.PPOTrainer` + `PPOConfig` against that reward
   (`learning_rate≈1e-6`, `kl_coef≈0.05`).

**Chain-of-thought critique** — score each principle (helpful / honest / harmless /
non-toxic) step-by-step before suggesting a revision, for reasoning transparency. See
the CoT section of [references/training-workflows.md](references/training-workflows.md).

## When to use vs alternatives

**Use Constitutional AI when**: you want safety alignment without human harm-labels,
explainable decisions, fewer evasive refusals, a clear principle set, and scalable
training. RLAIF gives AI-generated preferences (cheap, scalable); RLHF gives human
preferences (more accurate, expensive).

**Use alternatives instead**:
- **RLHF (PPO)** — you need human-validated safety signals.
- **DPO / SimPO** — you already hold a human preference dataset.
- **NeMo Guardrails** — you need runtime content filtering, not training.
- **LlamaGuard** — you need a pre-trained moderation classifier.

## Common issues

All fixes (with code) are in the Troubleshooting section of
[references/training-workflows.md](references/training-workflows.md):
- **Refuses too much (evasive)** — add a "engage thoughtfully, don't refuse" principle.
- **Weak self-critiques** — strengthen the critique prompt ("identify ANY issue").
- **Revisions don't improve** — iterate critique→revision multiple rounds.
- **Noisy RLAIF preferences** — ensemble multiple AI evaluators, majority-vote.

## Advanced topics

- **Constitution design**: [references/constitution-design.md](references/constitution-design.md)
  — principle selection, helpfulness↔harmlessness trade-offs, domain constitutions.
- **RLAIF vs RLHF**: [references/rlaif-comparison.md](references/rlaif-comparison.md)
  — performance, cost analysis, when to prefer AI vs human feedback.

## Hardware requirements

- **GPU**: NVIDIA A100/H100; BF16 mixed precision.
- **VRAM**: SL phase (7B) ≈ 1× A100 40GB; RL phase (7B) ≈ 2× A100 40GB (policy + reward).
- **Compute**: SL ≈ standard SFT; RL ≈ PPO (higher than DPO); plus extra inference for
  critique/preference generation. Single-node suffices for most cases.

## Resources

- Paper: https://arxiv.org/abs/2212.08073 (Dec 2022)
- Anthropic blog: https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback
- Implementation: TRL (`PPOTrainer` + `RewardTrainer`)
- Claude uses Constitutional AI for its safety system.
