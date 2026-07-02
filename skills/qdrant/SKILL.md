---
name: qdrant
description: High-performance Rust vector similarity search engine for RAG and semantic search. Use when building production RAG systems requiring fast nearest-neighbor search, hybrid search with metadata filtering, or scalable on-premise vector storage with sharding/replication. Do NOT use for simple embedded prototypes (use Chroma), pure raw-speed batch/research workloads (use FAISS), fully-managed zero-ops setups (use Pinecone), or GraphQL/built-in-vectorizer needs (use Weaviate).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [RAG, Vector Search, Qdrant, Semantic Search, Embeddings, Similarity Search, HNSW, Production, Distributed]
dependencies: [qdrant-client>=1.12.0]
---

# Qdrant - Vector Similarity Search Engine

High-performance vector database written in Rust for production RAG and semantic search.
This file is a router; detailed code lives in `references/`.

## When to use Qdrant

**Use Qdrant when:**
- Building production RAG systems requiring low latency
- You need hybrid search (vectors + metadata filtering)
- You require horizontal scaling with sharding/replication
- You want on-premise deployment with full data control
- You need multi-vector storage per record (dense + sparse)
- Building real-time recommendation systems

**Use alternatives instead:**
- **Chroma** - simpler setup, embedded prototypes
- **FAISS** - maximum raw speed, research/batch processing
- **Pinecone** - fully managed, zero ops preferred
- **Weaviate** - GraphQL preference, built-in vectorizers

**Key features:** Rust-powered performance; rich payload filtering during search;
dense/sparse/multi-dense vectors per point; scalar/product/binary quantization;
distributed via Raft consensus (sharding + replication); REST + gRPC with full parity.

## Quick start

```bash
pip install qdrant-client

# Docker (recommended for development), with persistent storage
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

client.upsert(
    collection_name="documents",
    points=[
        PointStruct(id=1, vector=[0.1, 0.2, ...], payload={"category": "tech"}),
        PointStruct(id=2, vector=[0.3, 0.4, ...], payload={"category": "science"}),
    ],
)

results = client.search(
    collection_name="documents",
    query_vector=[0.15, 0.25, ...],
    query_filter={"must": [{"key": "category", "match": {"value": "tech"}}]},
    limit=10,
)
for point in results:
    print(point.id, point.score, point.payload)
```

## Core concepts

**Point** = `id` (int or UUID string) + one or more `vector`s + arbitrary JSON `payload`.
Always batch with `client.upsert(..., points=[...], wait=True)` rather than one at a time.

**Collection** = a container of points with a fixed vector config. Tune the HNSW index at
creation via `HnswConfigDiff(m=16, ef_construct=100, full_scan_threshold=10000)` and set
`on_disk_payload=True` for large payloads. Inspect with `client.get_collection(name)`.

**Distance metrics:**

| Metric | Use Case | Range |
|--------|----------|-------|
| `COSINE` | Text embeddings, normalized vectors | 0 to 2 |
| `EUCLID` | Spatial data, image features | 0 to ∞ |
| `DOT` | Recommendations, unnormalized | -∞ to ∞ |
| `MANHATTAN` | Sparse features, discrete data | 0 to ∞ |

## Best practices

1. **Batch** upsert/search operations for throughput.
2. **Index payload fields** used in filters (`create_payload_index`).
3. **Quantize** large collections (>1M vectors) to cut memory.
4. **Shard** collections >10M vectors.
5. **Enable `on_disk_payload`** for large payloads.
6. **Reuse client instances** (connection pooling); use `prefer_grpc=True` for throughput.

## References

- **[Usage Examples](references/usage-examples.md)** - search (filtered/batch), RAG
  integrations (sentence-transformers, LangChain, LlamaIndex), multi-vector & sparse,
  quantization, payload indexing, production deployment & tuning.
- **[Advanced Usage](references/advanced-usage.md)** - distributed/cluster mode, hybrid
  search with fusion, recommendations, geo/full-text filtering, snapshots, multitenancy,
  async & gRPC clients.
- **[Troubleshooting](references/troubleshooting.md)** - connection/timeout, dimension
  mismatch, empty/slow results, memory and cluster issues, debugging tips.

## Resources

- **GitHub**: https://github.com/qdrant/qdrant
- **Docs**: https://qdrant.tech/documentation/
- **Python Client**: https://github.com/qdrant/qdrant-client
- **Cloud**: https://cloud.qdrant.io
- **Qdrant license**: Apache 2.0 | **Client version**: 1.12.0+
