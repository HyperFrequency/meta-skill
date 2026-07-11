# Data Quality, Validation & Splitting

Data quality sets the ceiling on model quality. This reference covers the gates every dataset
passes before training — schema validation, deduplication, diversity, token-length, PII
redaction, optional LLM-judge scoring, a health report — and the leak-free train/eval split.

## Quality dimensions and targets

| Dimension | Measures | Target |
|-----------|----------|--------|
| Correctness | Factual accuracy of responses | Manual review of a sample |
| Consistency | Similar inputs → similar outputs | Low variance on paraphrases |
| Completeness | Responses are thorough | Task-dependent length band |
| Format compliance | Output matches required schema | 100% schema-validation pass |
| Diversity | Coverage of the input space | `distinct-2 > 0.5` |
| Deduplication | Near-duplicates removed | < 5% duplicate rate |

## Schema validation

Fail loudly on any line that would break the trainer. Run this first and fix every flagged
line before proceeding.

```python
import json

def validate_jsonl(filepath):
    errors, valid = [], 0
    with open(filepath) as f:
        for i, line in enumerate(f, 1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: invalid JSON — {e}")
                continue
            if "messages" not in obj:
                errors.append(f"Line {i}: missing 'messages'")
                continue
            msgs = obj["messages"]
            if not isinstance(msgs, list) or len(msgs) < 2:
                errors.append(f"Line {i}: 'messages' must be a list of >= 2")
                continue
            if not any(m.get("role") == "user" for m in msgs) or \
               not any(m.get("role") == "assistant" for m in msgs):
                errors.append(f"Line {i}: need >= 1 user and >= 1 assistant")
                continue
            for j, m in enumerate(msgs):
                if "role" not in m or "content" not in m:
                    errors.append(f"Line {i}, msg {j}: missing role/content")
                elif m["role"] not in ("system", "user", "assistant"):
                    errors.append(f"Line {i}, msg {j}: bad role '{m['role']}'")
            valid += 1
    return {"valid": valid, "errors": errors, "total": valid + len(errors)}
```

## Deduplication (MinHash LSH)

Dedup on the **assistant target** (the thing being learned). MinHash LSH finds near-duplicates
cheaply; 0.8 is a sensible Jaccard threshold. Requires `datasketch` (MIT).

```python
from datasketch import MinHash, MinHashLSH

def deduplicate_dataset(examples, threshold=0.8, num_perm=128):
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    unique = []
    for i, ex in enumerate(examples):
        text = ex["messages"][-1]["content"]
        m = MinHash(num_perm=num_perm)
        for word in text.lower().split():
            m.update(word.encode("utf-8"))
        if not lsh.query(m):               # no near-neighbor already indexed
            lsh.insert(f"doc-{i}", m)
            unique.append(ex)
    removed = len(examples) - len(unique)
    print(f"Removed {removed} duplicates ({removed/len(examples)*100:.1f}%)")
    return unique
```

## Diversity (distinct-n)

`distinct-n` is the ratio of unique n-grams to total n-grams — low values mean repetitive data.

```python
from collections import Counter

def distinct_n(texts, n=2):
    total = Counter()
    for text in texts:
        words = text.lower().split()
        total.update(tuple(words[i:i+n]) for i in range(len(words) - n + 1))
    denom = sum(total.values())
    return len(total) / denom if denom else 0.0

def dataset_diversity_report(examples):
    responses = [ex["messages"][-1]["content"] for ex in examples]
    return {
        "total_examples": len(examples),
        "avg_response_words": sum(len(r.split()) for r in responses) / len(responses),
        "distinct_1": distinct_n(responses, 1),
        "distinct_2": distinct_n(responses, 2),
        "distinct_3": distinct_n(responses, 3),
    }
```

Aim for `distinct_2 > 0.5`. Below that, add variety at the source (Path C diversity levers)
rather than trying to fix it downstream.

## Token-length analysis

Analyze lengths with the **target model's** tokenizer to catch outliers and set
`max_seq_length`. Requires `transformers` (Apache-2.0).

```python
import numpy as np
from transformers import AutoTokenizer

def token_length_analysis(examples, model_name="meta-llama/Llama-3.1-8B"):
    tok = AutoTokenizer.from_pretrained(model_name)
    lengths = [
        len(tok.encode(tok.apply_chat_template(ex["messages"], tokenize=False)))
        for ex in examples
    ]
    lengths = np.array(lengths)
    return {
        "count": int(len(lengths)),
        "median": float(np.median(lengths)),
        "p95": float(np.percentile(lengths, 95)),
        "p99": float(np.percentile(lengths, 99)),
        "max": int(lengths.max()),
        "recommended_max_seq_length": int(np.percentile(lengths, 99) * 1.1),
    }
```

Setting `max_seq_length` near p99 (with headroom) avoids padding waste while truncating only
rare outliers.

## PII redaction

Redact before the data leaves your boundary — while you still have raw text, before dedup and
splitting. These regexes are a floor, not a guarantee; add domain-specific patterns and, for
sensitive data, a dedicated PII/NER pass.

```python
import re

PII_PATTERNS = {
    "email":       r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    "phone":       r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b',
    "ssn":         r'\b\d{3}-\d{2}-\d{4}\b',
    "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    "ip_address":  r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
}

def redact_pii(text, patterns=PII_PATTERNS):
    for name, pattern in patterns.items():
        text = re.sub(pattern, f"[{name.upper()}_REDACTED]", text)
    return text
```

## LLM-judge scoring (optional)

For high-stakes datasets, score each example 1–5 with a cheap judge model on task-specific
criteria and drop the low scorers. Sketch: send the (input, response, criteria) to the judge,
ask for JSON `{"scores": {...}, "overall": n, "reasoning": "..."}`, and filter `overall < 3`.
For judge design and calibration proper, use the `llm-as-judge-evaluation` skill rather than
hand-rolling it here.

## Train/eval split (leak-free)

Reserve **all real production examples for eval** so you measure against reality, then fill the
rest of the eval budget from synthetic/distilled data. Dedup across the split boundary too — a
near-duplicate straddling train and eval inflates scores.

```python
import random

def split_dataset(examples, eval_ratio=0.1, production_indices=None):
    """Production examples always go to eval; synthetic fills the remaining budget."""
    production_indices = set(production_indices or [])
    synthetic  = [ex for i, ex in enumerate(examples) if i not in production_indices]
    production = [ex for i, ex in enumerate(examples) if i in production_indices]

    eval_set = list(production)                                   # ground truth
    remaining = max(0, int(len(examples) * eval_ratio) - len(eval_set))
    random.shuffle(synthetic)
    eval_set.extend(synthetic[:remaining])
    train_set = synthetic[remaining:]

    print(f"Train: {len(train_set)}, Eval: {len(eval_set)} "
          f"({len(production)} production + {len(eval_set) - len(production)} synthetic)")
    return train_set, eval_set
```

If production data exceeds the eval budget, either accept a larger eval set or subsample
production for eval and move the remainder to train — never move an eval example into train
without re-deduplicating.

## Health report

A quick one-call overview for a finished file — turn counts, role distribution, response
length band, and the share of suspiciously short responses:

```python
def dataset_health_report(filepath):
    examples = [json.loads(l) for l in open(filepath)]
    roles = {}
    for ex in examples:
        for m in ex["messages"]:
            roles[m["role"]] = roles.get(m["role"], 0) + 1
    resp_words = [len(ex["messages"][-1]["content"].split()) for ex in examples]
    short = sum(1 for w in resp_words if w < 10)
    return {
        "total_examples": len(examples),
        "avg_turns": sum(len(ex["messages"]) for ex in examples) / len(examples),
        "role_distribution": roles,
        "response_words": {"min": min(resp_words), "max": max(resp_words),
                            "mean": sum(resp_words) / len(resp_words)},
        "short_responses": f"{short} ({short/len(examples)*100:.1f}%)",
    }
```
