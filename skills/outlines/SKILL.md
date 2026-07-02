---
name: outlines
description: Outlines (dottxt.ai) structured text generation — guarantee valid JSON/regex/grammar-constrained outputs from local LLMs via FSM-based constrained token sampling, with native Pydantic support. Use WHEN generating structured outputs (JSON, Pydantic models, regex-matched strings, multiple-choice, enums, typed scalars) from local models (Transformers, llama.cpp, vLLM) and you need 100% schema-valid output at near-zero overhead. Do NOT use for API-only providers that need automatic retry/validation loops (use the sibling `instructor` skill), token-healing or complex agentic control flow (use `guidance`), self-optimizing prompt pipelines (use `dspy`), or plain unconstrained free-text generation where no schema applies.
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Prompt Engineering, Outlines, Structured Generation, JSON Schema, Pydantic, Local Models, Grammar-Based Generation, vLLM, Transformers, Type Safety]
dependencies: [outlines, transformers, vllm, pydantic]
---

# Outlines: Structured Text Generation

Router skill for Outlines, dottxt.ai's library for guaranteed-valid structured
generation. It converts a schema (Pydantic / JSON Schema / regex / choice set)
into a Finite State Machine that filters invalid tokens at the logit level, so
outputs are valid by construction with near-zero overhead. Deep material lives in
`references/` — start here, then jump.

## When to Use

- Guarantee valid **JSON / Pydantic / regex / code** structure during generation.
- Get **type-safe** outputs (ints, floats, bools, enums, `Literal`s) — not strings.
- Run on **local models** (Transformers, llama.cpp, vLLM) at high throughput.
- Need **100% valid outputs with no retry loop** (FSM-enforced).

For API-first generation with automatic retries see the sibling `instructor`
skill; for token healing / agentic control flow see `guidance`; for prompt
optimization pipelines see `dspy`.

## Installation

```bash
pip install "outlines>=1.0"               # base (v1 API shown below)
pip install "outlines>=1.0" transformers  # Hugging Face models
pip install "outlines>=1.0" llama-cpp-python  # llama.cpp (GGUF)
pip install "outlines>=1.0" vllm          # high-throughput serving
```

> API note: examples below use the **Outlines v1 API** (`outlines.from_*` +
> `output_type=`). The pre-1.0 `outlines.models.*` / `outlines.generate.*`
> helpers are deprecated; see the v1 migration in the official docs.

## Quick Start

```python
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import outlines

class User(BaseModel):
    name: str
    age: int
    email: str

model = outlines.from_transformers(                       # schema -> CFG -> FSM
    AutoModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-4k-instruct"),
    AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct"),
)
# Call the model with output_type; returns a schema-valid JSON string
result = model("Extract user: John Doe, 30, john@example.com", output_type=User)
user = User.model_validate_json(result)
print(user.name, user.age)   # guaranteed valid User instance
```

```python
# Constrained choice — result is always one of the options
from typing import Literal
sentiment = model("Sentiment of 'This is amazing!': ",
                  output_type=Literal["positive", "negative", "neutral"])
print(sentiment)                                         # "positive"

# Reusable, pre-compiled generator (compile the FSM once, reuse across prompts)
generator = outlines.Generator(model, User)
user = User.model_validate_json(generator("Extract user: Jane, 28, jane@x.com"))
```

## Output Types

Generation is driven by the `output_type` passed to the model call (or to
`outlines.Generator(model, output_type)`):

| `output_type=` | Constraint | Output |
|----------------|-----------|--------|
| Pydantic model or JSON Schema (str/dict) | schema | JSON string → `Model.model_validate_json()` |
| `Literal[...]` or an `Enum` | fixed option set | one option |
| `outlines.types.Regex(pattern)` | regex | matching string |
| `int` / `float` | numeric type | numeric string |
| omitted | none | free text |

## Backends (summary)

| Backend | Loader (v1) | Best for |
|---------|-------------|----------|
| Transformers | `outlines.from_transformers(hf_model, hf_tokenizer)` | general local use |
| llama.cpp | `outlines.from_llamacpp(Llama.from_pretrained(...))` | GGUF / CPU+GPU |
| vLLM (offline) | `outlines.from_vllm_offline(LLM(id))` | batch / production throughput |
| vLLM / SGLang (server) | `outlines.from_vllm(openai_client, id)` | OpenAI-compatible serving |
| OpenAI | `outlines.from_openai(OpenAI())` | limited (no FSM features) |

Full per-backend configuration (device/dtype, GPU offload, quantization,
multi-GPU, production deployment) is in `references/backends.md`.

## How It Works (core concept)

1. Schema (Pydantic / JSON Schema / regex) → context-free grammar (CFG).
2. CFG → Finite State Machine (FSM), compiled once per schema and cached.
3. At each step the FSM masks invalid tokens; deterministic paths fast-forward.

Result: valid-by-construction output, no post-hoc validation or retries, speed
comparable to unconstrained generation.

## Choosing Outlines vs. Alternatives

| Feature | Outlines | Instructor | Guidance | LMQL |
|---------|----------|------------|----------|------|
| Pydantic support | Native | Native | No | No |
| Regex constraints | Yes | No | Yes | Yes |
| Local models | Full | Limited | Full | Full |
| API models | Limited | Full | Full | Full |
| Zero overhead | Yes | No | Partial | Yes |
| Automatic retrying | No | Yes | No | No |

Pick Outlines for local models, max speed, and zero-overhead schema enforcement.
Pick `instructor` (sibling skill) for API models with retries, `guidance` for
token healing, `dspy` for prompt optimization.

## References

> The reference files below currently document the **pre-1.0 (v0) API**
> (`outlines.generate.*` / `outlines.models.*`). The concepts (schemas,
> constraints, backend tuning) transfer directly; translate calls to the v1
> form shown above (`outlines.from_*` + `output_type=`) when running on
> `outlines>=1.0`.

- `references/json_generation.md` — Pydantic models, JSON Schema, nested/complex
  types, constraints, optional fields, validation, performance.
- `references/backends.md` — Transformers, llama.cpp, vLLM, OpenAI: full
  configuration, quantization, multi-GPU, production deployment.
- `references/examples.md` — production-ready patterns: data extraction,
  classification, form processing, multi-entity extraction, code generation,
  batch processing.

## Resources

- Docs: https://dottxt-ai.github.io/outlines/
- GitHub: https://github.com/dottxt-ai/outlines
- Blog: https://blog.dottxt.co
