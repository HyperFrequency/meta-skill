# CLIP Models & Deployment Reference

Model variants, performance characteristics, batching, vector-DB integration, and
operational best practices. For task-oriented code (classification, search,
moderation, VQA, retrieval, dedup) see `applications.md`.

## Available models

```python
import clip

# clip.available_models() returns the full list at runtime
models = [
    "RN50",      # ResNet-50
    "RN101",     # ResNet-101
    "RN50x4",    # ResNet-50, 4x compute
    "RN50x16",
    "RN50x64",
    "ViT-B/32",  # Vision Transformer (good default)
    "ViT-B/16",  # Better quality, slower
    "ViT-L/14",  # Best quality, slowest
    "ViT-L/14@336px",  # Highest resolution
]

model, preprocess = clip.load("ViT-B/32")
```

| Model      | Parameters | Speed  | Quality |
|------------|------------|--------|---------|
| RN50       | 102M       | Fast   | Good    |
| ViT-B/32   | 151M       | Medium | Better  |
| ViT-L/14   | 428M       | Slow   | Best    |

## Image-text similarity

```python
image_features = model.encode_image(image)
text_features = model.encode_text(text)

# Normalize before cosine similarity
image_features /= image_features.norm(dim=-1, keepdim=True)
text_features /= text_features.norm(dim=-1, keepdim=True)

similarity = (image_features @ text_features.T).item()
print(f"Similarity: {similarity:.4f}")
```

## Batch processing

```python
# Stack multiple preprocessed images into one tensor
images = torch.stack(
    [preprocess(Image.open(f"img{i}.jpg")) for i in range(10)]
).to(device)

with torch.no_grad():
    image_features = model.encode_image(images)
    image_features /= image_features.norm(dim=-1, keepdim=True)

texts = ["a dog", "a cat", "a bird"]
text_tokens = clip.tokenize(texts).to(device)
with torch.no_grad():
    text_features = model.encode_text(text_tokens)
    text_features /= text_features.norm(dim=-1, keepdim=True)

# Similarity matrix (10 images x 3 texts)
similarities = image_features @ text_features.T
print(similarities.shape)  # torch.Size([10, 3])
```

## Vector database integration (Chroma / FAISS)

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection("image_embeddings")

# Store normalized CLIP embeddings
for img_path, embedding in zip(image_paths, image_embeddings):
    collection.add(
        embeddings=[embedding.cpu().numpy().tolist()],
        metadatas=[{"path": img_path}],
        ids=[img_path],
    )

# Query with a text embedding from the same CLIP model
text_embedding = model.encode_text(clip.tokenize(["a sunset"]))
results = collection.query(
    query_embeddings=[text_embedding.cpu().numpy().tolist()],
    n_results=5,
)
```

Image and text embeddings share the same space, so a text query can retrieve
images and vice versa. Always store and query L2-normalized vectors and use cosine
(inner-product) distance.

## Performance (reference, ViT-B/32)

| Operation          | CPU     | GPU (V100) |
|--------------------|---------|------------|
| Image encoding     | ~200ms  | ~20ms      |
| Text encoding      | ~50ms   | ~5ms       |
| Similarity compute | <1ms    | <1ms       |

## Operational best practices

1. **Use ViT-B/32 as default** — best speed/quality balance; ViT-L/14 when quality matters most.
2. **Normalize embeddings** — required for cosine similarity / inner-product search.
3. **Batch** images and texts — far more efficient than one-at-a-time.
4. **Cache embeddings** — encoding is the expensive step; recompute only on change.
5. **Use descriptive prompts** — "a photo of a {label}" beats a bare label.
6. **Use a GPU** — 10-50x faster than CPU.
7. **Always use the provided `preprocess`** — matching the training transform matters.
```
