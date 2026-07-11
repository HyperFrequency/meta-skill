# Fireworks AI — Models & Pricing

Model IDs, availability, and prices change frequently. Treat everything here as
a starting point and verify against the live catalog
(https://fireworks.ai/models) and pricing page (https://fireworks.ai/pricing).

## Popular serverless models

| Model | Model ID | Params | Context |
|-------|----------|--------|---------|
| Llama 3.3 70B Instruct | `accounts/fireworks/models/llama-v3p3-70b-instruct` | 70B | 131K |
| Llama 3.2 11B Vision | `accounts/fireworks/models/llama-v3p2-11b-vision-instruct` | 11B | 128K |
| Llama 3.2 3B Instruct | `accounts/fireworks/models/llama-v3p2-3b-instruct` | 3B | 128K |
| Qwen 2.5 72B Instruct | `accounts/fireworks/models/qwen2p5-72b-instruct` | 72B | 32K |
| Qwen3 Coder 480B A35B | `accounts/fireworks/models/qwen3-coder-480b-a35b-instruct` | 480B (35B active) | 262K |
| DeepSeek V3 | `accounts/fireworks/models/deepseek-v3-0324` | 671B (37B active) | 164K |
| Mixtral 8x7B Instruct | `accounts/fireworks/models/mixtral-8x7b-instruct` | 46B (12B active) | 32K |
| Mixtral 8x22B Instruct | `accounts/fireworks/models/mixtral-8x22b-instruct` | 141B (39B active) | 65K |

Always pass the full account-scoped ID (`accounts/fireworks/models/...`); a bare
model name returns "model not found".

## Serverless pricing tiers (approximate)

Per 1M tokens, blended input+output.

| Tier | $/1M tokens |
|------|-------------|
| < 4B params | 0.10 |
| 4B – 16B params | 0.20 |
| > 16B params | 0.90 |
| MoE 0 – 56B params | 0.50 |
| MoE 56B – 176B params | 1.20 |

MoE models bill by their parameter tier while activating only a fraction of
weights per token — often the best quality-per-dollar for high volume.

## Model selection guide

| Use case | Recommended model |
|----------|-------------------|
| General chat / instruction following | `llama-v3p3-70b-instruct` |
| Code generation | `qwen3-coder-480b-a35b-instruct` |
| Vision / multimodal | `llama-v3p2-11b-vision-instruct` |
| Cost-sensitive workloads | `llama-v3p2-3b-instruct` |
| Reasoning / complex tasks | `deepseek-v3-0324` |
| Fast MoE inference | `mixtral-8x7b-instruct` |

## Embedding models

| Model ID | Dimensions |
|----------|------------|
| `nomic-ai/nomic-embed-text-v1.5` | 768 |
| `nomic-ai/nomic-embed-text-v1` | 768 |
| `thenlper/gte-large` | 1024 |
| `WhereIsAI/UAE-Large-V1` | 1024 |

Call these through `client.embeddings.create(...)` — see
[inference.md](inference.md).

## Cost checklist

| Lever | Rough savings | How |
|-------|---------------|-----|
| Smaller model | 50–90% | 3B at ~0.10/M vs 70B at ~0.90/M |
| Batch API | ~50% | Async processing for non-real-time work |
| Prompt caching | 20–40% | Consistent static system prompts / prefixes |
| MoE models | 30–50% | Large capacity, few active params per token |
| On-demand deployments | Variable | Predictable pricing at scale, no per-token markup |
| Lower `max_tokens` | 10–30% | Cap output to realistic lengths |

Batch inference and prompt caching are covered in
[integration-and-troubleshooting.md](integration-and-troubleshooting.md);
deployments in [deployments.md](deployments.md).
