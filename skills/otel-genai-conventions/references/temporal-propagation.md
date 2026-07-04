# Trace-Context Propagation Through Durable Temporal Workflows

The hard part of tracing an agent harness is not the attributes — it is keeping **one
trace** intact when the run is a durable Temporal workflow that suspends, restarts on a
different worker, replays from history, and continues-as-new. This is net-new glue: the
gen_ai donors emit spans but know nothing about Temporal; Temporal propagates context but
knows nothing about gen_ai. This file is the seam.

> Scope: **distributed tracing** through workflows. Temporal *metrics* (worker backlog,
> PromQL) belong to the **temporal-observability** skill.

## Where gen_ai spans live in a workflow

Map the two runtimes cleanly:

```
StartWorkflow / RunWorkflow            (Temporal workflow span — the orchestration)
  = invoke_agent <agent>               gen_ai.operation.name, SpanKind.INTERNAL
    ├─ RunActivity model_call          (Temporal activity span)
    │    └─ chat <model>               gen_ai CLIENT span — the real I/O
    ├─ RunActivity run_tool
    │    └─ execute_tool <name>
    └─ RunActivity judge
         └─ evaluate <scorer>
```

**Rule: the model call (`chat`) lives in an ACTIVITY, never in workflow code.** Workflow
code is deterministic and replays; network I/O and non-determinism must be in activities.
So the `gen_ai.*` CLIENT span is created inside the activity, and Temporal's context
propagation makes it a descendant of the workflow span automatically.

## The mechanism: SDK tracing interceptor → Temporal Header

Temporal does not propagate OTel context by ambient thread-locals across process/worker
boundaries. It rides in the workflow/activity **Header** (a key→payload map that is part
of the command and is persisted in event history).

1. Install the SDK's **OpenTelemetry tracing interceptor on BOTH sides** — the client
   (to *inject*) and every worker (to *extract* and to create workflow/activity spans).
   Installing on only one side silently breaks the trace (you get orphan spans).
   - Go: `go.temporal.io/sdk/contrib/opentelemetry.NewTracingInterceptor`
   - Python: `temporalio.contrib.opentelemetry.TracingInterceptor`
   - TypeScript: `@temporalio/interceptors-opentelemetry`
   - Java/Rust-core: the equivalent contrib interceptor / core telemetry layer.
2. On `StartWorkflow` / activity schedule / signal / child-workflow start, the interceptor
   uses the configured **OTel propagator (default W3C TraceContext — `traceparent` +
   `tracestate`)** to serialize the active span context into a Header entry. The Go/Java
   SDKs use the header key **`_tracer-data`**.
3. Because the Header is in **event history**, the context survives worker restarts and is
   re-read on replay — the trace does not fragment when the workflow moves workers or
   resumes after days idle.

You generally do **not** hand-serialize `traceparent` — you install the interceptor and
let it manage the Header. Hand-rolling is only for a non-SDK hop (see §remote).

## Determinism & replay — the trap

Workflow code re-executes from history on replay. Two failure modes:

- **Don't create OTel spans directly in workflow code using wall-clock/rand.** Span
  timestamps and ids would differ per replay, and you'd emit duplicate spans every time
  history is re-run. Let the interceptor create the workflow/activity spans at the
  boundary; keep workflow code span-free except through the interceptor.
- **If you must annotate inside workflow code**, guard on the replay flag
  (`workflow.IsReplaying()` / SDK equivalent) so you emit/log only on the *first*
  execution, not on every replay. The stock interceptors already suppress duplicate span
  emission on replay — respect that; don't add a parallel span you don't guard.

Consequence: the workflow span's *duration* is real (open at first run, closed at
completion), but everything inside it must be replay-safe. Put mutable telemetry
(token counts, content) on **activity** spans, which run exactly once per attempt.

## Continue-as-new — link, don't parent

`continue-as-new` starts a **new run** (new run id, same workflow id) and closes the
current one. Pitfalls:

- The prior run's workflow span has already **ended** — you cannot parent the new run's
  span under it. Model the relationship as an OTel **span link** (new run's span links to
  the previous run's span context, carried in the continued Header), not parent-child.
- A workflow that continues-as-new in a loop (the gepars GEPA-state pattern:
  `GEPAState` JSON in workflow state, continue-as-new at each generation) would otherwise
  build an unbounded parent chain / an ever-growing single trace. Use links + a stable
  **business correlation id** (`gen_ai.conversation.id`, an episode/run id) as the thing
  that ties the generations together for querying, rather than one mega-trace.

## Long-running workflows — bound your spans

A workflow may live for days or months. A single span open that entire time is an
anti-pattern: backends penalize very long open spans, and you lose granularity.

- Keep the workflow-boundary span, but push the real work into **short activity/turn
  spans** that open and close quickly.
- Carry durable identity in **attributes** (`gen_ai.conversation.id`, agent id, run id),
  not in span lifetime. Query "everything for this conversation" by attribute, not by one
  long trace.
- For a heartbeating long activity, prefer periodic child spans or span events over one
  span spanning the whole activity.

## Signals, child workflows, subagents

- **Signals** carry their own Header, so a signal handler's work can join the trace if the
  signaller propagated context. Signal-driven HITL gates (the durable tool-batch /
  human-approval pattern) should propagate the approving context so the resumed branch
  links to the approval.
- **Child workflows** receive the parent's context via the interceptor — so a judge panel
  that spawns N judges as child workflows shows all N under the panel's workflow span
  (`invoke_agent` → children `evaluate`), giving one readable tree for a deliberation.
- **Queries** are synchronous, side-effect-free reads and are normally *not* part of the
  workflow trace; don't force them in.

## Remote / non-SDK hops (MCP over the wire)

When a call leaves Temporal to a remote MCP action (the harness → ContextForge →
remote-MCP pipeline), the receiving side is not a Temporal worker, so the interceptor
Header does not reach it. There, inject W3C `traceparent`/`tracestate` **explicitly** into
the outbound request (HTTP headers, or the envelope metadata — keeping it outside any
encrypted body so intermediaries can read only the trace ids, never payload). The remote
`execute_tool`/`SERVER` span then links to the caller's activity span, closing the trace
across the boundary.

## Setup checklist

1. Interceptor installed on **client + every worker** (both, or the trace fragments).
2. Model/tool/judge I/O in **activities**; workflow code stays replay-safe and span-free
   except via the interceptor.
3. `chat`/`execute_tool`/`evaluate` gen_ai spans emitted **inside** the activities
   (`span-conventions.md`, `eval-spans.md`).
4. continue-as-new relationships modeled as **span links** + a stable correlation
   attribute, not as an unbounded parent chain.
5. A durable **`gen_ai.conversation.id`** on every span so a long-running run is queryable
   without one span spanning its whole lifetime.
6. Remote/off-worker hops inject `traceparent` explicitly (outside the encrypted body).
