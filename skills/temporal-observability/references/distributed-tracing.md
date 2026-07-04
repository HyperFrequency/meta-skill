# Distributed Tracing Through Durable Temporal Workflows

This reference covers the tracing pillar of Temporal observability: how OpenTelemetry
spans stay stitched into **one trace** while a run is a durable Workflow that suspends,
resumes on a different Worker, replays from event history, and continues-as-new. It is the
operational counterpart to the metrics references — set up, propagate, and reason about
traces; do not re-derive metric queries here.

**Scope split — read this before writing anything.**

- **This skill (temporal-observability)** owns *operating the tracing pipeline*: installing
  interceptors on both sides, propagation through the durable fabric, replay/continue-as-new
  trace topology, exporter/Collector wiring, sampling, and correlating traces with metrics
  and logs.
- **`temporal-developer`** owns *authoring the emission inside code* — where a
  `workflow.GetLogger`/manual span call goes in a Workflow or Activity, and the determinism
  rules for writing that code.
- **`otel-genai-conventions`** owns *what attributes go on the span* for LLM/agent work
  (`gen_ai.operation.name`, `gen_ai.usage.*`, etc.). This file is Temporal-native and
  attribute-agnostic; it works for any span, not just gen_ai. That skill's
  `references/temporal-propagation.md` is the gen_ai-flavoured view of the same seam —
  cross-link, don't duplicate.

## Why Temporal tracing is not "just install the OTel SDK"

An in-process OTel setup propagates context through thread-locals / async-context. Temporal
breaks every one of those assumptions:

- A Workflow and its Activities can run in **different processes on different Workers**.
- A Workflow can **sleep for days**, then resume on a Worker that never saw the start span.
- A Workflow **replays** its history (re-executes deterministic code) on recovery, cache
  eviction, or Worker restart — naive span creation would emit duplicate spans every replay.
- `continue-as-new` **ends the current run** and starts a fresh one, so there is no live
  parent span to attach the next run to.

The trace context therefore cannot ride ambient state; it must be **serialized into
Temporal's durable transport** and be replay- and restart-safe.

## The mechanism: tracing interceptor → Temporal Header

Temporal carries trace context in the Workflow/Activity **Header** — a `string → payload`
map attached to the command and **persisted in event history**. Because it is in history,
the context survives Worker restarts and is re-read verbatim on replay, so the trace does
not fragment when the Workflow moves Workers or wakes after idling.

You do not hand-serialize `traceparent`. You install the SDK's OpenTelemetry **tracing
interceptor on BOTH sides** and let it inject/extract via the configured propagator
(default W3C Trace Context: `traceparent` + `tracestate`):

- **Client side** injects the active span context into the Header on `StartWorkflow`,
  signal, activity schedule, and child-workflow start.
- **Worker side** extracts it, creates the Workflow/Activity boundary spans, and re-injects
  for downstream calls.

Installing on only one side is the #1 mistake: you silently get **orphan spans** (Activity
spans with no parent, or a Workflow span disconnected from the starter). Always both.

The Go/Java SDKs use the Header key **`_tracer-data`**; the Core-runtime SDKs manage an
equivalent Header entry internally — you rarely touch the key directly.

### Per-SDK interceptor wiring

| SDK | Interceptor / package | Install points |
|---|---|---|
| Go | `go.temporal.io/sdk/contrib/opentelemetry.NewTracingInterceptor(TracerOptions{})` | add to `client.Options.Interceptors` (covers client + the workers dialed from that client) |
| Python | `temporalio.contrib.opentelemetry.TracingInterceptor()` | pass in `Client.connect(..., interceptors=[TracingInterceptor()])`; the same client's workers inherit it |
| TypeScript | `@temporalio/interceptors-opentelemetry` | client: `OpenTelemetryWorkflowClientInterceptor`; worker activities: `OpenTelemetryActivityInboundInterceptor`; **workflow spans** need the in-sandbox `OpenTelemetryInboundInterceptor`/`OpenTelemetryOutboundInterceptor` **plus** a `makeWorkflowExporter(exporter, resource)` sink on the Worker (see caveat below) |
| Java | `io.temporal.opentracing.OpenTracingClientInterceptor` + `OpenTracingWorkerInterceptor` (OpenTracing API; bridge to OTel with `opentracing-shim`) | client: `WorkflowClientOptions.setInterceptors(...)`; worker: `WorkerFactoryOptions.setWorkerInterceptors(...)` |
| .NET | `Temporalio.Extensions.OpenTelemetry.TracingInterceptor` | add to `TemporalClientConnectOptions.Interceptors` |

Go, Java, and .NET also ship Datadog/OpenTracing variants; the mechanics (both sides, Header
transport) are identical — only the tracer wiring changes.

### TypeScript workflow-span caveat (the sandbox trap)

TS Workflow code runs in a **deterministic sandbox with no I/O**, so it cannot export spans
directly. The interceptor records span data inside the sandbox and hands it out through a
Worker **sink**; `makeWorkflowExporter(otlpExporter, resource)` on the Worker is what
actually ships those Workflow spans to your Collector/backend. If you install the workflow
interceptors but forget the exporter sink, Activity/client spans appear and Workflow spans
silently vanish. (Go/Java/Python create Workflow boundary spans on the Worker directly and
have no equivalent step.)

## Replay & determinism — the trap

Workflow code re-executes from history on replay. Two rules keep traces clean:

- **Never create spans with wall-clock time or random IDs directly in Workflow code.** Their
  timestamps/ids would differ per replay and you would emit duplicate spans each time
  history re-runs. Let the interceptor create the Workflow/Activity boundary spans; keep
  Workflow code span-free except through the interceptor.
- **Put mutable, high-value telemetry on ACTIVITY spans.** Activities run exactly once per
  attempt (network I/O and non-determinism belong there anyway), so token counts, payload
  sizes, external ids, and error detail attach to Activity spans safely.

The stock interceptors already suppress duplicate span emission on replay — respect that.
The Workflow boundary span's **duration is real** (opens at first execution, closes at
Workflow completion), but everything inside must be replay-safe. If you must annotate inside
Workflow code, guard on the replay flag (`workflow.IsReplaying(ctx)` / `workflow.info().isReplaying`
/ SDK equivalent) so the annotation fires only on the first execution.

## Continue-as-new — link, don't parent

`continue-as-new` starts a **new Run** (new run id, same workflow id) and closes the current
one. The prior Run's Workflow span has already **ended**, so you cannot parent the next Run's
span under it. Model the relationship as an OTel **span link** — the new Run's span links to
the previous Run's span context, carried forward in the continued Header — not as
parent-child.

A Workflow that continues-as-new in a loop (per-iteration state reset, entity/actor
workflows, long polling loops) would otherwise build an **unbounded parent chain** or one
ever-growing mega-trace. Instead:

- Use links between consecutive Runs, plus
- a stable **business correlation id** (an episode/session/order id, set as a span attribute
  and, where useful, a Search Attribute) as the thing you query on to reassemble "all Runs
  of this logical execution".

Query by correlation attribute, not by one giant trace.

## Long-running workflows — bound your spans

A Workflow may live for days or months. A single span open that whole time is an
anti-pattern: backends penalize very long open spans and you lose granularity.

- Keep the short-lived Workflow boundary span per Run; push real work into **short
  Activity/turn spans** that open and close quickly.
- Carry durable identity in **attributes** (correlation id, run id), not in span lifetime.
- For a heartbeating long Activity, prefer periodic **child spans or span events** over one
  span covering the whole Activity.

## Trace topology for the other primitives

- **Signals** carry their own Header. A signal handler joins the trace only if the signaller
  propagated context — signal-driven human-in-the-loop gates should propagate the approving
  context so the resumed branch links back to the approval.
- **Child workflows** receive the parent's context via the interceptor, so a parent that
  fans out N children shows all N nested under the parent's Workflow span — one readable tree
  per orchestration.
- **Queries** are synchronous, side-effect-free reads and are normally **not** part of the
  Workflow trace; don't force them in.
- **Nexus / cross-namespace calls** propagate via the same Header mechanism when both sides
  run the interceptor.

## Remote / non-Temporal hops

When a call leaves the Temporal fabric to a non-Worker (an HTTP service, a remote MCP action,
a message on a queue), the interceptor Header does not reach it. Inject W3C
`traceparent`/`tracestate` **explicitly** into the outbound transport (HTTP headers or
envelope metadata), and keep it **outside any encrypted payload body** so intermediaries can
read only the trace ids, never the data. The remote span then links back to the caller's
Activity span, closing the trace across the boundary.

## Exporting and sampling

- **Where spans land:** point the SDK/OTLP exporter at an **OpenTelemetry Collector** and let
  the Collector fan out to your backend(s). This is the same Collector you may already run for
  metrics — see the OpenTelemetry Collector section in `integrations.md` for the
  receiver/processor/exporter pipeline; add a `traces` pipeline alongside the `metrics` one.
- **Sampling:** decide at the **root** (the `StartWorkflow` client span) so a sampling
  decision is consistent for the whole durable execution — a per-hop decision would drop
  Activity spans out from under a sampled Workflow. Prefer **tail-based sampling in the
  Collector** (keep all traces that contain an error or exceed a latency threshold) over
  head sampling, since Temporal's most useful traces are the slow/failed ones.
- **Resource attributes:** set `service.name` distinctly per Worker deployment/task queue so
  a trace shows which fleet handled each Activity.

## Correlating traces with metrics and logs

Tracing does not replace the metrics pillar — it explains it.

- A worker-backlog or schedule-to-start-latency spike (see `worker-health-monitoring.md`)
  tells you **that** tasks are waiting; a trace of one slow Workflow tells you **where** the
  time went (which Activity, which retry, which downstream hop).
- Put the **trace id on logs** (see `structured-logging.md` § log-to-trace correlation) so a
  log line jumps to its trace and vice-versa.
- Keep a stable correlation attribute (episode/run/order id) on spans, logs, and — where
  supported — Search Attributes, so all three pillars pivot on the same key.

Diagnosis order that works: metrics flag the anomaly (USE protocol in the SKILL) → a trace
localizes it to a span → logs on that span/Activity give the detail.

## Setup checklist

1. Tracing interceptor installed on **client + every Worker** (both, or the trace fragments).
2. TypeScript only: `makeWorkflowExporter` sink registered on the Worker, or Workflow spans
   vanish.
3. Model/tool/external I/O in **Activities**; Workflow code stays replay-safe and span-free
   except via the interceptor.
4. Mutable telemetry (counts, payload sizes, errors) on **Activity** spans, not Workflow spans.
5. `continue-as-new` modeled as **span links** + a stable correlation attribute, not an
   unbounded parent chain.
6. Long-running Workflows bounded into short Activity/turn spans; identity in attributes.
7. Remote/off-Worker hops inject `traceparent` explicitly, outside any encrypted body.
8. Exporter → Collector, tail-based sampling on error/latency, distinct `service.name`.
9. Trace id stamped on logs for cross-pillar correlation.

## Validation

Tracing setup is not done until a trace is **queryable end-to-end in the destination
backend**, not just emitted:

- Start one Workflow that schedules at least one Activity.
- In the backend (Jaeger/Tempo/Datadog/etc.), find the trace and confirm it shows **one
  connected tree**: client `StartWorkflow` → Workflow span → Activity span(s). Orphaned
  Activity spans mean an interceptor is missing on one side.
- Force a replay (restart the Worker mid-execution or evict the sticky cache) and confirm the
  trace does **not** gain duplicate spans.
- If the Workflow continues-as-new, confirm consecutive Runs are joined by a **link**, not an
  ever-deepening parent chain.
</content>
</invoke>
