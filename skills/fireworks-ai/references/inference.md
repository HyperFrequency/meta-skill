# Fireworks AI — Inference

All inference runs against the OpenAI-compatible base URL
`https://api.fireworks.ai/inference/v1`. Every snippet assumes a `client`
constructed as in the SKILL.md Quick Start and `import os`.

## Chat completions

`POST /chat/completions`

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "Write a Python quicksort function."}],
    max_tokens=512,
    temperature=0.0,
)
print(response.choices[0].message.content)
```

Common parameters: `max_tokens`, `temperature`, `top_p`, `top_k`, `stop`,
`presence_penalty`, `frequency_penalty`, `n`. Token accounting is on
`response.usage` (`prompt_tokens`, `completion_tokens`, `total_tokens`).

## Streaming

```python
stream = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "Explain transformers."}],
    stream=True,
    max_tokens=512,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

To get token usage on a streamed call, pass
`stream_options={"include_usage": True}` and read `usage` from the final chunk.
Requires `openai >= 1.6.1`.

## Function calling / tool use

Supported by tool-capable models (Llama 3.3, Qwen, DeepSeek V3).

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "What is the weather in San Francisco?"}],
    tools=tools,
    tool_choice="auto",  # or {"type": "function", "function": {"name": "get_weather"}}
)
tool_call = response.choices[0].message.tool_calls[0]
print(tool_call.function.name, tool_call.function.arguments)  # arguments is a JSON string
```

## Structured output / JSON mode

Free-form JSON:

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "List 3 planets with mass and diameter."}],
    response_format={"type": "json_object"},
    max_tokens=512,
)
import json
data = json.loads(response.choices[0].message.content)
```

Schema-constrained output — Fireworks accepts a `schema` alongside
`json_object`, which enforces the structure at decode time (grammar-constrained
sampling), so the model cannot emit non-conforming JSON:

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "Extract name and age from: John is 30."}],
    response_format={
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        },
    },
)
```

Prefer the schema form when you parse the output programmatically — plain
`json_object` mode can still emit valid-but-off-shape JSON.

## Vision (multimodal)

Use a vision-capable model and content parts:

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p2-11b-vision-instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image."},
                {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}},
            ],
        }
    ],
    max_tokens=256,
)
print(response.choices[0].message.content)
```

The `url` may be an https link or a `data:image/...;base64,...` URI for local
images.

## Embeddings

`POST /embeddings`

```python
response = client.embeddings.create(
    model="nomic-ai/nomic-embed-text-v1.5",
    input=["Machine learning is a subset of AI.", "Deep learning uses neural networks."],
)
for i, item in enumerate(response.data):
    print(f"Embedding {i}: {len(item.embedding)} dimensions")
```

Supported embedding models and dimensions are in
[models-and-pricing.md](models-and-pricing.md).

## Fireworks-specific parameter

`context_length_exceeded_behavior` controls what happens when
`prompt + max_tokens` overflows the model's context window. Pass it via
`extra_body` so the OpenAI SDK forwards it:

```python
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "..."}],
    max_tokens=512,
    extra_body={"context_length_exceeded_behavior": "truncate"},  # or "error"
)
```

`"truncate"` drops overflow from the prompt; `"error"` (default) raises instead.
