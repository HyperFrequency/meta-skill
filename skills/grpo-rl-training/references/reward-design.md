# Reward Function Design

The full, copy-pasteable reward function library lives in
[`../examples/reward_functions_library.py`](../examples/reward_functions_library.py)
(20+ functions across correctness, format, length, style, and combined categories).
This page covers the design philosophy and the canonical templates.

## Design Philosophy

**Golden Rules:**
1. **Compose multiple reward functions** - Each handles one aspect (format, correctness, style).
2. **Scale rewards appropriately** - Higher weight = stronger signal.
3. **Use incremental rewards** - Partial credit for partial compliance.
4. **Test rewards independently** - Debug each reward function in isolation.

Combine 3-5 reward functions for robust training. Order matters less than diversity of signals.

## Reward Function Types

| Type | Use Case | Example Weight |
|------|----------|----------------|
| **Correctness** | Verifiable tasks (math, code) | 2.0 (highest) |
| **Format** | Strict structure enforcement | 0.5-1.0 |
| **Length** | Encourage verbosity/conciseness | 0.1-0.5 |
| **Style** | Penalize unwanted patterns | -0.5 to 0.5 |

## Template Structure

Every TRL reward function receives `prompts` and `completions` (both `List[List[Dict]]`)
plus any extra dataset columns as keyword args, and returns one float per completion.

```python
def reward_function_name(
    prompts,        # List[List[Dict]]: Original prompts
    completions,    # List[List[Dict]]: Model generations
    answer=None,    # Optional: Ground truth from dataset
    **kwargs        # Additional dataset columns
) -> list[float]:
    """Evaluate completions and return rewards (one float per completion)."""
    responses = [comp[0]['content'] for comp in completions]
    return [compute_score(r) for r in responses]
```

## Canonical Examples

### Correctness Reward (Math/Coding)
```python
def correctness_reward(prompts, completions, answer, **kwargs):
    """Reward correct answers with high score."""
    responses = [comp[0]['content'] for comp in completions]
    extracted = [extract_final_answer(r) for r in responses]
    return [2.0 if ans == gt else 0.0
            for ans, gt in zip(extracted, answer)]
```

### Format Reward (Structured Output)
```python
import re

def format_reward(completions, **kwargs):
    """Reward XML-like structured format."""
    pattern = r'<reasoning>.*?</reasoning>\s*<answer>.*?</answer>'
    responses = [comp[0]['content'] for comp in completions]
    return [1.0 if re.search(pattern, r, re.DOTALL) else 0.0
            for r in responses]
```

### Incremental Format Reward (Partial Credit)
```python
def incremental_format_reward(completions, **kwargs):
    """Award partial credit for format compliance."""
    responses = [comp[0]['content'] for comp in completions]
    rewards = []
    for r in responses:
        score = 0.0
        if '<reasoning>' in r:  score += 0.25
        if '</reasoning>' in r: score += 0.25
        if '<answer>' in r:     score += 0.25
        if '</answer>' in r:    score += 0.25
        # Penalize extra text after closing tag
        if r.count('</answer>') == 1:
            extra_text = r.split('</answer>')[-1].strip()
            score -= len(extra_text) * 0.001
        rewards.append(score)
    return rewards
```

## Dataset Preparation

GRPO prompts must be in chat format (list of `{'role', 'content'}` dicts). For verifiable
tasks, carry the ground truth as an additional column (passed back to rewards via `**kwargs`).

```python
from datasets import load_dataset, Dataset

SYSTEM_PROMPT = """
Respond in the following format:
<reasoning>
[Your step-by-step thinking]
</reasoning>
<answer>
[Final answer]
</answer>
"""

def prepare_dataset(raw_data):
    """Transform raw data into GRPO-compatible format.

    Returns Dataset with columns:
    - 'prompt': List[Dict] with role/content (system + user messages)
    - 'answer': str (ground truth, optional but recommended)
    """
    return raw_data.map(lambda x: {
        'prompt': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': x['question']}
        ],
        'answer': extract_answer(x['raw_answer'])
    })
```

**Pro Tips:**
- Use one-shot or few-shot examples in the system prompt for complex formats.
- Keep prompts concise (`max_prompt_length`: 256-512 tokens).
- Validate data quality before training (garbage in = garbage out).
