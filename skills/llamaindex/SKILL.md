---
name: llamaindex
description: Python data framework for building RAG (retrieval-augmented generation) and document-Q&A applications over private data. Covers ingestion (300+ LlamaHub connectors), indexing (vector/list/tree), query & chat engines, retrievers, function-calling agents, vector-store integrations (Chroma/Pinecone/FAISS), multi-modal RAG, and response evaluation. Use when building document Q&A, knowledge-base chatbots, or RAG pipelines. Use when the user names llama-index/LlamaIndex/LlamaHub. NOT for general-purpose agent orchestration or complex multi-step workflows (use LangChain), production search pipelines (Haystack), or when you only need raw vector storage (Chroma/FAISS directly).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Agents, LlamaIndex, RAG, Document Ingestion, Vector Indices, Query Engines, Knowledge Retrieval, Data Framework, Multimodal, Private Data, Connectors]
dependencies: [llama-index, openai, anthropic]
---

# LlamaIndex - Data Framework for LLM Applications

LlamaIndex connects LLMs to your data: ingest documents, index them, and query
them with RAG. This file is a router — concept overview plus pointers into
`references/` for the detailed, copy-pasteable guides.

## When to use

**Use LlamaIndex when:**
- Building RAG / retrieval-augmented generation applications
- Document question-answering over private data
- Ingesting from many sources (300+ LlamaHub connectors)
- Building knowledge bases or enterprise chatbots
- Structured data extraction from documents

**Use something else when:**
- **LangChain** — general-purpose agents, complex multi-step workflows
- **Haystack** — production search pipelines
- **txtai** — lightweight semantic search
- **Chroma / FAISS directly** — you only need raw vector storage, no LLM layer

## Quick start

```bash
pip install llama-index                      # starter (bundles common integrations)
# or minimal core + pick integrations:
pip install llama-index-core llama-index-llms-openai llama-index-embeddings-openai
```

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()   # 1. load
index = VectorStoreIndex.from_documents(documents)        # 2. index (embeds chunks)
query_engine = index.as_query_engine()                    # 3. query engine
print(query_engine.query("What did the author do growing up?"))
```

## Core concepts

- **Data connectors** — load documents from files, web, GitHub, databases, APIs.
  `SimpleDirectoryReader` handles local files; LlamaHub covers the rest.
- **Indices** — structure data for retrieval. `VectorStoreIndex` (semantic
  search, the default choice), `ListIndex` (sequential), `TreeIndex`
  (hierarchical summaries). Persist with `index.storage_context.persist(...)`
  and reload with `load_index_from_storage`.
- **Query engines** — `index.as_query_engine()`: retrieve chunks + generate an
  answer. Configure `similarity_top_k`, `response_mode`, `streaming`.
- **Retrievers** — `index.as_retriever()`: return raw nodes without generation;
  subclass `BaseRetriever` for custom logic.
- **Chat engines** — `index.as_chat_engine()`: query engine + conversation memory.
- **Agents** — `FunctionAgent` calls Python functions and query-engine tools,
  deciding when to search docs vs. invoke a tool.

```python
# Persist / reload an index
index.storage_context.persist(persist_dir="./storage")
from llama_index.core import load_index_from_storage, StorageContext
index = load_index_from_storage(StorageContext.from_defaults(persist_dir="./storage"))
```

## Detailed guides (references/)

- **[Query engines](references/query_engines.md)** — response modes, streaming,
  top-k, custom prompts, source attribution.
- **[Agents](references/agents.md)** — function tools, RAG agents
  (`QueryEngineTool`), multi-step reasoning.
- **[Data connectors](references/data_connectors.md)** — `SimpleDirectoryReader`,
  web/database/JSON loaders, custom loaders, the 300+ LlamaHub catalogue.
- **[Vector stores](references/vector_stores.md)** — Chroma, Pinecone, FAISS via
  `StorageContext`; reloading without re-embedding.
- **[Customization](references/customization.md)** — swap LLM/embeddings via
  `Settings`, custom prompt templates, multi-modal RAG, evaluation.
- **[RAG patterns](references/patterns.md)** — complete Q&A + chatbot pipelines,
  metadata filtering, structured (Pydantic) output, best practices, latencies.

## LlamaIndex vs LangChain

| Feature         | LlamaIndex          | LangChain                 |
|-----------------|---------------------|---------------------------|
| Best for        | RAG, document Q&A   | Agents, general LLM apps  |
| Data connectors | 300+ (LlamaHub)     | 100+                      |
| RAG focus       | Core feature        | One of many               |
| Learning curve  | Easier for RAG      | Steeper                   |

Pick LlamaIndex when RAG/document Q&A is the primary use case and you want many
connectors with a simpler API; pick LangChain for complex agents and flexible
multi-step workflows.

## Resources

- **GitHub**: https://github.com/run-llama/llama_index (45,000+ stars)
- **Docs**: https://developers.llamaindex.ai/python/framework/
- **LlamaHub** (connectors): https://llamahub.ai
- **LlamaCloud** (enterprise): https://cloud.llamaindex.ai
- **Version**: 0.14.x (latest 0.14.23 as of 2026-06) · **License**: MIT
