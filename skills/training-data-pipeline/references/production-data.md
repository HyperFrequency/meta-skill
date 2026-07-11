# Path A — Production Data

Production data is the highest-value training signal because it reflects your real input
distribution and no competitor can copy it. This reference covers extracting, cleaning, and
formatting it into `messages` JSONL.

## Signal quality ladder

Rank sources by how much you trust the output as a training target:

| Signal | Quality | How to use it |
|--------|---------|---------------|
| User **edited** the model output | Highest | Train on the *edited* version |
| Thumbs-up / accepted | High | Train on the original output |
| Thumbs-down / rejected | Medium | Exclude from SFT; keep for DPO as the rejected side |
| No feedback | Low | Use only with heuristic filtering |

Rule of thumb: whenever a `corrected_response` exists, it beats the raw `model_response`.

## From API logs

Most systems log request/response pairs. Pull the input messages and the response, preferring
a corrected version when present.

```python
import json

def api_log_to_training(log_entry):
    """Convert one API request/response log into a messages example."""
    messages = []
    if log_entry.get("system_prompt"):
        messages.append({"role": "system", "content": log_entry["system_prompt"]})
    messages.append({"role": "user", "content": log_entry["user_input"]})
    # Prefer a human-corrected response over the raw model output.
    response = log_entry.get("corrected_response") or log_entry["api_response"]
    messages.append({"role": "assistant", "content": response})
    return {"messages": messages}

with open("api_logs.jsonl") as src, open("training_data.jsonl", "w") as out:
    for line in src:
        out.write(json.dumps(api_log_to_training(json.loads(line))) + "\n")
```

If your logs already store an OpenAI-style envelope, the extraction path is usually
`input.messages` for context and `output.choices[0].message.content` for the target.

## From a database

If interactions live in a table, filter to non-rejected rows within a recency window and
coalesce to the corrected response:

```sql
SELECT
    system_prompt,
    user_input,
    COALESCE(corrected_response, model_response) AS target_response,
    user_feedback
FROM llm_interactions
WHERE user_feedback IS DISTINCT FROM 'rejected'
  AND created_at > NOW() - INTERVAL '90 days'
ORDER BY created_at DESC;
```

## From user corrections

A correction is a paired (original input, human-fixed output). The fixed output is the target:

```python
def correction_to_training(original_input, corrected_output, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": original_input})
    messages.append({"role": "assistant", "content": corrected_output})
    return {"messages": messages}
```

## From accept/reject signals

Keep accepted outputs as positive SFT examples. (Rejected outputs are not SFT data — reserve
them for a DPO/preference dataset, which is out of scope here.)

```python
def filter_accepted(logs):
    return [
        {"messages": [
            {"role": "user", "content": log["input"]},
            {"role": "assistant", "content": log["output"]},
        ]}
        for log in logs
        if log.get("user_action") == "accepted"
    ]
```

## Cleaning pipeline

Run this before validation. Order matters — redact PII while you still have raw text.

```python
def clean_production_data(examples):
    cleaned = []
    for ex in examples:
        messages = ex["messages"]

        # Drop empty/trivial targets.
        assistant = next((m for m in messages if m["role"] == "assistant"), None)
        if not assistant or len(assistant["content"].strip()) < 10:
            continue

        for msg in messages:
            msg["content"] = " ".join(msg["content"].split())   # normalize whitespace
            msg["content"] = redact_pii(msg["content"])          # see data-quality.md

        # Skip likely test traffic (near-empty user turns).
        user = next((m for m in messages if m["role"] == "user"), None)
        if user and len(user["content"].strip()) < 5:
            continue

        cleaned.append({"messages": messages})
    return cleaned
```

## Multi-turn conversations

To teach behavior at every assistant turn, emit one example per assistant message carrying the
full prior history:

```python
def conversation_to_training(conversation):
    """Each assistant turn becomes an example with all preceding context."""
    examples, messages = [], []
    for turn in conversation["turns"]:
        messages.append({"role": turn["role"], "content": turn["content"]})
        if turn["role"] == "assistant":
            examples.append({"messages": list(messages)})   # snapshot, not reference
    return examples
```

Note the `list(messages)` copy — appending in place afterward would otherwise mutate earlier
snapshots.

## Volume guidelines

| Dataset size | Viability | Recommended approach |
|--------------|-----------|----------------------|
| < 100 | Insufficient for SFT | Bootstrap synthetically (Path C) first |
| 100–1,000 | Minimum viable | LoRA fine-tune, watch eval closely |
| 1,000–10,000 | Good | Standard LoRA / QLoRA |
| 10,000–100,000 | Strong | Full fine-tune becomes viable |
| > 100,000 | Excellent | Multi-epoch, consider curriculum ordering |
