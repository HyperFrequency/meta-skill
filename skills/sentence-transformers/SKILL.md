---
name: sentence-transformers
description: Framework for state-of-the-art sentence, text, and image embeddings. Provides 5000+ pre-trained models for semantic similarity, clustering, and retrieval, including multilingual, domain-specific, and multimodal models. Use when generating embeddings locally for RAG, semantic search, clustering, or similarity tasks without an external API. Do NOT use when you need a fully managed/hosted embedding API (use OpenAI Embeddings or Cohere Embed) or task-instruction-conditioned embeddings (use Instructor); also not for generative LLM tasks (use transformers).
version: 1.0.0
author: Orchestra Research
license: Apache-2.0
tags: [Sentence Transformers, Embeddings, Semantic Similarity, RAG, Multilingual, Multimodal, Pre-Trained Models, Clustering, Semantic Search, Production]
dependencies: [sentence-transformers, transformers, torch]
---

# Sentence Transformers - State-of-the-Art Embeddings

Python framework for sentence and text embeddings using transformers.

## When to use Sentence Transformers

**Use when:**
- Need high-quality embeddings for RAG
- Semantic similarity and search
- Text clustering and classification
- Multilingual embeddings (100+ languages)
- Running embeddings locally (no API)
- Cost-effective alternative to OpenAI embeddings

**Metrics**:
- **15,700+ GitHub stars**
- **5000+ pre-trained models**
- **100+ languages** supported
- Based on PyTorch/Transformers

**Use alternatives instead**:
- **OpenAI Embeddings**: Need API-based, highest quality
- **Instructor**: Task-specific instructions
- **Cohere Embed**: Managed service

## Quick start

### Installation

```bash
pip install sentence-transformers
```

### Basic usage

```python
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embeddings
sentences = [
    "This is an example sentence",
    "Each sentence is converted to a vector"
]

embeddings = model.encode(sentences)
print(embeddings.shape)  # (2, 384)

# Cosine similarity
from sentence_transformers.util import cos_sim
similarity = cos_sim(embeddings[0], embeddings[1])
print(f"Similarity: {similarity.item():.4f}")
```

## Popular models

### General purpose

```python
# Fast, good quality (384 dim)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Better quality (768 dim)
model = SentenceTransformer('all-mpnet-base-v2')

# Best quality (1024 dim, slower)
model = SentenceTransformer('all-roberta-large-v1')
```

### Multilingual

```python
# 50+ languages
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 100+ languages
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
```

### Domain-specific

```python
# Legal domain
model = SentenceTransformer('nlpaueb/legal-bert-base-uncased')

# Scientific papers
model = SentenceTransformer('allenai/specter')

# Code
model = SentenceTransformer('microsoft/codebert-base')
```

## Semantic search

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

# Corpus
corpus = [
    "Python is a programming language",
    "Machine learning uses algorithms",
    "Neural networks are powerful"
]

# Encode corpus
corpus_embeddings = model.encode(corpus, convert_to_tensor=True)

# Query
query = "What is Python?"
query_embedding = model.encode(query, convert_to_tensor=True)

# Find most similar
hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=3)
print(hits)
```

## Similarity computation

```python
# Preferred (v3+): model.similarity() uses the model's configured
# similarity function (cosine by default) and returns a score matrix.
scores = model.similarity(embeddings, embeddings)  # (n, n) tensor

# Lower-level utilities (still supported)
similarity = util.cos_sim(embedding1, embedding2)   # cosine
similarity = util.dot_score(embedding1, embedding2) # dot product
```

## Retrieval: query vs. document prompts

For asymmetric search (short query against longer passages), use the
v5+ `encode_query` / `encode_document` methods. They automatically apply
the model's configured `query` / `document` (or `passage`/`corpus`)
prompt and set the retrieval task, improving recall for prompt-aware
models (e.g., mxbai, E5, Qwen3-Embedding).

```python
query_embedding = model.encode_query("What is the capital of France?")
doc_embeddings = model.encode_document([
    "Paris is the capital of France.",
    "Berlin is the capital of Germany.",
])
scores = model.similarity(query_embedding, doc_embeddings)
```

Models without saved prompts fall back to plain `encode`, so these
methods are safe to use everywhere.

## Batch encoding

```python
# Efficient batch processing
sentences = ["sentence 1", "sentence 2", ...] * 1000

embeddings = model.encode(
    sentences,
    batch_size=32,
    show_progress_bar=True,
    convert_to_tensor=False  # or True for PyTorch tensors
)
```

## Fine-tuning

Use the modern `SentenceTransformerTrainer` API (v3.0+). It accepts a
`datasets.Dataset`, a loss, and an optional `SentenceTransformerTrainingArguments`,
and supports evaluators, multi-GPU, bf16, and Hub push out of the box.

```python
from datasets import load_dataset
from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer
from sentence_transformers.losses import MultipleNegativesRankingLoss

model = SentenceTransformer("microsoft/mpnet-base")

# Dataset columns map positionally to the loss's expected inputs
# (e.g. (anchor, positive, negative) for a triplet loss)
dataset = load_dataset("sentence-transformers/all-nli", "triplet")
train_dataset = dataset["train"].select(range(10_000))
eval_dataset = dataset["dev"].select(range(1_000))

loss = MultipleNegativesRankingLoss(model)

trainer = SentenceTransformerTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    loss=loss,
)
trainer.train()

model.save_pretrained("models/mpnet-base-all-nli")
# model.push_to_hub("mpnet-base-all-nli")
```

> Legacy `model.fit()` with `InputExample` + `DataLoader` still works but
> is deprecated; prefer the trainer above for new code.

## LangChain integration

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

# Use with vector stores
from langchain_chroma import Chroma

vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings
)
```

## LlamaIndex integration

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

from llama_index.core import Settings
Settings.embed_model = embed_model

# Use in index
index = VectorStoreIndex.from_documents(documents)
```

## Model selection guide

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | General, prototyping |
| all-mpnet-base-v2 | 768 | Medium | Better | Production RAG |
| all-roberta-large-v1 | 1024 | Slow | Best | High accuracy needed |
| paraphrase-multilingual | 768 | Medium | Good | Multilingual |

## Best practices

1. **Start with all-MiniLM-L6-v2** - Good baseline
2. **Normalize embeddings** - Better for cosine similarity
3. **Use GPU if available** - 10× faster encoding
4. **Batch encoding** - More efficient
5. **Cache embeddings** - Expensive to recompute
6. **Fine-tune for domain** - Improves quality
7. **Test different models** - Quality varies by task
8. **Monitor memory** - Large models need more RAM

## Performance

| Model | Speed (sentences/sec) | Memory | Dimension |
|-------|----------------------|---------|-----------|
| MiniLM | ~2000 | 120MB | 384 |
| MPNet | ~600 | 420MB | 768 |
| RoBERTa | ~300 | 1.3GB | 1024 |

## Resources

- **Model selection deep-dive**: [references/models.md](references/models.md)
- **GitHub**: https://github.com/UKPLab/sentence-transformers ⭐ 15,700+
- **Models**: https://huggingface.co/sentence-transformers
- **Docs**: https://www.sbert.net
- **License**: Apache 2.0


