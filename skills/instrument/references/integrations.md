# Framework Detection & Integration Reference

Quick-reference for Step 2 (detect frameworks) and Step 4 (add integrations) of the
`instrument` skill. For the full, copy-paste integration code for every provider, see the
canonical Opik integrations reference in the sibling `opik` skill:
`../opik/references/integrations.md`.

## Detection → Integration mapping

Search the codebase's imports for each pattern and apply the matching integration.

| Import pattern | Framework | Integration |
|---|---|---|
| `from openai` / `import OpenAI` | OpenAI | `track_openai` |
| `import anthropic` | Anthropic | `track_anthropic` |
| `from langchain` / `@langchain` | LangChain | `OpikTracer` callback |
| `from langgraph` | LangGraph | `OpikTracer` with `graph=` |
| `from crewai` | CrewAI | `track_crewai` |
| `import dspy` | DSPy | `OpikCallback` |
| `from google` … `genai` | Google Gemini | `track_genai` |
| `import boto3` … `bedrock` | AWS Bedrock | `track_bedrock` |
| `from llama_index` | LlamaIndex | `LlamaIndexCallbackHandler` / `set_global_handler("opik")` |
| `import litellm` | LiteLLM | `OpikLogger` callback |
| `from pydantic_ai` | Pydantic AI | Logfire OTLP bridge |
| `from opik.integrations.adk` / `from google.adk` | Google ADK | `track_adk_agent_recursive` |
| `import ollama` | Ollama | `track_openai` with localhost base_url or manual `@opik.track` |
| `from agents import` / `from openai.agents` | OpenAI Agents SDK | `OpikTracingProcessor` |
| `from haystack` | Haystack | `OpikConnector` |
| `opik-openai` / `trackOpenAI` (TS) | OpenAI (TS) | `trackOpenAI` |
| `opik-vercel` / `OpikExporter` (TS) | Vercel AI SDK | `OpikExporter` |
| `opik-langchain` / `OpikCallbackHandler` (TS) | LangChain.js | `OpikCallbackHandler` |
| `opik-gemini` / `trackGemini` (TS) | Gemini (TS) | `trackGemini` |

Also handled in the canonical reference: AWS SageMaker, AI Suite, Guardrails AI, Harbor,
Instructor, OpenAI-compatible providers (Groq, DeepSeek, Fireworks, OpenRouter, Portkey,
Cohere, BytePlus), OTLP-export frameworks (Autogen/AG2, Agno, LiveKit, Smolagents,
Semantic Kernel, Strands, Pipecat), TypeScript Mastra and Cloudflare Workers AI, and
no-code platforms (Cursor, Dify, Flowise, Langflow, n8n, OpenWebUI).

## Choosing an integration

| Scenario | Recommended approach |
|---|---|
| Single provider with direct SDK support | Provider-specific (`track_openai`, `track_anthropic`, …) |
| OpenAI-compatible provider | `track_openai` with custom `base_url` |
| Multiple providers via one interface | LiteLLM with `OpikLogger` callback |
| Agent framework with direct support | Framework-specific (LangChain, CrewAI, DSPy, …) |
| OTLP-compatible framework | OTLP export to the Opik endpoint |
| No integration available | Manual `@opik.track` decorator |

## Layering note

Framework-level integrations combine with `@opik.track` decorators. When a callback
integration (notably LiteLLM's `OpikLogger`) runs inside `@opik.track` code, pass the
current span context via `metadata` (`{"opik": {"current_span_data": get_current_span_data()}}`)
so the callback nests under the active trace instead of creating orphaned top-level traces.
See the LiteLLM section of `../opik/references/integrations.md` for the exact pattern.
