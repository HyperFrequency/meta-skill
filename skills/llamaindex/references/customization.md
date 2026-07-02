# LlamaIndex Customization

Swap the LLM, embedding model, and prompts globally via `Settings`, or per
component by passing them directly.

## Custom LLM

```python
from llama_index.llms.anthropic import Anthropic
from llama_index.core import Settings

# Global default used by all query/chat engines
Settings.llm = Anthropic(model="claude-sonnet-4-5-20250929")

query_engine = index.as_query_engine()
```

## Custom embeddings

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, VectorStoreIndex

Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

index = VectorStoreIndex.from_documents(documents)
```

Note: the embedding model used at index time must match the one used at query
time, or retrieval quality collapses.

## Custom prompt templates

```python
from llama_index.core import PromptTemplate

qa_prompt = PromptTemplate(
    "Context: {context_str}\n"
    "Question: {query_str}\n"
    "Answer the question based only on the context. "
    "If the answer is not in the context, say 'I don't know'.\n"
    "Answer: "
)

query_engine = index.as_query_engine(text_qa_template=qa_prompt)
```

## Multi-modal RAG (image + text)

```python
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.multi_modal_llms.openai import OpenAIMultiModal

documents = SimpleDirectoryReader(
    "./data", required_exts=[".jpg", ".png", ".pdf"]
).load_data()

index = VectorStoreIndex.from_documents(documents)

multi_modal_llm = OpenAIMultiModal(model="gpt-4o")
query_engine = index.as_query_engine(llm=multi_modal_llm)
response = query_engine.query("What is in the diagram on page 3?")
```

## Evaluation (relevancy + faithfulness)

```python
from llama_index.core.evaluation import RelevancyEvaluator, FaithfulnessEvaluator

# Is the response relevant to the query?
relevancy = RelevancyEvaluator()
print(relevancy.evaluate_response(query="What is Python?", response=response).passing)

# Is the response grounded in retrieved context (no hallucination)?
faithfulness = FaithfulnessEvaluator()
print(faithfulness.evaluate_response(query="What is Python?", response=response).passing)
```
