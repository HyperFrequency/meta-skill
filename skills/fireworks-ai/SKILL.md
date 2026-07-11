---
name: fireworks-ai
version: 0.1.0
description: >-
  Fast serverless and dedicated-GPU inference plus managed fine-tuning for
  open-weight models (Llama, Qwen, DeepSeek, Mixtral) through Fireworks AI's
  OpenAI-compatible API at https://api.fireworks.ai/inference/v1. Use when you
  need low-latency pay-per-token inference on open models, a drop-in OpenAI SDK
  swap (change base_url + key), function calling / JSON-schema outputs / vision
  from open models, managed SFT/DPO/RL fine-tuning without owning a training
  loop, or dedicated on-demand GPU deployments with no rate limits (SOC2/HIPAA).
  Do NOT use for proprietary models like GPT-4o or Claude (call those vendors
  directly), for self-hosted serving you fully control (use `vllm`,
  `tensorrt-llm`, `sglang`), for raw GPU boxes or custom containers (use
  `lambda-labs`, `modal`, `skypilot`), or for local fine-tuning where you own
  the training loop (use `unsloth`, `peft`, `axolotl`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (openai Python SDK; Fireworks AI itself is a proprietary hosted service)"
---

# Fireworks AI — Fast Inference & Fine-Tuning

## Overview

Fireworks AI is a hosted inference cloud tuned for low-latency serving of
open-weight models. You reach it through an OpenAI-compatible REST surface at
`https://api.fireworks.ai/inference/v1`, so the stock `openai` SDK works after a
two-line change (`base_url` + `api_key`). One account covers serverless
pay-per-token inference, dedicated on-demand GPU deployments, managed
fine-tuning (SFT, DPO, RL), embeddings, and batch inference — with SOC2 and
HIPAA compliance.

This file is a **router**. Each capability below links to a focused reference
with runnable code, parameter tables, and gotchas. Read the reference for the
task at hand rather than loading everything.

## When to Use This Skill

- You need fast serverless inference on open models (Llama, Qwen, DeepSeek,
  Mixtral) with per-token billing and no infrastructure to run.
- You want an OpenAI-compatible surface so switching a provider is a two-line
  change — including for LangChain, LlamaIndex, and other OpenAI-SDK consumers.
- You need function calling, JSON/schema-constrained outputs, or vision from
  open models.
- You want SFT, DPO, or RL fine-tuning run as a managed job (LoRA by default),
  then served serverless or on a dedicated deployment.
- You need dedicated GPU deployments with predictable latency and no rate
  limits, or want to serve a custom / fine-tuned model.
- You must meet SOC2 or HIPAA requirements, or want prompt caching and batch
  inference for cost savings.

## When NOT to Use This Skill

- **Proprietary models** (GPT-4o, Claude, Gemini): call those vendors' APIs
  directly — they are not hosted on Fireworks.
- **Full control over the serving stack** (custom kernels, quantization,
  speculative decoding, on-prem): self-host with `vllm`, `tensorrt-llm`, or
  `sglang`.
- **Raw GPUs or custom containers**: rent dedicated instances with
  `lambda-labs`, run serverless containers with `modal`, or place jobs
  multi-cloud with `skypilot`.
- **Local/offline fine-tuning** where you own the training loop: use `unsloth`,
  `peft`, `axolotl`, or `llama-factory`.
- **Cheapest possible serverless**: compare against `together-ai` and other
  providers; Fireworks optimizes for latency, not always lowest price.
- **A single generate/classify call** where you already have a model SDK wired
  up: just call it; adding Fireworks buys nothing.

## Setup

Install a client. The OpenAI-compatible path needs only `openai`; the
first-party `fireworks-ai` SDK is optional:

```bash
pip install openai          # OpenAI-compatible path (recommended)
pip install fireworks-ai    # optional: first-party SDK
```

Get an API key from https://fireworks.ai/api-keys and export it. The examples
read it from the environment rather than hard-coding it:

```bash
export FIREWORKS_API_KEY="fw_..."
```

```bash
# Verify it is set (does not print the value)
[ -n "$FIREWORKS_API_KEY" ] && echo "FIREWORKS_API_KEY set" || echo "NOT SET"
```

## Quick Start

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.fireworks.ai/inference/v1",
    api_key=os.environ["FIREWORKS_API_KEY"],
)

response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain gradient descent in two sentences."},
    ],
    max_tokens=256,
    temperature=0.7,
)
print(response.choices[0].message.content)
```

Model IDs are the full account-scoped paths (e.g.
`accounts/fireworks/models/llama-v3p3-70b-instruct`). Confirm exact IDs and
availability in the live catalog at https://fireworks.ai/models.

## Capability Map

| Capability | What you get | Reference |
|------------|--------------|-----------|
| **Inference** | Chat completions, streaming, function calling, JSON/schema outputs, vision, embeddings, Fireworks-specific params | [references/inference.md](references/inference.md) |
| **Fine-tuning** | SFT / DPO / RL jobs, JSONL data formats, monitoring, pricing | [references/fine-tuning.md](references/fine-tuning.md) |
| **On-demand deployments** | Dedicated GPU deployments, shapes, GPU pricing, scaling, querying | [references/deployments.md](references/deployments.md) |
| **Models & pricing** | Serverless model table, tier pricing, selection guide, embedding models | [references/models-and-pricing.md](references/models-and-pricing.md) |
| **Integration & troubleshooting** | OpenAI SDK swap, native SDK, `firectl` CLI, prompt caching, batch inference, common errors | [references/integration-and-troubleshooting.md](references/integration-and-troubleshooting.md) |

## Choosing a model quickly

- **General chat / instruction following** → a 70B instruct model (Llama 3.3
  70B).
- **Code generation** → a large Qwen3 Coder MoE.
- **Reasoning / complex tasks** → DeepSeek-V3.
- **Vision / multimodal** → a Llama Vision model.
- **Cost-sensitive high volume** → a small dense model or an MoE (few active
  params per token), plus the batch API.

See [references/models-and-pricing.md](references/models-and-pricing.md) for the
tables and the cost checklist.

## Notes on API stability

The OpenAI-compatible surface (`chat.completions`, `embeddings`, `batches`) is
stable across SDK versions. The fine-tuning and deployment **control-plane**
REST paths (e.g. `supervisedFineTuningJobs`, `deployments`) and their field
names live under `https://api.fireworks.ai/v1/accounts/{account_id}/...` and
have shifted over time. The references show the current shape and prefer the
`firectl` CLI for control-plane work; confirm exact endpoints and field names
against https://docs.fireworks.ai/api-reference before scripting them. All
prices in the references are approximate — verify at
https://fireworks.ai/pricing.
