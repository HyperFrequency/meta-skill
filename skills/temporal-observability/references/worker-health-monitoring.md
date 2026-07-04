# Worker Fleet Health Monitoring

<!-- Source: docs/cloud/worker-health.mdx -->

This reference covers monitoring a Temporal Worker fleet: minimal observation set, task backlog detection and handling, greedy worker detection, misconfigured worker detection, sticky cache configuration, approximate backlog count, and worker heartbeating setup across SDKs.

## Minimal Observations
<!-- docs/cloud/worker-health.mdx:48-91 -->

These alerts should be configured first to gain intelligence into application health and behaviors. <!-- docs/cloud/worker-health.mdx:50 -->

### 1. Schedule-to-Start Latency Alerts
<!-- docs/cloud/worker-health.mdx:52-56 -->

Create monitors and alerts for Schedule-to-Start latency SDK metrics for both Workflow Executions (`temporal_workflow_task_schedule_to_start_latency`) and Activity Executions (`temporal_activity_schedule_to_start_latency`). <!-- docs/cloud/worker-health.mdx:52 -->

- Alert at >200ms for your p99 value <!-- docs/cloud/worker-health.mdx:55 -->
- Plot >100ms for your p95 value <!-- docs/cloud/worker-health.mdx:56 -->

### 2. Sync Match Rate Panel
<!-- docs/cloud/worker-health.mdx:58-62 -->

Create a Grafana panel called "Sync Match Rate".

- Alert at <95% for your p99 value <!-- docs/cloud/worker-health.mdx:61 -->
- Plot <99% for your p95 value <!-- docs/cloud/worker-health.mdx:62 -->

### 3. Poll Success Rate Panel
<!-- docs/cloud/worker-health.mdx:64-68 -->

Create a Grafana panel called "Poll Success Rate".

- Alert at <90% for your p99 value <!-- docs/cloud/worker-health.mdx:67 -->
- Plot <95% for your p95 value <!-- docs/cloud/worker-health.mdx:68 -->

### Additional Alerts
<!-- docs/cloud/worker-health.mdx:72-91 -->

1. **`temporal_worker_task_slots_available`**: Alert at 0 for your p99 value. <!-- docs/cloud/worker-health.mdx:72-75 -->
2. **`temporal_sticky_cache_size`**: Plot at {value} > {WorkflowCacheSize.Value}. <!-- docs/cloud/worker-health.mdx:77-80 -->
3. **`temporal_sticky_cache_total_forced_eviction`**: Alert at >{predetermined_high_number}. Available in Go SDK and Java SDK only. <!-- docs/cloud/worker-health.mdx:82-86 -->
4. **`temporal_cloud_v1_approximate_backlog_count`**: Alert when the value is growing over time for a given Task Queue. This provides a server-side view of how many Tasks are waiting in a Task Queue and complements the SDK Schedule-to-Start latency metrics. <!-- docs/cloud/worker-health.mdx:88-91 -->

---

## Detect Task Backlog
<!-- docs/cloud/worker-health.mdx:93-253 -->

### Symptoms of High Task Backlog
<!-- docs/cloud/worker-health.mdx:95-98 -->

If the Task backlog is too high, tasks are waiting to find Workers to run on, causing delays in Workflow execution. Detect a growing Task backlog by watching Schedule-to-Start latency, sync match rate, and approximate backlog count.

### Metrics to Monitor
<!-- docs/cloud/worker-health.mdx:100-106 -->

- **SDK**: `temporal_workflow_task_schedule_to_start_latency` <!-- docs/cloud/worker-health.mdx:102 -->
- **SDK**: `temporal_activity_schedule_to_start_latency` <!-- docs/cloud/worker-health.mdx:103 -->
- **Cloud**: `temporal_cloud_v1_poll_success_count` <!-- docs/cloud/worker-health.mdx:104 -->
- **Cloud**: `temporal_cloud_v1_poll_success_sync_count` <!-- docs/cloud/worker-health.mdx:105 -->
- **Cloud**: `temporal_cloud_v1_approximate_backlog_count` <!-- docs/cloud/worker-health.mdx:106 -->

### Schedule-to-Start Latency
<!-- docs/cloud/worker-health.mdx:108-113 -->

Represents how long Tasks stay unprocessed in Task Queues. A long time likely means Workers cannot keep up; either increase the number of Workers (if host load is already high) or increase the number of pollers per Worker. <!-- docs/cloud/worker-health.mdx:110-112 -->

If Schedule-to-Start latency is high, check the Sync Match Rate to decide if you need to adjust your Worker or fleet. If Sync Match Rate is low, contact Temporal Cloud support. <!-- docs/cloud/worker-health.mdx:114-116 -->

**Target:** This latency should be very low, close to zero. Any higher value indicates a bottleneck. <!-- docs/cloud/worker-health.mdx:152-153 -->

#### Prometheus Query Samples (SDK metrics)
<!-- docs/cloud/worker-health.mdx:120-148 -->

Workflow Task Latency, 99th percentile: <!-- docs/cloud/worker-health.mdx:122 -->
```promql
histogram_quantile(0.99, sum(rate(temporal_workflow_task_schedule_to_start_latency_seconds_bucket[5m])) by (le, namespace, task_queue))
```

Activity Task Latency, 99th percentile: <!-- docs/cloud/worker-health.mdx:136-139 -->
```promql
histogram_quantile(0.99, sum(rate(temporal_activity_schedule_to_start_latency_seconds_bucket[5m])) by (le, namespace, task_queue))
```

Note: These queries use `rate()` on SDK histogram metrics, which is correct. Do NOT apply `rate()` to Cloud `temporal_cloud_v1_*` metrics.

Note (unit suffix): the `_seconds_bucket` series name above is correct only for Go/Java SDKs. Core SDKs (TypeScript, Python, .NET, Ruby, PHP) export latency histograms in milliseconds, so the series is named `*_milliseconds_bucket` (e.g., `temporal_workflow_task_schedule_to_start_latency_milliseconds_bucket`) and the resulting `histogram_quantile` value is in ms (a 200ms threshold is `200`, not `0.2`). On Core SDKs, substitute the `*_milliseconds_bucket` series, or these queries return empty results.

### Sync Match Rate
<!-- docs/cloud/worker-health.mdx:155-185 -->

The sync match rate measures the rate of Tasks delivered to Workers without having to be persisted (Workers are up and available) against all delivered tasks. <!-- docs/cloud/worker-health.mdx:157 -->

A sync match is when a task is immediately matched to a Worker via the Sticky Queue. An async match is when a Task cannot be matched to the Sticky Queue. <!-- docs/cloud/worker-health.mdx:159-161 -->

**Calculate Sync Match Rate:** <!-- docs/cloud/worker-health.mdx:165-167 -->
```promql
temporal_cloud_v1_poll_success_sync_count / temporal_cloud_v1_poll_success_count = N
```

**Full query:** <!-- docs/cloud/worker-health.mdx:173-181 -->
```promql
sum by(temporal_namespace) (
    temporal_cloud_v1_poll_success_sync_count{temporal_namespace=~"$namespace"}
)
/
sum by(temporal_namespace) (
    temporal_cloud_v1_poll_success_count{temporal_namespace=~"$namespace"}
)
```

**Target:** The Sync Match Rate should be at least >95%, preferably >99%. <!-- docs/cloud/worker-health.mdx:185 -->

### Handling Task Backlog Issues
<!-- docs/cloud/worker-health.mdx:187-252 -->

#### High Schedule-to-Start Latency and High Sync Match Rate
<!-- docs/cloud/worker-health.mdx:191-205 -->

Three typical causes: <!-- docs/cloud/worker-health.mdx:193-197 -->
- Not enough Workers to perform work
- Each Worker is either under-resourced or misconfigured to handle enough work
- Congestion caused by the environment (e.g., network) hosting the Worker(s) and Temporal Cloud

Actions: <!-- docs/cloud/worker-health.mdx:201-204 -->
- Increase the number of available Workers
- Verify Worker hosts are appropriately resourced
- Increase the Worker configuration value for concurrent pollers for workers/task executions (if resources can accommodate it)

#### High Schedule-to-Start Latency and Low Sync Match Rate
<!-- docs/cloud/worker-health.mdx:206-246 -->

Verify that `ScheduleToStartTimeout` is not set in Activity Options, as this may skew observations. <!-- docs/cloud/worker-health.mdx:208 -->

Monitor the approximate backlog count to observe Task Queue depth directly: <!-- docs/cloud/worker-health.mdx:231-235 -->
```promql
temporal_cloud_v1_approximate_backlog_count{temporal_namespace=~"$namespace", temporal_task_queue=~"$task_queue"}
```

Actions: <!-- docs/cloud/worker-health.mdx:239-246 -->
- Check system CPU usage against `task_slots` and adjust `maxConcurrentWorkflowTaskExecutionSize` and `maxConcurrentActivityExecutionSize` as necessary.
- Check system memory usage against `sticky_cache_size` and adjust sticky cache size as necessary.
- Increase the Worker config for concurrent pollers for Workflow or Activity `task_slots`.
- Increase the number of available Workers.

---

## Detect Greedy Worker Resources
<!-- docs/cloud/worker-health.mdx:254-298 -->

If the Poll Success Rate shows low numbers, you might have too many resources polling Temporal Cloud. <!-- docs/cloud/worker-health.mdx:258-259 -->

### Metrics to Monitor
<!-- docs/cloud/worker-health.mdx:261-267 -->

- **Cloud**: `temporal_cloud_v1_poll_success_count` <!-- docs/cloud/worker-health.mdx:263 -->
- **Cloud**: `temporal_cloud_v1_poll_success_sync_count` <!-- docs/cloud/worker-health.mdx:264 -->
- **Cloud**: `temporal_cloud_v1_poll_timeout_count` <!-- docs/cloud/worker-health.mdx:265 -->
- **SDK**: `temporal_workflow_task_schedule_to_start_latency` <!-- docs/cloud/worker-health.mdx:266 -->
- **SDK**: `temporal_activity_schedule_to_start_latency` <!-- docs/cloud/worker-health.mdx:267 -->

### Calculate Poll Success Rate
<!-- docs/cloud/worker-health.mdx:271-275 -->

```promql
(temporal_cloud_v1_poll_success_count)
/
(temporal_cloud_v1_poll_success_count + temporal_cloud_v1_poll_timeout_count)
```

**Target:** Poll Success Rate should be >90% in most cases with steady load. For high volume and low latency, target >95%. <!-- docs/cloud/worker-health.mdx:279-280 -->

### Detection Pattern
<!-- docs/cloud/worker-health.mdx:286-291 -->

If you see all of the following at the same time, you might have too many Workers: <!-- docs/cloud/worker-health.mdx:286 -->
- Low poll success rate
- Low Schedule-to-Start latency
- Low worker host resource utilization

### Actions
<!-- docs/cloud/worker-health.mdx:294-298 -->

- Reduce the number of Workers polling the impacted Task Queue, OR
- Reduce the concurrent pollers per Worker, OR
- Both

---

## Detect Misconfigured Workers
<!-- docs/cloud/worker-health.mdx:300-342 -->

Worker configuration can negatively affect Task processing efficiency. <!-- docs/cloud/worker-health.mdx:304 -->

### Metrics to Monitor
<!-- docs/cloud/worker-health.mdx:306-310 -->

- **SDK**: `temporal_worker_task_slots_available` <!-- docs/cloud/worker-health.mdx:308 -->
- **SDK**: `temporal_sticky_cache_size` <!-- docs/cloud/worker-health.mdx:309 -->
- **SDK**: `temporal_sticky_cache_total_forced_eviction` <!-- docs/cloud/worker-health.mdx:310 -->

### Execution Size Configuration
<!-- docs/cloud/worker-health.mdx:312-315 -->

The `maxConcurrentWorkflowTaskExecutionSize` and `maxConcurrentActivityExecutionSize` define the number of total available slots for the Worker. If set too low, the Worker will not keep up processing Tasks. <!-- docs/cloud/worker-health.mdx:314-315 -->

**Target:** `temporal_worker_task_slots_available` should always be >0. <!-- docs/cloud/worker-health.mdx:319 -->

#### Prometheus Query Samples
<!-- docs/cloud/worker-health.mdx:323-333 -->

Over time: <!-- docs/cloud/worker-health.mdx:323 -->
```promql
avg_over_time(temporal_worker_task_slots_available{namespace="$namespace",worker_type="WorkflowWorker"}[10m])
```

Current time: <!-- docs/cloud/worker-health.mdx:329 -->
```promql
temporal_worker_task_slots_available{namespace="default", worker_type="WorkflowWorker", task_queue="$task_queue_name"}
```

**Action:** Increase `maxConcurrentWorkflowTaskExecutionSize` and `maxConcurrentActivityExecutionSize` values and monitor Worker resource metrics (CPU utilization, etc.) to ensure you have not created a new issue. <!-- docs/cloud/worker-health.mdx:342 -->

---

## Configure Sticky Execution Cache
<!-- docs/cloud/worker-health.mdx:344-371 -->

Sticky Execution means a Worker caches a Workflow Execution Event History and creates a dedicated Task Queue to listen on. It significantly improves performance because the Temporal Service only sends new events to the Worker instead of entire Event Histories. <!-- docs/cloud/worker-health.mdx:346-347 -->

**Target:** `sticky_cache_size` should report less than or equal to your `WorkflowCacheSize` value. Also, `sticky_cache_total_forced_eviction` should not report high numbers. <!-- docs/cloud/worker-health.mdx:351-352 -->

**Action:** If you see a high eviction count, verify there are no other inefficiencies in Worker configuration or resource provisioning. If the cache size metric exceeds `WorkflowCacheSize`, increase this value if Worker resources allow, or provision more Workers. <!-- docs/cloud/worker-health.mdx:356-357 -->

#### Prometheus Query Samples
<!-- docs/cloud/worker-health.mdx:362-371 -->

Sticky Cache Size: <!-- docs/cloud/worker-health.mdx:364 -->
```promql
max_over_time(temporal_sticky_cache_size{namespace="$namespace"}[10m])
```

Sticky Cache Evictions: <!-- docs/cloud/worker-health.mdx:370 -->
```promql
rate(temporal_sticky_cache_total_forced_eviction_total{namespace="$namespace"}[5m])
```

---

## Worker Heartbeating
<!-- docs/cloud/worker-health.mdx:374-458 -->

Workers send a heartbeat to Temporal Server every 60 seconds by default. This heartbeat provides liveness and configuration data from the Worker to the Server. <!-- docs/cloud/worker-health.mdx:382-383 -->

Uses include: <!-- docs/cloud/worker-health.mdx:386-387 -->
- Understanding the difference between a Worker that is down and one that is processing tasks for a long time
- Identifying a Worker with high CPU usage from the Server point of view

### Viewing Worker Information via CLI
<!-- docs/cloud/worker-health.mdx:389 -->

- `temporal worker describe` - see details of a specific Worker <!-- docs/cloud/worker-health.mdx:389 -->
- `temporal worker list` - get a complete list of all connected Workers <!-- docs/cloud/worker-health.mdx:389 -->

As of Replay 2026, Temporal Cloud also provides a **Worker Status UI** (Public Preview) that visualizes the same Worker heartbeat data (slots, host CPU, and Worker configuration) directly in the Cloud UI, complementing the `temporal worker describe`/`list` CLI and the heartbeat-derived metrics above. <!-- temporal.io/blog/replay-2026-product-announcements -->

### Heartbeat Configuration per SDK
<!-- docs/cloud/worker-health.mdx:391-458 -->

The allowed heartbeat interval range is 1s to 60s. Disabling the Worker heartbeat will cause features that provide the list of active Workers and information about those Workers to show missing or inaccurate information. <!-- docs/cloud/worker-health.mdx:391 -->

#### Go SDK
<!-- docs/cloud/worker-health.mdx:393-417 -->

Available since Go SDK v1.41.0. Set the `WorkerHeartbeatInterval` field on `client.Options` to adjust the heartbeat interval. Set it to a negative value to disable heartbeating. <!-- docs/cloud/worker-health.mdx:395-398 -->

Enable host resource reporting by setting `SysInfoProvider` on `worker.Options`: <!-- docs/cloud/worker-health.mdx:402-403 -->
```go
import (
    "go.temporal.io/sdk/contrib/sysinfo"
    "go.temporal.io/sdk/worker"
)

w := worker.New(c, "my-task-queue", worker.Options{
    SysInfoProvider: sysinfo.SysInfoProvider(),
})
```

#### Python SDK
<!-- docs/cloud/worker-health.mdx:420-424 -->

Available since Python SDK v1.20.0. Use `TelemetryConfig()` to adjust heartbeat settings. <!-- docs/cloud/worker-health.mdx:422-424 -->

#### TypeScript SDK
<!-- docs/cloud/worker-health.mdx:427-432 -->

Available since TypeScript SDK v1.14.0. Set the `workerHeartbeatInterval` property on `RuntimeOptions` to adjust the heartbeat interval. Set it to `0` to disable heartbeating. <!-- docs/cloud/worker-health.mdx:429-432 -->

#### .NET SDK
<!-- docs/cloud/worker-health.mdx:435-440 -->

Available since .NET SDK v1.10.0. Set the `WorkerHeartbeatInterval` property on `TemporalRuntimeOptions` to adjust the heartbeat interval. Set it to `null` to disable heartbeating. <!-- docs/cloud/worker-health.mdx:437-440 -->

#### Java SDK
<!-- docs/cloud/worker-health.mdx:443-448 -->

Available since Java SDK v1.35.0. Set the heartbeat interval on `WorkflowClientOptions.Builder` with `setWorkerHeartbeatInterval(Duration)`. Set it to a negative `Duration` to disable heartbeating. <!-- docs/cloud/worker-health.mdx:445-448 -->

#### Ruby SDK
<!-- docs/cloud/worker-health.mdx:451-455 -->

Available since Ruby SDK v1.1.0. Add configurations to `Runtime()` to adjust heartbeat settings. <!-- docs/cloud/worker-health.mdx:453-455 -->
