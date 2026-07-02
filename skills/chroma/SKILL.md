---
name: chroma
description: Open-source, self-hosted embedding (vector) database for RAG and semantic search. Store embeddings + metadata, run vector and full-text similarity search, filter by metadata via a simple add/query/get/delete API; scales from an in-memory notebook client to a persistent on-disk store or HTTP server. Use when you want a free, local, low-setup vector store for prototyping, document retrieval, or RAG over your own corpus. Do NOT use when you need a fully managed cloud service (use Pinecone), pure GPU/ANN similarity with no metadata layer (use FAISS), or large-scale production ML-native search (use Weaviate or Qdrant).
version: 1.0.2
author: Orchestra Research
license: MIT
tags: [RAG, Chroma, Vector Database, Embeddings, Semantic Search, Open Source, Self-Hosted, Document Retrieval, Metadata Filtering]
dependencies: [chromadb, sentence-transformers]
---

# Chroma - Open-Source Embedding Database

AI-native vector database for building LLM apps with memory. Apache 2.0,
~24k GitHub stars, latest `chromadb` 1.5.x (verify with `pip index versions chromadb`).

## When to use

- Building a RAG / retrieval-augmented generation pipeline
- Semantic search over your own documents
- You want a free, local/self-hosted vector store with minimal setup
- Prototyping in a notebook, then persisting to disk or a server

## When NOT to use (pick a sibling)

- **Managed cloud, auto-scaling** → Pinecone
- **Pure similarity/ANN, no metadata layer** → FAISS
- **Production, ML-native, GraphQL** → Weaviate
- **High-throughput, Rust-based ANN** → Qdrant

## 30-second start

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")  # survives restarts
collection = client.get_or_create_collection("my_docs")

collection.add(
    documents=["This is document 1", "This is document 2"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}],
    ids=["id1", "id2"],
)

results = collection.query(query_texts=["document about topic"], n_results=2)
print(results["documents"], results["distances"])
```

By default Chroma embeds with sentence-transformers `all-MiniLM-L6-v2` — no API
key needed. Swap in OpenAI/HuggingFace/custom embedders via `embedding_function`.

## Quick reference

- **Clients**: `Client()` (in-memory), `PersistentClient(path=...)` (on-disk),
  `HttpClient(host, port)` (server).
- **Collection**: `create_collection` / `get_collection` / `get_or_create_collection` / `delete_collection`.
- **CRUD**: `add`, `upsert` (add-or-update), `query` (similarity), `get` (by id/filter), `update`, `delete`; `count`, `peek`.
- **Distance**: default is L2 (squared euclidean); set cosine/ip at collection creation (see references/api.md).
- **Filtering**: `where=` on metadata (`$gt $lt $in $and $or` ...), `where_document={"$contains": ...}` for full-text.

## Detailed docs (references/)

- **[references/api.md](references/api.md)** — full client/collection/CRUD API,
  embedding functions, metadata-filter operators, server mode, best practices, perf.
- **[references/integration.md](references/integration.md)** — LangChain and
  LlamaIndex vector-store integration.

## Resources

- GitHub: https://github.com/chroma-core/chroma
- Docs: https://docs.trychroma.com
- License: Apache 2.0
