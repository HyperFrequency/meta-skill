# Embeddings & image generation

## Embeddings

`embeddings.create` accepts a single string or a list of strings and returns one
vector per input. Different models emit different dimensions — pin one model per
index so vectors stay comparable.

```python
from together import Together

client = Together()

# Single input
resp = client.embeddings.create(
    model="BAAI/bge-large-en-v1.5",
    input="What is the meaning of life?",
)
vector = resp.data[0].embedding
print(len(vector))          # 1024

# Batch input — order of resp.data matches order of input
texts = [
    "Machine learning is a subset of AI.",
    "Deep learning uses neural networks.",
    "Transformers revolutionized NLP.",
]
resp = client.embeddings.create(model="BAAI/bge-large-en-v1.5", input=texts)
for i, item in enumerate(resp.data):
    print(i, len(item.embedding))
```

### Embedding models

| Model ID | Dims | Best for |
|----------|------|----------|
| `BAAI/bge-large-en-v1.5` | 1024 | General-purpose English retrieval |
| `BAAI/bge-base-en-v1.5` | 768 | Balanced cost/quality |
| `WhereIsAI/UAE-Large-V1` | 1024 | High-accuracy retrieval |
| `togethercomputer/m2-bert-80M-8k-retrieval` | 768 | Long-context (8k) retrieval |

Common failure: mixing models within one vector store. A 768-dim query vector
cannot be compared against 1024-dim index vectors — re-embed the whole corpus if
you switch models.

## Image generation

Together hosts FLUX models from Black Forest Labs via `images.generate`. The
response carries a URL or base64 payload depending on request options.

```python
from together import Together

client = Together()

resp = client.images.generate(
    model="black-forest-labs/FLUX.1-schnell",
    prompt="A photorealistic mountain landscape at sunset with a lake reflection",
    steps=4,
    n=1,
    width=1024,
    height=1024,
)

print(resp.data[0].url)     # or resp.data[0].b64_json when requested
```

### Image models

| Model ID | Profile | Notes |
|----------|---------|-------|
| `black-forest-labs/FLUX.1-schnell` | Fastest | ~4 steps; lowest latency/cost |
| `black-forest-labs/FLUX.1-dev` | Balanced | Supports LoRA for custom styles |
| `black-forest-labs/FLUX.1.1-pro` | Highest quality | Best prompt adherence |

Tips:
- `FLUX.1-schnell` is step-count sensitive — raising `steps` far above ~4 wastes
  time with little gain. Use `dev`/`pro` when you need more fidelity.
- If generation times out, lower `steps` or `n`, or fall back to
  `FLUX.1-schnell`.

### Via the OpenAI SDK

Image generation is also reachable through the OpenAI-compatible endpoint,
useful when you standardize on one client:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["TOGETHER_API_KEY"],
    base_url="https://api.together.xyz/v1",
)

resp = client.images.generate(
    model="black-forest-labs/FLUX.1-schnell",
    prompt="A cyberpunk cityscape at night",
    n=1,
)
print(resp.data[0].url)
```
