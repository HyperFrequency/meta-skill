# Instrument — Detailed Code Patterns

Verbose patterns relocated from `SKILL.md` to keep the main file a lean router.
For full SDK signatures see the sibling `opik` skill's references
(`../opik/references/tracing-python.md`, `../opik/references/tracing-typescript.md`,
`../opik/references/integrations.md`).

## Entrypoint parameter rules (Step 3)

The function marked `entrypoint=True` **must only accept primitive-typed parameters**
(`str`, `int`, `float`, `bool`, and `list`/`dict` of primitives). Opik reads the
function's type hints to build a UI input form for the Local Runner, and users type
those values into text fields. Complex types (Pydantic models, dataclasses, request
objects, custom classes) cannot be entered there.

If the candidate entrypoint accepts complex types:
1. Look higher in the call chain for a function that already accepts primitives.
2. If none exists, create a thin wrapper that accepts only primitives, unpacks them,
   and calls the original function. Move `entrypoint=True` to the wrapper.

**Bad — complex parameter (do NOT mark as entrypoint):**

```python
# ❌ RecommendRequest is a Pydantic model
@app.post("/recommend")
async def recommend(request: RecommendRequest):
    summary, tool_results = await run_agent(user_message=build_user_message(request))
    return RecommendResponse(city=request.city, recommendations=_extract_recommendations(tool_results), summary=summary)
```

**Good — primitives only:**

```python
@opik.track(name="recommend-agent", entrypoint=True)
async def _run_entrypoint(user_message: str) -> tuple[str, list[dict]]:
    """Opik entrypoint — receives only the user message for Local Runner schema."""
    return await run_agent(user_message=user_message)

@app.post("/recommend")
async def recommend(request: RecommendRequest):
    summary, tool_results = await _run_entrypoint(user_message=build_user_message(request))
    return RecommendResponse(city=request.city, recommendations=_extract_recommendations(tool_results), summary=summary)
```

The wrapper extracts primitive values from the complex object and delegates to the
existing logic. The HTTP handler calls the wrapper, so the trace captures the full
execution.

## Framework integration snippets (Step 4)

**Python:**

```python
# OpenAI
from opik.integrations.openai import track_openai
client = track_openai(OpenAI())  # wrap existing client

# Anthropic
from opik.integrations.anthropic import track_anthropic
client = track_anthropic(anthropic.Anthropic())

# LangChain / LangGraph
from opik.integrations.langchain import OpikTracer
tracer = OpikTracer()
# pass config={"callbacks": [tracer]} to invoke()

# LiteLLM inside @opik.track — CRITICAL: pass span context
from opik.opik_context import get_current_span_data
# in every litellm.completion() call, add:
#   metadata={"opik": {"current_span_data": get_current_span_data()}}
```

**TypeScript:**

```typescript
// OpenAI
import { trackOpenAI } from "opik-openai";
const trackedClient = trackOpenAI(openai);

// Vercel AI SDK
import { OpikExporter } from "opik-vercel";
// set up NodeSDK with OpikExporter
```

## Client tracing scaffolding (Step 5, TypeScript)

```typescript
import { Opik } from "opik";
const client = new Opik({ projectName: "<project-name>" });

// In the entrypoint function:
const trace = client.trace({ name: "<agent-name>", input: { ... } });
const span = trace.span({ name: "<operation>", type: "tool", input: { ... } });
// ... logic
span.end({ output: { ... } });
trace.end({ output: { ... } });
await client.flush();
```

For entrypoints discoverable by `opik connect` — `params` must use only primitive
types (`string`, `number`, `boolean`) since users enter these in a UI text field:

```typescript
import { track } from "opik";

const myAgent = track(
  { name: "<agent-name>", entrypoint: true, params: [{ name: "query", type: "string" }] },
  async (query: string) => { /* ... */ }
);
```

## Prompt migration to the Prompt Library (Step 6)

`get_prompt` / `get_chat_prompt` returns `None` if the prompt doesn't exist yet —
check for `None` and create on first run so the same code handles both initial setup
and subsequent runs. Include model name, temperature, and other call-level parameters
in `metadata` so they version together with the template and can be edited from the
Opik UI without a code change.

**Python — single string prompt:**

```python
opik_client = opik.Opik()

@opik.track(entrypoint=True, project_name="<project-name>")
def run_agent(question: str) -> str:
    prompt = opik_client.get_prompt(name="<prompt-name>")
    if prompt is None:
        prompt = opik_client.create_prompt(
            name="<prompt-name>",
            prompt="<original hardcoded prompt text>",
            metadata={"model": "<model>", "temperature": <value>},
        )
    system_message = prompt.format()  # pass template vars if any: prompt.format(var=value)
    return llm_call(
        model=prompt.metadata["model"],
        temperature=prompt.metadata["temperature"],
        system_prompt=system_message,
        question=question,
    )
```

**Python — multi-turn message list:**

```python
    chat_prompt = opik_client.get_chat_prompt(name="<prompt-name>")
    if chat_prompt is None:
        chat_prompt = opik_client.create_chat_prompt(
            name="<prompt-name>",
            messages=[...],  # original hardcoded messages list
            metadata={"model": "<model>", "temperature": <value>},
        )
    messages = chat_prompt.format()  # pass template vars if any
    return llm_call(
        model=chat_prompt.metadata["model"],
        temperature=chat_prompt.metadata["temperature"],
        messages=messages,
    )
```

**TypeScript:**

```typescript
const opikClient = new Opik({ projectName: "<project-name>" });

const runAgent = track({ entrypoint: true, projectName: "<project-name>" }, async (question: string) => {
    let prompt = await opikClient.getPrompt({ name: "<prompt-name>" });
    if (prompt === null) {
        prompt = await opikClient.createPrompt({
            name: "<prompt-name>",
            prompt: "<original hardcoded prompt text>",
            metadata: { model: "<model>", temperature: <value> },
        });
    }
    const systemMessage = prompt.format();  // pass template vars if any
    const { model, temperature } = prompt.metadata as { model: string; temperature: number };
    return llmCall({ model, temperature, systemMessage, question });
});
```
