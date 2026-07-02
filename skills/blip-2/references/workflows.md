# BLIP-2 End-to-End Workflows

Reusable class wrappers for captioning, VQA, and retrieval. For lower-level snippets see [code-examples.md](code-examples.md).

## Workflow 1: Image captioning pipeline

```python
import torch
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from pathlib import Path

class ImageCaptioner:
    def __init__(self, model_name="Salesforce/blip2-opt-2.7b"):
        self.processor = Blip2Processor.from_pretrained(model_name)
        self.model = Blip2ForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )

    def caption(self, image_path: str, prompt: str = None) -> str:
        image = Image.open(image_path).convert("RGB")

        if prompt:
            inputs = self.processor(images=image, text=prompt, return_tensors="pt")
        else:
            inputs = self.processor(images=image, return_tensors="pt")

        inputs = inputs.to("cuda", torch.float16)

        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=50,
            num_beams=5
        )

        return self.processor.decode(generated_ids[0], skip_special_tokens=True)

    def caption_batch(self, image_paths: list, prompt: str = None) -> list:
        images = [Image.open(p).convert("RGB") for p in image_paths]

        if prompt:
            inputs = self.processor(
                images=images,
                text=[prompt] * len(images),
                return_tensors="pt",
                padding=True
            )
        else:
            inputs = self.processor(images=images, return_tensors="pt", padding=True)

        inputs = inputs.to("cuda", torch.float16)

        generated_ids = self.model.generate(**inputs, max_new_tokens=50)
        return self.processor.batch_decode(generated_ids, skip_special_tokens=True)

# Usage
captioner = ImageCaptioner()

# Single image
caption = captioner.caption("photo.jpg")
print(f"Caption: {caption}")

# With prompt for style
caption = captioner.caption("photo.jpg", "a detailed description of")
print(f"Detailed: {caption}")

# Batch processing
captions = captioner.caption_batch(["img1.jpg", "img2.jpg", "img3.jpg"])
for i, cap in enumerate(captions):
    print(f"Image {i+1}: {cap}")
```

## Workflow 2: Visual Q&A system

```python
class VisualQA:
    def __init__(self, model_name="Salesforce/blip2-flan-t5-xl"):
        self.processor = Blip2Processor.from_pretrained(model_name)
        self.model = Blip2ForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.current_image = None
        self.current_inputs = None

    def set_image(self, image_path: str):
        """Load image for multiple questions."""
        self.current_image = Image.open(image_path).convert("RGB")

    def ask(self, question: str) -> str:
        """Ask a question about the current image."""
        if self.current_image is None:
            raise ValueError("No image set. Call set_image() first.")

        # Format question for FlanT5
        prompt = f"Question: {question} Answer:"

        inputs = self.processor(
            images=self.current_image,
            text=prompt,
            return_tensors="pt"
        ).to("cuda", torch.float16)

        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=50,
            num_beams=5
        )

        return self.processor.decode(generated_ids[0], skip_special_tokens=True)

    def ask_multiple(self, questions: list) -> dict:
        """Ask multiple questions about current image."""
        return {q: self.ask(q) for q in questions}

# Usage
vqa = VisualQA()
vqa.set_image("scene.jpg")

# Ask questions
print(vqa.ask("What objects are in this image?"))
print(vqa.ask("What is the weather like?"))
print(vqa.ask("How many people are there?"))

# Batch questions
results = vqa.ask_multiple([
    "What is the main subject?",
    "What colors are dominant?",
    "Is this indoors or outdoors?"
])
```

## Workflow 3: Image search/retrieval

```python
import torch
import numpy as np
from PIL import Image
from lavis.models import load_model_and_preprocess

class ImageSearchEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model, self.vis_processors, self.txt_processors = load_model_and_preprocess(
            name="blip2_feature_extractor",
            model_type="pretrain",
            is_eval=True,
            device=self.device
        )
        self.image_features = []
        self.image_paths = []

    def index_images(self, image_paths: list):
        """Build index from images."""
        self.image_paths = image_paths

        for path in image_paths:
            image = Image.open(path).convert("RGB")
            image = self.vis_processors["eval"](image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                features = self.model.extract_features({"image": image}, mode="image")
                # Use projected features for matching
                self.image_features.append(
                    features.image_embeds_proj.mean(dim=1).cpu().numpy()
                )

        self.image_features = np.vstack(self.image_features)

    def search(self, query: str, top_k: int = 5) -> list:
        """Search images by text query."""
        # Get text features
        text = self.txt_processors["eval"](query)
        text_input = {"text_input": [text]}

        with torch.no_grad():
            text_features = self.model.extract_features(text_input, mode="text")
            text_embeds = text_features.text_embeds_proj[:, 0].cpu().numpy()

        # Compute similarities
        similarities = np.dot(self.image_features, text_embeds.T).squeeze()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(self.image_paths[i], similarities[i]) for i in top_indices]

# Usage
engine = ImageSearchEngine()
engine.index_images(["img1.jpg", "img2.jpg", "img3.jpg", ...])

# Search
results = engine.search("a sunset over the ocean", top_k=5)
for path, score in results:
    print(f"{path}: {score:.3f}")
```
