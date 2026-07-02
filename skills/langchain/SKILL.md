---
name: langchain
description: Framework for building LLM-powered applications - agents (create_agent), tool calling, RAG, and provider-agnostic model access (OpenAI, Anthropic, Google) across 600+ integrations, with LangSmith observability. WHAT - high-level abstractions for chatbots, question-answering/RAG pipelines, and autonomous tool-using agents. WHEN - rapid prototyping or production LLM apps where you want to swap providers, wire up retrieval, or build ReAct-style agents in a few lines. WHEN NOT - for complex stateful/cyclic or multi-agent workflows and human-in-the-loop graphs use LangGraph; for document-Q&A-first retrieval use LlamaIndex; for production search pipelines use Haystack; for a single direct model call with no chains/agents/retrieval, call the provider SDK directly. Note - LangChain v1 (1.x) uses create_agent + LCEL + LangGraph memory; the legacy LLMChain/RetrievalQA/ConversationChain/AgentExecutor APIs are deprecated.
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Agents, LangChain, RAG, Tool Calling, ReAct, Memory Management, Vector Stores, LLM Applications, Chatbots, Production]
dependencies: [langchain, langchain-core, langchain-openai, langchain-anthropic]
---

# LangChain - Build LLM Applications with Agents & RAG

Router skill for the most popular framework for building LLM-powered applications.
Deep, worked examples live in the reference files below — this page is a concise
map of what LangChain is for and how to start.

## When to use LangChain

**Use LangChain when:**
- Building agents with tool calling and reasoning (ReAct pattern)
- Implementing RAG (retrieval-augmented generation) pipelines
- You need to swap LLM providers easily (OpenAI, Anthropic, Google)
- Creating chatbots with conversation memory
- Rapid prototyping of LLM applications
- Production deployments with LangSmith observability

**Use alternatives instead:**
- **LangGraph** — stateful/cyclic workflows, multi-agent systems, human-in-the-loop, fine-grained control. LangChain's `create_agent` is built on LangGraph; reach for raw LangGraph when you outgrow the high-level helper.
- **LlamaIndex** — document-Q&A-first retrieval and indexing.
- **Haystack** — production search pipelines.
- **Semantic Kernel** — Microsoft ecosystem.
- **Provider SDK directly** (`anthropic`, `openai`) — a single LLM call with no chains, agents, or retrieval doesn't need LangChain.

Sibling skills in this collection: the `llamaindex` skill for document-Q&A-first
retrieval, the `rag` skill for framework-agnostic RAG patterns, and the `crewai`
/ `autogpt` skills for their respective agent frameworks.

## Version note (read first)

LangChain **v1 (1.x)** is the current line. APIs changed substantially from 0.x:

| Concept | Current (v1) | Deprecated/legacy (0.x) |
|---------|--------------|--------------------------|
| Agents | `create_agent(...)` | `create_tool_calling_agent` + `AgentExecutor` |
| Chains | LCEL: `prompt \| llm \| parser` | `LLMChain` |
| RAG chain | `create_retrieval_chain` / LCEL | `RetrievalQA`, `ConversationalRetrievalChain` |
| Memory | LangGraph checkpointer + `thread_id` | `ConversationBufferMemory`, `ConversationChain` |
| Pydantic | import from `pydantic` directly | `langchain_core.pydantic_v1` |

Prefer the current column. In v1 the legacy components moved to a separate
package — `pip install langchain-classic`, then import e.g.
`from langchain_classic.chains import LLMChain` (the old `langchain.chains` /
`langchain.memory` paths no longer resolve). The reference files lead with the
v1 APIs but also document these legacy patterns for migration; sections using
them are flagged as legacy.

## Installation

```bash
pip install -U langchain                # core (Python 3.10+)
pip install langchain-openai            # OpenAI provider
pip install langchain-anthropic         # Anthropic provider
pip install langchain-community         # community integrations
pip install langchain-chroma            # vector store
```

## Quick start

### Basic LLM call

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")
response = llm.invoke("Explain quantum computing in 2 sentences")
print(response.content)
```

Swap providers via `ChatOpenAI(model=...)`, `ChatGoogleGenerativeAI(model=...)`,
or the provider-agnostic `init_chat_model("claude-sonnet-4-5-20250929")`.

### Create an agent (v1)

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"It's sunny in {city}, 72F"

agent = create_agent(
    model=ChatAnthropic(model="claude-sonnet-4-5-20250929"),
    tools=[get_weather],
    system_prompt="You are a helpful assistant. Use tools when needed.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in Paris?"}]}
)
print(result["messages"][-1].content)
```

### Structured output (v1)

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    temperature: float
    condition: str

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather],
    response_format=ToolStrategy(WeatherReport),
)
result = agent.invoke({"messages": [{"role": "user", "content": "Weather in SF?"}]})
print(repr(result["structured_response"]))
```

A plain Pydantic model, dataclass, or `TypedDict` passed to `response_format`
auto-selects the provider's native structured-output strategy.

## Where to go next

- **[Agents Guide](references/agents.md)** — agent creation, tool definition, ReAct reasoning traces, parallel/sequential/conditional tool use, streaming agent steps, memory.
- **[RAG Guide](references/rag.md)** — document loaders, text splitters, embeddings, vector stores, retrievers (top-k, MMR, threshold), QA/retrieval chains, conversational RAG, chain types.
- **[Integration Guide](references/integration.md)** — vector store backends (Chroma, Pinecone, FAISS, Weaviate, Qdrant), LangSmith tracing/eval, FastAPI deployment, streaming responses.

## Best practices

1. Use `create_agent()` for most agent use cases; drop to LangGraph only when you need cycles/state.
2. Enable streaming for long responses (better UX).
3. Wrap tool bodies in error handling — tools fail; return readable errors.
4. Use LangSmith tracing for debugging agents and RAG.
5. Tune RAG chunk size (typically 500-1000 chars, ~200 overlap) and cache embeddings.
6. Monitor token usage and cost in production.

## Resources

- **GitHub**: https://github.com/langchain-ai/langchain
- **Docs**: https://docs.langchain.com
- **API Reference**: https://reference.langchain.com/python
- **LangSmith**: https://smith.langchain.com (observability)
- **License**: MIT
