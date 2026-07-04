# SDK Metrics Overview

<!-- Sources: docs/references/sdk-metrics.mdx, docs/cloud/metrics/sdk-metrics-setup.mdx -->

This reference covers SDK metrics: how they differ from Cloud metrics, how to expose a scrape endpoint per SDK, Prometheus configuration for SDK scrape, Grafana data source setup, the key SDK metrics for observability, and metric unit differences across SDKs.

## SDK Metrics vs Cloud Metrics

SDK metrics are emitted by SDK Clients used to start Workers and to start, signal, or query Workflow Executions. Unlike Temporal Cloud metrics (exposed through the OpenMetrics HTTP API endpoint at `metrics.temporal.io`), SDK metrics require setting up a Prometheus scrape endpoint in application code for Prometheus to collect and aggregate. <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:25-26 -->

All SDK metrics are prefixed with `temporal_` before being exported to their configured destination. <!-- docs/references/sdk-metrics.mdx:38 -->

SDK metrics are distinct from Cloud metrics (`temporal_cloud_v1_*`) and self-hosted cluster metrics (e.g., `service_requests`). They are emitted by the application-side SDK, not the Temporal Service.

## Metric Unit Differences Across SDKs
<!-- docs/references/sdk-metrics.mdx:55-65 -->

The unit of measurement for Histogram metrics varies by SDK:

- **Core-based SDKs** (TypeScript, Python, .NET, Ruby, PHP): Histogram metrics are measured in **milliseconds** by default. This can be customized to use seconds. <!-- docs/references/sdk-metrics.mdx:59-61 -->
- **Java and Go SDKs**: Histogram metrics are measured in **seconds**. <!-- docs/references/sdk-metrics.mdx:63 -->

The Core SDK is a shared common core library used by the TypeScript, Python, .NET, Ruby, and PHP SDKs. <!-- docs/references/sdk-metrics.mdx:61 -->

**PromQL series-name impact:** because Core SDKs export in milliseconds, their latency histogram series are named `*_milliseconds_bucket` (e.g., `temporal_activity_schedule_to_start_latency_milliseconds_bucket`), whereas Go/Java export `*_seconds_bucket`. PromQL examples written for `*_seconds_bucket` return empty results on Core SDKs unless the unit was reconfigured — change the metric-name suffix, not just the threshold value.

## Exposing a Metrics Endpoint
<!-- docs/cloud/metrics/sdk-metrics-setup.mdx:46-66 -->

Each language SDK exposes its own Prometheus scrape endpoint from application (Worker/Client) code. The minimal snippets below are the smallest config that produces a scrapeable endpoint; they all bind to `8077` to match the `scrape_configs` job in the next section (the Prometheus server itself runs separately on `9090`). Each snippet links the per-SDK observability guide and its working sample.

### Go SDK
[Observability guide](/develop/go/platform/observability#metrics) · [Sample](https://github.com/temporalio/samples-go/tree/main/metrics) <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:51,59 -->

Go uses Uber's `tally` with the Prometheus reporter, wrapped by `sdktally.NewMetricsHandler` and passed as `client.Options.MetricsHandler`. The tally Prometheus reporter serves the scrape endpoint on its `ListenAddress`:

```go
import (
    "log"
    "time"

    prom "github.com/prometheus/client_golang/prometheus"
    "github.com/uber-go/tally/v4"
    "github.com/uber-go/tally/v4/prometheus"
    "go.temporal.io/sdk/client"
    sdktally "go.temporal.io/sdk/contrib/tally"
)

// newPrometheusScope serves the scrape endpoint on cfg.ListenAddress.
func newPrometheusScope(cfg prometheus.Configuration) tally.Scope {
    reporter, err := cfg.NewReporter(prometheus.ConfigurationOptions{
        Registry: prom.NewRegistry(),
        OnError:  func(err error) { log.Println("prometheus reporter error:", err) },
    })
    if err != nil {
        log.Fatalln("error creating prometheus reporter", err)
    }
    scope, _ := tally.NewRootScope(tally.ScopeOptions{
        CachedReporter:  reporter,
        Separator:       prometheus.DefaultSeparator,
        SanitizeOptions: &sdktally.PrometheusSanitizeOptions,
    }, time.Second)
    return sdktally.NewPrometheusNamingScope(scope)
}

c, err := client.Dial(client.Options{
    MetricsHandler: sdktally.NewMetricsHandler(newPrometheusScope(prometheus.Configuration{
        ListenAddress: "0.0.0.0:8077", // Prometheus scrapes http://<host>:8077/metrics
        TimerType:     "histogram",
    })),
})
```

### Java SDK
[Observability guide](/develop/java/platform/observability#metrics) · [Sample](https://github.com/temporalio/samples-java/tree/main/core/src/main/java/io/temporal/samples/metrics) <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:52,60 -->

Java uses Micrometer: `MicrometerClientStatsReporter` over a `PrometheusMeterRegistry`, set as the metrics scope on `WorkflowServiceStubsOptions`. Expose the registry over HTTP with the Prometheus `HTTPServer`:

```java
// imports: io.micrometer.prometheus.{PrometheusConfig,PrometheusMeterRegistry};
// io.prometheus.client.exporter.HTTPServer; java.net.InetSocketAddress; com.uber.m3.tally.*;
// com.uber.m3.util.Duration; io.temporal.common.reporter.MicrometerClientStatsReporter;
// io.temporal.serviceclient.{WorkflowServiceStubs,WorkflowServiceStubsOptions}
PrometheusMeterRegistry registry = new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
Scope scope = new RootScopeBuilder()
        .reporter(new MicrometerClientStatsReporter(registry))
        .reportEvery(Duration.ofSeconds(1));

// Serves the scrape endpoint at http://<host>:8077/metrics
HTTPServer scrapeEndpoint =
        new HTTPServer(new InetSocketAddress(8077), registry.getPrometheusRegistry(), true);

WorkflowServiceStubs service = WorkflowServiceStubs.newServiceStubs(
        WorkflowServiceStubsOptions.newBuilder()
                .setMetricsScope(scope)
                .build());
```

### TypeScript SDK
[Observability guide](/develop/typescript/platform/observability#metrics) · [Sample](https://github.com/temporalio/samples-typescript/tree/main/interceptors-opentelemetry) <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:53,61 -->

Configure the Core `Runtime` once, before creating any Worker or Client:

```typescript
import { Runtime } from '@temporalio/worker';

// Serves http://0.0.0.0:8077/metrics
Runtime.install({
  telemetryOptions: {
    metrics: {
      prometheus: { bindAddress: '0.0.0.0:8077' },
    },
  },
});
```

### Python SDK
[Observability guide](/develop/python/platform/observability#metrics) · [Sample](https://github.com/temporalio/samples-python/tree/main/custom_metric) <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:54,62 -->

Build a `Runtime` with a `PrometheusConfig` bind address and pass it to the Client:

```python
from temporalio.client import Client
from temporalio.runtime import Runtime, TelemetryConfig, PrometheusConfig

# Serves http://0.0.0.0:8077/metrics
runtime = Runtime(
    telemetry=TelemetryConfig(
        metrics=PrometheusConfig(bind_address="0.0.0.0:8077")
    )
)
client = await Client.connect("localhost:7233", runtime=runtime)
```

### .NET SDK
[Observability guide](/develop/dotnet/platform/observability#metrics) · [Sample](https://github.com/temporalio/samples-dotnet/tree/main/src/OpenTelemetry/DotNetMetrics) <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:55,63 -->

Build a `TemporalRuntime` with Prometheus metrics options and pass it to the Client:

```csharp
using Temporalio.Client;
using Temporalio.Runtime;

// Serves http://0.0.0.0:8077/metrics
var runtime = new TemporalRuntime(new()
{
    Telemetry = new()
    {
        Metrics = new() { Prometheus = new() { BindAddress = "0.0.0.0:8077" } },
    },
});
var client = await TemporalClient.ConnectAsync(
    new("localhost:7233") { Runtime = runtime });
```

> The Core-runtime SDKs (TypeScript, Python, .NET, Ruby, PHP) all expose this same `telemetryOptions`/`Runtime` metrics config; only the surface syntax differs.

### OTLP / OpenTelemetry Push Export

Instead of exposing a Prometheus endpoint to be *pulled*, SDKs can *push* metrics to an OpenTelemetry Collector over OTLP. This is configured in the **same** telemetry/`Runtime` metrics config — swap the Prometheus bind address for an OTLP metrics endpoint:

- **Core-runtime SDKs** (TypeScript, Python, .NET, Ruby, PHP): use the `otel`/`OpenTelemetryConfig` metrics option instead of `prometheus`/`PrometheusConfig`. For example, TypeScript `metrics: { otel: { url: 'http://otel-collector:4317' } }`, or Python:

  ```python
  from temporalio.runtime import Runtime, TelemetryConfig, OpenTelemetryConfig

  runtime = Runtime(
      telemetry=TelemetryConfig(
          metrics=OpenTelemetryConfig(url="http://otel-collector:4317")
      )
  )
  ```

- **Go and Java**: use their OpenTelemetry-backed `MetricsHandler` (e.g. Go's `go.temporal.io/sdk/contrib/opentelemetry` with a `MeterProvider` wired to an OTLP metric exporter) in place of the tally/Micrometer Prometheus handler above.

The Collector then forwards the metrics to your backend. For the Collector pipeline itself (receivers/processors/exporters), see the **OpenTelemetry Collector** section in `integrations.md`.

## Prometheus Configuration for SDK Scrape
<!-- docs/cloud/metrics/sdk-metrics-setup.mdx:68-91 -->

Prometheus must be configured to listen on the scrape endpoints exposed in application code. The following example assumes the scrape endpoint is on port 8077: <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:70-74 -->

```yaml
global:
  scrape_interval: 30s

scrape_configs:
  - job_name: 'temporalsdkmetrics'
    metrics_path: /metrics
    scheme: http
    static_configs:
      - targets:
          - localhost:8077
```

To verify Prometheus is receiving SDK metrics, navigate to `http://localhost:9090` and check **Status > Targets** for the target endpoint status. <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:95-96 -->

## Grafana Data Source Setup
<!-- docs/cloud/metrics/sdk-metrics-setup.mdx:98-120 -->

To add the SDK metrics Prometheus endpoint as a Grafana data source:

1. Go to **Configuration > Data sources**. <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:106 -->
2. Select **Add data source > Prometheus**. <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:107 -->
3. Enter a name (e.g., "Temporal SDK metrics"). <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:108 -->
4. In the **HTTP** section, enter the Prometheus endpoint URL (e.g., `http://localhost:9090`). <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:109-110 -->
5. Enable **Skip TLS Verify** in the **Auth** section (for local setups). <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:111 -->
6. Click **Save and test** to verify. <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:112 -->

Community-driven example dashboards for Temporal SDKs are available at: https://github.com/temporalio/dashboards/tree/master/sdk <!-- docs/cloud/metrics/sdk-metrics-setup.mdx:128-129 -->

## Common Tags on SDK Metrics
<!-- docs/references/sdk-metrics.mdx:67-84 -->

Each metric may have some combination of the following tags:

| Tag | Description |
|---|---|
| `task_queue` | Task Queue that the Worker Entity is polling |
| `namespace` | Namespace the Worker is bound to |
| `poller_type` | One of: `workflow_task`, `activity_task`, `nexus_task` (Go and Java only), `sticky_workflow_task` |
| `worker_type` | One of: `ActivityWorker`, `WorkflowWorker`, `LocalActivityWorker` (Go and Java only), `NexusWorker` (Go and Java only) |
| `activity_type` | The name of the Activity Function |
| `workflow_type` | The name of the Workflow Function |
| `operation` | RPC method name; available for metrics related to Temporal Client gRPC requests |

Some tags may not be available in every SDK, and Histogram metrics may have different buckets in each SDK. <!-- docs/references/sdk-metrics.mdx:85 -->

## SDK-Side Cardinality Management

SDK metrics carry high-cardinality tags — `workflow_type`, `activity_type`, `operation`, and `task_queue` — so on self-hosted / SDK-scrape setups the series count grows with the number of distinct Workflow types, Activity types, RPC operations, and queues. (This is the same concern the Cloud OpenMetrics endpoint addresses with scrape-time filtering; see `openmetrics-endpoint.md` § Managing High Cardinality for the estimation formula and Cloud-side controls.) Control SDK-emitted cardinality at one of two layers:

- **At the SDK metrics handler** — where the SDK supports it, customize or exclude tags before they are emitted (for example, Go's tally scope tag handling, or a custom/wrapping `MetricsHandler` that drops a tag). This keeps the wire small at the source.
- **At scrape time** — drop or consolidate the offending labels with Prometheus `metric_relabel_configs` (`action: labeldrop`), exactly as shown for the Cloud endpoint in `openmetrics-endpoint.md`. This works uniformly regardless of SDK support.

Prefer dropping `workflow_type`/`activity_type` first when a single namespace has thousands of types, since those usually dominate the series count.

## Key SDK Metrics for Observability

The following are the most important SDK metrics for operational monitoring. The full list is in `docs/references/sdk-metrics.mdx`.

### Schedule-to-Start Latency

#### `temporal_workflow_task_schedule_to_start_latency`
<!-- docs/references/sdk-metrics.mdx:550-557 -->

The Schedule-To-Start time of a Workflow Task.

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

#### `temporal_activity_schedule_to_start_latency`
<!-- docs/references/sdk-metrics.mdx:171-182 -->

The Schedule-To-Start time of an Activity Task in seconds. Useful for ensuring Activity Tasks are being processed from the queue in a timely manner. <!-- docs/references/sdk-metrics.mdx:173-177 -->

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

### Execution Latency

#### `temporal_workflow_task_execution_latency`
<!-- docs/references/sdk-metrics.mdx:518-524 -->

Workflow Task Execution time.

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `workflow_type`

#### `temporal_activity_execution_latency`
<!-- docs/references/sdk-metrics.mdx:155-161 -->

Time to complete an Activity Execution, from the time the Activity Task is generated to the time the language SDK responded with a completion (failure or success).

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `activity_type`, `namespace`, `task_queue`

#### `temporal_workflow_endtoend_latency`
<!-- docs/references/sdk-metrics.mdx:489-495 -->

Total Workflow Execution time from schedule to completion for a single Workflow Run. A retried Workflow Execution is a separate Run.

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `workflow_type`

### Replay Latency

#### `temporal_workflow_task_replay_latency`
<!-- docs/references/sdk-metrics.mdx:543-548 -->

Time to catch up on replaying a Workflow Task.

- Type: Histogram
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `workflow_type`

### Task Slots

#### `temporal_worker_task_slots_available`
<!-- docs/references/sdk-metrics.mdx:437-445 -->

The total number of Workflow, Activity, Local Activity, or Nexus Task execution slots that are currently available. Use the `worker_type` tag to differentiate execution slots.

- Type: Gauge
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `worker_type`

#### `temporal_worker_task_slots_used`
<!-- docs/references/sdk-metrics.mdx:448-456 -->

The total number of Workflow, Activity, Local Activity, or Nexus Task execution slots in current use. Use the `worker_type` tag to differentiate execution slots.

- Type: Gauge
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `worker_type`

### Sticky Cache

#### `temporal_sticky_cache_hit`
<!-- docs/references/sdk-metrics.mdx:388-394 -->

A Workflow Task found a cached Workflow Execution to run against.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

#### `temporal_sticky_cache_miss`
<!-- docs/references/sdk-metrics.mdx:396-402 -->

A Workflow Task did not find a cached Workflow Execution to run against.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

#### `temporal_sticky_cache_size`
<!-- docs/references/sdk-metrics.mdx:404-410 -->

Current cache size, expressed in number of Workflow Executions.

- Type: Gauge
- Available in: Core, Go, Java
- Tags: `namespace` (TypeScript, Java), `task_queue` (TypeScript)

### Poll Metrics

#### `temporal_workflow_task_queue_poll_succeed`
<!-- docs/references/sdk-metrics.mdx:534-540 -->

A Workflow Worker polled a Task Queue and successfully picked up a Workflow Task.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

#### `temporal_workflow_task_queue_poll_empty`
<!-- docs/references/sdk-metrics.mdx:526-532 -->

A Workflow Worker polled a Task Queue and timed out without picking up a Workflow Task.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

#### `temporal_activity_poll_no_task`
<!-- docs/references/sdk-metrics.mdx:163-169 -->

An Activity Worker poll for an Activity Task timed out, and no Activity Task is available.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`

### Failure Metrics

#### `temporal_workflow_task_execution_failed`
<!-- docs/references/sdk-metrics.mdx:505-517 -->

A Workflow Task Execution failed.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `namespace`, `task_queue`, `workflow_type`, `failure_reason`

Valid values for `failure_reason`: <!-- docs/references/sdk-metrics.mdx:513-516 -->
- `NonDeterminismError`: The Workflow Task failed due to a non-determinism error.
- `WorkflowError`: The Workflow Task failed for any other reason.

#### `temporal_activity_execution_failed`
<!-- docs/references/sdk-metrics.mdx:148-153 -->

An Activity Execution failed. Does not include local Activity Failures in Go and Java SDKs.

- Type: Counter
- Available in: Core, Go, Java
- Tags: `activity_type`, `namespace`, `task_queue`

### Additional Worker and Client Metrics
<!-- docs/references/sdk-metrics.mdx:87-137 -->

Beyond the headline latency/slot/cache/poll/failure metrics above, the live SDK reference defines these additional names that are useful for operational monitoring. (Full table and exact per-SDK availability: `docs/references/sdk-metrics.mdx:87-137`.)

| Metric | Type | Purpose |
|---|---|---|
| `temporal_num_pollers` | Gauge | Current number of poller threads. Differentiate with the `poller_type` tag. |
| `temporal_workflow_active_thread_count` | Gauge | Number of active Workflow threads (coroutines) — surfaces threadpool pressure. |
| `temporal_worker_start` | Counter | A Worker was started (use `worker_type` to distinguish). |
| `temporal_poller_start` | Counter | A poller was started. |
| `temporal_request` | Counter | A successful (non-long-poll) gRPC request from the SDK Client. Tagged by `operation`. |
| `temporal_request_failure` | Counter | A failed (non-long-poll) gRPC request. Tagged by `operation`. |
| `temporal_long_request` | Counter | A successful long-poll gRPC request (e.g. task polling). Tagged by `operation`. |
| `temporal_long_request_failure` | Counter | A failed long-poll gRPC request. Tagged by `operation`. |
| `temporal_local_activity_execution_latency` | Histogram | Execution latency of a Local Activity (unit follows the per-SDK ms/seconds rule above). |
| `temporal_local_activity_succeed_endtoend_latency` | Histogram | End-to-end latency of a successful Local Activity. |
| `temporal_local_activity_execution_failed` | Counter | A Local Activity execution failed. |
| `temporal_activity_execution_cancelled` | Counter | An Activity execution was cancelled. |
| `temporal_unregistered_activity_invocation` | Counter | An Activity was invoked that is not registered on the Worker — signals a registration/routing bug. |
| `temporal_corrupted_signals` | Counter | A Signal payload could not be deserialized. |

`temporal_request*`/`temporal_long_request*` are the SDK-side complement to schedule-to-start latency for diagnosing Client↔Service connectivity issues; the long-poll variants are expected to be high-volume (polls), so alert on the `_failure` counters rather than raw request counts.

### Nexus Metrics

Nexus is a newer feature; these metrics are a non-core subset (Nexus Worker support is Go and Java only, see the `poller_type=nexus_task` / `worker_type=NexusWorker` tags above). They are emitted by Nexus task processing and follow the same Histogram unit rules as other SDK latencies:

- `temporal_nexus_task_execution_latency` — time to execute a Nexus Task.
- `temporal_nexus_task_endtoend_latency` — end-to-end latency of a Nexus Task from schedule to completion.
- `temporal_nexus_task_schedule_to_start_latency` — Schedule-To-Start time of a Nexus Task.
- `temporal_nexus_poll_no_task` — a Nexus Worker poll timed out without picking up a Nexus Task (the Nexus analogue of `temporal_activity_poll_no_task`).
- `temporal_nexus_task_execution_failed` — a Nexus Task execution failed (Counter).

Note: these are SDK metrics. There are no Nexus metrics on the Temporal Cloud OpenMetrics endpoint.

## Complete Metric List

For the full table of all SDK metrics, their types, and SDK availability, see `docs/references/sdk-metrics.mdx:87-137`. <!-- docs/references/sdk-metrics.mdx:87-137 -->

SDK metric definitions are maintained in the following source locations: <!-- docs/references/sdk-metrics.mdx:49-53 -->
- [Core SDK Worker metrics](https://github.com/temporalio/sdk-core/blob/master/crates/sdk-core/src/telemetry/metrics.rs)
- [Core SDK Client metrics](https://github.com/temporalio/sdk-core/blob/master/crates/client/src/metrics.rs)
- [Java SDK Worker metrics](https://github.com/temporalio/sdk-java/blob/master/temporal-sdk/src/main/java/io/temporal/worker/MetricsType.java)
- [Java SDK Client metrics](https://github.com/temporalio/sdk-java/blob/master/temporal-serviceclient/src/main/java/io/temporal/serviceclient/MetricsType.java)
- [Go SDK Worker and Client metrics](https://github.com/temporalio/sdk-go/blob/c32b04729cc7691f80c16f80eed7f323ee5ce24f/internal/common/metrics/constants.go)
