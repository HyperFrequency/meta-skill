---
name: guidance
description: Constrain LLM output at the token level with regex, CFG grammars, and select() choices to guarantee valid JSON/XML/code/dates/IDs, plus build multi-step agents with Pythonic control flow, using the guidance-ai framework (originally Microsoft Research). Use WHEN you need hard format guarantees during generation, token healing, grammar/regex constraints, or stateful generation loops over local (Transformers, llama.cpp) or API (Anthropic, OpenAI) models. Use the `instructor` skill instead when you want Pydantic-model extraction with automatic retries over API models; use `outlines` for JSON-schema / vLLM-first structured generation; use `dspy` when you want to optimize prompts/programs rather than constrain syntax. NOT for unconstrained free-text generation, prompt optimization, or providers without a guidance backend.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Prompt Engineering, Guidance, Constrained Generation, Structured Output, JSON Validation, Grammar, Microsoft Research, Format Enforcement, Multi-Step Workflows]
dependencies: []
---

# Guidance: Constrained LLM Generation

Token-level constrained generation from the guidance-ai project (18k+ GitHub stars, originally Microsoft Research). Outputs are forced to match a regex, CFG grammar, or fixed choice set *during* decoding — invalid tokens are filtered before they are sampled, so no retry loop is needed. Pythonic control flow (`@guidance` functions, loops, `select`) makes it suited to multi-step agents and workflows.

## When to Use This Skill

- You need a **hard guarantee** that output is valid JSON/XML/code or matches a format (date, email, ID, phone).
- You want **regex or context-free grammar** constraints applied at the token level.
- You want **token healing** to avoid tokenizer boundary artifacts (e.g. double spaces).
- You are building **multi-step / agentic loops** (ReAct, chain-of-thought) with Python control flow.
- You target **local models** (Transformers, llama.cpp) as well as API models (Anthropic, OpenAI).

## When NOT to Use

- **Unconstrained free-text** generation — plain prompting is simpler.
- **Pydantic extraction with auto-retry over API models** → use the `instructor` skill.
- **JSON-schema-first or vLLM-centric** structured generation → use the `outlines` skill.
- **Optimizing prompts/programs** rather than constraining syntax → use the `dspy` skill.
- A provider with **no guidance backend** (constraints need logit access or supported APIs).

## Installation

```bash
pip install guidance              # base
pip install guidance[transformers]  # Hugging Face local models
pip install guidance[llama_cpp]     # llama.cpp local models
```

## Quick Start

```python
from guidance import models, gen, select

lm = models.Anthropic("claude-sonnet-4-5-20250929")  # or models.OpenAI / Transformers / LlamaCpp

# Regex constraint — output is guaranteed to match
lm += "Date: " + gen("date", regex=r"\d{4}-\d{2}-\d{2}")

# Fixed-choice constraint
lm += "\nSentiment: " + select(["positive", "negative", "neutral"], name="sentiment")

print(lm["date"], lm["sentiment"])
```

Chat roles use context managers (`with system(): / with user(): / with assistant():`) — see `references/backends.md`.

## Core Concepts (pointers)

| Concept | What it does | Reference |
|---------|--------------|-----------|
| Regex / grammar constraints | Force output to match a pattern or CFG at token level | `references/constraints.md` |
| `select()` | Restrict output to a fixed set of choices | `references/constraints.md` |
| Token healing | Re-aligns prompt/generation token boundaries (on by default) | `references/constraints.md` |
| `@guidance` functions | Reusable, optionally stateful generation patterns; loops & control flow | `references/examples.md` |
| Backend setup | Anthropic, OpenAI, Transformers, llama.cpp config & tuning | `references/backends.md` |
| Production patterns | JSON gen, extraction, classification, ReAct agents, code gen | `references/examples.md` |

## Choosing Among Constrained-Generation Skills

| Feature | Guidance | `instructor` | `outlines` | LMQL |
|---------|----------|--------------|------------|------|
| Regex constraints | ✅ | ❌ | ✅ | ✅ |
| CFG grammar | ✅ | ❌ | ✅ | ✅ |
| Pydantic validation | ❌ | ✅ | ✅ | ❌ |
| Token healing | ✅ | ❌ | ✅ | ❌ |
| Local models | ✅ | ⚠️ | ✅ | ✅ |
| API models | ✅ | ✅ | ⚠️ | ✅ |
| Pythonic control flow | ✅ | ✅ | ✅ | ❌ (SQL-like) |

Pick **Guidance** for regex/grammar + token healing + control-flow-heavy workflows on local or API models.

## References

- `references/constraints.md` — regex & grammar patterns, `select()`, token healing, performance tuning, best practices.
- `references/backends.md` — Anthropic / OpenAI / Transformers / llama.cpp setup, chat roles, backend comparison.
- `references/examples.md` — production-ready JSON, extraction, classification, agent, and code-generation examples + production tips.

## Resources

- Documentation: https://guidance.readthedocs.io
- GitHub: https://github.com/guidance-ai/guidance
- Notebooks: https://github.com/guidance-ai/guidance/tree/main/notebooks
- Token healing paper: https://arxiv.org/abs/2306.17648
