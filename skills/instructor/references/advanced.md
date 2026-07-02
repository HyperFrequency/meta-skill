# Advanced Features, Error Handling, Best Practices

## Union Types

```python
from typing import Union
from pydantic import HttpUrl

class TextContent(BaseModel):
    type: str = "text"
    content: str

class ImageContent(BaseModel):
    type: str = "image"
    url: HttpUrl
    caption: str

class Post(BaseModel):
    title: str
    content: Union[TextContent, ImageContent]  # LLM picks the appropriate type
```

## Dynamic Models

```python
from pydantic import create_model, EmailStr, Field

DynamicUser = create_model(
    "User",
    name=(str, ...),
    age=(int, Field(ge=0)),
    email=(EmailStr, ...),
)

user = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[...],
    response_model=DynamicUser,
)
```

## Custom Modes

Modes control how Instructor coerces structured output from a provider.

```python
client = instructor.from_anthropic(Anthropic(), mode=instructor.Mode.TOOLS)
```

- `Mode.TOOLS` — tool/function calling; recommended for Claude and OpenAI.
- `Mode.ANTHROPIC_TOOLS` — Anthropic-specific tool calling.
- `Mode.JSON` — JSON fallback for providers without native structured outputs
  (e.g. local Ollama). See `references/providers.md`.

## Context Management

```python
with instructor.from_anthropic(Anthropic()) as client:
    result = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[...],
        response_model=YourModel,
    )
    # client closed automatically
```

## Error Handling

### Catching validation failures after retries

```python
from pydantic import ValidationError

try:
    user = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[...],
        response_model=User,
        max_retries=3,
    )
except ValidationError as e:
    print(f"Failed after retries: {e}")
except Exception as e:
    print(f"API error: {e}")
```

### Examples to guide extraction

```python
class ValidatedUser(BaseModel):
    name: str = Field(description="Full name, 2-100 characters")
    age: int = Field(description="Age between 0 and 120", ge=0, le=120)
    email: EmailStr = Field(description="Valid email address")

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "John Doe", "age": 30, "email": "john@example.com"}]
        }
    }
```

For graceful degradation, partial-fallback extraction, and per-field error inspection,
see `references/validation.md`.

## Best Practices

1. **Clear field descriptions.** `price: float = Field(description="Price in USD, no currency symbol")`
   beats a bare `price: float`.
2. **Use appropriate validation.** Constrain values with `Field(ge=1, le=5, ...)` rather than
   accepting anything and checking later.
3. **Provide examples in prompts.** Show the desired JSON shape in the user message.
4. **Use enums for fixed categories** so the LLM must choose from a known set.
5. **Handle missing data gracefully** with `Optional[...] = None` and defaults so extraction
   can succeed even when some fields are absent.

## Comparison to Alternatives

| Feature | Instructor | Manual JSON | LangChain | DSPy |
|---------|------------|-------------|-----------|------|
| Type safety | Yes | No | Partial | Yes |
| Auto validation | Yes | No | No | Limited |
| Auto retry | Yes | No | No | Yes |
| Streaming | Yes | No | Yes | No |
| Multi-provider | Yes | Manual | Yes | Yes |
| Learning curve | Low | Low | Medium | High |

**Choose Instructor** for structured, validated outputs with type safety and automatic retries
(data-extraction systems). **Choose alternatives** when you need prompt optimization (DSPy),
complex chains (LangChain), or a one-off throwaway extraction (manual JSON).
