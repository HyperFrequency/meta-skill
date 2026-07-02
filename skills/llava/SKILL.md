---
name: llava
description: >-
  Large Language and Vision Assistant (LLaVA) — open-source vision-language model combining a CLIP ViT vision encoder with Vicuna/LLaMA LLMs for visual instruction tuning. Use for conversational image understanding, visual question answering (VQA), multi-turn image chat, visual instruction following, and document-image understanding when you want a self-hostable, open-weight model (7B-34B). Do NOT use when highest-quality/SOTA needs are better served by hosted GPT-4o/Claude vision APIs; for simple zero-shot image classification (use CLIP); for captioning-only pipelines (BLIP-2 is lighter); or in CPU-only / no-GPU environments. For training/fine-tuning see references/training.md; for full inference, CLI, Web UI, quantization, and integration recipes see references/usage.md.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [LLaVA, Vision-Language, Multimodal, Visual Question Answering, Image Chat, CLIP, Vicuna, Conversational AI, Instruction Tuning, VQA]
dependencies: [transformers, torch, pillow]
---

# LLaVA - Large Language and Vision Assistant

Open-source vision-language model for conversational image understanding. Combines a
CLIP ViT-L/14 vision encoder with a Vicuna/LLaMA language model via a projection layer.

## When to use

**Use when:**
- Building self-hosted vision-language chatbots
- Visual question answering (VQA) and multi-turn image conversations
- Image description / captioning and visual instruction following
- Document understanding from images
- You need open weights you can fine-tune (7B-34B sizes)

**Use something else when:**
- You need top-tier quality → hosted GPT-4o / Claude vision APIs
- Simple zero-shot classification → **CLIP**
- Captioning-only, lighter footprint → **BLIP-2**
- No GPU available → LLaVA is impractical on CPU

## Key facts

- Repo: `haotian-liu/LLaVA` (Apache 2.0, 23,000+ stars)
- Sizes: LLaVA-v1.5 7B / 13B, LLaVA-v1.6 (NeXT) up to 34B
- VRAM: ~14 GB (7B FP16) down to ~4 GB with 4-bit quantization
- Benchmarks (v1.5): VQAv2 78.5%, GQA 62.0%, MM-Vet 35.4%, MMBench 64.3%

## Quick start

```bash
git clone https://github.com/haotian-liu/LLaVA && cd LLaVA && pip install -e .
python -m llava.serve.cli \
    --model-path liuhaotian/llava-v1.5-7b \
    --image-file image.jpg \
    --query "What is in this image?"
```

For the full Python inference loop, multi-turn chat, Web UI, model table,
quantization, and framework integration, see **`references/usage.md`**.

## References

- `references/usage.md` — inference API, CLI, Gradio UI, models, quantization, benchmarks, integration
- `references/training.md` — two-stage training, instruction-data format, custom fine-tuning, LoRA, hardware

## Links

- GitHub: https://github.com/haotian-liu/LLaVA
- Paper: https://arxiv.org/abs/2304.08485
- Demo: https://llava.hliu.cc
- Models: https://huggingface.co/liuhaotian
