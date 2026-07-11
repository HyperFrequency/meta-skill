# Groq Troubleshooting & Compatibility

Error triage, the OpenAI-compatibility surface, and a retry helper. For model
ids and rate-limit numbers see `models-and-limits.md`; for full working code see
`api-cookbook.md`.

## OpenAI endpoint support

Groq exposes an OpenAI-compatible surface at
`https://api.groq.com/openai/v1`. Not every OpenAI endpoint exists.

| Endpoint | Supported | Notes |
|----------|-----------|-------|
| `POST /chat/completions` | Yes | Streaming, tools, JSON mode. |
| `POST /audio/transcriptions` | Yes | Whisper. |
| `POST /audio/translations` | Yes | Whisper, any language → English. |
| `POST /audio/speech` | Yes | TTS (PlayAI / Orpheus). |
| `GET /models` | Yes | List available models. |
| `POST /embeddings` | No | Not offered — returns an error. |
| `POST /images/generations` | No | Not offered — returns an error. |

## Unsupported request fields

These OpenAI fields are rejected with `400 Bad Request`. Strip them before
sending:

- `logprobs`, `top_logprobs`
- `logit_bias`
- per-message `name`
- `n` (must be `1`; Groq does not return multiple choices)

Also use `max_completion_tokens`, not `max_tokens` — the OpenAI-legacy
`max_tokens` is deprecated on Groq and triggers a warning.

## Common issues

| Problem | Cause & fix |
|---------|-------------|
| `401 Unauthorized` | `GROQ_API_KEY` missing or invalid. Create one at https://console.groq.com/keys and export it. |
| `400 Bad Request` | An unsupported field is present. Remove `logprobs`, `logit_bias`, `top_logprobs`, per-message `name`, and set `n=1`. |
| `429 Too Many Requests` | Rate limit hit. Honor `retry-after`, back off exponentially, or upgrade to the developer tier for ~10x limits. |
| Empty stream output | `chunk.choices[0].delta.content` is `None` on role-only and final chunks — guard for `None` before printing. |
| Invalid JSON returned | Add "Output valid JSON only" to the system prompt and set `temperature=0`. Use `response_format={"type": "json_object"}`. |
| No tool calls produced | Not every model supports tools. Use `llama-3.3-70b-versatile` or a GPT-OSS model. |
| Audio upload rejected | Over the size cap (25 MB free / 100 MB developer). Downsample to 16 kHz mono WAV or upgrade the tier. |
| Vision request fails | Only Llama-4 models accept images, and each image must be ≤ 20 MB. |
| `n` parameter error | Groq only supports `n=1`. |
| `max_tokens` warning | Rename to `max_completion_tokens`. |

## Retry with exponential backoff

Handle `429` (and transient errors) without a client-side rate-limiter. Prefer
honoring the server's `retry-after` header when present; the backoff below is a
safe fallback.

```python
import time
from groq import Groq, RateLimitError

client = Groq()

def call_with_retry(messages, model="llama-3.3-70b-versatile", max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(model=model, messages=messages)
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

## Reference links

- API overview: https://console.groq.com/docs/overview
- OpenAI compatibility: https://console.groq.com/docs/openai
- Rate limits: https://console.groq.com/docs/rate-limits
- Status page: https://status.groq.com
