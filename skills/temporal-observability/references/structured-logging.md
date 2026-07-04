# Structured Logging Across Durable Temporal Workflows

This reference covers the logging pillar of Temporal observability: emitting **replay-safe,
structured (JSON) logs** from Workflows, Activities, and Workers, then shipping and
correlating them with traces and metrics. Like the tracing reference, it is written from the
*operate the pipeline* angle.

**Scope split.** `temporal-developer` owns the in-code emission API and the determinism rules
for calling a logger inside Workflow code; that skill's per-SDK observability references
(e.g. `references/go/observability.md`) show the `workflow.GetLogger` / `activity.GetLogger`
call sites. **This skill** owns configuring the logger the SDK uses, making it structured,
correlating it with traces, and getting the lines into a log backend. Cross-link, don't
restate the call-site basics.

## Why Workflow logging is special: replay

Workflow code re-executes from event history on replay (Worker restart, cache eviction,
recovery). A naive `print` / `fmt.Println` / `console.log` / `logger.info` in Workflow code
therefore **fires again on every replay**, producing duplicate, misleading log lines and — if
it does I/O — breaking determinism.

The fix is the SDK's **replay-aware Workflow logger**, which suppresses emission while the
Workflow is replaying and only lets a line through on the **first, real** execution:

| SDK | Workflow logger | Activity logger | Replay suppression control |
|---|---|---|---|
| Go | `workflow.GetLogger(ctx)` | `activity.GetLogger(ctx)` | suppressed by default; re-enable with `worker.Options.EnableLoggingInReplay = true` (debugging only) |
| Python | `temporalio.workflow.logger` (a `LoggerAdapter`) | `temporalio.activity.logger` | adapter's `log_during_replay` (default `False`) |
| TypeScript | `log` from `@temporalio/workflow` | standard logger in Activity context via `activityInfo`/interceptors | replay-suppressed by the Workflow logging bridge |
| Java | `Workflow.getLogger(Class)` | slf4j logger (standard) in Activity | `WorkerFactoryOptions.setEnableLoggingInReplay(true)` (default `false`) |
| .NET | `Workflow.Logger` | `ActivityExecutionContext.Logger` | replay-suppressed by default |

**Rule:** inside Workflow code use only the SDK's Workflow logger — never the language's raw
logger. Inside Activities, either the SDK Activity logger or a standard logger is fine
(Activities are not replayed), but routing it through the Activity logger auto-attaches
Activity/Workflow context.

If you must log inside Workflow code around a non-deterministic-looking branch, the built-in
logger already handles replay — do **not** hand-guard with `IsReplaying` for ordinary logging;
reserve that flag for custom side-effect-free diagnostics only.

## Context the SDK loggers attach for free

The Workflow/Activity loggers enrich every line with durable identifiers, which is what makes
the logs queryable and joinable to traces:

- **Workflow logger:** workflow id, run id, workflow type, task queue, namespace.
- **Activity logger:** the above **plus** activity id, activity type, and **attempt number**
  (critical — it distinguishes retry N's log line from the original attempt's).

Add your own persistent fields with the SDK's "with"/adapter mechanism (e.g. Go
`log.With(logger, "orderId", id)`, Python `workflow.logger` extra dict, Java MDC, TS logger
metadata) so a business correlation id rides on every line.

## Making logs structured (JSON)

The default SDK logger is usually a plain text/console logger. For production, plug a
**structured backend** so lines are JSON with typed fields, not interpolated strings:

- **Go:** the SDK ships one adapter, `log.NewStructuredLogger(slog.New(handler))`, and treats
  `slog` (Go 1.21+) as the universal bridge. Use `slog.NewJSONHandler` for JSON; back it with
  zap/zerolog/logrus via their `slog.Handler` shims. Set it on `client.Options.Logger`.
- **Python:** `workflow.logger`/`activity.logger` are standard-library `logging` adapters —
  attach a JSON formatter (e.g. a `logging.Formatter` that emits JSON, or `python-json-logger`)
  to the root/handler. The adapter's `extra` fields become structured keys.
- **TypeScript:** replace the Runtime logger via `Runtime.install({ logger: new DefaultLogger('INFO', fn) })`
  (or a custom `Logger`) and serialize entries as JSON in the sink.
- **Java / .NET:** these use slf4j / `Microsoft.Extensions.Logging`; configure a JSON encoder
  (logback JSON layout, Serilog, etc.) at the logging-framework level — the SDK just calls
  into it.

Keep the message a short stable string and push variable data into **fields**, so the log
backend can index and filter (e.g. filter by `workflow_type` and `attempt`).

## Log-to-trace correlation

The single highest-value logging move: **stamp the active trace id and span id onto every log
line** so one click pivots between a log and its trace (§ tracing in `distributed-tracing.md`).

- With the OTel tracing interceptor installed, an Activity runs inside the extracted span
  context, so a logging integration that reads the current OTel span (OTel log-appender /
  `slog` + OTel bridge / logback OTel MDC / Serilog OTel enricher) will attach `trace_id` and
  `span_id` automatically.
- Inside **Workflow code**, the current-span context is managed by the interceptor at the
  boundary; prefer to emit correlation from **Activity** logs (which run in a real span once)
  and keep Workflow-level logging to lifecycle events.
- Also stamp the **business correlation id** (episode/session/order id) so logs, spans, and
  Search Attributes all pivot on one key even when trace ids rotate across `continue-as-new`.

## Shipping logs off the Worker

- **Stdout + collector agent (simplest):** write JSON to stdout and let your platform's log
  agent (Fluent Bit, Vector, Datadog agent, the OTel Collector's `filelog` receiver) tail and
  forward it. Works everywhere; no app-side network coupling.
- **OTLP logs pipeline (unified):** the Core-runtime SDKs can forward the SDK/Core's own
  internal logs through the `Runtime` telemetry config, and app logs can be exported over OTLP
  via the OTel logs SDK to the **same Collector** carrying your traces and metrics — a single
  pipeline for all three pillars (see the OpenTelemetry Collector section in `integrations.md`;
  add a `logs` pipeline next to `traces`/`metrics`).
- Prefer one path per environment; don't double-ship the same lines.

## What to log (and what not to)

- **Do:** Workflow start/complete/fail with the correlation id; Activity attempt boundaries
  and terminal errors with `attempt`; non-determinism errors and their cause; heartbeat
  progress for long Activities; retriable-vs-terminal classification on failures.
- **Don't:** log high-volume per-poll or per-heartbeat noise at INFO (it dominates the backend
  and mirrors the poll metrics you already have); log full payloads, PII, secrets, or
  credentials — Temporal payloads may be encrypted at rest, and logs usually are not, so
  logging the decrypted payload defeats that. Log ids and sizes, not bodies.
- Keep **log levels meaningful**: ERROR for terminal/non-retriable, WARN for retriable
  failures that will be retried, INFO for lifecycle, DEBUG for replay-time diagnostics
  (behind `EnableLoggingInReplay`).

## Where logging fits the diagnosis flow

Logs are the **third** pillar, not the first probe. Metrics (USE protocol in the SKILL) flag
*that* something is wrong and *which resource*; a trace (`distributed-tracing.md`) localizes it
to a **span/Activity**; the structured log on that Activity — filtered by workflow id, run id,
and `attempt` — gives the concrete error, input shape, and downstream cause. Design the three
so they share the correlation id and trace id, and this pivot is one query, not a re-hunt.

## Validation

- Trigger a Workflow that runs an Activity which **fails once then succeeds on retry**.
- In the log backend, filter by the run id and confirm you see **distinct lines per attempt**
  (the `attempt` field increments) — not one merged or duplicated entry.
- Restart the Worker mid-execution to force a replay and confirm you do **not** get duplicate
  Workflow-level log lines (replay suppression working).
- Click a log line's `trace_id` and confirm it resolves to the matching trace in the tracing
  backend (correlation working).
</content>
