---
name: groq
version: 0.1.0
description: >-
  Ultra-fast, OpenAI-compatible LLM inference on Groq LPU hardware (500-1000+
  tok/s) for open-weight models (Llama, Qwen, GPT-OSS, Kimi). Use when you need
  lowest-latency real-time chat/agents, a drop-in OpenAI replacement backed by
  open models, fast Whisper transcription, Llama-4 vision, tool calling, JSON
  mode, or streaming — and a free tier for prototyping. Covers the `groq` Python
  SDK, model selection, rate limits, cost tuning, and failure modes. Do NOT use
  to fine-tune or train (inference only), to call proprietary models (GPT-4o,
  Claude, Gemini), or for embeddings/image generation (Groq offers neither) —
  for those use the vendor SDK or a multi-provider gateway.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (groq-python SDK)"
---

# Groq — Ultra-Fast LLM Inference

## Overview

Groq serves open-weight LLMs on custom LPU (Language Processing Unit) silicon,
delivering the lowest inference latency in the industry — commonly 280-1000+
tokens/sec depending on model. The API is OpenAI-compatible, has a free tier,
and bills pay-per-token. It is **inference only**: no fine-tuning, no training,
no embeddings, no image generation.

Reach for Groq when wall-clock latency is the constraint and an open-weight
model is acceptable. Everything you send is a standard chat/audio request; the
speed comes from the hardware, not from a different API surface.

This SKILL.md is a router. Deep material lives in `references/`:

- `references/models-and-limits.md` — full model catalog, selection guide,
  pricing snapshot, rate-limit tiers, cost-optimization tactics.
- `references/api-cookbook.md` — complete code for streaming, JSON mode, tool
  calling, vision, transcription/translation, TTS, and OpenAI-SDK compat.
- `references/troubleshooting.md` — error table, retry/backoff pattern,
  unsupported fields.

## When to Use This Skill

- You need the fastest possible token throughput: real-time chat, voice agents,
  interactive UIs, or agent loops where per-step latency dominates.
- You want open-weight models (Llama 3.x/4, Qwen3, GPT-OSS, Kimi K2, DeepSeek
  distills) without provisioning or managing GPUs.
- You want a **drop-in OpenAI-compatible** endpoint — point an existing OpenAI
  SDK at `https://api.groq.com/openai/v1` and swap the model id.
- You need fast Whisper speech-to-text/translation, or Llama-4 vision.
- You want free-tier access to prototype before committing spend.

## When NOT to Use This Skill

- You need to **fine-tune or train** a model — Groq is inference only. The
  sibling `together-ai` and `fireworks-ai` skills host open models and support
  fine-tuning.
- You need **proprietary models** (GPT-4o, Claude, Gemini) — use the vendor SDK.
  For Anthropic specifically see the `claude-api` skill.
- You need **embeddings** or **image generation** — Groq exposes neither
  endpoint; both return an error.
- You want to route across many providers with fallback/price arbitrage — a
  gateway fits better (see the `openrouter-typescript-sdk` skill). Groq is a
  single provider optimized for speed.

## Setup

```bash
pip install groq
export GROQ_API_KEY="gsk_..."   # create at https://console.groq.com/keys
```

The `Groq()` client reads `GROQ_API_KEY` from the environment automatically.
Verify it is present without printing the value:

```bash
[ -n "$GROQ_API_KEY" ] && echo "GROQ_API_KEY set" || echo "NOT SET"
```

## Quick Start

```python
from groq import Groq

client = Groq()  # reads GROQ_API_KEY
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in one paragraph."},
    ],
    temperature=0.7,
    max_completion_tokens=512,   # NOTE: Groq uses max_completion_tokens, not max_tokens
)
print(response.choices[0].message.content)
```

## Capabilities at a Glance

Groq's chat endpoint supports **streaming**, **JSON mode**
(`response_format={"type": "json_object"}`), and **tool/function calling** with
the same request shape as OpenAI. Multimodal and audio ride separate model ids
and endpoints. For the full, copy-pasteable code for each, see
`references/api-cookbook.md`.

| Capability | Endpoint / knob | Notes |
|------------|-----------------|-------|
| Chat + streaming | `chat.completions.create(..., stream=True)` | Guard `delta.content` for `None`. |
| JSON mode | `response_format={"type": "json_object"}` | Pair with `temperature=0`; instruct "JSON only" in the system prompt. |
| Tool calling | `tools=[...]`, `tool_choice="auto"` | Not every model supports tools — prefer Llama 3.3 70B or GPT-OSS. |
| Vision | Llama-4 models, `image_url` content part | Image ≤ 20 MB; URL or base64. |
| Speech-to-text | `audio.transcriptions.create(...)` | Whisper on LPU; ≤ 25 MB free / 100 MB dev. |
| Translation → EN | `audio.translations.create(...)` | Any language to English. |
| Text-to-speech | `audio.speech.create(...)` | PlayAI / Orpheus voices; returns bytes. |

## Model Selection (short form)

Pick the smallest model that clears your quality bar — it is the largest cost
and latency lever you have.

- **Fastest + cheapest**: `llama-3.1-8b-instant` — classification, extraction,
  routing, simple chat.
- **Best all-round quality**: `llama-3.3-70b-versatile` — reasoning, coding,
  general chat.
- **Best value**: `openai/gpt-oss-120b` — strong quality at ~500 t/s and low
  input price; `openai/gpt-oss-20b` for max speed (~1000 t/s).
- **Vision**: `meta-llama/llama-4-scout-17b-16e-instruct`.
- **Long context**: `moonshotai/kimi-k2-instruct-0905` (~262K window).
- **Transcription**: `whisper-large-v3-turbo` (cheaper/faster) or
  `whisper-large-v3` (max accuracy).

Model ids, pricing, context windows, and speeds drift — treat
`references/models-and-limits.md` and
`https://console.groq.com/docs/models` as the source of truth before hardcoding
a model or a price.

## OpenAI Compatibility

Any OpenAI SDK works unchanged — override `base_url` and `api_key`:

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)
```

Chat, audio (transcription/translation/speech), and `GET /models` are supported;
`embeddings` and `images/generations` are not. Several OpenAI request fields are
rejected with `400` (`logprobs`, `logit_bias`, `top_logprobs`, per-message
`name`, and `n` > 1). Full endpoint matrix and field list:
`references/troubleshooting.md`.

## Failure Modes

Common errors and fixes (auth, `400` unsupported fields, `429` rate limits,
empty stream chunks, oversized audio/images, tool-calling gaps, and the
`max_tokens` → `max_completion_tokens` migration) plus a ready retry-with-backoff
helper are in `references/troubleshooting.md`.

## Resources

- API overview: https://console.groq.com/docs/overview
- Models: https://console.groq.com/docs/models
- Rate limits: https://console.groq.com/docs/rate-limits
- OpenAI compat: https://console.groq.com/docs/openai
- Python SDK: https://github.com/groq/groq-python
- Status: https://status.groq.com
