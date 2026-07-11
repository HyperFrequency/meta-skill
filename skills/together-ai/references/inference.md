# Inference

Chat completions are the primary endpoint. All examples use the first-party
`together` SDK; every call here also works with the `openai` SDK pointed at
`https://api.together.xyz/v1` (see
[integration-and-troubleshooting.md](integration-and-troubleshooting.md)).

## Chat completions

Supports system/user/assistant messages plus the usual sampling controls:
`max_tokens`, `temperature`, `top_p`, `top_k`, `repetition_penalty`, and `stop`.

```python
from together import Together

client = Together()

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3",
    messages=[
        {"role": "system", "content": "You are an expert ML researcher."},
        {"role": "user", "content": "Compare LoRA vs full fine-tuning."},
    ],
    max_tokens=512,
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    repetition_penalty=1.1,
    stop=["</s>"],
)

print(response.choices[0].message.content)
print(f"Tokens used: {response.usage.total_tokens}")
```

Note: `top_k` and `repetition_penalty` are Together extensions. They are honored
on the native endpoint but are ignored (or rejected) if you send them through
the strict OpenAI SDK schema — keep them out of `openai`-SDK calls.

## Streaming

Set `stream=True` and iterate deltas. Streaming does not change price; it lowers
time-to-first-token and lets you abort early.

```python
from together import Together

client = Together()

stream = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    messages=[{"role": "user", "content": "Write a haiku about transformers."}],
    max_tokens=128,
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
print()
```

## Function calling

Supported on tool-capable models (Llama 3.x, DeepSeek, Qwen3, Mistral variants).
Pass OpenAI-style tool schemas; read back `message.tool_calls`.

```python
from together import Together

client = Together()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather in San Francisco?"},
    ],
    tools=tools,
    tool_choice="auto",
)

tool_calls = response.choices[0].message.tool_calls
if tool_calls:
    call = tool_calls[0]
    print(call.function.name, call.function.arguments)
```

If tool calls never fire, confirm the model supports tools — many base/instruct
models do not.

## JSON mode (structured outputs)

Force valid JSON with `response_format`. For reliability, also restate the
schema in the system prompt — some models honor the constraint only when the
schema is visible in-context.

```python
import json
from together import Together

client = Together()

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "age", "skills"],
}

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    messages=[
        {"role": "system",
         "content": f"Respond only in JSON matching this schema: {json.dumps(schema)}"},
        {"role": "user", "content": "Create a profile for a senior ML engineer."},
    ],
    response_format={"type": "json_object", "schema": schema},
)

data = json.loads(response.choices[0].message.content)
print(json.dumps(data, indent=2))
```

Always wrap `json.loads` in a try/except and retry once — constrained decoding
reduces but does not eliminate malformed output on smaller models.

## Vision (multimodal)

Send content parts with `image_url` to a vision-language model. URLs and
`data:` base64 URIs both work.

```python
from together import Together

client = Together()

response = client.chat.completions.create(
    model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail."},
                {"type": "image_url",
                 "image_url": {"url": "https://example.com/image.jpg"}},
            ],
        }
    ],
    max_tokens=512,
)

print(response.choices[0].message.content)
```

Confirm the exact vision model ID in the live catalog — VLM suffixes and
availability change.

## Async client

For high-throughput fan-out, use `AsyncTogether` and `await` the same methods:

```python
import asyncio
from together import AsyncTogether

client = AsyncTogether()

async def ask(prompt: str) -> str:
    resp = await client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Reference",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=128,
    )
    return resp.choices[0].message.content

async def main():
    prompts = ["What is PyTorch?", "What is JAX?", "What is Triton?"]
    print(await asyncio.gather(*(ask(p) for p in prompts)))

asyncio.run(main())
```

Expect `429 Rate Limited` under heavy concurrency; wrap calls in exponential
backoff and cap in-flight requests. See
[integration-and-troubleshooting.md](integration-and-troubleshooting.md).
