---
name: opik
version: 0.1.0
description: Opik observability for LLM agents — tracing, Prompt Library, Local Runner (opik connect), Test Suites & evaluation, threads, integrations. Use for "manage my prompts", "connect my agent", "evaluate my agent", "trace my LLM calls", or "integrate with Opik". NOT for general-purpose APM/infra monitoring (use a standard APM), classic non-LLM ML experiment tracking (use Comet ML or MLflow), or building the agent logic itself — Opik only observes and evaluates LLM traces/spans.
---

# Opik — Observability for LLM Agents

Integrating with Opik always means adding both components unless the user explicitly asks for only one:

1. **Tracing** — instrument LLM calls with the appropriate integration or `@opik.track`
2. **Entrypoint** — mark the top-level function with `entrypoint=True` for Local Runner and UI integration

## Setup

**Pick the config mechanism before editing anything.** Inspect the project's existing
approach first and never introduce a second one: if it already loads `.env`, append
`OPIK_API_KEY` / `OPIK_WORKSPACE` there (and update `.env.example`); otherwise use
`~/.opik.config` (Python INI) or a new `.env` (TS). Never overwrite existing values;
prefer `project_name` in code. Full decision tree: `references/setup.md`.

### Config Formats & Deployments

Env vars: `OPIK_API_KEY`, `OPIK_URL_OVERRIDE`, `OPIK_WORKSPACE` (TS uses `OPIK_WORKSPACE`
+ `workspaceName` in `new Opik({...})`). URLs — Cloud `https://www.comet.com/opik/api`
(needs key + workspace); Local OSS `http://localhost:5173/api` (workspace `default`);
self-hosted uses its custom URL. Python without `.env` uses `~/.opik.config` (INI). Set
`project_name` / `projectName` in code, not env. Exact INI/env/interactive snippets and
`opik configure` / `npx opik-ts configure` commands: `references/setup.md`.

## Python Instrumentation

```python
import opik

@opik.track(entrypoint=True, name="my-agent")
def agent(query: str) -> str:
    context = retrieve(query)
    return generate(query, context)

@opik.track(type="tool")
def retrieve(query: str) -> list:
    return search_db(query)

@opik.track(type="llm")
def generate(query: str, context: list) -> str:
    return llm_call(query, context)

result = agent("What is ML?")
opik.flush_tracker()  # required in scripts
```
Valid span types for manual instrumentation: `general`, `llm`, `tool`, `guardrail`.

**Framework integrations** — these capture tokens, model, and cost automatically:

```python
from opik.integrations.openai import track_openai        # OpenAI
from opik.integrations.anthropic import track_anthropic   # Anthropic
from opik.integrations.langchain import OpikTracer        # LangChain
from opik.integrations.crewai import track_crewai         # CrewAI
from opik.integrations.dspy import OpikCallback           # DSPy
from opik.integrations.adk import track_adk_agent_recursive  # Google ADK
```

**CRITICAL — LiteLLM `OpikLogger` inside `@opik.track`:** whenever `litellm.completion` /
`litellm.acompletion` appears in code you instrument with `@opik.track`, pass
`metadata={"opik": {"current_span_data": get_current_span_data()}}` (from
`opik.opik_context`) on every call so the `OpikLogger` callback nests under the active
trace. Without it, `OpikLogger` creates **orphaned top-level traces** separate from your
`@opik.track` hierarchy. Full snippet in `references/tracing-python.md`.

## TypeScript Instrumentation

```typescript
import { Opik } from "opik";

const client = new Opik({ projectName: "my-project" });
const trace = client.trace({ name: "my-agent", input: { query: "What is ML?" } });
const llmSpan = trace.span({ name: "generate", type: "llm", input: { prompt: "What is ML?" } });
// ...model call...
llmSpan.end({ output: { response: "..." } });
trace.end({ output: { response: "..." } });
await client.flush();  // always flush before exit
```

Prefer the client-based path in TypeScript and set `projectName` in code rather than machine-wide config. Valid span types: `general`, `llm`, `tool`, `guardrail`. The `track()` decorator form, framework integrations (Vercel AI SDK, LangChain.js), and full span/trace options are in `references/tracing-typescript.md`.

## Threads (Conversations)

Group conversation turns via `thread_id`. Each turn = one trace; shared `thread_id` = one thread.

```python
@opik.track(entrypoint=True)
def handle_message(session_id: str, message: str) -> str:
    opik.update_current_trace(thread_id=session_id)
    return generate_response(session_id, message)
```

Score whole threads with `opik.evaluation.evaluate_threads(project_name=..., metrics=[...])` using conversation metrics `SessionCompletenessQuality`, `UserFrustrationMetric`, `ConversationalCoherenceMetric` (from `opik.evaluation.metrics.conversation`) — see "Test Suites & Evaluation" below and `references/evaluation.md`.

Use for chat agents, support bots, multi-step assistants. Skip for single-shot agents or batch processing.

**Pitfalls:** Missing `thread_id` → turns appear as unrelated traces. Shared `thread_id` across users → conversations get mixed.

## Test Suites & Evaluation

"Evaluate my agent" means running it against scored test items. **Test Suites** are
the recommended path (legacy `evaluate()` over Datasets still works — see the reference).
A suite pairs test items with natural-language assertions (checked by an LLM judge) and
an execution policy for multi-run reliability. Run it with `opik.run_tests()` (Python) /
`runTests()` (TS); gate CI on `results.all_items_passed` / `results.allItemsPassed`.

```python
import opik

client = opik.Opik()
suite = client.get_or_create_test_suite(
    name="my-agent-suite",
    global_assertions=["Response is factually accurate and not hallucinated"],
    global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
)
suite.insert([{"data": {"input": "Capital of France?"},
               "assertions": ["Correctly identifies Paris"]}])

results = opik.run_tests(
    test_suite=suite,
    task=lambda item: {"input": item["input"], "output": my_agent(item["input"])},
    model="gpt-4o",
)
assert results.all_items_passed  # CI gate
```

**Run evaluations locally:** point `model` / env at a local OSS server
(`OPIK_URL_OVERRIDE=http://localhost:5173/api`) and invoke `run_tests` from a script or
`pytest`; results stream to the local Opik UI under "Test Suites" (not "Datasets").

For multi-turn agents, score whole conversations with `opik.evaluation.evaluate_threads()`
using `metrics=[SessionCompletenessQuality(), UserFrustrationMetric(), ConversationalCoherenceMetric()]`
(see the Threads section). Full suite/dataset/experiment API, the 60+ built-in metrics, and the
legacy `evaluate()` path live in `references/evaluation.md`.

## Prompt Library

Manage versioned prompts through the `opik.Opik` client. Use `create_prompt` / `get_prompt` for string-based prompts and `create_chat_prompt` / `get_chat_prompt` for multi-turn chat templates. Use `{{variable}}` syntax in prompt text for template variables rendered at call time via `.format()`.

**Storing model config alongside the prompt.** Model names, temperatures, and other parameters that you want to version together with the prompt text go in the `metadata` dict on the prompt. They are stored at the prompt version level, so when you fetch a prompt you get both the template and its associated config from `prompt.metadata`.

**CRITICAL — call `get_prompt` / `get_chat_prompt` inside a `@opik.track`-decorated function.** This is what links the fetched prompt version to the trace, making it visible in the Traces view in the Opik UI. Fetching at module level works but the prompt will not appear in traces.

**Python** (fetch inside `@opik.track`; read config back from `prompt.metadata`):

```python
@opik.track(entrypoint=True, project_name="my-agent")
def run_agent(question: str) -> str:
    prompt = client.get_prompt(name="agent-system-prompt")
    system_message = prompt.format(product="Opik")
    return llm_call(model=prompt.metadata["model"], system_prompt=system_message, question=question)
```

Full example (with create-on-first-run fallback), multi-turn chat templates (`create_chat_prompt` / `get_chat_prompt`), and the TypeScript path (`getPrompt` / `createPrompt`): `references/prompt-library.md`.

After the first run the prompt is registered in the library; it can be edited, versioned, and have its metadata updated from the Opik UI, and `get_prompt` / `get_chat_prompt` always return the latest published version with its metadata.

## Local Runner (opik connect)

Pair your local agent with the Opik browser UI. Get a pairing code from the UI, then:

```bash
opik connect --pair <CODE> python3 app.py        # Python
opik connect --pair <CODE> npx tsx app.ts         # TypeScript
```

Replace the trailing command with however you normally start the app.

Python: `@track(entrypoint=True)` + type-hinted parameters for schema discovery.
TypeScript: `track({ entrypoint: true, params: [{name, type}] }, fn)`.

After pairing: entrypoint registered as agent, UI shows input form, jobs from UI or Optimizer trigger runs.

| Issue | Fix |
|-------|-----|
| No entrypoint found | Add `entrypoint=True` (Python) or `entrypoint: true` (TS) |
| Invalid pair code | Codes expire — get a new one |
| Connection refused | Check Opik server (OSS) or API key (Cloud) |


## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Using deprecated `opik.Prompt` / `opik.ChatPrompt` / `opik.Config` | Migrate to `client.get_prompt()` / `client.get_chat_prompt()` from the Prompt library |
| Storing model/temperature in a separate config object | Put them in `metadata` on the prompt — they version together with the template and are read via `prompt.metadata["model"]` etc. |
| Fetching prompt outside `@opik.track` | Prompt won't appear in traces — fetch inside the decorated function |
| Missing entrypoint | Add `entrypoint=True` for Local Runner |
| No thread_id on conversational agent | Wire `thread_id` from session ID |
| TS missing `params` | Add explicit `params` array |
| Missing `flush_tracker()` in scripts | Call before exit |

## References

| Topic | File |
|-------|------|
| Setup config formats (INI / env / interactive) | `references/setup.md` |
| Python SDK (decorators, async, distributed, config, entrypoint) | `references/tracing-python.md` |
| TypeScript SDK (client, decorators, entrypoint, params) | `references/tracing-typescript.md` |
| REST API | `references/tracing-rest-api.md` |
| Prompt Library (chat templates, TypeScript) | `references/prompt-library.md` |
| All integrations | `references/integrations.md` |
| Core concepts (traces, spans, threads, metadata) | `references/observability.md` |
| Test Suites, `run_tests()`, 60+ built-in metrics, legacy `evaluate()` | `references/evaluation.md` |
