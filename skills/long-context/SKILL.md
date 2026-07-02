---
name: long-context
description: Extend context windows of transformer models using RoPE, YaRN, ALiBi, and position interpolation. Use when processing long documents (32k-128k+ tokens), extending pre-trained models (LLaMA, Mistral, etc.) beyond their original context limit, or implementing efficient positional encodings (rotary embeddings, attention biases, interpolation/extrapolation strategies). NOT for short-context work (<8k) where the base model already fits, RAG/retrieval used as a substitute for true context extension, KV-cache or memory-only inference optimizations (use a quantization/serving skill), or non-transformer architectures (SSM/Mamba, RNNs).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Emerging Techniques, Long Context, RoPE, YaRN, ALiBi, Position Interpolation, Extended Context, Rotary Embeddings, Attention Bias, Context Extension, Positional Encoding]
dependencies: [transformers, torch, flash-attn]
---

# Long Context: Extending Transformer Context Windows

Router skill for choosing and applying a context-extension method. Conceptual
summaries and the decision table live below; full implementations, math, and
runnable scripts live in `references/` (linked per topic).

## When to Use This Skill

- **Process long documents** (32k, 64k, 128k+ tokens) with transformer models
- **Extend context windows** of pre-trained models (LLaMA, Mistral, etc.)
- **Implement efficient positional encodings** (RoPE, ALiBi)
- **Train models** with length-extrapolation capabilities
- **Fine-tune** existing models for longer contexts with minimal compute

## When NOT to Use This Skill

- The base model's native context already fits the workload (<8k) — no extension needed
- You want **RAG/retrieval** to feed a fixed window instead of truly extending it
- The goal is **KV-cache / memory / throughput** optimization (paged attention,
  quantization, serving) rather than position-encoding extension
- The model is **non-transformer** (SSM/Mamba, RNN) — these use different
  long-sequence mechanisms

## Key Techniques (one-line summaries)

- **RoPE** (Rotary Position Embeddings) — encodes position via rotation; provides
  relative-position dependency and a base for most extension methods.
- **YaRN** — NTK-aware interpolation + attention temperature scaling; most
  data-efficient way to extend an existing RoPE model (to 128k).
- **ALiBi** — no positional embeddings; applies a per-head linear distance penalty
  to attention scores. Lowest memory, strong extrapolation, best trained from scratch.
- **Position Interpolation** — linearly down-scales position indices to stay within
  the trained range; fastest extension (~1k fine-tune steps) but no extrapolation.

**Papers**: RoFormer (arXiv 2104.09864), YaRN (arXiv 2309.00071), ALiBi (arXiv 2108.12409), Position Interpolation (arXiv 2306.15595)

## Installation

```bash
# HuggingFace Transformers (includes RoPE, YaRN support)
pip install transformers torch
pip install einops                  # tensor ops for custom impls
pip install rotary-embedding-torch  # standalone RoPE (optional)
pip install flash-attn --no-build-isolation  # optional, faster long attention
```

## Choosing a Method

| Method | Max Context | Training Needed | Memory | Extrapolation | Best For |
|--------|-------------|-----------------|--------|---------------|----------|
| **RoPE** | 8k-32k | Full pre-training | Moderate | Good | New models |
| **YaRN** | 32k-128k | Minimal (10× efficient) | Moderate | Excellent | Extending existing RoPE models |
| **ALiBi** | Unlimited | Full pre-training | Low (-11%) | Excellent | Training from scratch |
| **Position Interpolation** | 32k+ | Minimal (~1k steps) | Moderate | Poor (by design) | Quick extension |

Quick decision:
- New model from scratch → **ALiBi**
- Extend an existing RoPE model with best quality → **YaRN**
- Quick extension, minimal compute → **Position Interpolation**
- Moderate extension, simplest setup → **Linear RoPE scaling** (`rope_scaling={"type":"linear"}`)

Two pitfalls worth flagging up front: (1) applying `rope_scaling` without any
fine-tuning degrades quality badly — always fine-tune after scaling; (2) jump
scaling (e.g. 8k→128k in one go) is unstable — scale incrementally.

## References

Deep content lives here — read the matching file before implementing:

- [`references/rope.md`](references/rope.md) — RoPE theory, math derivation, GPT-J
  vs GPT-NeoX styles, and scaling variants (linear, NTK-aware, dynamic, YaRN);
  HuggingFace `rope_scaling` config and a custom implementation.
- [`references/extension_methods.md`](references/extension_methods.md) — full
  YaRN / ALiBi / Position Interpolation implementations, parameters, slope
  derivations, and a method comparison with use-case recommendations.
- [`references/fine_tuning.md`](references/fine_tuning.md) — data preparation
  (PG-19, arXiv, etc.), training configs for Position Interpolation and YaRN,
  evaluation (perplexity, passkey retrieval, long-doc QA), and deployment.

## Resources

- **RoPE Paper (RoFormer)**: https://arxiv.org/abs/2104.09864
- **YaRN Paper**: https://arxiv.org/abs/2309.00071
- **ALiBi Paper (Train Short, Test Long)**: https://arxiv.org/abs/2108.12409
- **Position Interpolation**: https://arxiv.org/abs/2306.15595
- **HuggingFace RoPE Utils**: https://github.com/huggingface/transformers/blob/main/src/transformers/modeling_rope_utils.py
- **YaRN Implementation**: https://github.com/jquesnelle/yarn
- **Together AI Blog (LLaMA-2-7B-32K)**: https://www.together.ai/blog/llama-2-7b-32k
