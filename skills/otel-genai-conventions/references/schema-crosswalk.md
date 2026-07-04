# Schema Crosswalk — gen_ai.* vs the Other GenAI Telemetry Schemas

Multiple projects independently invented attribute schemas for LLM traces. They overlap in
intent, differ in keys, and **must not be mixed on one span**. This file (a) lists the
key renames *within* `gen_ai.*`, and (b) maps `gen_ai.*` against the other families so you
can ingest foreign traces or decide which to emit. All attribute keys below are public
convention facts.

## A. Migration within `gen_ai.*` (read old traces correctly)

The conventions renamed keys mid-flight. When reading historical traces, normalize:

| Old key | Current key | What |
|---|---|---|
| `gen_ai.system` | `gen_ai.provider.name` | Provider identity |
| `gen_ai.usage.prompt_tokens` | `gen_ai.usage.input_tokens` | Input tokens |
| `gen_ai.usage.completion_tokens` | `gen_ai.usage.output_tokens` | Output tokens |
| `gen_ai.completion` / `gen_ai.prompt` (flat) | `gen_ai.output.messages` / `gen_ai.input.messages` (structured) | Content capture |
| `gen_ai.content.prompt` / `.completion` | `gen_ai.input.messages` / `.output.messages` | Content (OpenLLMetry-era flat form) |
| per-role events (`gen_ai.system.message`, `gen_ai.user.message`, `gen_ai.assistant.message`, `gen_ai.tool.message`, `gen_ai.choice`) | consolidated `gen_ai.input.messages` / `gen_ai.output.messages` | Content moved from span *events* to structured span *attributes* |

Emit the **current** keys. A robust ingester accepts both and canonicalizes to current.

## B. The four families you'll actually see

### 1. OpenTelemetry GenAI — `gen_ai.*` (this skill)
Vendor-neutral, governed by the OTel semconv WG. Structured message parts, explicit
operation taxonomy, standard metric instruments. **This is the canonical target.**

### 2. OpenInference — the **phoenix** skill's schema (DIFFERENT — do not blend)
Arize's schema, native to Phoenix/`arize-phoenix`. Same traces, different keys and a
different span-kind attribute. A donor emits *either* gen_ai *or* OpenInference behind one
`format` flag, writing to the same span — **never both key families at once**.

| Concept | gen_ai.* | OpenInference |
|---|---|---|
| Span kind | `gen_ai.operation.name` = `chat`/`invoke_agent`/`execute_tool`/… | `openinference.span.kind` = `LLM`/`AGENT`/`TOOL`/`CHAIN`/`RETRIEVER`/`EMBEDDING`/`RERANKER` |
| Provider | `gen_ai.provider.name` | `llm.system` |
| Model | `gen_ai.request.model` | `llm.model_name` |
| Input tokens | `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| Output tokens | `gen_ai.usage.output_tokens` | `llm.token_count.completion` |
| Total tokens | `gen_ai.usage.total_tokens` | `llm.token_count.total` |
| Structured input | `gen_ai.input.messages` (parts JSON) | `llm.input_messages.<i>.message.role` / `.content` (indexed) |
| Raw input | — (parts only) | `input.value` + `input.mime_type` |
| Raw output | — (parts only) | `output.value` + `output.mime_type` |
| Tool call | `gen_ai.tool.name`/`.call.id`/`.call.arguments` | `tool_call.function.name` / `.arguments`, `tool.name` |

Decision: **if the sink is Phoenix and you want its native UI affordances, emit
OpenInference and use the phoenix skill.** If you want a vendor-neutral schema any OTLP
backend reads (Phoenix reads gen_ai.* too), emit gen_ai.*. Choose once per pipeline; don't
straddle.

### 3. OpenLLMetry / Traceloop — `llm.*` + flat content
The Traceloop lineage (and its `llm.*` prefix) predates the structured gen_ai content
form. Common keys: `llm.request.type`, `llm.request.model`, `llm.usage.total_tokens`,
`llm.token_count.prompt`/`completion` (shared with OpenInference), and flat content in
`gen_ai.prompt`/`gen_ai.completion`. Map `llm.*` model/usage → `gen_ai.request.*`/
`gen_ai.usage.*`; expand flat prompt/completion into structured messages on ingest.

### 4. Langfuse — `langfuse.observation.*`
Langfuse's OTLP dialect namespaces under `langfuse.observation.*`
(`.input`, `.output`, `.cost_details`, `.completion_start_time`, and
`.metadata.<...>` including session/provider). It is OTLP-compatible on the wire but its
own key family. Map `.input`/`.output` → content attrs, `.cost_details` → the cost
extension, `.metadata.session_id` → `gen_ai.conversation.id`.

### 5. Vercel AI SDK — `ai.*`
The Vercel `ai` SDK emits `ai.model.id`, `ai.model.provider`, `ai.prompt` /
`ai.prompt.messages`, `ai.response.text` / `ai.result.text`, `ai.usage.tokens`,
`ai.settings.mode`, `ai.chat_stream`. Map: `ai.model.id`→`gen_ai.request.model`,
`ai.model.provider`→`gen_ai.provider.name`, `ai.usage.tokens`→split into
`gen_ai.usage.input_tokens`/`output_tokens` (Vercel often reports a combined figure — do
not assume it's total unless the SDK version splits it).

## C. Ingest strategy (many schemas in → one canonical out)

If your `trace-store` must accept traces from arbitrary SDKs (it will):

1. **Detect** the family by its signature key: `openinference.span.kind` → OpenInference;
   `langfuse.observation.*` → Langfuse; `ai.model.provider` → Vercel; `gen_ai.system`
   (no `provider.name`) → old gen_ai/OpenLLMetry; `gen_ai.provider.name` → current gen_ai.
2. Run a family-specific **extractor** (model, provider, I/O, params, usage, tool,
   prompt-name, metadata) that reads that family's keys.
3. **Canonicalize** to current `gen_ai.*` keys, compute usage+cost, and (optionally)
   promote a fixed set of high-value fields into typed columns while keeping the full
   attribute map — a hybrid typed-columns + attribute-bag schema.

Keep detection and extraction **per-family and testable** — never a giant if-chain inline
in the ingest hot path; one extractor trait per family, dispatched by the signature key.

## D. The single rule

**One span, one schema.** Dual-emit is legitimate only as an explicit format toggle that
writes two *separate* exports (or two spans), never as mixed keys on one span. When in
doubt, emit current `gen_ai.*` and let a downstream mapper produce vendor dialects.
