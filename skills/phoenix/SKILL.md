---
name: phoenix
description: Open-source AI observability platform (Arize Phoenix) for LLM tracing, evaluation, datasets, experiments, and real-time monitoring via OpenTelemetry/OpenInference. Use when debugging LLM apps with detailed traces, running LLM-as-judge evals on datasets, comparing prompts/models with experiments, or self-hosting production AI observability without vendor lock-in. Do NOT use when you want a managed/hosted platform (Arize Cloud, LangSmith), LangChain-only tracing where LangSmith is simpler, classic ML experiment tracking (use Weights & Biases or MLflow), or general APM for non-LLM services (use Datadog/Grafana).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Observability, Phoenix, Arize, Tracing, Evaluation, Monitoring, LLM Ops, OpenTelemetry]
dependencies: [arize-phoenix>=12.0.0]
---

# Phoenix - AI Observability Platform

Open-source AI observability and evaluation platform for LLM applications: tracing,
evaluation, datasets, experiments, and real-time monitoring. This file is a router —
the detailed APIs live in `references/`.

## When to use Phoenix

**Use Phoenix when:**
- Debugging LLM application issues with detailed traces
- Running systematic LLM-as-judge evaluations on datasets
- Comparing prompts, models, or configs with experiment pipelines
- Monitoring production LLM systems in real-time
- Self-hosting observability without vendor lock-in (PostgreSQL or SQLite)

**Use alternatives instead:**
- **Arize Cloud** — managed Phoenix with enterprise features (you want hosted)
- **LangSmith** — managed, LangChain-first tracing (simpler for pure LangChain)
- **Weights & Biases / MLflow** — classic ML experiment tracking & model registry
- **Datadog / Grafana** — general APM for non-LLM services

**Key features:** OpenTelemetry/OpenInference tracing for any LLM framework; LLM-as-judge
evaluators; versioned datasets for regression testing; experiments; interactive playground.

## Quick start

### Installation

```bash
pip install arize-phoenix

# Optional split packages
pip install arize-phoenix-otel     # OpenTelemetry config helpers
pip install arize-phoenix-evals    # Evaluation framework
pip install arize-phoenix-client   # Lightweight REST client
pip install arize-phoenix[embeddings]  # Embedding analysis
```

### Launch the server

```python
import phoenix as px

session = px.launch_app()   # notebook (ThreadServer)
session.view()              # embedded iframe
print(session.url)          # http://localhost:6006
```

```bash
phoenix serve --port 6006   # standalone / production
```

### First trace

```python
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor

tracer_provider = register(
    project_name="my-llm-app",
    endpoint="http://localhost:6006/v1/traces",
)
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# All OpenAI calls are now traced
from openai import OpenAI
client = OpenAI()
client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

## Where to go next

- **[Core usage](references/core-usage.md)** — traces/spans & projects, framework
  instrumentation (OpenAI, LangChain, LlamaIndex, Anthropic), evaluators, datasets &
  experiments, client API, production deployment (Docker/PostgreSQL/auth), best practices.
- **[Advanced usage](references/advanced-usage.md)** — custom & multi-criteria evaluators,
  batch/concurrent eval, A/B and multi-model experiments, Kubernetes/Compose/HA manifests,
  distributed & session tracing, data export/retention, CI/CD and alerting pipelines.
- **[Troubleshooting](references/troubleshooting.md)** — traces not appearing, missing/
  duplicate spans, eval rate limits, client/DB connection errors, performance tuning.

## Related skills

- Sibling observability skills under `neuro-centrifuge/observability/` for tracing
  backends and dashboards.
- LLM-as-judge evaluation workflows pair with eval/dataset skills in `neuro-quant`.

## Resources

- Documentation: https://docs.arize.com/phoenix
- Repository: https://github.com/Arize-ai/phoenix
- Docker Hub: https://hub.docker.com/r/arizephoenix/phoenix
- Phoenix license: Apache 2.0 (this skill: MIT)
