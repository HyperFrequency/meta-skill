# Phoenix Core Usage

Detailed APIs for tracing, framework instrumentation, evaluation, datasets/experiments,
the client, and production deployment. The SKILL.md quick start covers install + launch +
a first trace; this file is the reference for everything beyond that.

## Core concepts

### Traces and spans

A **trace** is a complete execution flow; **spans** are individual operations within it.

```python
from phoenix.otel import register
from opentelemetry import trace

tracer_provider = register(project_name="my-app")
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_query") as span:
    span.set_attribute("input.value", query)

    # Child spans are automatically nested
    with tracer.start_as_current_span("retrieve_context"):
        context = retriever.search(query)

    with tracer.start_as_current_span("generate_response"):
        response = llm.generate(query, context)

    span.set_attribute("output.value", response)
```

### Projects

Projects organize related traces:

```python
import os
os.environ["PHOENIX_PROJECT_NAME"] = "production-chatbot"

# Or per-trace
from phoenix.otel import register
tracer_provider = register(project_name="experiment-v2")
```

## Framework instrumentation

All integrations follow the same pattern: `register()` once, then call the matching
OpenInference instrumentor. Install the instrumentor package alongside it, e.g.
`pip install openinference-instrumentation-openai`.

### OpenAI

```python
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor

tracer_provider = register()
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

### LangChain

```python
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

tracer_provider = register()
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
response = llm.invoke("Hello!")
```

### LlamaIndex

```python
from phoenix.otel import register
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

tracer_provider = register()
LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
```

### Anthropic

```python
from phoenix.otel import register
from openinference.instrumentation.anthropic import AnthropicInstrumentor

tracer_provider = register()
AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
```

## Evaluation framework

### Built-in evaluators

```python
from phoenix.evals import (
    OpenAIModel,
    HallucinationEvaluator,
    RelevanceEvaluator,
    ToxicityEvaluator,
    llm_classify,
)

eval_model = OpenAIModel(model="gpt-4o")

hallucination_eval = HallucinationEvaluator(eval_model)
results = hallucination_eval.evaluate(
    input="What is the capital of France?",
    output="The capital of France is Paris.",
    reference="Paris is the capital of France.",
)
```

### Custom evaluators

```python
from phoenix.evals import llm_classify

def evaluate_helpfulness(input_text, output_text):
    template = """
    Evaluate if the response is helpful for the given question.

    Question: {input}
    Response: {output}

    Is this response helpful? Answer 'helpful' or 'not_helpful'.
    """
    return llm_classify(
        model=eval_model,
        template=template,
        input=input_text,
        output=output_text,
        rails=["helpful", "not_helpful"],
    )
```

See `advanced-usage.md` for template-based, multi-criteria, and batch/concurrent evaluators.

### Run evaluations on a dataset of spans

```python
from phoenix import Client
from phoenix.evals import run_evals

client = Client()

spans_df = client.get_spans_dataframe(
    project_name="my-app",
    filter_condition="span_kind == 'LLM'",
)

eval_results = run_evals(
    dataframe=spans_df,
    evaluators=[
        HallucinationEvaluator(eval_model),
        RelevanceEvaluator(eval_model),
    ],
    provide_explanation=True,
)

client.log_evaluations(eval_results)
```

## Datasets and experiments

### Create a dataset

```python
from phoenix import Client

client = Client()

dataset = client.create_dataset(
    name="qa-test-set",
    description="QA evaluation dataset",
)

client.add_examples_to_dataset(
    dataset_name="qa-test-set",
    examples=[
        {"input": {"question": "What is Python?"}, "output": {"answer": "A programming language"}},
        {"input": {"question": "What is ML?"}, "output": {"answer": "Machine learning"}},
    ],
)
```

### Run an experiment

```python
from phoenix import Client
from phoenix.experiments import run_experiment

client = Client()

def my_model(input_data):
    question = input_data["question"]
    return {"answer": generate_answer(question)}

def accuracy_evaluator(input_data, output, expected):
    correct = expected["answer"].lower() in output["answer"].lower()
    return {"score": 1.0 if correct else 0.0, "label": "correct" if correct else "incorrect"}

results = run_experiment(
    dataset_name="qa-test-set",
    task=my_model,
    evaluators=[accuracy_evaluator],
    experiment_name="baseline-v1",
)

print(f"Average accuracy: {results.aggregate_metrics['accuracy']}")
```

See `advanced-usage.md` for A/B prompt testing and multi-model comparison experiments.

## Client API

### Query traces and spans

```python
from phoenix import Client

client = Client(endpoint="http://localhost:6006")  # no /v1 suffix for the client

spans_df = client.get_spans_dataframe(
    project_name="my-app",
    filter_condition="span_kind == 'LLM'",
    limit=1000,
)

span = client.get_span(span_id="abc123")
trace = client.get_trace(trace_id="xyz789")
```

### Log feedback / annotations

```python
client.log_annotation(
    span_id="abc123",
    name="user_rating",
    annotator_kind="HUMAN",
    score=0.8,
    label="helpful",
    metadata={"comment": "Good response"},
)
```

### Export data

```python
df = client.get_spans_dataframe(project_name="my-app")
traces = client.list_traces(project_name="my-app")
```

## Production deployment

### Docker

```bash
docker run -p 6006:6006 arizephoenix/phoenix:latest
```

### With PostgreSQL

```bash
export PHOENIX_SQL_DATABASE_URL="postgresql://user:pass@host:5432/phoenix"
phoenix serve --host 0.0.0.0 --port 6006
```

### Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PHOENIX_PORT` | HTTP server port | `6006` |
| `PHOENIX_HOST` | Server bind address | `127.0.0.1` |
| `PHOENIX_GRPC_PORT` | gRPC/OTLP port | `4317` |
| `PHOENIX_SQL_DATABASE_URL` | Database connection | SQLite temp |
| `PHOENIX_WORKING_DIR` | Data storage directory | OS temp |
| `PHOENIX_ENABLE_AUTH` | Enable authentication | `false` |
| `PHOENIX_SECRET` | JWT signing secret | Required if auth enabled |

### With authentication

```bash
export PHOENIX_ENABLE_AUTH=true
export PHOENIX_SECRET="your-secret-key-min-32-chars"
export PHOENIX_ADMIN_SECRET="admin-bootstrap-token"

phoenix serve
```

See `advanced-usage.md` for Kubernetes, Docker Compose, and HA deployment manifests.

## Best practices

1. **Use projects** to separate traces by environment (dev/staging/prod).
2. **Add metadata** (user IDs, session IDs) for debugging.
3. **Evaluate regularly** — run automated evaluations in CI/CD.
4. **Version datasets** to track test-set changes over time.
5. **Monitor costs** via token usage in Phoenix dashboards.
6. **Self-host** with PostgreSQL for production deployments.
