---
name: instructor
description: Get type-safe, validated structured data out of LLMs using Instructor + Pydantic. WHAT - define a Pydantic response_model, call a patched client (from_anthropic/from_openai/from_provider), and Instructor coerces the LLM response into that model, auto-retrying with error feedback when validation fails; supports nested models, enums, custom validators, streaming partials/iterables, and Anthropic/OpenAI/Ollama. WHEN to use - extracting structured fields from text, classification into fixed categories, multi-entity extraction, schema-validated JSON, or streaming partial objects to a UI, in Python. WHEN NOT to use - free-form prose generation with no schema, non-Python stacks, prompt optimization (use DSPy), or building multi-step agent chains (use LangChain); for those, route elsewhere.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Prompt Engineering, Instructor, Structured Output, Pydantic, Data Extraction, JSON Parsing, Type Safety, Validation, Streaming, OpenAI, Anthropic]
dependencies: [instructor, pydantic, openai, anthropic]
---

# Instructor: Structured LLM Outputs

Instructor wraps an LLM client so that any call returns a validated Pydantic model
instead of raw text. Define a `response_model`, and Instructor handles JSON coercion,
Pydantic validation, and automatic retries with error feedback. Battle-tested across
many providers (Anthropic, OpenAI, Ollama, and more).

## When to Use

- **Extract structured data** from unstructured text reliably.
- **Validate outputs** against Pydantic schemas, with automatic retry on failure.
- **Classify** into fixed categories via enums.
- **Stream partial results** (`create_partial`) or sequences (`create_iterable`).
- **Support multiple providers** behind one consistent API.

Not the right tool for free-form generation with no schema, non-Python stacks, prompt
optimization (DSPy), or orchestrating agent chains (LangChain).

## 30-Second Example

```python
import instructor
from pydantic import BaseModel
from anthropic import Anthropic

class User(BaseModel):
    name: str
    age: int
    email: str

client = instructor.from_anthropic(Anthropic())

user = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "John Doe, 30, john@example.com"}],
    response_model=User,
)
print(user.name, user.age, user.email)
```

## Reference Map

Read the reference that matches your task — do not load all of them.

- **`references/core-concepts.md`** — installation, quick start, response models
  (basic / nested / optional / enums), automatic retrying, and streaming. Start here.
- **`references/validation.md`** — built-in constraints, custom field validators,
  model-level/cross-field validation, error inspection, and graceful degradation.
- **`references/providers.md`** — Anthropic, OpenAI, and local Ollama setup, plus modes
  (`Mode.TOOLS`, `Mode.ANTHROPIC_TOOLS`, `Mode.JSON`).
- **`references/advanced.md`** — union types, dynamic models, custom modes, context
  management, error handling, best practices, and comparison to alternatives.
- **`references/examples.md`** — end-to-end patterns: extraction, classification,
  multi-entity, structured analysis, batch processing, streaming.

## Related Skills

- `strategy-translator`, `scientific-pipeline-builder` — when structured extraction feeds
  a larger codegen/pipeline step.
- For prompt-optimization or agent-chain framing, route to a DSPy/LangChain-oriented skill
  rather than Instructor.

## Resources

- Docs: https://python.useinstructor.com
- GitHub: https://github.com/567-labs/instructor
- Cookbook: https://python.useinstructor.com/examples
