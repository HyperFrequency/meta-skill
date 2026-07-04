# Temporal Observability Skill

A skill for coding agents to use across the full [Temporal](https://temporal.io/) observability pillar — instrumenting, collecting, querying, and alerting on metrics; propagating distributed traces through durable Workflows; and configuring replay-aware structured logging — across Temporal Cloud and self-hosted deployments.

> [!WARNING]
> This Skill is currently in Public Preview, and will continue to evolve and improve.
> We would love to hear your feedback - positive or negative - over in the [Community Slack](https://t.mp/slack), in the [#topic-ai channel](https://temporalio.slack.com/archives/C0818FQPYKY)

## Installation

### Via manual clone (user-level)

Cloning into `~/.claude/skills/` makes the skill available across all sessions and projects for your user.

```bash
mkdir -p ~/.claude/skills && git clone https://github.com/temporalio/skill-temporal-observability ~/.claude/skills/temporal-observability
```

### Via CLI flag (per-session)

```bash
claude --plugin-dir /path/to/skill-temporal-observability
```

This loads the skill for a single session without permanently installing it.

## Supported Integrations

- Datadog
- Grafana Cloud
- ClickStack
- New Relic
- Prometheus (self-hosted)
- OpenTelemetry Collector
