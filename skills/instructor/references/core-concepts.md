# Core Concepts

Quick start, response models, automatic retrying, and streaming.

## Installation

```bash
pip install instructor                  # base
pip install "instructor[anthropic]"     # Anthropic Claude
pip install "instructor[openai]"        # OpenAI
pip install "instructor[all]"           # all providers
```

## Quick Start

### Anthropic

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
    messages=[{
        "role": "user",
        "content": "John Doe is 30 years old. His email is john@example.com"
    }],
    response_model=User,
)

print(user.name, user.age, user.email)  # "John Doe" 30 "john@example.com"
```

> Modern alternative: `instructor.from_provider("anthropic/claude-sonnet-4-5-20250929")`
> resolves the SDK client and a sensible mode in one call. See `references/providers.md`.

### OpenAI

```python
from openai import OpenAI

client = instructor.from_openai(OpenAI())

user = client.chat.completions.create(
    model="gpt-4o-mini",
    response_model=User,
    messages=[{"role": "user", "content": "Extract: Alice, 25, alice@email.com"}],
)
```

## Response Models (Pydantic)

Response models define the structure and validation rules for LLM outputs. Benefits:
type safety, automatic validation, self-documenting `Field` descriptions, IDE autocomplete.

### Basic model

```python
from pydantic import BaseModel, Field

class Article(BaseModel):
    title: str = Field(description="Article title")
    author: str = Field(description="Author name")
    word_count: int = Field(description="Number of words", gt=0)
    tags: list[str] = Field(description="List of relevant tags")
```

### Nested models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class Person(BaseModel):
    name: str
    age: int
    address: Address  # Nested model

# person.address.city  ->  "Boston"
```

### Optional fields and defaults

```python
from typing import Optional

class Product(BaseModel):
    name: str
    price: float
    discount: Optional[float] = None              # optional
    description: str = Field(default="No description")  # default value
```

### Enums for constrained values

```python
from enum import Enum

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class Review(BaseModel):
    text: str
    sentiment: Sentiment  # only these three values allowed
```

## Automatic Retrying

When Pydantic validation fails, Instructor sends the error back to the LLM and retries.

```python
user = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Extract user from: John, age unknown"}],
    response_model=User,
    max_retries=3,  # default is 3
)
```

How it works:
1. LLM generates output.
2. Pydantic validates.
3. If invalid, the validation error message is sent back to the LLM.
4. The LLM tries again with that feedback.
5. Repeats up to `max_retries`.

See `references/validation.md` for the full validation guide.

## Streaming

Stream partial results for real-time processing. Note: Pydantic validators are NOT
supported on models used with streaming.

### Streaming a single object as it fills in (`create_partial`)

```python
class Story(BaseModel):
    title: str
    content: str
    tags: list[str]

for partial_story in client.create_partial(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a short sci-fi story"}],
    response_model=Story,
):
    print(f"Title: {partial_story.title}")
    print(f"Content so far: {partial_story.content[:100]}...")
```

### Streaming a sequence of objects (`create_iterable`)

```python
class Task(BaseModel):
    title: str
    priority: str

for task in client.create_iterable(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Generate 10 project tasks"}],
    response_model=Task,
):
    print(f"- {task.title} ({task.priority})")
```

> `create_partial`/`create_iterable` live on the patched client itself
> (`client.create_partial(...)`), not under `client.messages`.
