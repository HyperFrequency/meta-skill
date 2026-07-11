# Dataset row templates

Six row schemas for common dataset shapes. Validate rows against the matching schema
before upload (see `hub-management.md` → validation) so every example in a split has
a consistent structure. Each template lists **required** fields (must be present),
**recommended** fields (kept if present, warned if missing), per-field type rules,
and an example row.

Type rules use: `string`, `number`, `array`, `object`, `string|array` (either), and
`enum:a,b,c` (value must be one of the listed literals).

---

## `chat` — multi-turn conversation / tool use

- **Required:** `messages`
- **Recommended:** `scenario`, `complexity`
- **Rules:** `messages` is a non-empty array; each message is an object with a
  `role` in `{user, assistant, tool, system}` and a `content` field. Tool responses
  may carry a `tool_call_id`.

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Find open PRs in the repo."},
    {"role": "assistant", "content": "Calling the GitHub tool...", "tool_call_id": "call_123"},
    {"role": "tool", "content": "[{\"pr\": 42, \"title\": \"...\"}]", "tool_call_id": "call_123"},
    {"role": "assistant", "content": "There is 1 open PR: #42."}
  ],
  "scenario": "repo triage via tool call",
  "complexity": "intermediate"
}
```

`complexity` when present: `enum:simple,intermediate,advanced`.

---

## `classification` — text classification

- **Required:** `text`, `label`
- **Recommended:** `confidence`, `metadata`, `source`
- **Rules:** `text` is a string; `label` is a string (single-label) or array
  (multi-label); `confidence` is a number in [0,1]; `metadata` is an object.

```json
{
  "text": "The camera quality is outstanding and the battery lasts all day.",
  "label": "positive",
  "confidence": 0.98,
  "metadata": {"language": "en", "domain": "product_reviews"},
  "source": "customer_feedback"
}
```

---

## `qa` — question answering

- **Required:** `question`, `answer`
- **Recommended:** `context`, `answer_type`, `difficulty`, `topic`, `source`
- **Rules:** `question` is a string; `answer` is a string or array; `context` is a
  string; `answer_type` is `enum:factual,explanatory,opinion,yes_no,multiple_choice`;
  `difficulty` is `enum:easy,medium,hard`.

```json
{
  "question": "Based on the passage, what caused the downturn?",
  "answer": "A sudden drop in consumer confidence after the bank failures.",
  "context": "The 2008 downturn began when several banks failed...",
  "answer_type": "explanatory",
  "difficulty": "medium",
  "topic": "economics",
  "source": "reading_comprehension"
}
```

---

## `completion` — prompt/continuation

- **Required:** `prompt`, `completion`
- **Recommended:** `domain`, `style`
- **Rules:** `prompt` and `completion` are strings; `domain` when present is
  `enum:code,creative,technical,conversational`.

```json
{
  "prompt": "def fibonacci(n):",
  "completion": "\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
  "domain": "code",
  "style": "concise iterative implementation"
}
```

---

## `tabular` — structured rows with a column spec

- **Required:** `columns`, `data`
- **Recommended:** `source`
- **Rules:** `columns` is an array of `{name, type, description}` objects; `data` is
  an array of row objects keyed by column name.

```json
{
  "columns": [
    {"name": "feature1", "type": "numeric", "description": "First feature"},
    {"name": "target", "type": "categorical", "description": "Target variable"}
  ],
  "data": [
    {"feature1": 123, "target": "class_a"},
    {"feature1": 456, "target": "class_b"}
  ]
}
```

---

## `custom` — caller-defined schema

No fixed required fields. Use when none of the above fits. Define your own required
set and validate against it explicitly:

```python
required = {"input", "output", "meta"}
assert all(required <= set(r) for r in rows)
```

Keep the schema uniform across a split — the Hub infers one Parquet schema per
split, and rows with divergent keys/types will fail to load or coerce to null.

---

## Applying a template

```python
def validate(rows, required, field_types=None):
    for i, r in enumerate(rows):
        missing = set(required) - set(r)
        if missing:
            raise ValueError(f"row {i}: missing required {missing}")
        for field, rule in (field_types or {}).items():
            if field in r and rule.startswith("enum:"):
                allowed = set(rule[5:].split(","))
                if r[field] not in allowed:
                    raise ValueError(f"row {i}: {field}={r[field]!r} not in {allowed}")
    return True

validate(rows,
         required=["question", "answer"],
         field_types={"difficulty": "enum:easy,medium,hard"})
```

Then publish with either path in `hub-management.md`.
