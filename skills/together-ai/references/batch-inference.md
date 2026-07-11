# Batch inference

The batch API runs large volumes of requests asynchronously at roughly half the
per-token price, with a turnaround window (about 24 hours). Use it for
evaluations, synthetic dataset generation, and bulk classification — anything
that does not need a live response.

> The first-party `batches` method names (`create_batch`, `get_batch`,
> `list_batches`) have varied across `together` releases. Confirm the current
> shape against your installed version (`pip show together`) and
> https://docs.together.ai/reference. Together also exposes an
> OpenAI-compatible `/v1/batches` surface, so the stock `openai` SDK's
> `client.batches.create/retrieve/list` is a stable alternative worth preferring
> if the first-party names drift.

## Input file format

One request per line. Each line has a `custom_id` (your correlation key) and a
`body` that is a normal chat-completions payload.

```jsonl
{"custom_id": "request-1", "body": {"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "What is machine learning?"}], "max_tokens": 200}}
{"custom_id": "request-2", "body": {"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "Explain gradient descent."}], "max_tokens": 200}}
{"custom_id": "request-3", "body": {"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "What are transformers?"}], "max_tokens": 200}}
```

Keep `custom_id` unique per line — results come back unordered and you join on
it. A malformed line (missing `custom_id` or `body`) can fail the batch, so
validate the JSONL first.

## Submit and poll (first-party SDK)

```python
from together import Together

client = Together()

# 1. Upload the batch file
batch_file = client.files.upload(file="batch_requests.jsonl", purpose="batch-api")

# 2. Create the batch job
batch = client.batches.create_batch(
    file_id=batch_file.id,
    endpoint="/v1/chat/completions",
)
print(f"Batch ID: {batch.id}")

# 3. Poll status
status = client.batches.get_batch(batch.id)
print(status.status)

# 4. Download results when COMPLETED
if status.status == "COMPLETED":
    results = client.files.retrieve_content(id=status.output_file_id)
    print(results)

# List all batches
for b in client.batches.list_batches():
    print(b.id, b.status)
```

## Submit via the OpenAI SDK (stable alternative)

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["TOGETHER_API_KEY"],
    base_url="https://api.together.xyz/v1",
)

up = client.files.create(file=open("batch_requests.jsonl", "rb"), purpose="batch")
batch = client.batches.create(
    input_file_id=up.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)
batch = client.batches.retrieve(batch.id)
if batch.status == "completed":
    content = client.files.content(batch.output_file_id)
    print(content.text)
```

## Operational notes

- Poll on an interval (e.g. every 30–60s); do not busy-loop.
- A failed batch usually means bad JSONL — check that every line has
  `custom_id` and `body`, and that each `body.model` is a valid, available
  model ID.
- Batch is a throughput/cost tool, not a latency tool. If you need answers now,
  use live `chat.completions` (see [inference.md](inference.md)).
