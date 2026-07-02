# Chroma API Reference

Detailed code for the Python client. Install: `pip install chromadb`
(JS/TS: `npm install chromadb @chroma-core/default-embed`).

## Clients

```python
import chromadb

client = chromadb.Client()                              # in-memory (ephemeral)
client = chromadb.PersistentClient(path="./chroma_db")  # on-disk, auto-persisted
client = chromadb.HttpClient(host="localhost", port=8000)  # connect to server
```

## Collections

```python
collection = client.create_collection("my_docs")
collection = client.get_collection("my_docs")
collection = client.get_or_create_collection("my_docs")
client.delete_collection("my_docs")

# With a custom embedding function (see below)
collection = client.create_collection(name="my_docs", embedding_function=ef)
```

## Add

```python
collection.add(
    documents=["Doc 1", "Doc 2"],
    metadatas=[{"source": "web"}, {"source": "pdf", "page": 5}],
    ids=["id1", "id2"],
)

# Or supply your own vectors instead of letting Chroma embed
collection.add(embeddings=[[0.1, 0.2], [0.3, 0.4]], documents=["a", "b"], ids=["1", "2"])
```

## Query (similarity search)

```python
results = collection.query(
    query_texts=["machine learning tutorial"],
    n_results=5,
    where={"source": "web"},  # optional metadata filter
)

results["documents"]   # matching docs
results["metadatas"]   # per-doc metadata
results["distances"]   # similarity scores
results["ids"]         # doc ids
```

## Get / Update / Upsert / Delete

```python
collection.get(ids=["id1", "id2"])
collection.get(where={"category": "tutorial"}, limit=10)
collection.get()  # all

collection.update(ids=["id1"], documents=["new content"], metadatas=[{"source": "x"}])

# upsert = update if id exists, else insert (avoids duplicate-id errors)
collection.upsert(ids=["id1"], documents=["content"], metadatas=[{"source": "x"}])

collection.delete(ids=["id1", "id2"])
collection.delete(where={"source": "outdated"})

collection.count()      # number of items
collection.peek(10)     # first n items (default 10), for inspection
```

## Distance metric (cosine vs L2)

Default similarity space is **L2 (squared euclidean)**. Set the space at collection
creation — it cannot be changed afterward. Lower `distances` always means more similar.

```python
collection = client.create_collection(
    name="docs",
    metadata={"hnsw:space": "cosine"},  # "l2" (default) | "cosine" | "ip" (inner product)
)
```

## Metadata filters (`where`)

- Exact: `{"category": "tutorial"}`
- Comparison: `{"page": {"$gt": 10}}` — `$gt $gte $lt $lte $ne $eq`
- Membership: `{"tags": {"$in": ["python", "ml"]}}` — also `$nin`
- Logical: `{"$and": [...]}`, `{"$or": [...]}`
- Full-text on documents: `where_document={"$contains": "keyword"}`

## Embedding functions

```python
from chromadb.utils import embedding_functions

# Default: sentence-transformers all-MiniLM-L6-v2 (no config needed)
collection = client.create_collection("docs")

# OpenAI
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="...", model_name="text-embedding-3-small")

# HuggingFace
hf_ef = embedding_functions.HuggingFaceEmbeddingFunction(
    api_key="...", model_name="sentence-transformers/all-mpnet-base-v2")

# Custom
from chromadb import Documents, EmbeddingFunction, Embeddings
class MyEF(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return embeddings  # your logic
```

## Server mode

```bash
chroma run --path ./chroma_db --port 8000
```

```python
from chromadb.config import Settings
client = chromadb.HttpClient(host="localhost", port=8000,
    settings=Settings(anonymized_telemetry=False))
```

## Best practices

- Use `PersistentClient` so data survives restarts; back up the `chroma_db` dir.
- Add metadata to enable filtering; use unique ids to avoid collisions.
- Batch adds rather than one document at a time.
- Pick an embedding model that balances speed and quality for your domain.
- Use server mode for multi-user / production deployments.

## Rough performance

| Operation        | Latency      | Notes                          |
|------------------|--------------|--------------------------------|
| Add 100 docs     | ~1-3s        | includes embedding             |
| Query (top 10)   | ~50-200ms    | grows with collection size     |
| Metadata filter  | ~10-50ms     | fast with proper indexing      |
