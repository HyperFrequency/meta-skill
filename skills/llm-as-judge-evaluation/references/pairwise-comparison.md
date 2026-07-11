# Pairwise Comparison Reference

Pairwise comparison is the most reliable LLM-as-judge method. Asking "which of
these two responses is better?" is an easier, more consistent judgment than "how
good is this response on a scale?" — so it yields higher inter-annotator (and
inter-run) agreement and detects smaller quality differences.

## Pairwise vs Likert — when to pick which

| Aspect | Pairwise | Likert (1-5) |
|--------|----------|--------------|
| Inter-run agreement | High | Low-moderate |
| Calibration needed | No | Yes (what does "4" mean?) |
| Position bias | Present, but mitigatable via swap | N/A (single response) |
| Sensitivity to small gaps | High | Low (coarse scale) |
| Cost per judgment | 2x (swap needed) | 1x |
| Best for | A/B testing, model selection, preference data | Monitoring, fixed thresholds |

## Full comparison with position-swap mitigation

Run the comparison twice with A/B swapped and only count a win if both orderings
agree; disagreement means the judge's position bias decided it, so return a tie.

```python
from openai import OpenAI
import json

client = OpenAI()

PAIRWISE_PROMPT = """You are an expert evaluator. Compare two responses to the same prompt.

## Task Context
{task_description}

## User Input
{user_input}

## Response A
{response_a}

## Response B
{response_b}

## Evaluation Criteria
{criteria}

Which response is better? Consider all criteria above.
Return JSON: {{"winner": "A" or "B" or "tie", "reasoning": "brief explanation"}}"""

FLIP = {"A": "B", "B": "A", "tie": "tie"}

def _judge_once(user_input, response_a, response_b, task_description, criteria, model):
    prompt = PAIRWISE_PROMPT.format(
        task_description=task_description, user_input=user_input,
        response_a=response_a, response_b=response_b, criteria=criteria,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)["winner"]

def pairwise_compare(user_input, response_a, response_b, task_description, criteria,
                     model="gpt-4o", swap_positions=True):
    """Return 'A', 'B', or 'tie'. With swap_positions, both orderings must agree."""
    first = _judge_once(user_input, response_a, response_b, task_description, criteria, model)
    if not swap_positions:
        return first
    # Swap the two responses; flip the swapped verdict back to the original frame.
    swapped = _judge_once(user_input, response_b, response_a, task_description, criteria, model)
    second = FLIP[swapped]
    return first if first == second else "tie"
```

## Driving a full eval set

Randomize which response lands in position A per example so any *residual* position
bias averages out across the set, then flip the verdict back to a stable frame.

```python
import random

def evaluate_model_pair(eval_set, model_a_fn, model_b_fn, task_description, criteria,
                        judge_model="gpt-4o"):
    """model_a_fn / model_b_fn map an input string to a response string."""
    tally = {"A": 0, "B": 0, "tie": 0}
    details = []
    for i, example in enumerate(eval_set):
        resp_a = model_a_fn(example["input"])
        resp_b = model_b_fn(example["input"])
        if random.random() < 0.5:
            winner = pairwise_compare(example["input"], resp_a, resp_b,
                                      task_description, criteria, judge_model)
        else:
            winner = FLIP[pairwise_compare(example["input"], resp_b, resp_a,
                                           task_description, criteria, judge_model)]
        tally[winner] += 1
        details.append({"input": example["input"], "response_a": resp_a,
                        "response_b": resp_b, "winner": winner})
        if (i + 1) % 20 == 0:
            print(f"{i+1}/{len(eval_set)} — A:{tally['A']} B:{tally['B']} tie:{tally['tie']}")
    total = sum(tally.values())
    report = {
        "total_comparisons": total,
        "model_a_wins": tally["A"], "model_b_wins": tally["B"], "ties": tally["tie"],
        "model_a_win_rate": tally["A"] / total,
        "model_b_win_rate": tally["B"] / total,
        "tie_rate": tally["tie"] / total,
    }
    return report, details
```

## Chain-of-thought judging

Let the judge reason before it decides. Analyzing each response and comparing
criterion-by-criterion before committing to a winner measurably improves agreement,
at the cost of more tokens.

```python
COT_PAIRWISE_PROMPT = """You are an expert evaluator comparing two responses.

## Task: {task_description}
## Input: {user_input}
## Response A
{response_a}
## Response B
{response_b}
## Evaluation Criteria
{criteria}

Think step by step:
1. Analyze Response A's strengths and weaknesses
2. Analyze Response B's strengths and weaknesses
3. Compare on each criterion
4. Make your final judgment

Return JSON:
{{
  "analysis_a": "...",
  "analysis_b": "...",
  "comparison": "criterion-by-criterion",
  "winner": "A" or "B" or "tie",
  "confidence": "high" or "medium" or "low"
}}"""
```

## Reference-grounded comparison

When a ground-truth reference exists, give it to the judge and ask which response is
more faithful to it while staying helpful. This sharply reduces subjective drift.

```python
REFERENCE_PAIRWISE_PROMPT = """Compare two responses against a known correct reference.

## Input: {user_input}
## Reference (ground truth)
{reference}
## Response A
{response_a}
## Response B
{response_b}

Which response is more faithful to the reference while remaining helpful?
Return JSON: {{"winner": "A" or "B" or "tie", "reasoning": "..."}}"""
```

## Tie rate as a rubric-quality signal

The fraction of ties diagnoses whether your criteria are sharp enough.

| Tie rate | Interpretation | Action |
|----------|----------------|--------|
| < 10% | Clear quality difference | Good signal |
| 10-30% | Models are close | Normal; increase sample size |
| 30-50% | Very similar quality | Add finer-grained criteria |
| > 50% | Criteria too vague | Rewrite rubric with specific anchors |

## Bias pitfalls to control

1. **Length bias** — judges prefer longer responses; add a conciseness criterion.
2. **Format bias** — judges prefer markdown/structure; normalize formatting first.
3. **Sycophancy** — judges prefer answers that agree with the user; keep criteria neutral.
4. **Self-preference** — a model prefers its own style; judge with a different model family.
5. **Instruction-following vs quality** — separate these into distinct criteria so a
   well-written but off-brief answer doesn't win on style.
