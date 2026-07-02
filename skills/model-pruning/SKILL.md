---
name: model-pruning
description: Reduce LLM size and accelerate inference using pruning techniques like Wanda and SparseGPT. Use when compressing models without retraining, achieving 50% sparsity with minimal accuracy loss, or enabling faster inference via N:M structured sparsity on hardware accelerators. Covers unstructured, structured, N:M, magnitude, and one-shot pruning. Do NOT use for quantization / bit-width reduction, knowledge-distillation (training a smaller student), MoE routing, or speculative decoding — use the sibling skills for those; and do NOT use unstructured pruning when you need real wall-clock speedup (only N:M and structured pruning yield GPU speedups; unstructured only saves storage/memory).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Emerging Techniques, Model Pruning, Wanda, SparseGPT, Sparsity, Model Compression, N:M Sparsity, One-Shot Pruning, Structured Pruning, Unstructured Pruning, Fast Inference]
dependencies: [transformers, torch]
---

# Model Pruning: Compressing LLMs

A router for one-shot and iterative weight pruning of LLMs. Deep, runnable code lives
in `references/`; this file is the map.

## When to Use This Skill

- **Reduce model size** by 40-60% with <1% accuracy loss
- **Accelerate inference** using hardware-friendly N:M sparsity (2-4× speedup)
- **Deploy on constrained hardware** (mobile, edge devices)
- **Compress without retraining** using one-shot methods (Wanda, SparseGPT)
- **Reduce serving memory footprint**

**When NOT to use**: for bit-width reduction use quantization; to train a smaller
model use `../knowledge-distillation`; for expert sparsity use `../moe-training`;
for decode speedup without compression use `../speculative-decoding`. Unstructured
pruning saves memory but gives **no** GPU wall-clock speedup — choose N:M/structured
if latency is the goal.

**Key techniques**: Wanda (|weight| × activation), SparseGPT (second-order /
Hessian), magnitude (baseline), structured (neurons/heads/layers), N:M semi-structured.

**Papers**: Wanda — ICLR 2024, arXiv 2306.11695; SparseGPT — ICML 2023, arXiv 2301.00774.

## Installation

```bash
git clone https://github.com/locuslab/wanda            # Wanda
git clone https://github.com/IST-DASLab/sparsegpt      # SparseGPT
pip install torch transformers accelerate datasets lm-eval
```

## Method Selection (quick router)

| Goal | Use | Reference |
|------|-----|-----------|
| One-shot, fastest, no retraining | **Wanda** | `references/wanda.md`, `references/implementations.md` |
| Best one-shot quality | **SparseGPT** | `references/implementations.md` |
| GPU wall-clock speedup | **N:M (2:4 / 4:8)** | `references/implementations.md` |
| High sparsity (>70%) with budget | **Iterative prune + fine-tune** | `references/implementations.md` |
| Baseline / sanity check | **Magnitude** | `references/implementations.md` |

Full runnable code for every row — Wanda, SparseGPT, N:M, gradual/layer-wise/iterative
strategies, the end-to-end production pipeline, and lm-eval evaluation — is in
**[`references/implementations.md`](references/implementations.md)**.
Wanda's criterion and theory are in **[`references/wanda.md`](references/wanda.md)**.

## Core Concepts

### Pruning criteria
- **Magnitude** (baseline): importance = `|weight|`; prune smallest.
- **Wanda**: importance = `|weight| × ‖activation‖` — accounts for how weights are
  actually used; no backprop, compared per output row.
- **SparseGPT**: second-order, `weight² / diag(Hessian⁻¹)` with layer-wise
  reconstruction; most accurate, more compute.

### Structured vs unstructured
- **Unstructured** (per-weight): highest quality, irregular sparsity → **no** speedup.
- **Structured** (neurons/heads/layers): hardware-friendly, more accuracy loss.
- **N:M semi-structured** (keep N of every M, e.g. 2:4): ~2× speedup on NVIDIA
  Ampere+ sparse tensor cores with minimal accuracy loss.

### Sparsity selection
- `0.3` conservative (<0.5% loss) · `0.5` balanced/recommended (~1% loss) ·
  `0.7` aggressive (2-5% loss) · `0.9` extreme (significant degradation, needs iterative).

### Common pitfalls
- Don't prune without calibration data (Wanda/SparseGPT need activation stats).
- Don't jump to very high sparsity in one shot — go gradual/iterative.
- Don't expect speedup from unstructured sparsity — only N:M/structured deliver it.

## Performance Comparison

Pruning methods at 50% sparsity (LLaMA-7B):

| Method | Accuracy Loss | Speed | Memory | Retraining |
|--------|---------------|-------|--------|------------|
| **Magnitude** | -2.5% | 1.0× | -50% | No |
| **Wanda** | -0.8% | 1.0× | -50% | No |
| **SparseGPT** | -0.4% | 1.0× | -50% | No |
| **N:M (2:4)** | -1.0% | 2.0× | -50% | No |
| **Structured** | -3.0% | 2.0× | -50% | No |

Source: Wanda (ICLR 2024) and SparseGPT papers.

## Resources

- Wanda paper (ICLR 2024): https://arxiv.org/abs/2306.11695
- Wanda GitHub: https://github.com/locuslab/wanda
- SparseGPT paper: https://arxiv.org/abs/2301.00774
- SparseGPT GitHub: https://github.com/IST-DASLab/sparsegpt
- NVIDIA sparse tensor cores: https://developer.nvidia.com/blog/accelerating-inference-with-sparsity-using-ampere-and-tensorrt/
</content>
