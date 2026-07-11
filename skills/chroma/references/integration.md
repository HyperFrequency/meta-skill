# Chroma Integration Guide

Integration with LangChain, LlamaIndex, and frameworks.

## LangChain

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Chunk long documents before indexing
docs = RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(documents)

vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)

# Query
results = vectorstore.similarity_search("query", k=3)

# As retriever (control fan-out with search_kwargs)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

## LlamaIndex

```python
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection("docs")

vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Build an index over the Chroma-backed store, then query it
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
query_engine = index.as_query_engine()
response = query_engine.query("What is machine learning?")
```

## Resources

- **Docs**: https://docs.trychroma.com
