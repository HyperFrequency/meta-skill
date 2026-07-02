# LlamaIndex RAG Patterns

End-to-end patterns and the advanced retrieval features most projects reach for.

## Document Q&A system (persisted)

```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

documents = SimpleDirectoryReader("docs").load_data()
index = VectorStoreIndex.from_documents(documents)
index.storage_context.persist(persist_dir="./storage")

query_engine = index.as_query_engine(
    similarity_top_k=3,
    response_mode="compact",
    verbose=True,
)
response = query_engine.query("What is the main topic?")
print(response)
print(f"Sources: {[n.metadata['file_name'] for n in response.source_nodes]}")
```

## Chatbot with memory

```python
chat_engine = index.as_chat_engine(
    chat_mode="condense_plus_context",  # also: "context", "react"
    verbose=True,
)

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    print(f"Bot: {chat_engine.chat(user_input)}")
```

`condense_plus_context` rewrites the follow-up using chat history, then retrieves
fresh context each turn — good default for multi-turn document chat.

## Metadata filtering

```python
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

filters = MetadataFilters(filters=[
    ExactMatchFilter(key="category", value="tutorial"),
    ExactMatchFilter(key="difficulty", value="beginner"),
])

retriever = index.as_retriever(similarity_top_k=3, filters=filters)
query_engine = index.as_query_engine(filters=filters)
```

## Structured output

```python
from pydantic import BaseModel
from llama_index.core.output_parsers import PydanticOutputParser

class Summary(BaseModel):
    title: str
    main_points: list[str]
    conclusion: str

output_parser = PydanticOutputParser(output_cls=Summary)
query_engine = index.as_query_engine(output_parser=output_parser)

summary = query_engine.query("Summarize the document")  # Summary instance
print(summary.title, summary.main_points)
```

## Best practices

1. Use vector indices for most cases — best performance/recall tradeoff.
2. Persist indices to disk — avoid re-embedding on every run.
3. Chunk documents to ~512–1024 tokens.
4. Add metadata — enables filtering and source attribution.
5. Stream long responses for better UX.
6. Enable `verbose=True` during development to inspect retrieval.
7. Evaluate relevancy + faithfulness before shipping.
8. Use a chat engine (not a query engine) when you need conversation memory.
9. Monitor embedding and LLM token costs.

## Approximate latencies

| Operation        | Latency           | Notes                          |
|------------------|-------------------|--------------------------------|
| Index 100 docs   | ~10–30s           | One-time, can persist          |
| Query (vector)   | ~0.5–2s           | Retrieval + LLM generation     |
| Streaming query  | ~0.5s first token | Better perceived latency       |
| Agent w/ tools   | ~3–8s             | Multiple tool-call round trips |
