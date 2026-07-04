# GenAI Span Conventions

The span-level `gen_ai.*` attribute registry: what goes on a span, its name, and its
`SpanKind`. Attribute names track OpenTelemetry semconv (Development status). Where a key
was recently renamed, the old form is flagged — see `schema-crosswalk.md` for the full
migration table.

## 1. Operation taxonomy (`gen_ai.operation.name`)

Every gen_ai span carries exactly one `gen_ai.operation.name`. It drives both the span
name and the `SpanKind`.

| `gen_ai.operation.name` | Meaning | Span name | SpanKind |
|---|---|---|---|
| `chat` | A chat/completions model call | `chat <request.model>` | CLIENT |
| `text_completion` | Legacy completion call | `text_completion <model>` | CLIENT |
| `embeddings` | Embedding generation | `embeddings <model>` | CLIENT |
| `generate_content` | Multimodal generate (Gemini-style) | `generate_content <model>` | CLIENT |
| `create_agent` | Agent construction/registration | `create_agent <agent.name>` | INTERNAL / CLIENT |
| `invoke_agent` | One agent turn / run (usually the root) | `invoke_agent <agent.name>` | INTERNAL / CLIENT |
| `execute_tool` | A tool invocation | `execute_tool <tool.name>` | INTERNAL |
| `evaluate` | A scorer/judge run (see `eval-spans.md`) | `evaluate <scorer>` | INTERNAL |

**Span-name rule:** `"<operation.name> <target>"`, low cardinality. The target is the
model for model ops, the agent name for agent ops, the tool name for tools. **Never** put
request ids, user ids, or free text in the span name — those are attributes.

**SpanKind rule:** a call that leaves the process to a model/inference API is `CLIENT`.
In-process orchestration (agent turn, tool dispatch, evaluation) is `INTERNAL`. A span
that models a *remote* sub-service (a remote MCP tool, a downstream agent service) may be
`CLIENT` on the caller and `SERVER` on the callee so the two link into one trace.

## 2. Request attributes (`gen_ai.request.*`)

Set on the span *before* the call.

| Attribute | Type | Notes |
|---|---|---|
| `gen_ai.provider.name` | string | Provider/system, e.g. `openai`, `anthropic`, `azure.ai.inference`. **Renamed from `gen_ai.system`** — older traces use that key. |
| `gen_ai.request.model` | string | Model as requested, e.g. `gpt-4o`, `claude-sonnet-4`. |
| `gen_ai.request.temperature` | double | |
| `gen_ai.request.top_p` | double | |
| `gen_ai.request.top_k` | int | |
| `gen_ai.request.max_tokens` | int | |
| `gen_ai.request.stop_sequences` | string[] | |
| `gen_ai.request.frequency_penalty` | double | |
| `gen_ai.request.presence_penalty` | double | |
| `gen_ai.request.seed` | int | |
| `gen_ai.request.choice.count` | int | `n` > 1. |
| `gen_ai.request.encoding_formats` | string[] | embeddings only. |
| `gen_ai.conversation.id` | string | Stable thread/session id linking multiple spans. |
| `gen_ai.agent.id` / `gen_ai.agent.name` / `gen_ai.agent.description` | string | Agent identity on agent spans. |

## 3. Response attributes (`gen_ai.response.*`)

Set after the call returns.

| Attribute | Type | Notes |
|---|---|---|
| `gen_ai.response.id` | string | Provider response id. |
| `gen_ai.response.model` | string | Model that actually served (may differ from request). |
| `gen_ai.response.finish_reasons` | string[] | e.g. `["stop"]`, `["tool_calls"]`, `["length"]`, `["content_filter"]`. Array — one per choice. |
| `error.type` | string | On failure, the error class (base OTel attr). Set span `Status` to `Error`. |

## 4. Usage attributes (`gen_ai.usage.*`)

| Attribute | Type | Notes |
|---|---|---|
| `gen_ai.usage.input_tokens` | int | **Renamed from `gen_ai.usage.prompt_tokens`.** |
| `gen_ai.usage.output_tokens` | int | **Renamed from `gen_ai.usage.completion_tokens`.** |
| `gen_ai.usage.total_tokens` | int | Some backends derive it; prefer input+output. |

Common **non-standard extensions** seen in the wild (donor-observed; keep the
`gen_ai.usage.` namespace so backends group them): `cache_read.input_tokens`,
`cache_creation.input_tokens` (Anthropic prompt caching), `reasoning.output_tokens`
(o-series/thinking), plus cost extensions `gen_ai.usage.cost`, `.cost.input`,
`.cost.output` (currency in a sibling attr or backend config). Cost is *not* in the
stable spec — it is a widely-adopted extension; document the unit you emit.

## 5. Tool attributes (`gen_ai.tool.*`)

On an `execute_tool` span (and referenced from tool-call parts in content):

| Attribute | Type | Notes |
|---|---|---|
| `gen_ai.tool.name` | string | Tool name. |
| `gen_ai.tool.call.id` | string | Correlates the model's request to this execution. |
| `gen_ai.tool.type` | string | `function`, `custom`, `extension`, `mcp`, etc. |
| `gen_ai.tool.description` | string | |
| `gen_ai.tool.call.arguments` | string (JSON) | Content-gated (opt-in). |
| `gen_ai.tool.call.result` | string (JSON) | Content-gated (opt-in). |

## 6. Content capture (opt-in) — the four structured attributes

Prompts and completions are **off by default** (PII/size). When enabled
(`include_content = true`), the spec puts them in **four JSON-string span attributes**,
not scattered fields — the whole message array is serialized into one string per slot:

| Attribute | Holds |
|---|---|
| `gen_ai.input.messages` | The full input message array. |
| `gen_ai.output.messages` | The output message array (assistant + finish_reason). |
| `gen_ai.system_instructions` | System prompt as a parts array. |
| `gen_ai.tool.definitions` | Tool schemas offered to the model. |

### Message-part JSON shape

Each message is `{ "role": ..., "parts": [ ... ], "finish_reason"?: ... }`. `role` is one
of `system` / `user` / `assistant` / `tool`. A user message whose parts are *all* tool
results is promoted to `role: "tool"` (this is what Phoenix/Langfuse/Jaeger expect). Each
part is `#[serde(tag="type")]`-shaped:

| part `type` | Fields |
|---|---|
| `text` | `content` (string) |
| `reasoning` | `content` (string) — thinking/CoT |
| `tool_call` | `id`, `name`, `arguments` (parsed JSON, or the raw string if unparseable) |
| `tool_call_response` | `id`, `response` (parsed JSON or string) |
| `blob` | inline base64: `modality` (`text`/`image`/`audio`/`video`/`other`), `mime_type`, `content` |
| `uri` | remote file: `modality`, `mime_type`, `uri` |
| `file` | pre-uploaded ref: `modality`, `mime_type`, `file_id` |
| `<vendor>.unknown` | `content` (opaque JSON) — fall-through for shapes the spec can't model |

`finish_reason` appears only on output (assistant) messages; values mirror
`gen_ai.response.finish_reasons` (`stop`, `stop_sequence`, `length`, `tool_call`,
`content_filter`, `unknown`).

**Streaming aggregation.** For a streamed response, buffer chunks and aggregate into the
same `gen_ai.output.messages` shape before setting the attribute: chunks sharing a
`(part-kind, id)` key collapse — text/reasoning fragments concatenate; a tool call's raw
argument fragments concatenate then JSON-parse **once** at the end; the last non-null
`finish_reason` across chunks wins. Key on `(kind, id)` not `id` alone, because some
providers reuse a positional id (`"0"`) across a text part and a thought part in the same
turn — keying on id alone would drop one.

## 7. Content-free by default — design rule

The serde/mapping layer that produces these attributes should be **dependency-free of the
OTel SDK**: map your internal types into `Serialize` structs whose JSON matches the spec
1:1, then `serde_json::to_string(&value)` into the attribute. This keeps the wire contract
visible in the type definitions and lets you unit-test the JSON shape without a tracer.
Emit content attributes only when the caller opted in; usage/model/finish attributes are
always safe to emit.

## 8. Minimal correct `chat` span (checklist)

1. Name `chat <request.model>`, `SpanKind::CLIENT`.
2. Before call: `gen_ai.operation.name=chat`, `gen_ai.provider.name`,
   `gen_ai.request.model`, any params, `gen_ai.conversation.id` if threaded.
3. On success: `gen_ai.response.id`, `gen_ai.response.model`,
   `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens`/`output_tokens`.
4. On error: set `error.type`, span `Status = Error`, still emit whatever usage you have.
5. If content enabled: the four JSON attributes from §6.
