# Groq Models, Rate Limits & Cost

Model ids, speeds, context windows, and prices drift as Groq rotates its
catalog. Treat this file as a snapshot and confirm against
`https://console.groq.com/docs/models` and `https://groq.com/pricing` before
hardcoding a model id or a price into production.

Speeds below are approximate steady-state output throughput (tokens/sec) and
vary with load, prompt length, and sampling settings.

## Production models

| Model | Model id | Speed | Context | Max output | Input $/1M | Output $/1M |
|-------|----------|-------|---------|------------|------------|-------------|
| Llama 3.1 8B | `llama-3.1-8b-instant` | ~560 t/s | 131,072 | 131,072 | $0.05 | $0.08 |
| Llama 3.3 70B | `llama-3.3-70b-versatile` | ~280 t/s | 131,072 | 32,768 | $0.59 | $0.79 |
| GPT-OSS 120B | `openai/gpt-oss-120b` | ~500 t/s | 131,072 | 65,536 | $0.15 | $0.60 |
| GPT-OSS 20B | `openai/gpt-oss-20b` | ~1000 t/s | 131,072 | 65,536 | $0.075 | $0.30 |
| Whisper V3 | `whisper-large-v3` | — | — | — | $0.111/hr audio | — |
| Whisper V3 Turbo | `whisper-large-v3-turbo` | — | — | — | $0.04/hr audio | — |

## Preview models

Preview ids can change or be retired with little notice — do not pin a
production system to them.

| Model | Model id | Speed | Context | Input $/1M | Output $/1M |
|-------|----------|-------|---------|------------|-------------|
| Llama 4 Scout | `meta-llama/llama-4-scout-17b-16e-instruct` | ~750 t/s | 131,072 | $0.11 | $0.34 |
| Llama 4 Maverick | `meta-llama/llama-4-maverick-17b-128e-instruct` | ~600 t/s | 131,072 | $0.20 | $0.60 |
| Qwen3 32B | `qwen/qwen3-32b` | ~400 t/s | 131,072 | $0.29 | $0.59 |
| Kimi K2 | `moonshotai/kimi-k2-instruct-0905` | ~200 t/s | 262,144 | $1.00 | $3.00 |
| Safeguard GPT-OSS 20B | `openai/gpt-oss-safeguard-20b` | ~1000 t/s | 131,072 | $0.075 | $0.30 |
| Llama Guard 4 12B | `meta-llama/llama-guard-4-12b` | — | 131,072 | $0.20 | $0.20 |

## Agentic systems & TTS

| Name | Model id | Notes |
|------|----------|-------|
| Compound | `groq/compound` | Agentic system with built-in web search + code execution. |
| Compound Mini | `groq/compound-mini` | Lighter/cheaper agentic variant. |
| PlayAI TTS | `playai-tts` | Text-to-speech, ~$22 / 1M chars. |
| Orpheus English | `canopylabs/orpheus-v1-english` | Text-to-speech, ~$22 / 1M chars. |

## Selection guide

Pick the smallest model that clears your quality bar — model choice is the
largest cost and latency lever.

- **Fastest + cheapest**: `llama-3.1-8b-instant` — classification, extraction,
  routing, guardrails, simple chat.
- **Best all-round quality**: `llama-3.3-70b-versatile` — complex reasoning,
  coding, agent planning, general chat.
- **Best value**: `openai/gpt-oss-120b` — strong quality at ~500 t/s and low
  input price. Drop to `openai/gpt-oss-20b` when raw speed matters most.
- **Vision**: `meta-llama/llama-4-scout-17b-16e-instruct` (cheapest multimodal)
  or `meta-llama/llama-4-maverick-17b-128e-instruct` for higher quality.
- **Long context**: `moonshotai/kimi-k2-instruct-0905` (~262K window).
- **Transcription**: `whisper-large-v3-turbo` (cheaper/faster) or
  `whisper-large-v3` (max accuracy).
- **Safety / moderation**: `meta-llama/llama-guard-4-12b` or
  `openai/gpt-oss-safeguard-20b`.

## Rate limits

| Tier | Price | Requests/min | Tokens/min | Tokens/day |
|------|-------|--------------|------------|------------|
| Free | $0 | 30 | 6,000 | 500,000 |
| Developer | Pay-per-token | up to 1,000 | up to 300,000 | Unlimited |

Limits are per-model and change over time; the numbers above are the documented
defaults. Every response carries rate-limit headers so you can pace clients
without guessing:

- `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`
- `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`
- `retry-after` (seconds) on a `429`

See `troubleshooting.md` for a retry-with-backoff helper.

## Cost optimization

1. **Right-size the model.** `llama-3.1-8b-instant` is ~10x cheaper than the 70B
   for classification/extraction — use the small model until quality forces you
   up.
2. **Cap output with `max_completion_tokens`.** Output tokens usually cost more
   than input; bounding them bounds both cost and tail latency.
3. **Try `openai/gpt-oss-20b`.** Strong price/performance at ~$0.075 input and
   ~1000 t/s for latency-sensitive work.
4. **Run deterministic prompts at `temperature=0`.** Identical prompts yield
   identical output, which makes an application-level response cache effective
   (Groq does not bill less for this by itself — the saving comes from your
   cache).
5. **Prefer Whisper Turbo.** `whisper-large-v3-turbo` is ~64% cheaper than v3
   with minimal accuracy loss for most transcription.
6. **Preprocess audio** to 16 kHz mono WAV to shrink uploads and stay under the
   size cap.

For per-token economics and cross-provider price comparison, see the sibling
`model-economics` skill; for alternative fast open-model hosts, see the
`together-ai` and `fireworks-ai` skills.
