---
name: ml-training-recipes
version: 1.0.0
description: Battle-tested PyTorch training recipes across domains — LLMs, vision, diffusion, medical imaging, protein/drug discovery, spatial omics, genomics. Covers training loops, optimizer selection (AdamW, Muon), LR scheduling, mixed precision, scaling laws, debugging, and systematic experimentation. Use when training or fine-tuning neural networks in raw PyTorch, debugging loss spikes/NaNs/OOM, choosing an architecture for a dataset, or optimizing GPU throughput (MFU). Not for classical/tabular model selection (use scikit-learn), high-level Lightning training scaffolds (use pytorch-lightning), HuggingFace model/tokenizer/Trainer APIs (use transformers), or reinforcement-learning training (use stable-baselines3 or pufferlib).
author: dailycafi
license: MIT
tags: [PyTorch, Training, Optimization, LLM, Vision, Diffusion, Biomedical, Muon, AdamW, Debugging]
dependencies: [torch>=2.0.0]
---

# ML Training Recipes

Battle-tested patterns for PyTorch training across domains. Drawn from production codebases
(Karpathy's autoresearch/nanochat, torchvision, HuggingFace) and modern training practice.

This file is a **router**: it points to the reference that holds the detail you need. Read the
matching reference before writing training code — do not work from this summary alone.

## Reference files (read when needed)

- `references/architecture.md` — Transformer/LLM architecture code: RMSNorm, RoPE, Flash Attention, GQA, SwiGLU, soft capping, weight init
- `references/optimizers.md` — Muon (orthogonalization, NorMuon), AdamW best practices, hybrid Muon+AdamW, per-group LR, weight-decay & momentum schedules, compiled steps
- `references/training-loop.md` — The training loop, LR scheduling (time-based/cosine/WSD), mixed precision & `torch.compile`, memory/MFU/OOM tuning
- `references/scaling-and-selection.md` — Scaling laws (Chinchilla), architecture decision trees, data-scale thresholds, compute/memory planning, instability at scale, DGX Spark / bandwidth-limited GPUs
- `references/domain-specific.md` — Vision augmentation, diffusion/flow-matching, EMA, contrastive/SSL, fine-tuning/LoRA, DDP/FSDP, checkpointing, data loading
- `references/biomedical.md` — Drug discovery, protein/structure models, medical imaging (nnU-Net), genomics, single-cell omics, clinical NLP, EHR/survival
- `references/debugging-and-recipes.md` — Debugging checklists (NaN, low MFU, plateaus, silent failures), hyperparameter search order, the 2025 default recipe, eval metrics by domain
- `references/experiment-loop.md` — Autonomous experiment loop (autoresearch keep/discard/revert), tokenizer training, data prep

---

## Quick orientation

Match your task to the reference that holds the real guidance, then read it before coding.

- **Choosing a model for a dataset?** Match model to data *type* and *scale*; the recipe matters more
  than the architecture at equal compute → `references/scaling-and-selection.md` (cross-domain),
  `references/biomedical.md` (bio domains).
- **Planning compute / token budget?** Scaling laws, FLOP/token math, repetition limits →
  `references/scaling-and-selection.md`.
- **Writing the training loop?** Autocast, grad accumulation, clipping, LR schedules, divergence
  fast-fail → `references/training-loop.md`.
- **Configuring optimizers?** Per-param-group Muon/AdamW split, eps/weight-decay rules →
  `references/optimizers.md`.
- **Hitting OOM or low throughput?** OOM-reduction ladder and MFU targets → `references/training-loop.md`.
- **Loss exploding, NaN, plateau, or silent bug?** Symptom-keyed checklists → `references/debugging-and-recipes.md`.
- **Running many experiments?** Tracking, keep/discard criterion, fixed-budget comparison →
  `references/experiment-loop.md`.

---

## Boundaries & related skills

- **In scope**: raw-PyTorch training mechanics, optimizer/scheduler/precision tuning, architecture
  selection by data scale, GPU memory/throughput, training debugging, domain-specific (vision,
  diffusion, LLM, biomedical) recipes.
- **Out of scope / use instead**:
  - High-level training scaffolds, callbacks, multi-GPU boilerplate → `pytorch-lightning`
  - HuggingFace model/tokenizer/`Trainer` APIs and pretrained checkpoints → `transformers`
  - Classical / tabular model selection, preprocessing, metrics → `scikit-learn`
  - Reinforcement-learning training → `stable-baselines3`, `pufferlib`
  - Model explainability after training → `shap`
