# Operational Diagnostics Reference

<!-- Sources: Adapted from temporalio/temporal-pm-skills ops-health skill (PR #102), cross-referenced with docs/cloud/worker-health.mdx, docs/cloud/service-health.mdx, docs/troubleshooting/performance-bottlenecks.mdx -->

This reference provides the USE methodology framework, metric name mappings, decision trees, and platform-specific query examples for the Diagnosis Protocol defined below (§ Diagnosis Protocol); SKILL.md carries the router stub that points here for symptom-driven diagnosis. For threshold values and detailed metric descriptions, see `worker-health-monitoring.md`, `service-health-monitoring.md`, and `troubleshooting.md`.

## Diagnosis Protocol (USE Methodology, Steps D1-D5)

When the user describes a symptom (slow workflows, growing backlog, activity failures, high latency), follow this systematic process. Never diagnose without metrics data.

### Step D1: Classify the Symptom

Map the user's description to a category:

| User says... | Category |
|---|---|
| "workflows slow to start", "backlog growing", "schedule-to-start high", "tasks queuing up" | **Throughput/Backlog** |
| "activities failing", "workflow failures spiking", "retries not working", "error rate high" | **Failure/Error** |
| "workflows taking too long end-to-end", "execution slow", "replay latency" | **Latency** |
| "resource exhausted errors", "throttling", "hitting limits" | **Resource Pressure** |
| "can't connect", "auth error", "certificate expired" | **Not this skill** — hand off to `temporal-cloud` |
| "need to tune workers", "autoscaling", "slot sizing" | **Not this skill** — hand off to `temporal-workertuning` |

If the symptom doesn't clearly map, ask what behavior they're seeing, when it started, and what changed.

### Step D2: Detect the Environment

Use context clues to determine:
- **Deployment**: Cloud, self-hosted, or dev server
- **SDK language**: Go, Java, TypeScript, Python, .NET, Ruby, PHP (affects metric units — Core SDKs use milliseconds, Go/Java use seconds)
- **Observability platform**: Prometheus, Datadog, Grafana Cloud, New Relic, etc.

See § Environment Detection below for the clue table. If confidence is below 95%, ask.

### Step D3: Establish Metrics Access

You do not have access to live metrics. Establish how to get values:

1. **MCP tool** — if the user has a Datadog or Grafana MCP server connected, use it to query metrics directly.
2. **Screenshots** — ask the user to capture specific dashboard panels. Tell them which panels based on the symptom category:
   - Throughput/Backlog: schedule-to-start latency, backlog count, task slots available, sync match rate
   - Failure/Error: activity failure count (by type if possible), workflow failure count, activity execution latency
   - Include the time axis and legend in screenshots
3. **Manual values** — provide the exact query for their platform and ask them to run it and report values.

Always provide queries in the user's platform syntax. See § Query Examples by Platform below for Datadog and New Relic translations. For PromQL, see `worker-health-monitoring.md` and `service-health-monitoring.md`.

**Do not proceed with diagnosis without metrics data.**

### Step D4: Run USE Diagnostic

For each Temporal resource relevant to the symptom, check all three USE dimensions:

- **Utilization**: How busy is the resource? (slots used, poll success rate, action count vs limit)
- **Saturation**: Is work queuing up? (backlog count, schedule-to-start latency, cache evictions)
- **Errors**: Is work failing? (activity_fail_count, workflow_failed_count, resource_exhausted)

Consult the sections below:
- § USE Resource Inventory — maps Temporal resources to their U/S/E metrics
- § Metric Name Mapping — which metric name to use for Cloud vs SDK
- § Decision Trees — follow the appropriate scenario tree based on symptom category

Cross-reference thresholds and detailed metric descriptions from:
- `worker-health-monitoring.md` — backlog, sync match, poll success, task slots, sticky cache
- `service-health-monitoring.md` — failure rates, error rates, limits, replication
- `troubleshooting.md` — per-bottleneck root causes and diagnostic steps

### Step D5: Explain Then Prescribe

Structure every diagnosis response using this format:

**What's Happening**: Plain-language explanation of the mechanics. Connect the user's metrics to the behavior they're seeing. Explain how Temporal's internals work in this situation so the user builds a mental model.

**USE Analysis**:

| Resource | Utilization | Saturation | Errors |
|---|---|---|---|
| (resource) | (metric: value + interpretation) | (metric: value) | (metric: value) |

**Why**: Root cause grounded in metric evidence. Explain the causal chain ("X is high because Y, caused by Z"). If multiple factors interact, show how.

**Fix**: Ordered list, most impactful first. For each action, explain **why it helps** in one sentence.
- Worker tuning → hand off to `temporal-workertuning`
- Cloud infrastructure / namespace admin → hand off to `temporal-cloud`
- Self-hosted infrastructure changes (cluster sizing, persistence, scaling) → no sibling skill covers this; prescribe the change directly to the user, grounded in the metric evidence gathered (e.g., "persistence_latency p99 is X, so scale the database / add History shards").
- Code changes → hand off to `temporal-developer`

**Monitor After**: Which metrics to watch, target values, and expected timeline for improvement.

**If Not Resolved**: What persistence of the issue would indicate, and next diagnostic step or skill handoff.

For fully worked examples of this protocol in action, see `diagnosis-examples.md`.

### Diagnosis Common Pitfalls

| Pitfall | Correct Behavior |
|---|---|
| Applying `rate()` to `temporal_cloud_v1_*` metrics in queries | v1 metrics are pre-computed rates — use directly. `rate()` is only valid for SDK and self-hosted metrics. |
| Confusing SDK metric units across SDKs | Go/Java use seconds; Core SDKs (TypeScript/Python/.NET/Ruby/PHP) use milliseconds. A 200ms threshold is `0.2` in Go/Java and `200` in Core SDKs. On Core SDKs the exported histogram series is also named `*_milliseconds_bucket`, not `*_seconds_bucket`. |
| Assuming `approximate_backlog_count = 0` means no backlog | This metric resets to zero on idle queues. Confirm with schedule-to-start latency. |
| Jumping to "add more workers" without checking slots | First check if existing workers have available slots. Slot depletion with low host CPU = configuration issue, not capacity. |
| Diagnosing without knowing the environment | Cloud vs self-hosted changes which metrics exist. Always establish environment first. |
| Ignoring the failure conversion rate | High activity failures with low workflow failures = healthy error handling. Always compute the ratio in failure scenarios. |
| Prescribing without explaining | Users who understand the mechanics make better decisions. Explain before recommending. |

## USE Resource Inventory

The USE method (Utilization, Saturation, Errors) applied to Temporal resources. For every resource relevant to the user's symptom, check all three dimensions before concluding.

| Resource | Utilization | Saturation | Errors |
|---|---|---|---|
| **Task Queue** | Sync match rate (poll_success_sync / poll_success) | `approximate_backlog_count`, schedule-to-start latency | `no_poller_tasks_count`, poll timeouts |
| **Worker Task Slots** | Slots in use vs available (`worker_task_slots_available`) | Slots at 0 (fully consumed) | Task execution failures |
| **Activity Execution** | Activity execution duration | Retry pressure (repeated failures consuming slots) | `activity_fail_count`, timeout errors |
| **Workflow Execution** | Workflow task execution latency | Concurrent workflows at limit | `workflow_failed_count` |
| **Sticky Cache** | `sticky_cache_size` vs WorkflowCacheSize config | `sticky_cache_total_forced_eviction` | Cache miss ratio (miss / (hit + miss)) |
| **Namespace Actions** | `total_action_count` / `action_limit` | `total_action_throttled_count` | `resource_exhausted_error_count` |
| **Namespace Requests** | `service_request_count` / `service_request_limit` | `service_request_throttled_count` | `resource_exhausted_error_count` |
| **Namespace Operations** | `operations_count` / `operations_limit` | `operations_throttled_count` | `resource_exhausted_error_count` |

All Cloud metric names above are shorthand — full names use the `temporal_cloud_v1_` prefix. See `cloud-metrics-catalog.md` for complete definitions. SDK metrics use `temporal_` prefix without `cloud`. For namespace limit triads, see `service-health-monitoring.md` § Monitoring Trends Against Limits.

## Metric Name Mapping: Cloud vs SDK

When diagnosing, the metric name depends on the user's environment. Use this table to select the right metric.

### Scenario 1: Task Backlog / Schedule-to-Start Latency

| What to Measure | Cloud Metric | SDK Metric |
|---|---|---|
| Backlog depth | `temporal_cloud_v1_approximate_backlog_count` | N/A (use `DescribeTaskQueue` API) |
| Schedule-to-start latency (workflow tasks) | N/A (derived from SDK) | `temporal_workflow_task_schedule_to_start_latency` |
| Schedule-to-start latency (activities) | N/A (derived from SDK) | `temporal_activity_schedule_to_start_latency` |
| Poll success (sync) | `temporal_cloud_v1_poll_success_sync_count` | N/A |
| Poll success (total) | `temporal_cloud_v1_poll_success_count` | N/A |
| Poll timeouts | `temporal_cloud_v1_poll_timeout_count` | N/A |
| Available task slots | N/A | `temporal_worker_task_slots_available` |
| Sync match rate | Derived: `poll_success_sync_count / poll_success_count` | N/A |
| Poll success rate | Derived: `poll_success_count / (poll_success_count + poll_timeout_count)` | N/A |
| No-poller tasks | `temporal_cloud_v1_no_poller_tasks_count` | N/A |

### Scenario 2: Activity Failure Cascade

| What to Measure | Cloud Metric | SDK Metric |
|---|---|---|
| Activity failures | `temporal_cloud_v1_activity_fail_count` | `temporal_activity_execution_failed` |
| Workflow failures | `temporal_cloud_v1_workflow_failed_count` | `temporal_workflow_failed` |
| Activity success | `temporal_cloud_v1_activity_success_count` | `temporal_activity_execution_latency` (duration, not count) |
| Failure conversion rate | Derived: `workflow_failed_count / activity_fail_count` | Derived: `workflow_failed / activity_execution_failed` |
| Activity execution latency | `temporal_cloud_v1_activity_start_to_close_latency_p99` | `temporal_activity_execution_latency` |
| Resource exhaustion | `temporal_cloud_v1_resource_exhausted_error_count` | `temporal_request_failure` (filtered by status) |

For threshold values (failure conversion rate >0.1 = poor, <0.01 = good; activity success rate target >95%), see `service-health-monitoring.md` § Ratio-Based Monitoring. For schedule-to-start and sync match thresholds, see `worker-health-monitoring.md` § Minimal Observations.

## Environment Detection

When the user hasn't stated their environment, use these clues. Ask if confidence is below 95%.

| Clue | Likely Environment |
|---|---|
| Namespace format `*.tmprl.cloud` or `<name>.<account>.tmprl.cloud` | Cloud |
| `temporal_cloud_v1_*` metrics | Cloud |
| Mentions `metrics.temporal.io`, API key auth, tcld, Cloud UI | Cloud |
| Mentions Actions billing, Temporal Resource Units | Cloud |
| Custom server addresses, internal IPs, non-`.tmprl.cloud` domains | Self-hosted |
| References Helm charts, docker-compose, Cassandra/MySQL persistence | Self-hosted |
| References `dynamicconfig/`, `config/development.yaml` | Self-hosted |
| Mentions history/matching/frontend service components | Self-hosted |
| Mentions `temporal server start-dev` | Dev server |
| Only SDK-side metrics, `localhost` addresses, no namespace mentioned | Ambiguous — ask |

## Decision Trees

### Scenario 1: Task Backlog / Schedule-to-Start Latency

```
User reports: workflows slow to start / backlog growing / high latency
│
├─ Check: schedule-to-start latency (SDK metric)
│   Ref: worker-health-monitoring.md § Schedule-to-Start Latency for thresholds
│
│  ├─ LOW → Backlog is NOT the problem
│  │  └─ Check execution latency, replay latency
│  │     Ref: troubleshooting.md § temporal_workflow_task_execution_latency,
│  │          § temporal_activity_execution_latency
│  │
│  └─ HIGH → Backlog confirmed, continue below
│
├─ Check: sync match rate (Cloud metric)
│   Ref: worker-health-monitoring.md § Sync Match Rate for calculation + thresholds
│
│  ├─ HIGH (healthy) → Workers exist and are matching, but cannot keep up
│  │  │
│  │  ├─ Check: worker_task_slots_available (SDK metric)
│  │  │  ├─ ZERO on all workers → Slots depleted
│  │  │  │  ├─ Host CPU/memory high → Scale horizontally (add worker instances)
│  │  │  │  └─ Host CPU/memory low → Increase max concurrent execution size
│  │  │  │     (hand off to temporal-workertuning for tuning guidance)
│  │  │  │
│  │  │  └─ Slots available → Workers have capacity but aren't polling fast enough
│  │  │     └─ Increase concurrent pollers per worker
│  │  │
│  │  └─ Ref: worker-health-monitoring.md § Handling Task Backlog Issues
│  │        § High Schedule-to-Start Latency and High Sync Match Rate
│  │
│  └─ LOW → Tasks not matching to waiting pollers
│     │
│     ├─ Check: approximate_backlog_count trend
│     │  ├─ Growing → Tasks accumulating faster than consumed
│     │  └─ Stable → May be transient spike, monitor
│     │
│     ├─ Check: no_poller_tasks_count
│     │  ├─ Non-zero → Task queue has no registered pollers at all
│     │  │  └─ Verify workers are configured for the correct task queue name
│     │  └─ Zero → Pollers exist but aren't matching
│     │
│     └─ Ref: worker-health-monitoring.md § Handling Task Backlog Issues
│           § High Schedule-to-Start Latency and Low Sync Match Rate
│
├─ Also check: is this workflow tasks or activity tasks?
│  ├─ Workflow tasks → Check replay latency, sticky cache evictions
│  │  Ref: troubleshooting.md § High temporal_workflow_task_replay_latency
│  └─ Activity tasks → Check activity execution latency, downstream dependencies
│     Ref: troubleshooting.md § temporal_activity_execution_latency Spike
│
└─ Also check: namespace capacity
   Ref: service-health-monitoring.md § Monitoring Trends Against Limits
   └─ resource_exhausted_error_count > 0 → Namespace-level throttling,
      separate problem from worker capacity
```

### Scenario 2: Activity Failure Cascade

```
User reports: activity failures / workflow failures / error rate spiking
│
├─ Check: activity failure rate
│   Cloud: temporal_cloud_v1_activity_fail_count
│   SDK: temporal_activity_execution_failed
│
│  ├─ LOW / ZERO → Failures not activity-driven
│  │  └─ Check workflow_failed_count, service_error_count directly
│  │     Ref: service-health-monitoring.md § Service Error Rate
│  │
│  └─ ELEVATED → Activity failures confirmed, continue below
│
├─ Check: failure conversion rate
│   (workflow_failed_count / activity_fail_count)
│   Ref: service-health-monitoring.md § Failure Conversion Rate for thresholds
│
│  ├─ HIGH → Workflows not handling activity failures gracefully
│  │  └─ Fix: add error handling in workflow code (try/catch, fallbacks,
│  │     compensation logic, human notification)
│  │     Hand off to temporal-developer for code changes
│  │
│  └─ LOW → Good resilience; activities fail but workflows recover
│     └─ Focus on reducing the activity failure rate itself (below)
│
├─ Check: activity success rate
│   Ref: service-health-monitoring.md § Activity Success Rate for formula + target
│
│  ├─ Below target → Systematic activity problem
│  │  │
│  │  ├─ Failures concentrated on one activity type?
│  │  │  └─ YES → Downstream dependency problem for that activity
│  │  │     ├─ Check: is the activity timing out (execution latency ≈ timeout)?
│  │  │     │  ├─ YES → Dependency slow or unresponsive; consider circuit breaker
│  │  │     │  └─ NO → Dependency returning errors; check its logs/health
│  │  │     └─ Each failed retry holds a task slot for the full timeout duration,
│  │  │        potentially starving other activities (link to Scenario 1 if
│  │  │        schedule-to-start latency also elevated)
│  │  │
│  │  └─ Failures spread across all activity types?
│  │     └─ Infrastructure-level issue
│  │        ├─ Check worker host resources (CPU, memory, disk, network)
│  │        ├─ Check for resource_exhausted_error_count (namespace limits)
│  │        └─ Check network between workers and downstream services
│  │
│  └─ Above target → Intermittent failures, likely transient
│
├─ Check: are retries eventually succeeding?
│  ├─ YES → Transient issue; monitor, may self-resolve
│  │  └─ Watch for retry storms consuming worker capacity
│  └─ NO → Persistent failure; retries waste capacity
│     └─ Fix root cause; reduce retry attempts or add backoff
│
└─ Also check: is schedule-to-start latency elevated?
   ├─ YES → Combined backlog + failure problem → also run Scenario 1
   │  (retry storms can consume slots and cause backlog)
   └─ NO → Pure failure problem, focus on activity code/dependencies
```

## Query Examples by Platform

**Critical**: All `temporal_cloud_v1_*` metrics are pre-computed per-second rates with delta temporality. NEVER apply `rate()`, `increase()`, `irate()`, or `histogram_quantile()` to them — on any platform. See SKILL.md § Critical Rules. The `rate()` function IS correct for SDK metrics (`temporal_workflow_*`, `temporal_activity_*`, etc.) and self-hosted cluster metrics.

For PromQL queries already defined in existing references, see:
- Sync match rate, poll success rate, schedule-to-start latency: `worker-health-monitoring.md`
- Failure conversion rate, activity success rate, service error rate: `service-health-monitoring.md`

### Datadog

These examples show Datadog syntax for queries not covered in other reference files.

**Backlog trend by task queue:**
```
sum:temporal_cloud_v1_approximate_backlog_count{temporal_namespace:$namespace} by {temporal_task_queue}
```

**Activity failure rate by activity type:**
```
sum:temporal_cloud_v1_activity_fail_count{temporal_namespace:$namespace} by {temporal_activity_type}
```

**Failure conversion rate:**
```
sum:temporal_cloud_v1_workflow_failed_count{temporal_namespace:$namespace}
/
sum:temporal_cloud_v1_activity_fail_count{temporal_namespace:$namespace}
```

**Namespace capacity utilization (actions):**
```
sum:temporal_cloud_v1_total_action_count{temporal_namespace:$namespace}
/
sum:temporal_cloud_v1_action_limit{temporal_namespace:$namespace}
```

**SDK schedule-to-start latency (Datadog with SDK metrics via DogStatsD or OpenMetrics):**
```
p99:temporal_activity_schedule_to_start_latency{namespace:$namespace}
```

> **Getting SDK metrics into Datadog:** Cloud metrics arrive via the serverless OpenMetrics integration (see `integrations.md`), but *SDK* metrics are emitted from your own Workers and must be ingested separately. Two options: (1) point the Datadog Agent's OpenMetrics check (`openmetrics`) at the Worker's Prometheus `/metrics` endpoint from `sdk-metrics.md` § Exposing a Metrics Endpoint, or (2) configure the SDK's statsd/DogStatsD reporter to push directly to a DogStatsD agent. Remember the unit suffix: Core SDKs export `*_milliseconds_*` series, Go/Java export `*_seconds_*`.

### New Relic (NRQL)

**Backlog count:**
```sql
SELECT latest(temporal_cloud_v1_approximate_backlog_count) FROM Metric
WHERE temporal_namespace = '{namespace}' FACET temporal_task_queue TIMESERIES
```

**Failure conversion rate:**
```sql
SELECT sum(temporal_cloud_v1_workflow_failed_count) / sum(temporal_cloud_v1_activity_fail_count)
FROM Metric WHERE temporal_namespace = '{namespace}' TIMESERIES
```

**SDK schedule-to-start latency, p99** (SDK metrics ingested via the New Relic infrastructure agent/flex integration; use the `*_milliseconds_bucket` series on Core SDKs):
```sql
SELECT percentile(temporal_activity_schedule_to_start_latency_seconds_bucket, 99) FROM Metric
WHERE namespace = '{namespace}' FACET task_queue TIMESERIES
```

## Capacity Quick Reference

For full details on limit/count/throttle triads and alerting guidance, see `service-health-monitoring.md` § Monitoring Trends Against Limits. This table adds the USE diagnostic lens.

| Resource | Utilization Check | Saturation Signal | Error Signal | Alert Strategy |
|---|---|---|---|---|
| Actions | `total_action_count / action_limit` | `total_action_throttled_count > 0` | `resource_exhausted_error_count > 0` | See alert guidance below |
| Service Requests | `service_request_count / service_request_limit` | `service_request_throttled_count > 0` | `resource_exhausted_error_count > 0` | See alert guidance below |
| Operations | `operations_count / operations_limit` | `operations_throttled_count > 0` | `resource_exhausted_error_count > 0` | See alert guidance below |
| Pollers | `service_pending_requests` approaching `poller_limit` | N/A | N/A | Monitor trend |

For alert thresholds on these limits, see `service-health-monitoring.md` § Alerting Guidance.

All metric names above are shorthand for `temporal_cloud_v1_` prefix.
