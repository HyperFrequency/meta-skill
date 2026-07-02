---
name: instrument
version: 0.1.0
description: Add Opik tracing to an existing codebase. Detects language (Python/TypeScript), identifies LLM frameworks, adds appropriate decorators and integrations, marks entrypoints, and wires up environment config. Use for "instrument my code", "add opik tracing", "add observability", or "trace my agent". Not for initial Opik setup or configuration-only tasks — use /opik for setup.
argument-hint: "[file or directory path]"
compatibility: Works with Claude Code, OpenAI Codex, Cursor, and any Agent Skills-compatible tool. Requires a Python or TypeScript project.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
---

# Instrument — Add Opik Tracing to a Codebase

You are instrumenting an existing codebase with Opik observability. Follow these steps precisely.

## Step 1 — Scope

If `$ARGUMENTS` is provided, scope your work to those files or directories. Otherwise, discover the project root and instrument the main application code.

## Step 2 — Detect Language & Frameworks

Scan the codebase to determine:

1. **Language**: Python (look for `*.py`, `pyproject.toml`, `requirements.txt`) or TypeScript (look for `*.ts`, `*.tsx`, `package.json`)
2. **LLM frameworks in use** — search imports for the most common patterns:

| Import pattern | Framework | Integration |
|---|---|---|
| `from openai` / `import OpenAI` | OpenAI | `track_openai` |
| `import anthropic` | Anthropic | `track_anthropic` |
| `from langchain` / `@langchain` | LangChain | `OpikTracer` callback |
| `import litellm` | LiteLLM | `OpikLogger` callback |
| `from crewai` | CrewAI | `track_crewai` |

   These cover the common cases. For the **full detection table** (LangGraph, DSPy, Gemini, Bedrock, LlamaIndex, Pydantic AI, Google ADK, Ollama, OpenAI Agents SDK, Haystack, and all TypeScript integrations), see `references/integrations.md`.

3. **Existing Opik usage** — check if `opik` or `@opik.track` is already imported. If so, audit rather than re-instrument.

## Step 3 — Identify the Call Graph

Find:
- **Entrypoint**: the top-level function that kicks off the agent (e.g., `main`, `run`, `agent`, `handle_message`, a route handler, or whatever the user's main orchestration function is)
- **LLM call sites**: functions that call an LLM provider directly
- **Tool functions**: retrieval, search, API calls, or other tool-like operations
- **Prompts and prompt-related config**: hardcoded prompt strings, system messages, message templates, and any associated model/temperature values — note these as candidates for the Prompt Library (`client.get_prompt` / `client.get_chat_prompt` with `metadata` for model config)

### Entrypoint Parameter Rules

The function marked with `entrypoint=True` **must only accept primitive-typed parameters**: `str`, `int`, `float`, `bool`, and `list`/`dict` of primitives. This is because:
- Opik reads the function's type hints to build an **input form in the UI**
- Users will type these values manually in a text field via the Local Runner
- Complex types (Pydantic models, dataclasses, request objects, custom classes) cannot be entered in a UI input field

**If the candidate entrypoint accepts complex types** (e.g., a request model, a config object, a dataclass):
1. **Look higher in the call chain** for a function that already accepts primitives
2. If none exists, **create a thin wrapper function** that accepts only primitives, unpacks them, and calls the original function. Move the `entrypoint=True` decorator to this wrapper.

See `references/patterns.md` → "Entrypoint parameter rules" for wrapper examples.

## Step 4 — Add Framework Integrations

For each detected framework, add the appropriate integration at the module level. See `references/integrations.md` for the full detection→integration table and `references/patterns.md` → "Framework integration snippets" for ready-to-paste Python/TypeScript patterns. The canonical per-provider code lives in the sibling opik skill at `../opik/references/integrations.md`.

## Step 5 — Add `@opik.track` Decorators (Python) or Client Tracing (TypeScript)

This step adds the tracing scaffolding that the prompt migration in Step 6 relies on. Add decorators first so that the `get_prompt` / `get_chat_prompt` calls introduced next will land inside `@opik.track`-decorated functions.

### Python

Add `import opik` at the top of each file you instrument.

| Function role | Decorator |
|---|---|
| Entrypoint (top-level agent) | `@opik.track(entrypoint=True, name="<agent-name>")` |
| LLM call | `@opik.track(type="llm")` |
| Tool / retrieval | `@opik.track(type="tool")` |
| Guardrail / validation | `@opik.track(type="guardrail")` |
| Other helper in the call chain | `@opik.track` |

- **Entrypoint parameters must be primitives only** (`str`, `int`, `float`, `bool`, `list`, `dict`). If the natural entrypoint takes a complex type, create a wrapper — see Step 3 "Entrypoint Parameter Rules".
- Place the decorator **above** any existing decorators (e.g., above `@app.route`)
- For async functions, `@opik.track` works the same way — no changes needed
- If the function is a **script entrypoint** (not a long-running server), add `opik.flush_tracker()` after the top-level call
- **`client.get_prompt()` / `client.get_chat_prompt()` must be called inside a `@opik.track`-decorated function** — this links the fetched prompt version to the trace so it appears in the Traces view. Fetching at module level works but the prompt won't be visible in traces.

### TypeScript

Use the client-based approach: create an `Opik` client, open a `trace`, open one `span`
per operation (set `type` to `tool`/`llm`/etc.), `end()` each span and the trace with
their outputs, then `await client.flush()`. For entrypoints discoverable by
`opik connect`, use `track({ entrypoint: true, params: [...] }, fn)` with **primitive-only**
`params` (`string`, `number`, `boolean`). See `references/patterns.md` →
"Client tracing scaffolding" for the full code.

## Step 6 — Migrate Prompts to the Prompt Library

For every prompt found in Step 3, replace the hardcoded value with a `get_prompt` / `get_chat_prompt` call inside the enclosing `@opik.track`-decorated function added in Step 5.

**Classify each prompt:**
- Single string (system prompt, instruction, template) → `create_prompt` / `get_prompt`
- List of `{"role", "content"}` messages → `create_chat_prompt` / `get_chat_prompt`

**Include model name, temperature, and any other call-level parameters in `metadata`** so they version together with the prompt template and can be updated from the Opik UI without a code change.

`get_prompt` / `get_chat_prompt` returns `None` if the prompt doesn't exist yet — check for `None` and create on first run so the same code handles both initial setup and subsequent runs.

See `references/patterns.md` → "Prompt migration to the Prompt Library" for the full Python (single string and multi-turn message list) and TypeScript code.

## Step 7 — Conversational Agents: Add `thread_id`

If the agent handles multi-turn conversations (chat bots, support agents, multi-step assistants), wire `thread_id`:

```python
@opik.track(entrypoint=True)
def handle_message(session_id: str, message: str) -> str:
    opik.update_current_trace(thread_id=session_id)
    return generate_response(session_id, message)
```

Skip this for single-shot agents or batch processing.

## Step 8 — Environment Config

Follow the setup decision tree from the main opik skill:

1. If the project has `.env` / `.env.local` → append `OPIK_API_KEY`, `OPIK_WORKSPACE`, `OPIK_URL_OVERRIDE` (if missing)
2. If no `.env` exists → Python: create/update `~/.opik.config`; TypeScript: create `.env` or `.env.local`
3. Never introduce a second config mechanism
4. Never overwrite existing values
5. Update `.env.example` / `.env.sample` if one exists
6. Set `project_name` in code, not in env files

### `OPIK_URL_OVERRIDE` path rules

The URL suffix depends on where Opik is hosted:

| Deployment | URL format | Example |
|---|---|---|
| Opik Cloud / managed | `<base>/opik/api` | `https://www.comet.com/opik/api` |
| Self-hosted (local) | `<base>/api` | `http://localhost:5173/api` |

- **Cloud/managed**: always append `/opik/api`
- **Self-hosted** (typically `localhost` or an internal hostname): append only `/api` — no `/opik` prefix
- When writing or suggesting an `OPIK_URL_OVERRIDE` value, apply this rule so users don't have to remember it

## Step 9 — Install Dependencies

Print the install command but do NOT run it automatically. Let the user decide.

**Python:**
```
pip install opik
```
Plus any integration packages if needed (most are included in `opik`).

**TypeScript:**
```
npm install opik
```
Plus framework-specific packages: `opik-openai`, `opik-vercel`, `opik-langchain`, `opik-gemini` as needed.

## Step 10 — Verify

After instrumentation, do a quick audit:

- [ ] Every LLM call site is traced (via integration wrapper or `@opik.track`)
- [ ] Exactly one function has `entrypoint=True`
- [ ] The entrypoint function accepts only primitive parameters (`str`, `int`, `float`, `bool`, `list`, `dict`) — no Pydantic models, dataclasses, or custom classes
- [ ] Script entrypoints call `opik.flush_tracker()` (Python) or `await client.flush()` (TypeScript)
- [ ] LiteLLM calls inside `@opik.track` pass `current_span_data` via metadata
- [ ] No hardcoded API keys were introduced
- [ ] Existing tests still import correctly (no circular imports introduced)
- [ ] No deprecated `opik.Prompt` / `opik.ChatPrompt` / `opik.Config` usage introduced — use the Prompt library instead
- [ ] All `client.get_prompt()` / `client.get_chat_prompt()` calls are inside `@opik.track`-decorated functions — prompt version will not appear in traces otherwise

## Anti-Patterns to Avoid

- **Double-wrapping**: Don't add `@opik.track(type="llm")` to a function that already uses a framework integration (e.g., `track_openai`). The integration handles tracing.
- **Orphaned LiteLLM traces**: Always pass `current_span_data` when `OpikLogger` is used inside `@opik.track` code.
- **Complex entrypoint parameters**: The entrypoint function must only accept primitives (`str`, `int`, `float`, `bool`, `list`, `dict`). Pydantic models, dataclasses, or custom classes can't be typed into a UI input field. If the natural entrypoint takes a complex type, create a thin wrapper that accepts primitives.
- **Using deprecated `opik.Prompt` / `opik.ChatPrompt` / `opik.Config`**: These have been retired. Use `client.get_prompt()` / `client.get_chat_prompt()` from the Prompt library instead.
- **Fetching prompts outside `@opik.track`**: `client.get_prompt()` / `client.get_chat_prompt()` must be called inside a `@opik.track`-decorated function. Fetching at module level works functionally but the prompt version won't be linked to the trace and won't appear in the Traces view.
- **Missing entrypoint**: Without `entrypoint=True`, Local Runner (`opik connect`) won't discover the agent.
- **Missing flush**: Scripts that exit without flushing lose trace data.
- **Overwriting config**: Check before writing to `.env` or `~/.opik.config`.

## References

For detailed API signatures and advanced patterns, see:
- `references/integrations.md` — framework detection→integration table and selection guide
- `references/patterns.md` — full code for Steps 3–6 (entrypoint wrappers, integration snippets, prompt migration)

For deeper Opik SDK reference, see the sibling `opik` skill:
- `../opik/references/tracing-python.md` — Python SDK reference
- `../opik/references/tracing-typescript.md` — TypeScript SDK reference
- `../opik/references/integrations.md` — canonical per-provider integration code
- `../opik/references/observability.md` — Core concepts (traces, spans, threads)
