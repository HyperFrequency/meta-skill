# Path B — Frontier Distillation

Distillation uses a large teacher (GPT / Claude / Gemini) to label your real production inputs.
The student then learns to match the teacher on your narrow task at a fraction of inference
cost. Labels are a one-time cost and reusable, so this pays off when volume is high and the
task is narrow enough for a smaller model to absorb.

Use it when you have real inputs but no gold outputs. If you have outputs already, that is
Path A and beats distillation.

## Batch APIs (roughly half price)

Both major providers offer async batch endpoints at about 50% of real-time pricing with up to
24h turnaround. Prefer them for labeling — you are not latency-bound.

| Provider | Endpoint | Discount | Turnaround | Approx. max batch |
|----------|----------|----------|------------|-------------------|
| OpenAI | Batch API | ~50% | up to 24h | ~50,000 requests |
| Anthropic | Message Batches | ~50% | up to 24h | ~100,000 requests |
| Google | Batch prediction | varies | hours | large |

Limits and pricing change — confirm current numbers in the provider docs before sizing a run.

### OpenAI batch file

Each line is a request envelope with a `custom_id` you use to re-join results to inputs:

```python
import json

def create_batch_file(inputs, system_prompt, model="gpt-4o", path="batch_input.jsonl"):
    with open(path, "w") as f:
        for i, user_input in enumerate(inputs):
            f.write(json.dumps({
                "custom_id": f"request-{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                    "max_tokens": 4096,
                },
            }) + "\n")
    return path

# Submit (CLI):
#   openai api batches create -i batch_input.jsonl -e /v1/chat/completions -c 24h
```

### Anthropic Message Batches

```python
import anthropic

client = anthropic.Anthropic()

def create_anthropic_batch(inputs, system_prompt, model="claude-sonnet-4-5-20250929"):
    requests = [
        {
            "custom_id": f"request-{i}",
            "params": {
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_input}],
            },
        }
        for i, user_input in enumerate(inputs)
    ]
    batch = client.messages.batches.create(requests=requests)
    return batch.id
```

### Joining results back to training JSONL

Results come back unordered; recover order from `custom_id`. OpenAI's per-line result nests the
message under `response.body.choices[0].message.content`:

```python
def batch_results_to_training(results_file, inputs, system_prompt=None,
                              out="distilled_training.jsonl"):
    training = []
    with open(results_file) as f:
        for line in f:
            result = json.loads(line)
            idx = int(result["custom_id"].split("-")[1])
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": inputs[idx]})
            content = result["response"]["body"]["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": content})
            training.append({"messages": messages})
    with open(out, "w") as f:
        for ex in training:
            f.write(json.dumps(ex) + "\n")
    return len(training)
```

Anthropic's result envelope differs (`result.message.content` blocks) — read the batch results
schema for the provider you used before indexing into it.

## Distillation prompt design

Distilled quality is capped by prompt quality. Be explicit about format, tone, length, and
what must / must not appear. Match production conditions — reuse the same system prompt you run
in production so the student learns the real task.

```python
DISTILLATION_SYSTEM_PROMPT = """You are generating training data for a specialized model.

Task: {task_description}

Requirements:
- Output format: {format_spec}
- Tone: {tone}
- Length: {length_constraint}
- Must include: {required_elements}
- Must NOT include: {forbidden_elements}

Produce the highest-quality response possible; it will be a training target."""
```

Sample and manually review 50–100 outputs before trusting the whole batch.

## Quality filtering

Teacher outputs are not automatically good. Filter refusals and out-of-band lengths:

```python
def filter_distilled_data(examples, min_length=50, max_length=4000):
    refusals = ("i cannot", "i'm unable to", "i don't have access", "as an ai", "i'm not able to")
    kept = []
    for ex in examples:
        response = ex["messages"][-1]["content"]
        if not (min_length <= len(response) <= max_length):
            continue
        if any(p in response.lower() for p in refusals):
            continue
        kept.append(ex)
    print(f"Kept {len(kept)}/{len(examples)} ({len(kept)/len(examples)*100:.1f}%)")
    return kept
```

## Cost estimation

Batch price is roughly half real-time. Estimate before submitting; pull current per-million-
token rates from the provider (the numbers below are illustrative and go stale):

```python
def estimate_distillation_cost(num_examples, avg_input_tokens, avg_output_tokens, model="gpt-4o"):
    # Illustrative BATCH prices, USD per 1M tokens — verify against current provider pricing.
    prices = {
        "gpt-4o":       {"input": 1.25,  "output": 5.00},
        "gpt-4o-mini":  {"input": 0.075, "output": 0.30},
        "claude-sonnet":{"input": 1.50,  "output": 7.50},
    }
    p = prices.get(model, prices["gpt-4o"])
    input_cost = num_examples * avg_input_tokens / 1_000_000 * p["input"]
    output_cost = num_examples * avg_output_tokens / 1_000_000 * p["output"]
    return {"model": model, "examples": num_examples,
            "total_cost": f"${input_cost + output_cost:.2f}"}
```

## Multi-teacher distillation

Labeling with more than one teacher reduces single-model style bias. Two common strategies:
use the strongest model as primary and others to validate, or keep only examples where all
teachers agree as a high-confidence subset. Weigh the extra API cost against the bias
reduction — for narrow tasks a single strong teacher is usually enough.
