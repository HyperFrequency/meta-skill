---
name: dspy
description: Program language models declaratively with DSPy (Stanford NLP) instead of hand-writing prompts. Use when building multi-stage LM systems (RAG, agents, classifiers, pipelines), when you want prompts/few-shot examples optimized automatically from data via teleprompters (BootstrapFewShot, MIPRO, COPRO, and GEPA reflective prompt evolution), or when you need portable, type-safe Signatures that work across LMs. Covers modules (Predict, ChainOfThought, ReAct, ProgramOfThought), optimizers, metrics, evaluation, and the modern dspy.LM provider setup. Do NOT use for one-off manual prompts, simple single-call chatbots, or when you have no eval data/metric to optimize against (use plain SDK calls or the claude-api skill instead); for prebuilt integration chains prefer LangChain; for cross-framework strategy porting see strategy-translator; to run GEPA on raw prompt components OUTSIDE a DSPy program (non-Python evals, ProcessAdapter over an eval binary) use the gepa-evolve skill instead.
version: 1.2.0
author: Orchestra Research
license: MIT
tags: [Prompt Engineering, DSPy, Declarative Programming, RAG, Agents, Prompt Optimization, LM Programming, Stanford NLP, Automatic Optimization, Modular AI, GEPA, Reflective Prompt Evolution]
dependencies: [dspy, openai, anthropic]
---

# DSPy: Declarative Language Model Programming

DSPy (Stanford NLP) replaces brittle hand-written prompt strings with
**Signatures** (typed input→output specs), **Modules** (composable strategies
like ChainOfThought), and **Optimizers** (teleprompters that tune prompts and
few-shot demos from data). You write the program; DSPy compiles the prompts.

## When to Use

- Building multi-component LM systems: RAG, agents, classifiers, pipelines.
- You have (or can bootstrap) examples + a metric and want prompts optimized automatically.
- You want one program portable across different LMs.

## When NOT to Use

- A single manual prompt or simple chatbot — use the provider SDK or the `claude-api` skill.
- No eval data and no metric to optimize against — DSPy's main payoff is gone.
- You just need prebuilt tool/integration chains — LangChain is lighter.
- Porting a strategy between frameworks/languages — see `strategy-translator`.

## Installation

```bash
pip install dspy                 # stable
pip install dspy[anthropic]      # with a provider extra (openai, all, ...)
```

## Quick Start

```python
import dspy

# Modern unified LM API (DSPy 2.5+): "<provider>/<model>", backed by LiteLLM.
# Reads ANTHROPIC_API_KEY / OPENAI_API_KEY from env, or pass api_key=...
lm = dspy.LM("anthropic/claude-opus-4-8")
dspy.configure(lm=lm)

# Signature: declare the task, not the prompt.
class QA(dspy.Signature):
    """Answer questions with short factual answers."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="often between 1 and 5 words")

# ChainOfThought adds an automatic reasoning step before the answer.
qa = dspy.ChainOfThought(QA)
response = qa(question="What is the capital of France?")
print(response.reasoning, response.answer)   # "...", "Paris"
```

> Note: the legacy per-provider classes (`dspy.Claude`, `dspy.OpenAI`,
> `dspy.OllamaLocal`) are removed. Always use `dspy.LM(...)` + `dspy.configure(...)`.

## Core Concepts (at a glance)

- **Signatures** — typed task spec, inline (`"question -> answer"`) or a class
  with a docstring and field `desc`s. Inline for prototypes; class for complex tasks.
- **Modules** — strategies that turn a signature into LM calls: `Predict`,
  `ChainOfThought`, `ReAct` (tool use), `ProgramOfThought` (code exec). Compose
  them by subclassing `dspy.Module` and writing a `forward()`.
- **Optimizers (teleprompters)** — compile a module against `trainset` + `metric`
  to learn instructions and few-shot demos: `BootstrapFewShot` (quick),
  `MIPRO`/`COPRO` (instruction search), `GEPA` (reflective instruction evolution —
  needs a feedback metric), `BootstrapFinetune` (weight tuning).
- **Metrics & Evaluate** — a `metric(example, pred, trace=None)` callable plus
  `dspy.evaluate.Evaluate` to score and compare programs.

## References

- `references/modules.md` — every module (Predict, ChainOfThought, ReAct,
  ProgramOfThought, MultiChainComparison, Retry), composition, batching, save/load.
- `references/optimizers.md` — BootstrapFewShot, MIPRO, COPRO, GEPA, KNNFewShot,
  BootstrapFinetune; metric design; train/val/test workflow; pitfalls.
- `references/gepa.md` — GEPA (reflective prompt evolution) in depth: the
  feedback-metric contract, budget/reflection_lm params, the loop, results
  inspection, and `dspy.GEPA` vs. the standalone `gepa-evolve` engine.
- `references/examples.md` — end-to-end RAG, agents, classifiers, multi-stage
  pipelines, and a production customer-support bot.
- `references/configuration.md` — LM provider setup (Anthropic/OpenAI/Ollama),
  scoped models, best practices, evaluation, and DSPy-vs-alternatives comparison.

## Resources

- Docs: https://dspy.ai
- GitHub: https://github.com/stanfordnlp/dspy
- Paper: "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines"
