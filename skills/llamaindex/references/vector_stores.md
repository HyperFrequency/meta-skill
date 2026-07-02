# LlamaIndex Vector Store Integrations

LlamaIndex defaults to a simple in-memory vector store. For persistence and
scale, plug in a dedicated vector store via `StorageContext`. LlamaHub ships
40+ integrations; the three below are the most common.

## Chroma (local, persistent)

```python
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection("my_collection")

vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
```

## Pinecone (managed cloud)

```python
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
import pinecone

pinecone.init(api_key="your-key", environment="us-west1-gcp")
pinecone_index = pinecone.Index("my-index")

vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
```

## FAISS (fast, in-process)

```python
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
import faiss

d = 1536  # embedding dimension (e.g. text-embedding-3-small / ada-002)
faiss_index = faiss.IndexFlatL2(d)

vector_store = FaissVectorStore(faiss_index=faiss_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
```

## Reloading a persisted store

To reload, recreate the vector store pointing at the same backing store, then
pass it to `VectorStoreIndex.from_vector_store(vector_store)` (rather than
`from_documents`), so you don't re-embed.
