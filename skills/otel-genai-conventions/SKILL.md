---
name: otel-genai-conventions
version: 0.1.0
description: "OpenTelemetry gen_ai.* semantic conventions for tracing LLM/agent systems — the vendor-neutral wire schema, not a platform. Covers span attributes (request/response/usage/tool/agent), the gen_ai.operation.name taxonomy (chat, embeddings, invoke_agent, execute_tool, evaluate) and SpanKind mapping, opt-in content capture, gen_ai.client.* metric instruments, the gen_ai.evaluation.* convention, and trace-context propagation through Temporal workflows (interceptor Headers, replay/determinism, continue-as-new links). Use when emitting or reading gen_ai.* spans/metrics, choosing a span's operation.name or kind, mapping an LLM SDK's telemetry to OTel, distinguishing gen_ai.* from OpenInference/OpenLLMetry/Langfuse/Vercel-ai.*, or threading trace context across activity boundaries. Do NOT use to operate Phoenix or emit OpenInference (openinference.span.kind, llm.*) — a DIFFERENT schema, use phoenix; nor Temporal METRICS/PromQL (temporal-observability); nor to build a judge/eval runner (judge-panel, skill-eval-runner)."
allowed-tools: Read Write Edit Bash
license: MIT
---

# OTel GenAI Semantic Conventions

The **wire contract** for telemetry from LLM and agent systems: OpenTelemetry's
`gen_ai.*` semantic conventions. This skill is the reference for *what attributes to
set, on which span, with which name and kind* — so traces from the harness, the
`llm-router`, judges, and Temporal workers all speak one schema and any OTLP backend
(Jaeger, Grafana Tempo, Phoenix, Langfuse) can read them.

This is a **schema skill, not a platform skill.** It emits/reads spans; it does not run
a collector or a UI. This file is a router — depth lives in `references/`.

## The one distinction that trips everyone up

**`gen_ai.*` (this skill) and OpenInference (the `phoenix` skill) are two DIFFERENT
schemas for the same traces.** They are not interchangeable and must not be blended on
one span. Pick one per span; dual-emit only via an explicit format toggle.

| | OpenTelemetry GenAI (this skill) | OpenInference (phoenix skill) |
|---|---|---|
| Governance | OpenTelemetry semconv WG (vendor-neutral) | Arize (Phoenix-native) |
| Span kind attr | `gen_ai.operation.name` = `chat`/`invoke_agent`/… | `openinference.span.kind` = `LLM`/`AGENT`/… |
| Model | `gen_ai.request.model` | `llm.model_name` |
| Tokens | `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| Raw I/O | `gen_ai.input.messages` / `gen_ai.output.messages` (structured parts) | `input.value` / `output.value` (+ `.mime_type`) |
| Provider | `gen_ai.provider.name` | `llm.system` |

A donor like tensorzero emits **either** shape behind one config flag
(`format: opentelemetry | openinference`) writing to the *same* span — never both key
families at once. Full crosswalk (adds OpenLLMetry `llm.*`, Langfuse, Vercel `ai.*`,
TraceLoop): **`references/schema-crosswalk.md`**.

## Mental model

One LLM/agent run is a **tree of spans**, each carrying `gen_ai.operation.name`:

```
invoke_agent <agent>        SpanKind.INTERNAL   (the agent turn / root)
 ├─ chat <model>            SpanKind.CLIENT     (one model call)
 │   ├─ execute_tool <name> SpanKind.INTERNAL   (a tool the model asked for)
 │   └─ execute_tool <name> SpanKind.INTERNAL
 └─ chat <model>            SpanKind.CLIENT
      └─ evaluate <scorer>  SpanKind.INTERNAL   (a judge/scorer run — gen_ai.evaluation.*)
```

- **Span name** = `"<operation.name> <model-or-target>"` (e.g. `chat gpt-4o`,
  `execute_tool search`, `invoke_agent researcher`). Low cardinality; no ids in the name.
- **SpanKind**: outbound model/embeddings call → `CLIENT`; in-process agent/tool/eval →
  `INTERNAL`; a span representing a remote sub-service → `CLIENT`/`SERVER`.
- Attributes fall in five families: `gen_ai.request.*` (inputs/params),
  `gen_ai.response.*` (ids/model/finish), `gen_ai.usage.*` (tokens/cost),
  `gen_ai.tool.*` (tool calls), `gen_ai.agent.*`/`conversation.id` (agent identity).
- **Content** (prompts/completions) is opt-in and goes in four JSON-string attributes,
  not scattered fields — see `references/span-conventions.md`.

## Route to the depth you need

| You are… | Read |
|---|---|
| setting attributes on a chat/tool/agent span, or naming it | `references/span-conventions.md` |
| emitting histograms/counters (token usage, op duration, cost) | `references/metric-conventions.md` |
| tracing a judge/scorer/eval run as telemetry | `references/eval-spans.md` |
| threading trace context through Temporal workflows/activities | `references/temporal-propagation.md` |
| mapping another SDK's attrs, or choosing gen_ai vs OpenInference | `references/schema-crosswalk.md` |

## Fast triggers

- "what's the `gen_ai.operation.name` for a tool call?" → `execute_tool`
  (`references/span-conventions.md`).
- "old span uses `gen_ai.system` / `prompt_tokens` — still right?" → **renamed**;
  now `gen_ai.provider.name` / `gen_ai.usage.input_tokens`. Migration table in
  `references/schema-crosswalk.md`.
- "which metric for token counts?" → `gen_ai.client.token.usage` histogram with
  `gen_ai.token.type` = `input|output` (`references/metric-conventions.md`).
- "trace context lost across an activity boundary" → the SDK **tracing interceptor**
  must be installed on client + worker so the span context rides in the workflow
  `Header` (`references/temporal-propagation.md`).
- "how do I record a judge's score on the trace?" → `gen_ai.evaluation.name` +
  `gen_ai.evaluation.score.value`/`.label`/`.explanation` (`references/eval-spans.md`).

## Boundaries / anti-triggers

- **Operating Phoenix, or emitting OpenInference** (`openinference.span.kind`, `llm.*`,
  `input.value`) → use the **phoenix** skill. Different schema; this skill only tells you
  how the two differ.
- **Collecting/alerting on Temporal's own metrics** (worker backlog, PromQL, OpenMetrics
  endpoint) → **temporal-observability**. That skill is metrics-only; *this* one owns the
  distributed-tracing side it explicitly defers.
- **Building a judge panel or an eval runner** → **judge-panel** / **skill-eval-runner**.
  This skill only defines the *telemetry* those runners emit.
- **Instrumenting an SDK's control plane vs. gen_ai payloads** — non-LLM spans use base
  OTel conventions, not `gen_ai.*`.

## Status note (pin awareness)

The `gen_ai.*` conventions are still **Development/experimental** in OTel semconv and
have already renamed keys (`gen_ai.system` → `gen_ai.provider.name`; `prompt_tokens`/
`completion_tokens` → `input_tokens`/`output_tokens`). Pin the semconv version you target
and treat the crosswalk's migration column as load-bearing when reading older traces.

## Cross-links

- **phoenix** — the OpenInference sibling schema + the platform that ingests both.
- **temporal-observability** — Temporal metrics (the tracing counterpart lives here).
- **judge-panel**, **skill-eval-runner** — producers of the `gen_ai.evaluation.*` spans.
- **tensorzero-flywheel**, **trajectory-miner** — upstream/downstream of this trace data.
