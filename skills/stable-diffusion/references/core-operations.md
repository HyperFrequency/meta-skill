# Stable Diffusion Core Operations

Copy-paste recipes for the common Diffusers tasks beyond plain text-to-image.
All examples assume `import torch` and a CUDA GPU; swap `.to("cuda")` for your
device. For full canonical docs see https://huggingface.co/docs/diffusers.

## Image-to-image

Transform an existing image under text guidance. `strength` (0-1) controls how
much of the original is overwritten — lower keeps more of the input.

```python
from diffusers import AutoPipelineForImage2Image
from PIL import Image

pipe = AutoPipelineForImage2Image.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

init_image = Image.open("input.jpg").resize((512, 512))

image = pipe(
    prompt="A watercolor painting of the scene",
    image=init_image,
    strength=0.75,
    num_inference_steps=50
).images[0]
```

## Inpainting

Fill a masked region with context-aware content. The mask is a single-channel
image where **white pixels = the area to regenerate**.

```python
from diffusers import AutoPipelineForInpainting
from PIL import Image

pipe = AutoPipelineForInpainting.from_pretrained(
    "runwayml/stable-diffusion-inpainting",
    torch_dtype=torch.float16
).to("cuda")

result = pipe(
    prompt="A red car parked on the street",
    image=Image.open("photo.jpg"),
    mask_image=Image.open("mask.png"),
    num_inference_steps=50
).images[0]
```

## ControlNet

Condition generation on a spatial signal (edges, pose, depth) for precise
structural control.

```python
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel

controlnet = ControlNetModel.from_pretrained(
    "lllyasviel/control_v11p_sd15_canny",
    torch_dtype=torch.float16
)

pipe = StableDiffusionControlNetPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    controlnet=controlnet,
    torch_dtype=torch.float16
).to("cuda")

control_image = get_canny_image(input_image)  # your preprocessing

image = pipe(
    prompt="A beautiful house in the style of Van Gogh",
    image=control_image,
    num_inference_steps=30
).images[0]
```

### Available ControlNets

| ControlNet | Input Type | Use Case |
|------------|------------|----------|
| `canny` | Edge maps | Preserve structure |
| `openpose` | Pose skeletons | Human poses |
| `depth` | Depth maps | 3D-aware generation |
| `normal` | Normal maps | Surface details |
| `mlsd` | Line segments | Architectural lines |
| `scribble` | Rough sketches | Sketch-to-image |

## LoRA adapters

Load fine-tuned style/character adapters on top of a base model.

```python
from diffusers import DiffusionPipeline

pipe = DiffusionPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    torch_dtype=torch.float16
).to("cuda")

pipe.load_lora_weights("path/to/lora", weight_name="style.safetensors")
image = pipe("A portrait in the trained style").images[0]

pipe.fuse_lora(lora_scale=0.8)   # bake in at a chosen strength
pipe.unload_lora_weights()        # remove
```

### Multiple LoRAs

```python
pipe.load_lora_weights("lora1", adapter_name="style")
pipe.load_lora_weights("lora2", adapter_name="character")
pipe.set_adapters(["style", "character"], adapter_weights=[0.7, 0.5])
image = pipe("A portrait").images[0]
```

## Model variants and components

```python
# FP16 (recommended for GPU) / BF16 (Ampere+ GPUs, better precision)
pipe = DiffusionPipeline.from_pretrained(
    "model-id", torch_dtype=torch.float16, variant="fp16"
)

# Swap in a custom VAE
from diffusers import AutoencoderKL
vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse")
pipe = DiffusionPipeline.from_pretrained(
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    vae=vae, torch_dtype=torch.float16
)
```

## Batch generation

```python
# Multiple distinct prompts in one call
images = pipe(["A cat playing piano", "A dog reading a book"],
              num_inference_steps=30).images

# Multiple images for one prompt
images = pipe("A beautiful sunset", num_images_per_prompt=4,
              num_inference_steps=30).images
```
