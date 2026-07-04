# Alert Rule Templates

Copy-pasteable alert definitions for the headline worker- and service-health signals this skill already defines thresholds for. Thresholds come from `worker-health-monitoring.md` and `service-health-monitoring.md`; consult those files for what each signal means and how to interpret it.

**Before using:**
- These are templates — replace `$namespace`, label values, `for:` durations, and notification targets with your own.
- **SDK histogram unit suffix:** the schedule-to-start examples use `*_seconds_bucket` (Go/Java). For Core SDKs (TypeScript, Python, .NET, Ruby, PHP) the series is `*_milliseconds_bucket` and the threshold is in ms (`200`, not `0.2`). See `sdk-metrics.md` § Metric Unit Differences.
- **Never apply `rate()` to `temporal_cloud_v1_*` metrics** — they are pre-computed rates. `rate()` is correct only for SDK metrics (the schedule-to-start histograms below).

## Headline signals and thresholds

| Signal | Source metric(s) | Alert threshold |
|---|---|---|
| Schedule-to-start latency (p99) | `temporal_*_schedule_to_start_latency` (SDK) | > 200ms p99 (> 100ms p95 = warn) |
| Sync match rate | `temporal_cloud_v1_poll_success_sync_count` / `temporal_cloud_v1_poll_success_count` | < 95% p99 (< 99% p95 = warn) |
| Poll success rate | `temporal_cloud_v1_poll_success_count` / (success + timeout) | < 90% (< 95% for high-volume/low-latency) |
| Failure conversion rate | `temporal_cloud_v1_workflow_failed_count` / `temporal_cloud_v1_activity_fail_count` | > 0.1 (poor error handling); < 0.01 is healthy |

## Prometheus (`alerting_rules.yml`)

```yaml
groups:
  - name: temporal-worker-health
    rules:
      # Schedule-to-start latency, p99 > 200ms.
      # Go/Java: *_seconds_bucket, threshold 0.2. Core SDKs: *_milliseconds_bucket, threshold 200.
      - alert: TemporalWorkflowScheduleToStartHigh
        expr: |
          histogram_quantile(0.99,
            sum(rate(temporal_workflow_task_schedule_to_start_latency_seconds_bucket{namespace="$namespace"}[5m]))
            by (le, namespace, task_queue)
          ) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Workflow Task schedule-to-start p99 > 200ms on {{ $labels.task_queue }}"
          description: "Tasks are waiting for workers. Check sync match rate to decide whether to add workers/pollers."

      - alert: TemporalActivityScheduleToStartHigh
        expr: |
          histogram_quantile(0.99,
            sum(rate(temporal_activity_schedule_to_start_latency_seconds_bucket{namespace="$namespace"}[5m]))
            by (le, namespace, task_queue)
          ) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Activity schedule-to-start p99 > 200ms on {{ $labels.task_queue }}"

      # Sync match rate < 95% (Cloud v1 metrics — no rate()).
      - alert: TemporalSyncMatchRateLow
        expr: |
          sum by (temporal_namespace) (temporal_cloud_v1_poll_success_sync_count{temporal_namespace=~"$namespace"})
          /
          sum by (temporal_namespace) (temporal_cloud_v1_poll_success_count{temporal_namespace=~"$namespace"})
          < 0.95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Sync match rate < 95% in {{ $labels.temporal_namespace }}"
          description: "Tasks are being persisted instead of matched directly to available workers."

      # Poll success rate < 90% (Cloud v1 metrics).
      - alert: TemporalPollSuccessRateLow
        expr: |
          sum by (temporal_namespace) (temporal_cloud_v1_poll_success_count{temporal_namespace=~"$namespace"})
          /
          (
            sum by (temporal_namespace) (temporal_cloud_v1_poll_success_count{temporal_namespace=~"$namespace"})
            +
            sum by (temporal_namespace) (temporal_cloud_v1_poll_timeout_count{temporal_namespace=~"$namespace"})
          )
          < 0.90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Poll success rate < 90% in {{ $labels.temporal_namespace }}"
          description: "If schedule-to-start latency and host utilization are also low, you may have too many pollers/workers (greedy workers)."

  - name: temporal-service-health
    rules:
      # Failure conversion rate > 0.1 (Cloud v1 metrics).
      - alert: TemporalFailureConversionRateHigh
        expr: |
          sum by (temporal_namespace) (temporal_cloud_v1_workflow_failed_count{temporal_namespace=~"$namespace"})
          /
          sum by (temporal_namespace) (temporal_cloud_v1_activity_fail_count{temporal_namespace=~"$namespace"})
          > 0.1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Failure conversion rate > 0.1 in {{ $labels.temporal_namespace }}"
          description: "Activity failures are converting into workflow failures — error handling may be inadequate."
```

## Datadog monitor (JSON, via the Monitors API)

Example for sync match rate < 95%. Datadog exposes the scraped OpenMetrics series under their original names; adjust if your integration prefixes them.

```json
{
  "name": "Temporal sync match rate < 95%",
  "type": "metric alert",
  "query": "sum:temporal_cloud_v1_poll_success_sync_count{temporal_namespace:$namespace}.as_count() / sum:temporal_cloud_v1_poll_success_count{temporal_namespace:$namespace}.as_count() < 0.95",
  "message": "Sync match rate below 95% — tasks are being persisted instead of matched to available workers. @slack-temporal-alerts",
  "tags": ["service:temporal", "team:platform"],
  "options": {
    "thresholds": { "critical": 0.95 },
    "notify_no_data": true,
    "no_data_timeframe": 10,
    "evaluation_delay": 180
  }
}
```

Notes:
- `evaluation_delay: 180` accounts for the ~3-minute Cloud metrics data latency.
- For schedule-to-start latency in Datadog, alert on the SDK distribution metric's p99 (e.g., `p99:temporal_workflow_task_schedule_to_start_latency{...} > 0.2` for Go/Java, `> 200` for Core SDKs).

## Grafana (provisioned alert rule, `alerting/*.yaml`)

Grafana alert backed by a Prometheus datasource. This example is sync match rate < 95%; swap the `expr` for any PromQL rule above.

```yaml
apiVersion: 1
groups:
  - orgId: 1
    name: temporal-worker-health
    folder: Temporal
    interval: 1m
    rules:
      - uid: temporal-sync-match-rate
        title: Temporal sync match rate < 95%
        condition: C
        data:
          - refId: A
            datasourceUid: ${PROMETHEUS_DS_UID}
            model:
              expr: |
                sum by (temporal_namespace) (temporal_cloud_v1_poll_success_sync_count{temporal_namespace=~"$namespace"})
                /
                sum by (temporal_namespace) (temporal_cloud_v1_poll_success_count{temporal_namespace=~"$namespace"})
              instant: true
          - refId: C
            datasourceUid: __expr__
            model:
              type: threshold
              expression: A
              conditions:
                - evaluator:
                    type: lt
                    params: [0.95]
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: Sync match rate below 95%
```
