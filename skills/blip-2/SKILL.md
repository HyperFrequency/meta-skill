---
name: blip-2
description: Salesforce BLIP-2 vision-language framework that bridges frozen image encoders and LLMs via a lightweight Q-Former. Use for zero-shot image captioning, visual question answering (VQA), image-text retrieval/matching, and image feature extraction with transformers or LAVIS. Do NOT use for instruction-following multimodal chat (use InstructBLIP or LLaVA), plain image-text similarity without generation (use CLIP), few-shot visual learning (use Flamingo), or production proprietary chat (use GPT-4V/Claude).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Multimodal, Vision-Language, Image Captioning, VQA, Zero-Shot]
dependencies: [transformers>=4.30.0, torch>=1.10.0, Pillow]
---

# BLIP-2: Vision-Language Pre-training

Router for using Salesforce's BLIP-2 for vision-language tasks with frozen image encoders and large language models. Detailed code lives in `references/`.

## When to use BLIP-2

**Use when:**
- High-quality, natural image captioning
- Visual question answering (VQA) systems
- Zero-shot image-text understanding without task-specific training
- Leveraging LLM reasoning for visual tasks
- Image-text retrieval / matching or Q-Former feature extraction

**Use alternatives instead:**
- **InstructBLIP** — improved instruction-following (direct BLIP-2 successor)
- **LLaVA** — instruction-following multimodal chat
- **CLIP** — simple image-text similarity without generation
- **Flamingo** — few-shot visual learning
- **GPT-4V / Claude** — production proprietary multimodal chat

**Key features:** Q-Former (lightweight query transformer, ~188M trained params) bridges a frozen ViT-G/14 vision encoder and a frozen LLM (OPT 2.7B/6.7B or FlanT5 XL/XXL), giving strong zero-shot results without fine-tuning the large backbones.

## Quick start

```bash
pip install transformers accelerate torch Pillow   # HuggingFace (recommended)
pip install salesforce-lavis                        # Or LAVIS (Salesforce official)
```

### Image captioning

```python
import torch
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration

processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained(
    "Salesforce/blip2-opt-2.7b",
    torch_dtype=torch.float16,
    device_map="auto",
)

image = Image.open("photo.jpg").convert("RGB")
inputs = processor(images=image, return_tensors="pt").to("cuda", torch.float16)
generated_ids = model.generate(**inputs, max_new_tokens=50)
print(processor.batch_decode(generated_ids, skip_special_tokens=True)[0])
```

### Visual question answering

```python
question = "What color is the car in this image?"
inputs = processor(images=image, text=question, return_tensors="pt").to("cuda", torch.float16)
generated_ids = model.generate(**inputs, max_new_tokens=50)
print(processor.batch_decode(generated_ids, skip_special_tokens=True)[0])
```

For batching, generation control, quantization, image-text matching, feature extraction, and output formats, see [references/code-examples.md](references/code-examples.md). For LAVIS loading, see the LAVIS examples in that file and `references/advanced-usage.md`.

## Architecture

```
Frozen Vision Encoder (ViT-G/14, EVA-CLIP)
            │ image features
            ▼
        Q-Former                 ← only trained component (~188M)
  32 learned queries (×768)
  cross-attention to image
  self-attention layers
            │ linear projection
            ▼
   Frozen LLM (OPT or FlanT5) → text output
```

## Model variants

| Model | LLM Backend | Approx. download | Use case |
|-------|-------------|------------------|----------|
| `blip2-opt-2.7b` | OPT-2.7B | ~4GB | General captioning, VQA |
| `blip2-opt-6.7b` | OPT-6.7B | ~8GB | Better reasoning |
| `blip2-flan-t5-xl` | FlanT5-XL | ~5GB | Instruction following |
| `blip2-flan-t5-xxl` | FlanT5-XXL | ~13GB | Best quality |

Q-Former components: 32×768 learned queries, an image transformer (~108M, cross-attends to vision features), a text transformer (~108M), and a linear projection to the LLM hidden dimension. GPU VRAM by precision is tabulated in `references/code-examples.md`.

## Common issues

| Issue | Solution |
|-------|----------|
| CUDA OOM | INT8/INT4 quantization, smaller model |
| Slow generation | Greedy decoding, reduce `max_new_tokens` |
| Poor captions | Try a FlanT5 variant, use prompts |
| Hallucinations | Lower temperature, use beam search |
| Wrong answers | Rephrase question, provide context |

See [references/troubleshooting.md](references/troubleshooting.md) for deeper diagnosis.

## References

- **[Code examples](references/code-examples.md)** — batching, generation control, quantization, ITM, feature extraction, output formats, performance/VRAM tables
- **[Workflows](references/workflows.md)** — end-to-end captioning, VQA, and retrieval class wrappers
- **[Advanced usage](references/advanced-usage.md)** — fine-tuning, integration, deployment
- **[Troubleshooting](references/troubleshooting.md)** — common issues and solutions

## Related skills

- `multimodal/llava` — instruction-following multimodal chat
- `multimodal/clip` — contrastive image-text similarity (no generation)

## Resources

- **Paper**: https://arxiv.org/abs/2301.12597
- **GitHub (LAVIS)**: https://github.com/salesforce/LAVIS
- **HuggingFace**: https://huggingface.co/Salesforce/blip2-opt-2.7b
- **Demo**: https://huggingface.co/spaces/Salesforce/BLIP2
- **InstructBLIP**: https://arxiv.org/abs/2305.06500 (successor)
