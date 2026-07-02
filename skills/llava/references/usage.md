# LLaVA Inference & Serving Guide

Detailed inference, CLI, Web UI, quantization, and framework-integration recipes.
For training/fine-tuning, see `training.md`.

## Installation

```bash
git clone https://github.com/haotian-liu/LLaVA
cd LLaVA
pip install -e .
```

## Basic Python inference

```python
from llava.model.builder import load_pretrained_model
from llava.mm_utils import get_model_name_from_path, process_images, tokenizer_image_token
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates
from PIL import Image
import torch

# Load model
model_path = "liuhaotian/llava-v1.5-7b"
tokenizer, model, image_processor, context_len = load_pretrained_model(
    model_path=model_path,
    model_base=None,
    model_name=get_model_name_from_path(model_path)
)

# Load image
image = Image.open("image.jpg")
image_tensor = process_images([image], image_processor, model.config)
image_tensor = image_tensor.to(model.device, dtype=torch.float16)

# Create conversation
conv = conv_templates["llava_v1"].copy()
conv.append_message(conv.roles[0], DEFAULT_IMAGE_TOKEN + "\nWhat is in this image?")
conv.append_message(conv.roles[1], None)
prompt = conv.get_prompt()

# Generate response
input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).to(model.device)

with torch.inference_mode():
    output_ids = model.generate(
        input_ids,
        images=image_tensor,
        do_sample=True,
        temperature=0.2,
        max_new_tokens=512
    )

response = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
print(response)
```

## Available models

| Model | Parameters | VRAM (FP16) | VRAM (4-bit) | Speed (tok/s, A100) | Quality |
|-------|------------|-------------|--------------|---------------------|---------|
| LLaVA-v1.5-7B  | 7B  | ~14 GB | ~4 GB  | ~20 | Good   |
| LLaVA-v1.5-13B | 13B | ~28 GB | ~8 GB  | ~12 | Better |
| LLaVA-v1.6-34B | 34B | ~70 GB | ~18 GB | ~5  | Best   |

```python
model_7b  = "liuhaotian/llava-v1.5-7b"
model_13b = "liuhaotian/llava-v1.5-13b"
model_34b = "liuhaotian/llava-v1.6-34b"  # v1.6 = LLaVA-NeXT, higher-res inputs
```

## CLI usage

```bash
# Single image query
python -m llava.serve.cli \
    --model-path liuhaotian/llava-v1.5-7b \
    --image-file image.jpg \
    --query "What is in this image?"

# Multi-turn conversation (type questions interactively)
python -m llava.serve.cli \
    --model-path liuhaotian/llava-v1.5-7b \
    --image-file image.jpg
```

## Web UI (Gradio)

```bash
python -m llava.serve.gradio_web_server \
    --model-path liuhaotian/llava-v1.5-7b \
    --load-4bit          # Optional: reduce VRAM
# Access at http://localhost:7860
```

## Multi-turn conversations

```python
conv = conv_templates["llava_v1"].copy()

# Turn 1
conv.append_message(conv.roles[0], DEFAULT_IMAGE_TOKEN + "\nWhat is in this image?")
conv.append_message(conv.roles[1], None)
response1 = generate(conv, model, image)  # "A dog playing in a park"

# Turn 2 — write the previous answer back before adding the next question
conv.messages[-1][1] = response1
conv.append_message(conv.roles[0], "What breed is the dog?")
conv.append_message(conv.roles[1], None)
response2 = generate(conv, model, image)  # "Golden Retriever"

# Turn 3
conv.messages[-1][1] = response2
conv.append_message(conv.roles[0], "What time of day is it?")
conv.append_message(conv.roles[1], None)
response3 = generate(conv, model, image)
```

## Common task prompts

```python
# Captioning
"Describe this image in detail."
# Visual question answering
"How many people are in the image?"
# Object listing (textual detection)
"List all the objects you can see in this image."
# Scene understanding
"What is happening in this scene?"
# Document understanding
"What is the main topic of this document?"
```

## Quantization (reduce VRAM)

```python
# 4-bit (~4x VRAM reduction)
tokenizer, model, image_processor, context_len = load_pretrained_model(
    model_path="liuhaotian/llava-v1.5-13b",
    model_base=None,
    model_name=get_model_name_from_path("liuhaotian/llava-v1.5-13b"),
    load_4bit=True
)

# 8-bit (~2x VRAM reduction)
# pass load_8bit=True instead
```

## Framework integration

### LangChain

```python
from langchain.llms.base import LLM

class LLaVALLM(LLM):
    def _call(self, prompt, stop=None):
        # Custom LLaVA inference
        return response

llm = LLaVALLM()
```

### Gradio app

```python
import gradio as gr

def chat(image, text, history):
    return ask_llava(model, image, text)

demo = gr.ChatInterface(
    chat,
    additional_inputs=[gr.Image(type="pil")],
    title="LLaVA Chat"
)
demo.launch()
```

## Benchmarks (LLaVA-v1.5)

| Benchmark | Score |
|-----------|-------|
| VQAv2   | 78.5% |
| GQA     | 62.0% |
| MM-Vet  | 35.4% |
| MMBench | 64.3% |

## Best practices

1. Start with the 7B model — good quality, manageable VRAM.
2. Use 4-bit quantization to cut VRAM significantly.
3. GPU required — CPU inference is extremely slow.
4. Clear, specific prompts yield better answers.
5. Maintain conversation context for multi-turn chat.
6. Temperature 0.2-0.7 balances creativity vs. consistency.
7. `max_new_tokens` 512-1024 for detailed responses.
8. Process multiple images sequentially (batch).

## Limitations

1. Hallucinations — may describe things not in the image.
2. Spatial reasoning — struggles with precise locations.
3. Small text — difficulty reading fine print.
4. Object counting — imprecise for many objects.
5. VRAM requirements — needs a powerful GPU.
6. Inference speed — slower than CLIP.
