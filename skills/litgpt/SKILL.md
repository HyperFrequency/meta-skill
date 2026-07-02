---
name: litgpt
description: Implement, fine-tune, pretrain, and deploy LLMs with Lightning AI's LitGPT — 20+ clean single-file architectures (Llama, Gemma, Phi, Qwen, Mistral, Mixtral, Falcon). Use when you need readable from-scratch model implementations, LoRA/QLoRA or full fine-tuning, pretraining recipes, or LitGPT's CLI/`LLM` API. NOT for inference-only serving at scale (use vLLM), broadest HF model coverage or `transformers`/`peft` APIs (use the transformers skill), maximum-throughput >70B training (use Megatron-Core), YAML-config fine-tuning frameworks (Axolotl/TRL), or non-LitGPT PyTorch Lightning training loops (use the pytorch-lightning skill).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Model Architecture, LitGPT, Lightning AI, LLM Implementation, LoRA, QLoRA, Fine-Tuning, Llama, Gemma, Phi, Mistral, Educational]
dependencies: [litgpt, torch, transformers]
---

# LitGPT — Clean LLM Implementations

LitGPT provides 20+ pretrained LLM implementations as readable single-file code
with production training workflows (pretrain, fine-tune, LoRA/QLoRA, deploy).
This file routes; deep detail lives in `references/`.

## Quick start

```bash
pip install 'litgpt[extra]'
litgpt download list          # list available models
```

```python
from litgpt import LLM

llm = LLM.load("microsoft/phi-2")
print(llm.generate("What is the capital of France?",
                   max_new_tokens=50, temperature=0.7))
```

## Workflows — full walkthroughs in [references/workflows.md](references/workflows.md)

1. **Fine-tune on a custom dataset** — `litgpt download` → Alpaca-JSON data →
   `litgpt finetune` (full) or `litgpt finetune_lora` (16GB GPU).
2. **LoRA fine-tuning on a single GPU** — most memory-efficient; rank/alpha/dropout
   tuning, then `litgpt merge_lora` for deployment.
3. **Pretrain from scratch** — tokenize corpus → architecture YAML →
   `litgpt pretrain` single- or multi-GPU (FSDP/SLURM).
4. **Convert and deploy** — local/streaming/batch inference, NF4 quantization,
   GGUF export, FastAPI or `litgpt serve`.

Troubleshooting (OOM, slow training, model not loading, oversized LoRA adapters)
is in the same file's appendix.

## When to use vs alternatives

**Use LitGPT when** you want to understand architectures (clean, readable code),
need production training recipes, are prototyping a new model, do research/education,
or already live in the Lightning ecosystem.

**Use something else when:**
- **vLLM** — inference/serving only, no training.
- **HuggingFace `transformers`/`peft`** — broadest model coverage, more APIs (see the `transformers` skill).
- **Megatron-Core** — maximum throughput for >70B-parameter training.
- **Axolotl / TRL** — richer YAML-config fine-tuning feature set.
- **`pytorch-lightning` skill** — generic Lightning training loops not tied to LitGPT.

## Reference index

- [references/workflows.md](references/workflows.md) — the four end-to-end workflows + troubleshooting.
- [references/supported-models.md](references/supported-models.md) — full 20+ architecture list with sizes/variants.
- [references/training-recipes.md](references/training-recipes.md) — proven hyperparameters for LoRA/QLoRA/full fine-tuning.
- [references/distributed-training.md](references/distributed-training.md) — FSDP multi-GPU/multi-node setup.
- [references/custom-models.md](references/custom-models.md) — implementing new architectures in LitGPT style.

## Hardware requirements

- **GPU**: NVIDIA (CUDA 11.8+), AMD (ROCm), Apple Silicon (MPS).
- **Memory**: inference Phi-2 ~6GB · LoRA fine-tune 7B ~16GB · full fine-tune 7B 40GB+ · pretrain 1B ~24GB.
- **Storage**: 5-50GB per model depending on size.

## Resources

- GitHub: https://github.com/Lightning-AI/litgpt
- Docs: https://lightning.ai/docs/litgpt
- Tutorials: https://lightning.ai/docs/litgpt/tutorials
