# Groq API Cookbook

Copy-pasteable code for every capability. All snippets use the `groq` Python
SDK (`pip install groq`); the `Groq()` client reads `GROQ_API_KEY` from the
environment. The OpenAI SDK works identically against
`https://api.groq.com/openai/v1` — see the last section.

## Streaming

Stream tokens as they are generated. Guard against `None` deltas (the final
chunk and role-only chunks carry no content).

```python
from groq import Groq

client = Groq()
stream = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Explain fast inference."}],
    stream=True,
)
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="")
```

## JSON Mode

Force valid JSON output. Always instruct the model to emit JSON in the system
prompt and set `temperature=0` for stable parsing.

```python
from groq import Groq
import json

client = Groq()
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "Output valid JSON only."},
        {"role": "user", "content": "List 3 programming languages with their paradigms."},
    ],
    response_format={"type": "json_object"},
    temperature=0,
)
data = json.loads(response.choices[0].message.content)
```

## Tool / Function Calling

The model returns a `tool_calls` list. Execute the function yourself, then send
the result back as a `role="tool"` message referencing the original
`tool_call_id`. Not all models support tools — prefer Llama 3.3 70B or GPT-OSS.

```python
from groq import Groq
import json

client = Groq()
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
}]

messages = [{"role": "user", "content": "Weather in San Francisco?"}]
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=messages,
    tools=tools,
    tool_choice="auto",
)

message = response.choices[0].message
if message.tool_calls:
    call = message.tool_calls[0]
    args = json.loads(call.function.arguments)
    # ... run the real function using `args` ...
    result = {"temperature": 62, "condition": "foggy"}
    followup = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            *messages,
            message,  # the assistant turn that requested the tool
            {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)},
        ],
    )
    print(followup.choices[0].message.content)
```

## Vision

Llama-4 models accept image input as a content part, by URL or base64 data URI.
Max image size 20 MB.

```python
from groq import Groq

client = Groq()
response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image."},
            {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}},
        ],
    }],
    max_completion_tokens=1024,
)
print(response.choices[0].message.content)
```

Vision-capable ids: `meta-llama/llama-4-scout-17b-16e-instruct`,
`meta-llama/llama-4-maverick-17b-128e-instruct`.

## Speech-to-Text (Whisper)

Near-instant transcription on the LPU. Accepted formats: flac, mp3, mp4, mpeg,
mpga, m4a, ogg, wav, webm. Max upload 25 MB (free) / 100 MB (developer tier).
Pass the file as a `(filename, fileobj)` tuple.

```python
from groq import Groq

client = Groq()
with open("audio.mp3", "rb") as f:
    result = client.audio.transcriptions.create(
        file=("audio.mp3", f),
        model="whisper-large-v3-turbo",
        language="en",
        response_format="verbose_json",
    )
print(result.text)
```

### Translation (any language → English)

```python
from groq import Groq

client = Groq()
with open("french.mp3", "rb") as f:
    result = client.audio.translations.create(
        file=("french.mp3", f),
        model="whisper-large-v3",
    )
print(result.text)
```

## Text-to-Speech

Returns raw audio bytes on `.content`. Voices are model-specific (PlayAI,
Orpheus).

```python
from groq import Groq
from pathlib import Path

client = Groq()
speech = client.audio.speech.create(
    model="playai-tts",
    voice="Arista-PlayAI",
    input="Hello from Groq!",
)
Path("output.mp3").write_bytes(speech.content)
```

## OpenAI SDK Compatibility

Drop-in for the OpenAI Python SDK — override `base_url` and `api_key`, then use
the same call shapes as above.

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello from the OpenAI SDK!"}],
)
print(response.choices[0].message.content)
```

Supported vs. unsupported endpoints and rejected request fields are listed in
`troubleshooting.md`.
