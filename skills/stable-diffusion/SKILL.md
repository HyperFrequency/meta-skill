---
name: stable-diffusion
description: Local/self-hosted text-to-image generation with Stable Diffusion (SD 1.5, SDXL, SD3, Flux) via the HuggingFace Diffusers library. Use when generating images from text prompts on your own GPU, doing image-to-image translation, inpainting/outpainting, ControlNet conditioning, LoRA styling, or building custom diffusion pipelines. Do NOT use for API-only generation without a GPU (use DALL-E 3, Imagen, or Midjourney instead), for video/3D/audio generation, for training LLMs, or for non-diffusion image models.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Image Generation, Stable Diffusion, Diffusers, Text-to-Image, Multimodal, Computer Vision]
dependencies: [diffusers>=0.30.0, transformers>=4.41.0, accelerate>=0.31.0, torch>=2.0.0]
---

# Stable Diffusion Image Generation

Comprehensive guide to generating images with Stable Diffusion using the HuggingFace Diffusers library.

## When to use Stable Diffusion

**Use Stable Diffusion when:**
- Generating images from text descriptions
- Performing image-to-image translation (style transfer, enhancement)
- Inpainting (filling in masked regions)
- Outpainting (extending images beyond boundaries)
- Creating variations of existing images
- Building custom image generation workflows

**Key features:**
- **Text-to-Image**: Generate images from natural language prompts
- **Image-to-Image**: Transform existing images with text guidance
- **Inpainting**: Fill masked regions with context-aware content
- **ControlNet**: Add spatial conditioning (edges, poses, depth)
- **LoRA Support**: Efficient fine-tuning and style adaptation
- **Multiple Models**: SD 1.5, SDXL, SD 3.0, Flux support

**Use alternatives instead:**
- **DALL-E 3**: For API-based generation without GPU
- **Midjourney**: For artistic, stylized outputs
- **Imagen**: For Google Cloud integration
- **Leonardo.ai**: For web-based creative workflows

## Quick start

### Installation

```bash
pip install diffusers transformers accelerate torch
pip install xformers  # Optional: memory-efficient attention
```

### Basic text-to-image

```python
from diffusers import DiffusionPipeline
import torch

# Load pipeline (auto-detects model type)
pipe = DiffusionPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    torch_dtype=torch.float16
)
pipe.to("cuda")

# Generate image
image = pipe(
    "A serene mountain landscape at sunset, highly detailed",
    num_inference_steps=50,
    guidance_scale=7.5
).images[0]

image.save("output.png")
```

### Using SDXL (higher quality)

```python
from diffusers import AutoPipelineForText2Image
import torch

pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16"
)
pipe.to("cuda")

# Enable memory optimization
pipe.enable_model_cpu_offload()

image = pipe(
    prompt="A futuristic city with flying cars, cinematic lighting",
    height=1024,
    width=1024,
    num_inference_steps=30
).images[0]
```

## Architecture overview

### Three-pillar design

Diffusers is built around three core components:

```
Pipeline (orchestration)
├── Model (neural networks)
│   ├── UNet / Transformer (noise prediction)
│   ├── VAE (latent encoding/decoding)
│   └── Text Encoder (CLIP/T5)
└── Scheduler (denoising algorithm)
```

### Pipeline inference flow

```
Text Prompt → Text Encoder → Text Embeddings
                                    ↓
Random Noise → [Denoising Loop] ← Scheduler
                      ↓
               Predicted Noise
                      ↓
              VAE Decoder → Final Image
```

## Core concepts

### Pipelines

Pipelines orchestrate complete workflows:

| Pipeline | Purpose |
|----------|---------|
| `StableDiffusionPipeline` | Text-to-image (SD 1.x/2.x) |
| `StableDiffusionXLPipeline` | Text-to-image (SDXL) |
| `StableDiffusion3Pipeline` | Text-to-image (SD 3.0) |
| `FluxPipeline` | Text-to-image (Flux models) |
| `StableDiffusionImg2ImgPipeline` | Image-to-image |
| `StableDiffusionInpaintPipeline` | Inpainting |

### Schedulers

Schedulers control the denoising process:

| Scheduler | Steps | Quality | Use Case |
|-----------|-------|---------|----------|
| `EulerDiscreteScheduler` | 20-50 | Good | Default choice |
| `EulerAncestralDiscreteScheduler` | 20-50 | Good | More variation |
| `DPMSolverMultistepScheduler` | 15-25 | Excellent | Fast, high quality |
| `DDIMScheduler` | 50-100 | Good | Deterministic |
| `LCMScheduler` | 4-8 | Good | Very fast |
| `UniPCMultistepScheduler` | 15-25 | Excellent | Fast convergence |

### Swapping schedulers

```python
from diffusers import DPMSolverMultistepScheduler

# Swap for faster generation
pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config
)

# Now generate with fewer steps
image = pipe(prompt, num_inference_steps=20).images[0]
```

## Generation parameters

### Key parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | Required | Text description of desired image |
| `negative_prompt` | None | What to avoid in the image |
| `num_inference_steps` | 50 | Denoising steps (more = better quality) |
| `guidance_scale` | 7.5 | Prompt adherence (7-12 typical) |
| `height`, `width` | 512/1024 | Output dimensions (multiples of 8) |
| `generator` | None | Torch generator for reproducibility |
| `num_images_per_prompt` | 1 | Batch size |

### Reproducible generation

```python
import torch

generator = torch.Generator(device="cuda").manual_seed(42)

image = pipe(
    prompt="A cat wearing a top hat",
    generator=generator,
    num_inference_steps=50
).images[0]
```

### Negative prompts

```python
image = pipe(
    prompt="Professional photo of a dog in a garden",
    negative_prompt="blurry, low quality, distorted, ugly, bad anatomy",
    guidance_scale=7.5
).images[0]
```

## Core operations (img2img, inpaint, ControlNet, LoRA, batch)

Copy-paste recipes for everything beyond plain text-to-image live in
**[references/core-operations.md](references/core-operations.md)**:

| Task | Pipeline / API | Notes |
|------|----------------|-------|
| Image-to-image | `AutoPipelineForImage2Image` | `strength` (0-1) controls how much is overwritten |
| Inpainting | `AutoPipelineForInpainting` | mask: white = region to regenerate |
| ControlNet | `StableDiffusionControlNetPipeline` + `ControlNetModel` | canny / openpose / depth / normal / mlsd / scribble |
| LoRA styling | `pipe.load_lora_weights` / `set_adapters` / `fuse_lora` | stack adapters with per-adapter weights |
| Custom VAE / precision | `torch_dtype` + `variant="fp16"`, `AutoencoderKL` | BF16 needs Ampere+ |
| Batch | `num_images_per_prompt` or list of prompts | one call, multiple outputs |

## Memory optimization

Apply these (roughly in order of impact) when VRAM is tight:

```python
pipe.enable_model_cpu_offload()             # offload idle models to CPU
pipe.enable_sequential_cpu_offload()        # more aggressive, slower
pipe.enable_attention_slicing()             # chunked attention ("max" for smallest)
pipe.enable_xformers_memory_efficient_attention()  # needs xformers
pipe.enable_vae_slicing()                    # large images: decode in slices
pipe.enable_vae_tiling()                     # large images: decode in tiles
```

## End-to-end workflows

For complete recipes, see **[references/advanced-usage.md](references/advanced-usage.md)**:

- **High-quality SDXL** — SDXL base + `DPMSolverMultistepScheduler` + CPU offload at 1024x1024.
- **Fast prototyping** — SDXL + LCM LoRA + `LCMScheduler` for ~4-step (~1s) generation.
- Also: custom pipelines from components, IP-Adapter, SDXL refiner, T2I-Adapter, DreamBooth/LoRA/textual-inversion training, quantization, FastAPI/Docker/Kubernetes deployment, callbacks, multi-GPU.

## Common issues

Quick fixes for the three most frequent failures:

- **CUDA out of memory** → `pipe.enable_model_cpu_offload()` + `pipe.enable_attention_slicing()` + `pipe.enable_vae_slicing()`, or drop to `torch_dtype=torch.float16`.
- **Black/noise images** → dtype mismatch or NSFW safety filter; ensure consistent dtype and check `pipe.safety_checker`.
- **Slow generation** → swap to `DPMSolverMultistepScheduler` and reduce `num_inference_steps` to ~20, or use an LCM LoRA.

See **[references/troubleshooting.md](references/troubleshooting.md)** for the full diagnostic guide (install conflicts, blurry/distorted output, prompt adherence, LoRA/ControlNet/Hub issues, debugging).

## References

- **[Core Operations](references/core-operations.md)** - img2img, inpainting, ControlNet, LoRA, variants, batch recipes
- **[Advanced Usage](references/advanced-usage.md)** - Custom pipelines, fine-tuning, deployment
- **[Troubleshooting](references/troubleshooting.md)** - Common issues and solutions

## Resources

- **Documentation**: https://huggingface.co/docs/diffusers
- **Repository**: https://github.com/huggingface/diffusers
- **Model Hub**: https://huggingface.co/models?library=diffusers
- **Discord**: https://discord.gg/diffusers
