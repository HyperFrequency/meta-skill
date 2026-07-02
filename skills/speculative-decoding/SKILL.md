---
name: speculative-decoding
description: Accelerate LLM inference using speculative decoding (small draft model verified by a large target), Medusa multiple decoding heads, and lookahead (Jacobi) decoding — all lossless. Use when reducing token-generation latency for real-time apps (chatbots, code gen) at low batch sizes, serving large models on limited compute, or seeking 1.5-3.6× speedup without changing model quality or architecture. Covers draft-model selection, tree-based attention, Jacobi iteration, hyperparameter tuning, and Transformers/vLLM deployment. Do NOT use when the model is already small (draft overhead dominates), when the workload is throughput-bound at large batch sizes (gains shrink as compute saturates), when the goal is lower memory/cost rather than lower latency (use quantization or distillation instead), or when no same-tokenizer draft model exists and Medusa/Lookahead are not set up.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Emerging Techniques, Speculative Decoding, Medusa, Lookahead Decoding, Fast Inference, Draft Models, Tree Attention, Parallel Generation, Latency Reduction, Inference Optimization]
dependencies: [transformers, torch]
---

# Speculative Decoding: Accelerating LLM Inference

This skill is a router. Quick starts and the method-selection table live here;
deep per-method detail (algorithms, training, hyperparameters, deployment) lives
in `references/`.

## When to Use This Skill

Use Speculative Decoding when you need to:
- **Speed up inference** by 1.5-3.6× with **no quality loss**
- **Reduce latency** for real-time applications (chatbots, code generation)
- **Serve large models** on limited hardware at low batch sizes
- **Generate faster** without changing the model architecture

### When NOT to Use
- The model is already small (e.g. <7B): draft/verification overhead can erase gains — measure first.
- The workload is **throughput-bound at large batch sizes**: speculative gains shrink as compute saturates; these methods help latency most at low batch sizes.
- The goal is lower **memory or cost**, not latency: use quantization or distillation instead.
- For draft-model speculative specifically: no smaller model with the **same tokenizer** is available — use Medusa or Lookahead, which need no draft model.

**Key techniques**: draft-model speculative decoding, Medusa (multiple heads), Lookahead Decoding (Jacobi iteration).

**Papers**: Speculative Decoding (Leviathan et al., ICML 2023; Chen et al., 2023), Medusa (arXiv 2401.10774), Lookahead Decoding (ICML 2024), Survey (arXiv 2401.07851).

## Installation

```bash
# Standard speculative decoding (Transformers assisted generation, 4.36+)
pip install transformers accelerate

# Medusa (multiple decoding heads)
git clone https://github.com/FasterDecoding/Medusa && cd Medusa && pip install -e .

# Lookahead Decoding
git clone https://github.com/hao-ai-lab/LookaheadDecoding && cd LookaheadDecoding && pip install -e .

# Optional: vLLM with speculative decoding
pip install vllm
```

## Quick Start

### Draft-Model Speculative (Transformers assisted generation)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Target = large/slow; draft = small/fast (same tokenizer/family)
target_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf", device_map="auto", torch_dtype=torch.float16)
draft_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf", device_map="auto", torch_dtype=torch.float16)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-70b-hf")

inputs = tokenizer("Explain quantum computing simply:", return_tensors="pt").to("cuda")
outputs = target_model.generate(
    **inputs,
    assistant_model=draft_model,  # Enables speculative decoding
    max_new_tokens=256, do_sample=True, temperature=0.7,
)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### Medusa (multiple decoding heads)

```python
from medusa.model.medusa_model import MedusaModel
from transformers import AutoTokenizer

model = MedusaModel.from_pretrained(
    "FasterDecoding/medusa-vicuna-7b-v1.3", torch_dtype="auto", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained("FasterDecoding/medusa-vicuna-7b-v1.3")

inputs = tokenizer("Write a fibonacci function in Python:", return_tensors="pt").to("cuda")
outputs = model.medusa_generate(
    **inputs, max_new_tokens=256, temperature=0.7,
    posterior_threshold=0.09,  # Acceptance threshold (from paper)
    posterior_alpha=0.3,       # Tree construction parameter
)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### Lookahead Decoding (Jacobi iteration)

```python
# lade patches HF models in place — no dedicated class; use standard generate()
import os
os.environ["USE_LADE"] = "1"  # or run with USE_LADE=1 in the environment
import lade
lade.augment_all()
# LEVEL = N-gram size, WINDOW_SIZE = W (lookahead width), GUESS_SET_SIZE = G
lade.config_lade(LEVEL=5, WINDOW_SIZE=15, GUESS_SET_SIZE=15, DEBUG=0)

from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf", torch_dtype="auto", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

inputs = tokenizer("Implement quicksort in Python:", return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=256)  # accelerated by lade
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## Core Concepts (at a glance)

1. **Draft-model speculative** — a small draft proposes K tokens; the target
   verifies all K in one parallel forward pass, accepting matches and resampling
   the first mismatch. Lossless. → `references/draft_model.md`
2. **Medusa** — extra prediction heads on a frozen (Medusa-1) or fine-tuned
   (Medusa-2) base predict tokens t+1…t+k; a tree of candidates is verified in a
   single forward pass. No separate draft model. → `references/medusa.md`
3. **Lookahead** — reframes autoregressive decoding as Jacobi fixed-point
   iteration: generate n-grams in parallel (lookahead branch), then verify and
   accept matches (verification branch). No draft model, no training.
   → `references/lookahead.md`

## Method Comparison

| Method | Speedup | Training Needed | Draft Model | Quality Loss |
|--------|---------|-----------------|-------------|--------------|
| **Draft-model speculative** | 1.5-2× | No | Yes (external, same tokenizer) | None |
| **Medusa** | 2-3.6× | Minimal (heads only) | No (built-in heads) | None |
| **Lookahead** | 1.5-2.3× | None | No | None |
| **Naive batching** | 1.2-1.5× | No | No | None |

## Choosing a Method

- **New deployment, want best speedup, no draft available** → Medusa (`references/medusa.md`).
- **Existing deployment with a small same-tokenizer model** → draft-model speculative (`references/draft_model.md`).
- **Zero training/setup, plug-and-play** → Lookahead (`references/lookahead.md`).

Each reference file covers that method's training recipe (where applicable),
hyperparameter tuning, and production deployment.

## Resources

- Speculative Decoding (Leviathan et al., ICML 2023): https://arxiv.org/abs/2211.17192
- Speculative Sampling (Chen et al., DeepMind 2023): https://arxiv.org/abs/2302.01318
- Medusa Paper: https://arxiv.org/abs/2401.10774 · GitHub: https://github.com/FasterDecoding/Medusa
- Lookahead Decoding (ICML 2024): https://lmsys.org/blog/2023-11-21-lookahead-decoding/ · GitHub: https://github.com/hao-ai-lab/LookaheadDecoding
- Comprehensive Survey: https://arxiv.org/abs/2401.07851

## See Also

- `references/draft_model.md` — draft-model algorithm, selection, hybrid, vLLM deployment
- `references/medusa.md` — Medusa architecture, training (Medusa-1/2), tuning
- `references/lookahead.md` — Lookahead implementation, Jacobi math, tuning
