---
name: together-ai
version: 0.1.0
description: >-
  Serverless inference, managed fine-tuning, embeddings, image generation, and
  batch processing across 200+ open-weight models (Llama, DeepSeek, Qwen,
  Mistral, FLUX) through Together AI's OpenAI-compatible API at
  https://api.together.xyz/v1. Use when you need fast pay-per-token access to
  open-source LLMs without provisioning GPUs, want a drop-in OpenAI SDK swap
  (change base_url + key), need LoRA or full fine-tuning as a hosted service, or
  want asynchronous batch inference at roughly half price. Do NOT use for
  proprietary models like GPT-4o or Claude (call those providers directly), for
  self-hosted inference you fully control (use `vllm`, `tensorrt-llm`,
  `sglang`), for dedicated GPU boxes or custom containers (use `lambda-labs`,
  `modal`, `skypilot`), or for local fine-tuning frameworks (use `unsloth`,
  `peft`, `axolotl`, `llama-factory`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (togethercomputer/together-python SDK)"
---

# Together AI — Serverless Inference & Fine-Tuning

## Overview

Together AI is a hosted inference cloud that serves 200+ open-weight models
behind an OpenAI-compatible REST API (`https://api.together.xyz/v1`). You call
it with either the first-party `together` Python SDK or the stock `openai` SDK
pointed at Together's base URL. One account gives you chat/instruct models,
reasoning and code models, embeddings, FLUX image generation, LoRA/full
fine-tuning, and an asynchronous batch endpoint — all pay-per-token, no GPU
provisioning.

This file is a **router**. Each capability below links to a focused reference
with runnable code, parameter tables, and gotchas. Read the reference for the
task at hand rather than loading everything.

## When to Use This Skill

- You need fast serverless inference on open models (Llama, DeepSeek, Qwen,
  Mistral, gpt-oss) with per-token billing and no infrastructure.
- You want an OpenAI-compatible surface so switching a provider is a two-line
  change (`api_key` + `base_url`) — including for LangChain, LlamaIndex, etc.
- You need function calling, JSON/structured outputs, or vision from open
  models.
- You want LoRA or full fine-tuning run as a managed job, then served serverless
  or downloaded.
- You have a large, non-urgent workload (evals, dataset generation, bulk
  classification) that can run through the batch API at ~50% cost.
- You need embeddings or FLUX image generation alongside chat in one provider.

## When NOT to Use This Skill

- **Proprietary models** (GPT-4o, Claude, Gemini): call those vendors' APIs
  directly — they are not hosted on Together.
- **Full control over the serving stack** (custom kernels, quantization,
  speculative decoding, on-prem): self-host with `vllm`, `tensorrt-llm`, or
  `sglang`.
- **Raw GPUs or custom containers**: rent dedicated instances with
  `lambda-labs`, or run serverless containers with `modal`; use `skypilot` for
  multi-cloud placement.
- **Local/offline fine-tuning** where you own the training loop: use `unsloth`,
  `peft`, `axolotl`, or `llama-factory`.
- **A single generate/classify call** where you already have a model SDK wired
  up: just call it; adding Together buys nothing.

## Setup

Install either SDK (they interoperate):

```bash
pip install together      # first-party SDK + CLI
pip install openai        # optional: OpenAI-compatible path
```

Authenticate with an API key from https://api.together.xyz/settings/api-keys.
The `together` SDK and CLI read `TOGETHER_API_KEY` from the environment:

```bash
export TOGETHER_API_KEY="your-api-key"
```

```bash
# Verify it is set (does not print the value)
[ -n "$TOGETHER_API_KEY" ] && echo "TOGETHER_API_KEY set" || echo "NOT SET"
```

## Quick Start

```python
from together import Together

client = Together()  # reads TOGETHER_API_KEY from the environment

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain gradient descent in one paragraph."},
    ],
    max_tokens=256,
    temperature=0.7,
)

print(response.choices[0].message.content)
print(f"Tokens used: {response.usage.total_tokens}")
```

Model IDs are the full Hugging Face-style paths (e.g.
`meta-llama/Llama-3.3-70B-Instruct-Reference`). Confirm exact IDs and
availability in the live catalog: https://docs.together.ai/docs/serverless-models

## Capability Map

| Capability | What you get | Reference |
|------------|--------------|-----------|
| **Inference** | Chat completions, streaming, function calling, JSON/structured outputs, vision | [references/inference.md](references/inference.md) |
| **Fine-tuning** | JSONL data format, upload, LoRA/full jobs, monitoring, CLI, supported-model matrix | [references/fine-tuning.md](references/fine-tuning.md) |
| **Embeddings & images** | `bge`/`m2-bert` embeddings and FLUX image generation | [references/embeddings-and-images.md](references/embeddings-and-images.md) |
| **Batch inference** | Async JSONL jobs at ~50% cost, ~24h window | [references/batch-inference.md](references/batch-inference.md) |
| **Models & pricing** | Chat/reasoning/code model tables, MoE cost levers, right-sizing | [references/models-and-pricing.md](references/models-and-pricing.md) |
| **Integration & troubleshooting** | OpenAI SDK swap, LangChain, CLI reference, common errors | [references/integration-and-troubleshooting.md](references/integration-and-troubleshooting.md) |

## Choosing a model quickly

- **Cheap/fast general tasks** → an 8B instruct model.
- **High-quality general purpose** → a 70B instruct model.
- **Complex reasoning / code** → DeepSeek-V3, DeepSeek-R1, or a large Qwen3
  Coder MoE.
- **Cost-sensitive high volume** → a mixture-of-experts model (few active
  params per token) plus the batch API.

See [references/models-and-pricing.md](references/models-and-pricing.md) for the
tables and the cost-optimization checklist. All pricing there is approximate —
verify against https://www.together.ai/pricing.

## Notes on API stability

The OpenAI-compatible surface (`chat.completions`, `embeddings`,
`images.generate`) is stable across SDK versions. The first-party `fine_tuning`
and `batches` method names have shifted between `together` releases — the
references show the current shape but tell you to confirm signatures against
your installed version (`pip show together`) and the live API reference
(https://docs.together.ai/reference). Do not assume an exact method name for
fine-tuning or batch calls without checking.
