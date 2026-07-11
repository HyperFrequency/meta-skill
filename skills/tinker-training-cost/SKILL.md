---
name: tinker-training-cost
version: 0.1.0
description: >-
  Estimate the dollar cost of fine-tuning a model on Thinking Machines' Tinker
  training API by tokenizing your JSONL dataset with the model's own Hugging Face
  tokenizer and applying Tinker's per-million-token training rate. Use when
  budgeting a Tinker LoRA fine-tune, counting tokens in chat / text / instruction
  datasets, comparing training price across Qwen, Llama, DeepSeek, GPT-OSS, or
  Kimi models, or deciding how many epochs a fixed budget buys. Do NOT use for
  inference or serving cost (prefill and sample rates differ from the train
  rate), for full-parameter fine-tuning or GPU-hour billed providers, or for
  exact invoice reconciliation — prices change and real token counts depend on
  the chat template and packing, so treat every figure as a pre-flight estimate
  to re-verify against the live pricing page.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (Hugging Face transformers)"
---

# Tinker Training Cost Estimator

## Overview

Tinker (Thinking Machines Lab) bills fine-tuning by tokens processed, at a
per-model rate quoted in USD per million tokens. This skill turns a training
dataset into a cost estimate in two steps: tokenize the data with the model's
**native** tokenizer, then apply the model's **train** rate over your epoch
count. It ships a runnable script plus reference tables for pricing and
tokenizer selection.

## When to Use This Skill

- Budgeting a Tinker LoRA fine-tune before you launch it.
- Counting tokens in a JSONL dataset (chat, plain-text, or instruction format).
- Comparing training price across candidate base models.
- Sizing dataset or epoch count to a fixed dollar budget.

## When NOT to Use This Skill

- **Inference / serving cost** — that uses the prefill + sample rates, not the
  train rate, and the arithmetic is different (input vs. output tokens). The
  rates live in `references/pricing.md`, but this skill computes training only.
- **GPU-hour or full-parameter fine-tuning providers** — the token-rate model
  does not apply.
- **Exact invoice reconciliation** — prices move and Tinker tokenizes with the
  chat template plus sequence packing, so an estimate and a bill will diverge.
- **Multimodal / image token accounting** — a text tokenizer does not count
  image patches (see Caveats).

## Cost model

```
training_cost_usd = dataset_tokens × epochs × train_rate_per_million / 1_000_000
```

- `dataset_tokens` — tokens in your dataset from the model's own tokenizer, not
  a generic one.
- `epochs` — passes over the dataset (default 3; set it to your run's value).
- `train_rate_per_million` — the model's **Train** rate from the pricing table.

Only the Train rate feeds training cost. The Prefill (input) and Sample (output)
rates are for inference and are listed for reference, not used here.

## Quick start

```bash
# List models with their train / prefill / sample rates
python scripts/estimate_tinker_cost.py --list-models

# Estimate for a JSONL dataset (defaults: model Qwen3-8B, 3 epochs)
python scripts/estimate_tinker_cost.py training_data.jsonl --model Qwen3-8B --epochs 3

# Machine-readable output
python scripts/estimate_tinker_cost.py training_data.jsonl --model Llama-3.1-70B --json
```

Requires `transformers>=4.40`. The script loads the correct tokenizer, counts
tokens (applying the chat template for chat rows when the tokenizer defines one),
and prints dataset tokens, training tokens, and estimated cost.

## Counting tokens correctly

Token counts are tokenizer-specific — the same text yields different counts under
different tokenizers, so always use the base model's own tokenizer:

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", trust_remote_code=True)
n = len(tok.encode("your training text"))
```

For chat data, tokenizing the raw concatenated `content` **under-counts**,
because it drops the role and special tokens the chat template inserts (and the
BOS/EOS Tinker will add). Prefer `tok.apply_chat_template(messages, tokenize=True)`
when the tokenizer ships a template. The full model-to-tokenizer mapping, plus
gated-model, vision, and proxy-tokenizer caveats, is in
`references/tokenizers.md`.

## Supported dataset formats

The script reads JSONL and extracts text per row:

- **Chat**: `{"messages": [{"role": "...", "content": "..."}]}` — uses the chat
  template when available, otherwise falls back to concatenating `content`.
- **Text**: `{"text": "..."}`
- **Instruction (Alpaca)**: `{"instruction": "...", "input": "...", "output": "..."}`

Rows that parse but match none of these contribute zero tokens; malformed JSON
lines are skipped and counted (reported on stderr).

## Pricing

The rates are a dated snapshot. The full per-family tables, the as-of date, and
the source URL are in `references/pricing.md`. **Prices change** — re-verify
against the live Tinker pricing page and update the `MODELS` table in the script
before you quote a number you will act on.

Quick anchors (Train rate, USD per million tokens): Qwen3-8B `$0.40` ·
Llama-3.1-70B `$3.16` · Qwen3-235B-Instruct `$2.04`. So 1M tokens × 3 epochs on
Qwen3-8B ≈ `$1.20`. More worked examples are in `references/pricing.md`.

## Caveats

- **LoRA, not full fine-tune** — Tinker trains LoRA adapters; the token rate
  covers that regime.
- **Snapshot pricing** — verify live before committing spend.
- **Chat template** — naive concatenation under-counts vs. what Tinker
  tokenizes; the script applies the template when the tokenizer defines one.
- **Vision (VL) models** — text tokenizers do not count image tokens, so
  estimates under-count multimodal data, and VL train rates are higher.
- **Proxy tokenizers** — a few entries (GPT-OSS, VL) map to a *compatible
  stand-in* tokenizer; those counts are approximate. See
  `references/tokenizers.md`.
- **Gated models** — Llama and some others require accepting a license and
  setting an HF token before the tokenizer will download.
- **trust_remote_code** — required for the Qwen and DeepSeek tokenizers.

## Related skills

- `transformers` — tokenizer loading, chat templates, and the wider Hugging Face
  stack this skill builds on.
