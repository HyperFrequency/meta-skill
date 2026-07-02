---
name: clip
description: "OpenAI's contrastive vision-language model connecting images and text in a shared embedding space. Use for zero-shot image classification, image-text matching, semantic image search, cross-modal retrieval (image<->text), and broad content moderation without fine-tuning. Trained on 400M image-text pairs; matches ResNet-50 on ImageNet zero-shot. WHEN NOT to use: fine-grained recognition (specific breeds/models/faces), object detection or bounding boxes (use Segment Anything / detection models), image captioning or free-form description (use BLIP-2), vision-language chat/reasoning (use LLaVA), or tasks needing counting and precise spatial layout — CLIP's spatial and counting ability is weak."
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Multimodal, CLIP, Vision-Language, Zero-Shot, Image Classification, OpenAI, Image Search, Cross-Modal Retrieval, Content Moderation]
dependencies: [transformers, torch, pillow]
---

# CLIP - Contrastive Language-Image Pre-Training

OpenAI's model that maps images and natural-language text into a shared embedding
space, enabling zero-shot vision tasks by comparing image and text embeddings.

## When to use CLIP

**Use when:**
- Zero-shot image classification (no training data needed)
- Image-text similarity / matching
- Semantic image search (text query -> images)
- Cross-modal retrieval (image -> text, text -> image)
- Broad content moderation (e.g. SFW vs NSFW vs violent buckets)
- Coarse visual question answering via yes/no prompt scoring

**Use alternatives instead:**
- **BLIP-2** — image captioning / free-form description
- **LLaVA** — vision-language chat and reasoning
- **Segment Anything / detection models** — segmentation, bounding boxes
- Fine-grained classifiers — specific breeds, product SKUs, faces

CLIP is weak at counting, precise spatial layout, and fine-grained distinctions.

## Quick start

```bash
pip install git+https://github.com/openai/CLIP.git
pip install torch torchvision ftfy regex tqdm
```

```python
import torch, clip
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

image = preprocess(Image.open("photo.jpg")).unsqueeze(0).to(device)
labels = ["a dog", "a cat", "a bird", "a car"]
text = clip.tokenize(labels).to(device)

with torch.no_grad():
    logits_per_image, _ = model(image, text)
    probs = logits_per_image.softmax(dim=-1).cpu().numpy()[0]

for label, prob in zip(labels, probs):
    print(f"{label}: {prob:.2%}")
```

## Reference docs

- **[references/applications.md](references/applications.md)** — task recipes: zero-shot
  classification, semantic search, content moderation, image-to-text retrieval,
  visual question answering, image deduplication.
- **[references/models-and-deployment.md](references/models-and-deployment.md)** — model
  variants and trade-offs, image-text similarity, batching, vector-DB (Chroma/FAISS)
  integration, performance numbers, operational best practices.

## Limitations

1. **Not for fine-grained tasks** — best on broad categories.
2. **Prompt-sensitive** — vague labels perform poorly; use "a photo of a {label}".
3. **Dataset bias** — trained on uncurated web data.
4. **No localization** — whole-image only, no bounding boxes.
5. **Weak spatial/counting** — position and quantity reasoning is unreliable.

## Resources

- **GitHub**: https://github.com/openai/CLIP (25,300+ stars, MIT)
- **Paper**: https://arxiv.org/abs/2103.00020
- **Colab**: https://colab.research.google.com/github/openai/clip/
