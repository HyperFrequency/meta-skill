# Qdrant Usage Examples

Detailed, copy-paste code examples for common Qdrant tasks. For distributed/cluster
mode, hybrid (dense+sparse) search, recommendations, and advanced filtering see
[advanced-usage.md](advanced-usage.md). For error fixes see [troubleshooting.md](troubleshooting.md).

> API note: examples use `client.search(...)`, which remains supported in
> `qdrant-client>=1.12`. The newer unified `client.query_points(...)` API is preferred
> for hybrid/fusion queries (see advanced-usage.md).

## Search operations

### Basic search

```python
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, ...],
    limit=10,
    with_payload=True,
    with_vectors=False,  # Don't return vectors (faster)
)
```

### Filtered search

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(key="category", match=MatchValue(value="tech")),
            FieldCondition(key="timestamp", range=Range(gte=1699000000)),
        ],
        must_not=[
            FieldCondition(key="status", match=MatchValue(value="archived")),
        ],
    ),
    limit=10,
)

# Shorthand dict filter syntax
results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter={
        "must": [
            {"key": "category", "match": {"value": "tech"}},
            {"key": "price", "range": {"gte": 10, "lte": 100}},
        ]
    },
    limit=10,
)
```

### Batch search

```python
from qdrant_client.models import SearchRequest

results = client.search_batch(
    collection_name="documents",
    requests=[
        SearchRequest(vector=[0.1, ...], limit=5),
        SearchRequest(vector=[0.2, ...], limit=5, filter={"must": [...]}),
        SearchRequest(vector=[0.3, ...], limit=10),
    ],
)
```

## RAG integration

### With sentence-transformers

```python
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

encoder = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="knowledge_base",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

documents = [
    {"id": 1, "text": "Python is a programming language", "source": "wiki"},
    {"id": 2, "text": "Machine learning uses algorithms", "source": "textbook"},
]

points = [
    PointStruct(
        id=doc["id"],
        vector=encoder.encode(doc["text"]).tolist(),
        payload={"text": doc["text"], "source": doc["source"]},
    )
    for doc in documents
]
client.upsert(collection_name="knowledge_base", points=points)

def retrieve(query: str, top_k: int = 5) -> list[dict]:
    query_vector = encoder.encode(query).tolist()
    results = client.search(
        collection_name="knowledge_base",
        query_vector=query_vector,
        limit=top_k,
    )
    return [{"text": r.payload["text"], "score": r.score} for r in results]

context = retrieve("What is Python?")
prompt = f"Context: {context}\n\nQuestion: What is Python?"
```

### With LangChain

```python
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Qdrant.from_documents(
    documents, embeddings, url="http://localhost:6333", collection_name="docs"
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

### With LlamaIndex

```python
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext

vector_store = QdrantVectorStore(client=client, collection_name="llama_docs")
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
query_engine = index.as_query_engine()
```

## Multi-vector support

### Named vectors (different embedding models)

```python
from qdrant_client.models import VectorParams, Distance

client.create_collection(
    collection_name="hybrid_search",
    vectors_config={
        "dense": VectorParams(size=384, distance=Distance.COSINE),
        "sparse": VectorParams(size=30000, distance=Distance.DOT),
    },
)

client.upsert(
    collection_name="hybrid_search",
    points=[
        PointStruct(
            id=1,
            vector={"dense": dense_embedding, "sparse": sparse_embedding},
            payload={"text": "document text"},
        )
    ],
)

# Search a specific named vector
results = client.search(
    collection_name="hybrid_search",
    query_vector=("dense", query_dense),
    limit=10,
)
```

### Sparse vectors (BM25, SPLADE)

```python
from qdrant_client.models import SparseVectorParams, SparseIndexParams, SparseVector

client.create_collection(
    collection_name="sparse_search",
    vectors_config={},
    sparse_vectors_config={
        "text": SparseVectorParams(index=SparseIndexParams(on_disk=False))
    },
)

client.upsert(
    collection_name="sparse_search",
    points=[
        PointStruct(
            id=1,
            vector={"text": SparseVector(indices=[1, 5, 100], values=[0.5, 0.8, 0.2])},
            payload={"text": "document"},
        )
    ],
)
```

## Quantization (memory optimization)

```python
from qdrant_client.models import ScalarQuantization, ScalarQuantizationConfig, ScalarType

# Scalar quantization (~4x memory reduction)
client.create_collection(
    collection_name="quantized",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    quantization_config=ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            quantile=0.99,     # Clip outliers
            always_ram=True,   # Keep quantized vectors in RAM
        )
    ),
)

# Search with rescoring of the top candidates
results = client.search(
    collection_name="quantized",
    query_vector=query,
    search_params={"quantization": {"rescore": True}},
    limit=10,
)
```

See advanced-usage.md for product and binary quantization strategies.

## Payload indexing

```python
from qdrant_client.models import PayloadSchemaType

client.create_payload_index(
    collection_name="documents",
    field_name="category",
    field_schema=PayloadSchemaType.KEYWORD,
)

client.create_payload_index(
    collection_name="documents",
    field_name="timestamp",
    field_schema=PayloadSchemaType.INTEGER,
)

# Index types: KEYWORD, INTEGER, FLOAT, GEO, TEXT (full-text), BOOL
```

## Production deployment

### Qdrant Cloud

```python
from qdrant_client import QdrantClient

client = QdrantClient(
    url="https://your-cluster.cloud.qdrant.io",
    api_key="your-api-key",
)
```

### Performance tuning

```python
from qdrant_client.models import HnswConfigDiff

# Optimize for search recall
client.update_collection(
    collection_name="documents",
    hnsw_config=HnswConfigDiff(ef_construct=200, m=32),
)

# Optimize for bulk indexing speed
client.update_collection(
    collection_name="documents",
    optimizer_config={"indexing_threshold": 20000},
)
```
