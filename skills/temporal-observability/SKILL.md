---
name: temporal-observability
description: 'The whole Temporal observability pillar -- metrics, tracing, and logging across Temporal Cloud and self-hosted, not metrics alone. METRICS: Cloud OpenMetrics endpoint, SDK/self-hosted metrics, integrations (Datadog, Grafana, New Relic, Prometheus, OTel Collector, ClickStack), worker-fleet health, PromQL v0-to-v1 migration, USE diagnosis. TRACING: OpenTelemetry interceptors propagated through durable Workflows via Temporal Headers, replay-safe spans, continue-as-new links, Collector export. LOGGING: replay-aware workflow/activity loggers, JSON sinks, log-to-trace correlation. Use for Temporal metrics/monitoring/alerting, metrics.temporal.io, worker backlog, OpenMetrics, PromQL migration, Temporal tracing, OTel spans through Workflows, trace propagation, or replay-safe/structured logging. Not for writing Workflows/Activities or in-code logger/span emission (temporal-developer), Worker tuning (temporal-workertuning), Cloud admin (temporal-cloud), or the gen_ai.* span-attribute schema (otel-genai-conventions).'
version: 0.2.0
---

# Skill: temporal-observability

## Overview

This skill covers the full Temporal observability pillar — **metrics**, **distributed tracing**, and **structured logging** — across setup, querying, alerting, and diagnosis. Metrics tell you *that* something is wrong and which resource; a trace localizes it to a span/Activity; a structured log on that span gives the detail. The three share a correlation id so you pivot between them in one query (see the cross-pillar notes in `distributed-tracing.md` and `structured-logging.md`).

For the metrics work it operates in three modes:

- **Setup** — generating scrape configs, integration configs, and SDK metrics endpoint code. Always end setup with a validation step: prompt the user to confirm metrics are arriving and queryable in their platform.
- **Query** — writing PromQL, Datadog metric query syntax, or NRQL queries for dashboards and alerts.
- **Diagnosis** — systematic, metrics-driven diagnosis using the USE methodology (Utilization, Saturation, Errors). Follow the Diagnosis Protocol below.

You produce configs, queries, and code snippets. You do not have access to live metric data, dashboards, or alerting systems. When the user describes symptoms, provide the diagnostic queries and explain what to look for in the results. This skill owns the metrics collection and query layer. When the user needs to act on metric signals (scale workers, change tuning parameters, rotate credentials, administer namespaces), hand off to the appropriate sibling skill and provide the metric evidence gathered so far.

**Scope boundary:** This skill covers all three observability pillars from the *operate-the-pipeline* angle, and delineates cleanly from the code-authoring and schema siblings:

- **Metrics** — collection, querying, alerting, and metrics-driven diagnosis (the bulk of the references below).
- **Distributed tracing** — installing OpenTelemetry tracing interceptors on both sides, propagation through the durable Workflow fabric (Temporal Headers, replay/determinism, continue-as-new link semantics), Collector export, sampling, and correlating traces with metrics/logs. See `references/distributed-tracing.md`.
- **Structured logging** — configuring replay-aware Workflow/Activity loggers, making them JSON, log-to-trace correlation, and shipping to a backend. See `references/structured-logging.md`.

What this skill does **not** own: authoring the emission *inside* code — where a `workflow.GetLogger`/span call goes in a Workflow/Activity and the determinism rules for writing it — is `temporal-developer` (its per-SDK `observability.md` references show the call sites). Writing *custom application metrics* from inside Workflow/Activity code (via the SDK metrics handler, e.g. `workflow.GetMetricsHandler`) is likewise `temporal-developer`; this skill collects/scrapes/queries/alerts on metrics the SDK already emits. And the `gen_ai.*` **span-attribute schema** for LLM/agent traces (what attributes go on a span) belongs to `otel-genai-conventions` — this skill is Temporal-native and attribute-agnostic; its tracing reference works for any span. Cross-link those; don't duplicate them.

## How to Use This Skill

### Step 1: Determine the metric source

Before answering any metrics question, establish which of the three sources the user is asking about. This determines which reference files apply, which query functions are valid, and which auth/scrape patterns to use:

- **Cloud metrics** (`temporal_cloud_v1_*` only) — from `metrics.temporal.io`, API key auth. Never use `rate()`. Never recommend deprecated `temporal_cloud_v0_*` metrics.
- **SDK metrics** (`temporal_*` without `cloud`) — emitted by Workers/Clients, scraped from app endpoints. `rate()` is correct here.
- **Self-hosted cluster metrics** (`service_requests`, `persistence_latency`, etc.) — emitted by the Temporal Service itself. `rate()` is correct here.

If the source is ambiguous, ask before writing queries.

### Step 2: Determine the deployment context

Cloud, self-hosted, or dev server. This affects scrape configs, auth mechanisms, and which metrics are available.

### Step 3: Determine the observability platform

Prometheus, Datadog, Grafana Cloud, New Relic, ClickStack, or OTel Collector. This affects config format, query language, and available features.

### Step 4: For SDK metrics, determine the SDK language

Histogram units differ: milliseconds for Core-based SDKs (TypeScript, Python, .NET, Ruby, and PHP) vs seconds for Go and Java. Getting this wrong produces thresholds that are off by 1000x.

### Multi-file routing for common questions

Most real questions require 2-3 reference files:

- **"Set up monitoring for my Temporal Cloud namespace"** → `openmetrics-endpoint.md` (auth + scrape) + `integrations.md` (platform config) + `service-health-monitoring.md` (what to alert on) + `worker-health-monitoring.md` (worker fleet).
- **"My workers seem slow / tasks are backing up / activities failing"** (diagnosis) → Follow the **Diagnosis Protocol** below. Consult `ops-diagnostics-reference.md` (USE framework, decision trees, metric mappings) + `worker-health-monitoring.md` (thresholds, queries) + `service-health-monitoring.md` (failure rates, limits) + `troubleshooting.md` (per-bottleneck root causes). For worked examples: `diagnosis-examples.md`. If they need to act on findings: hand off to `temporal-workertuning`.
- **"Migrate from v0 to v1"** → `migration-v0-to-v1.md` (mapping table + auth changes). Only relevant for users already on v0 — never suggest v0 to new users. v0 is deprecated and unavailable to new accounts.
- **"What metrics should I watch?"** → `service-health-monitoring.md` + `worker-health-monitoring.md` for the essential observation set.
- **"Trace / instrument tracing through my Workflows"** (spans keep breaking across replay/continue-as-new, orphan spans, set up the tracing interceptor) → `distributed-tracing.md` (interceptor both-sides, Header propagation, replay/determinism, continue-as-new links, export/sampling). For *what gen_ai.\* attributes to put on the spans*: hand off to `otel-genai-conventions`. For *where the emission call goes in code*: `temporal-developer`.
- **"Structured / replay-safe logging"** (duplicate log lines on replay, JSON logs, correlate logs with traces) → `structured-logging.md` (replay-aware loggers per SDK, JSON sinks, log-to-trace correlation, shipping). For the in-code logger call site and determinism rules: `temporal-developer`.

## Diagnosis Protocol (USE Methodology)

When the user describes a symptom (slow workflows, growing backlog, activity failures, high latency), run the systematic 5-step USE protocol (Utilization, Saturation, Errors). **Never diagnose without metrics data.**

1. **D1 Classify** — map the symptom to a category (Throughput/Backlog, Failure/Error, Latency, Resource Pressure) or hand off (`temporal-cloud` for connectivity/auth, `temporal-workertuning` for tuning requests).
2. **D2 Detect Environment** — Cloud vs self-hosted vs dev server, SDK language (drives metric units), and observability platform.
3. **D3 Establish Metrics Access** — you have no live data; obtain values via a connected MCP, dashboard screenshots, or manual query results, always in the user's platform syntax.
4. **D4 Run USE Diagnostic** — for each relevant resource, check Utilization, Saturation, and Errors against the USE inventory and decision trees.
5. **D5 Explain Then Prescribe** — respond with What's Happening → USE Analysis table → Why → Fix (most impactful first) → Monitor After → If Not Resolved, routing each action to the right sibling skill.

Load `references/ops-diagnostics-reference.md` for the full D1–D5 mechanics, pitfalls table, and decision trees; `references/diagnosis-examples.md` for worked examples.

## Key Facts

- OpenMetrics endpoint: `metrics.temporal.io`, API key auth, 30s recommended scrape interval, 30k datapoints per scrape, 180 requests/hour rate limit, ~3-minute data latency.
- PromQL/v0 endpoint is deprecated and unavailable to new users. Sunset date October 5, 2026. Never recommend v0 metrics — always use v1.
- v1 metrics are pre-computed per-second rates with delta temporality. Never apply `rate()`, `increase()`, `irate()`, or `histogram_quantile()`.
- SDK histogram units: milliseconds for Core SDKs (TypeScript, Python, .NET, Ruby, PHP) vs seconds (Go, Java). On Core SDKs the exported histogram series is named `*_milliseconds_bucket` (not `*_seconds_bucket`), so PromQL examples must change the metric-name suffix, not just the threshold value.
- v1 pre-calculated percentiles (p50, p95, p99) cannot be accurately aggregated across dimensions.
- `temporal_cloud_v1_approximate_backlog_count` is approximate — can overcount and resets to zero on idle queues.
- Self-hosted Frontend Service health checks: port 7233, not 8080.
- `worker_version` label is deprecated — use `temporal_worker_deployment_name` and `temporal_worker_build_id`.
- **Tracing:** the OTel tracing interceptor must be installed on **both** the client and every Worker — one side alone silently produces orphan spans. Trace context rides the Workflow/Activity **Header** (Go/Java key `_tracer-data`), which is persisted in event history, so it survives Worker restarts and replay. Default propagator is W3C Trace Context.
- **Tracing/replay:** never create spans with wall-clock/random ids directly in Workflow code (they duplicate every replay) — let the interceptor create boundary spans and attach mutable telemetry to **Activity** spans (which run once per attempt).
- **Tracing/continue-as-new:** a new Run's span must **link** to the prior Run (whose span has ended), never parent under it — otherwise a continue-as-new loop builds an unbounded trace.
- **TypeScript tracing:** Workflow spans need a `makeWorkflowExporter` sink on the Worker (the sandbox has no I/O); forget it and Workflow spans silently vanish while Activity spans still appear.
- **Logging:** use the SDK's replay-aware Workflow logger (`workflow.GetLogger` / `workflow.logger` / SDK equivalent) inside Workflow code — never the raw language logger, which re-fires on every replay. Replay suppression is on by default (Go `EnableLoggingInReplay`, Java `setEnableLoggingInReplay`, Python `log_during_replay` toggle it for debugging).
- **Logging:** the Activity logger auto-attaches the `attempt` number — essential for telling retry N's line apart from the original. Never log decrypted payloads/PII (payloads may be encrypted at rest; logs usually are not).

## Intent Decision Table

| User intent | Action |
|---|---|
| Wants to know which Cloud metrics exist, their types, or labels | Consult `references/cloud-metrics-catalog.md` for the complete `temporal_cloud_v1_*` catalog |
| Needs to set up or configure the OpenMetrics endpoint (auth, scrape config, rate limits) | Consult `references/openmetrics-endpoint.md` |
| Wants to integrate metrics with Datadog, Grafana Cloud, ClickStack, New Relic, Prometheus, or OTel Collector | Consult `references/integrations.md` |
| Needs to configure SDK metrics scrape endpoints or understand SDK metric units | Consult `references/sdk-metrics.md` |
| Setting up monitoring for a self-hosted Temporal Service | Consult `references/self-hosted-monitoring.md` |
| Wants to monitor Temporal Cloud service health (latency, error rates, failures, limits) | Consult `references/service-health-monitoring.md` |
| Needs to monitor Worker fleet health (backlog, greedy workers, misconfigured workers, sticky cache) | Consult `references/worker-health-monitoring.md` |
| Migrating from PromQL/v0 to OpenMetrics/v1 | Consult `references/migration-v0-to-v1.md` |
| Troubleshooting performance bottlenecks using metrics | Consult `references/troubleshooting.md` |
| Describing a symptom that needs systematic diagnosis (slow workflows, backlog, failures, latency) | Follow the **Diagnosis Protocol** above. Consult `references/ops-diagnostics-reference.md` for USE framework and decision trees |
| Wants a worked example of a diagnostic workflow | Consult `references/diagnosis-examples.md` |
| Wants ready-to-use alert rules (Prometheus, Datadog monitor, Grafana) for the headline worker/service signals | Consult `references/alert-rules.md` |
| Setting up or debugging **distributed tracing** through Workflows (tracing interceptor, orphan spans, replay-safe spans, continue-as-new trace topology, span export/sampling) | Consult `references/distributed-tracing.md` |
| Setting up **structured/replay-safe logging** (duplicate logs on replay, JSON logs, per-SDK Workflow/Activity loggers, log-to-trace correlation, shipping logs) | Consult `references/structured-logging.md` |
| Wants to know **what `gen_ai.*` span attributes** to emit on LLM/agent traces (operation.name, usage, tool/agent attributes) | Defer to `otel-genai-conventions` — this skill is Temporal-native/attribute-agnostic and owns propagation, not the schema |
| Wants to write Workflow/Activity/Worker SDK code, or the in-code logger/span **emission** call site and its determinism rules (not the observability pipeline) | Defer to `temporal-developer` |
| Wants to tune Worker performance (slot suppliers, tuners, cache sizing) | Defer to `temporal-workertuning` -- this skill owns collection/query layer only |
| Wants Cloud connectivity, auth, namespace config, or to administer a Temporal Cloud environment (not metrics) | Defer to `temporal-cloud`. For self-hosted cluster administration there is no sibling skill -- prescribe changes directly from the metric evidence (see Step D5) |

## Critical Rules

### Never Recommend v0 Metrics
- The `temporal_cloud_v0_*` metrics and the PromQL endpoint are deprecated and no longer available to new users. **Never recommend v0 metrics for any purpose.** Do not include v0 metric names in configs, queries, dashboards, or examples. Always use the `temporal_cloud_v1_*` equivalents.
- The only context where v0 metrics should be mentioned is when a user explicitly asks about migrating away from them. In that case, consult `references/migration-v0-to-v1.md` and guide them to the v1 replacements.
- If a user references a v0 metric name (e.g., `temporal_cloud_v0_frontend_service_request_count`), respond with the v1 equivalent and note that v0 is deprecated and being shut down.

### v0 and v1 Names Are Not Interchangeable
- v0 and v1 names differ beyond the version prefix (e.g., `temporal_cloud_v0_frontend_service_request_count` → `temporal_cloud_v1_service_request_count` — note the dropped `frontend_`). When helping users migrate, consult the mapping table in `references/migration-v0-to-v1.md`; do not attempt to guess v1 names by swapping the version prefix.

### Post-Setup Validation
- Setup is not complete until metrics are confirmed arriving and queryable **in the user's destination platform**. Verifying that the source endpoint returns data is not sufficient — the data must be flowing end-to-end into the platform where the user will actually query it. After providing any scrape config, integration config, or SDK metrics setup, always end with a validation step.
- **Validate at the destination, not the source.** Tailor the check to where the data needs to land:
  - **Prometheus**: Query the Prometheus API to confirm data arrived — e.g., `curl -s "http://localhost:9090/api/v1/query?query=temporal_cloud_v1_service_request_count"` should return results with recent timestamps.
  - **Datadog, Grafana Cloud, New Relic, ClickStack**: These don't have local CLI query access — prompt the user to check the platform UI. Tell them exactly what to search for (e.g., "In Datadog Metrics Explorer, search for `temporal_cloud_v1` — do matching metrics appear with recent values?").
- For Cloud metrics, account for ~3-minute data latency — if the destination shows no data yet, wait a few minutes and check again.
- Do not assume setup succeeded just because the config looks correct. Verify at the destination or ask the user to verify.

### Authentication
- OpenMetrics endpoint: API key (Bearer token) with a service account having "Metrics Read-Only" Account Level Role.
- PromQL endpoint (deprecated): mTLS certificates with customer-specific endpoints (`<account-id>.tmprl.cloud/prometheus`).
- Never mix these authentication methods or endpoint URLs.
