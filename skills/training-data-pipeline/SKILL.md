---
name: training-data-pipeline
version: 0.1.0
description: >-
  Build SFT / instruction-tuning datasets for LLM specialization and turn them into clean,
  train-ready chat JSONL. Covers three sourcing paths — formatting production data (API logs,
  user corrections, accept/reject signals), distilling labels from frontier batch APIs
  (OpenAI/Anthropic, ~50% off), and synthetic bootstrapping when you have < ~1000 real
  examples — plus the quality gates every dataset needs: schema validation, MinHash
  deduplication, distinct-n diversity, PII redaction, token-length analysis, and a leak-free
  train/eval split. Use WHEN preparing data for fine-tuning: converting logs to messages-array
  JSONL, batch-labeling unlabeled inputs, or validating a corpus before training. Do NOT use
  for the trainer itself (see `fine-tuning`, `post-training`, `tinker`, `colab-finetuning`),
  DPO/reward-model preference loops, general tabular/ETL cleaning (`data-processing`), or eval
  harness design (`evaluation`, `llm-as-judge-evaluation`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Training Data Pipeline

## Overview

A fine-tune is only as good as the JSONL you feed it. This skill takes you from raw
signal to a validated, split, train-ready dataset in the standard chat format that every
major trainer (`tinker`, Unsloth, TRL, Axolotl) accepts. It covers the three ways to source
that data, then the quality gates that separate a dataset that teaches from one that just
memorizes noise.

The pipeline is always the same four stages: **source → format → validate → split**. This
router covers the format contract and the decision logic; the deep code for each stage lives
in `references/`.

## When to Use This Skill

Use this skill when you need to:

- **Format production data** — turn API request/response logs, user edits/corrections, or
  accept/reject signals into `messages`-array JSONL.
- **Distill from frontier models** — label unlabeled production inputs with a teacher model
  (GPT / Claude / Gemini) via batch APIs when you have real inputs but no gold outputs.
- **Bootstrap synthetically** — generate seed examples when you have fewer than ~1000 real
  ones, as a stopgap until production data accumulates.
- **Validate before training** — run schema checks, MinHash dedup, diversity metrics, PII
  redaction, and token-length analysis so training loss actually moves.
- **Split without leakage** — carve a train/eval split that reserves real production data for
  eval as ground truth.

## When NOT to Use This Skill

- **Running the training loop itself** — model loading, LoRA/QLoRA, SFTTrainer, GRPO. Use
  `fine-tuning`, `post-training`, `tinker`, or `colab-finetuning`.
- **Preference / reward-model data (DPO/RLHF)** — this skill produces SFT targets, not
  chosen/rejected pairs. (Accept/reject signals here become *positive* SFT examples; capturing
  the rejected side for DPO is out of scope.)
- **General tabular ETL / dataframe cleaning** — use `data-processing`.
- **Designing the eval harness or judges** — use `evaluation` or `llm-as-judge-evaluation`.
  This skill only carves the eval *split*; it does not score models.
- **The build-vs-buy / distillation cost decision at portfolio level** — use `model-economics`.

## The Three Data Paths

Pick a path by what you already have. You can and often should combine them.

| Path | Use when | Source | Cost | Reference |
|------|----------|--------|------|-----------|
| **A — Production** | You have logs or user feedback | Your own systems | Free (already collected) | [production-data.md](references/production-data.md) |
| **B — Distillation** | You have inputs but no labels | Frontier batch APIs | ~50% of real-time API price | [frontier-distillation.md](references/frontier-distillation.md) |
| **C — Synthetic** | You have < ~1000 real examples | Frontier generation | Varies by volume | [synthetic-bootstrap.md](references/synthetic-bootstrap.md) |

**Prefer Path A.** Production data — especially user corrections — is the signal competitors
cannot replicate. Use B to fill label gaps and C only to cold-start, replacing synthetic
examples with real ones as they arrive.

## JSONL Chat Format (the contract)

Every path produces the same output: one JSON object per line, each a `messages` array.

```jsonl
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "What is 2+2?"}, {"role": "assistant", "content": "4"}]}
{"messages": [{"role": "user", "content": "Translate to French: Hello"}, {"role": "assistant", "content": "Bonjour"}]}
```

Rules that trip people up:

- One JSON object per line, **no trailing commas**, UTF-8, no BOM.
- Roles: optional `system` (first only), then alternating `user` / `assistant`. Need at least
  one `user` and one `assistant`.
- **The `assistant` message is the training target.** Everything else is context the loss is
  not (usually) computed on. Put your best output there — for corrections, the *corrected*
  text, not the original.
- Multi-turn: keep the whole conversation in one `messages` array. To train on every assistant
  turn, emit one example per turn with the full prior history (see
  [production-data.md](references/production-data.md)).
- Some trainers also accept `{"prompt": "...", "completion": "..."}` pairs, but chat format is
  the safe default and the only one that handles multi-turn cleanly.

Always tokenize with the **target model's** tokenizer for length checks — a length that fits
one model's context can overflow another's.

## Pipeline Stages

1. **Source** — choose Path A/B/C above and read that reference.
2. **Format** — emit `messages` JSONL. Normalize whitespace, drop empties, redact PII while
   you have the raw text (see [production-data.md](references/production-data.md) and the PII
   patterns in [data-quality.md](references/data-quality.md)).
3. **Validate** — schema-check every line, MinHash-dedup on the assistant target
   (0.8 threshold), check `distinct-2 > 0.5`, and analyze token-length percentiles to set
   `max_seq_length`. All in [data-quality.md](references/data-quality.md).
4. **Split** — 90/10 train/eval, and route **all real production examples into eval** as
   ground truth so you measure against reality, not synthetic echoes. Split code is in
   [data-quality.md](references/data-quality.md).

## Quick-Start Checklist

1. Identify the source: production (A), distillation (B), or synthetic (C).
2. Format to `messages` JSONL — best output in the `assistant` slot.
3. Validate the file (schema + role checks); fix every flagged line before proceeding.
4. Deduplicate (MinHash LSH, threshold 0.8) on the assistant target.
5. Diversity report — aim `distinct-2 > 0.5`; if low, add variety (Path C diversity levers).
6. Token-length pass with the target tokenizer; confirm p99 fits the context window.
7. Split 90/10, production data pinned to eval.
8. Hand the JSONL to the trainer skill (`fine-tuning`, `tinker`, `post-training`,
   `colab-finetuning`).

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `JSONDecodeError` on load | Trailing commas / malformed line | Run the validator, fix flagged lines |
| Training loss won't drop | Noisy or contradictory data | Filter low-quality examples, dedup harder |
| Model parrots the training set | Overfitting a tiny corpus | More diverse examples, fewer epochs |
| Eval scores implausibly high | Leakage — eval seen in train | Split with production pinned to eval; dedup across the split |
| Examples silently truncated | Wrong tokenizer for length check | Use the **target** model's tokenizer |
| Odd characters / `UnicodeDecodeError` | Non-UTF-8 input | `text.encode('utf-8', errors='replace').decode('utf-8')` |
| Distilled data full of refusals | Teacher declined the prompt | Filter refusal phrases (see distillation reference) |

## References

- [production-data.md](references/production-data.md) — Path A: log/DB/feedback extraction,
  cleaning pipeline, multi-turn expansion, volume guidelines.
- [frontier-distillation.md](references/frontier-distillation.md) — Path B: OpenAI/Anthropic
  batch APIs, distillation prompt design, quality filtering, cost estimation, multi-teacher.
- [synthetic-bootstrap.md](references/synthetic-bootstrap.md) — Path C: seed-prompt strategy,
  diversity levers, when synthetic hurts.
- [data-quality.md](references/data-quality.md) — schema validation, MinHash dedup,
  distinct-n, token-length analysis, PII redaction, LLM-judge scoring, health report, and the
  leak-free train/eval split.
