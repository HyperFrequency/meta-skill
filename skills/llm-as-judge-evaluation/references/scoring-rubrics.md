# Scoring Rubrics Reference

A good rubric is the difference between noisy and reliable Likert (absolute) scoring.
Use these templates as starting points and adapt the anchors to your task.

## Likert scorer

```python
from openai import OpenAI
import json

client = OpenAI()

LIKERT_PROMPT = """You are an expert evaluator. Rate this response on a 1-5 scale.

## Task Context
{task_description}

## User Input
{user_input}

## Response
{response}

## Scoring Rubric
{rubric}

Rate the response on each dimension, then give an overall score.
Return JSON: {{"scores": {{"dimension_name": score, ...}}, "overall": score, "reasoning": "..."}}"""

def likert_score(user_input, response, task_description, rubric, model="gpt-4o"):
    prompt = LIKERT_PROMPT.format(
        task_description=task_description, user_input=user_input,
        response=response, rubric=rubric,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)
```

## Rubric design principles

1. **Specific anchors** — each score level describes observable behavior, not vague
   quality ("contains factual errors" beats "poor").
2. **Independent dimensions** — criteria must not overlap; avoid pairing "quality"
   with "helpfulness".
3. **Weighted dimensions** — not all criteria matter equally; assign weights that
   sum to 1.0.
4. **Calibration examples** — include 2-3 example responses with their expected
   scores to anchor the judge.
5. **Task-aligned** — the rubric should reflect what your users actually care about.

## Template: General Quality

```
1. Accuracy
   1: Contains factual errors or hallucinations
   2: Mostly correct but with notable inaccuracies
   3: Factually correct on main points, minor issues
   4: Accurate and well-supported claims
   5: Perfectly accurate with appropriate caveats
2. Relevance
   1: Does not address the question   3: Addresses the main question adequately
   5: Precisely addresses every aspect of the question
3. Clarity
   1: Confusing, poorly organized   3: Clear and logically organized
   5: Exceptionally clear, easy to scan
4. Conciseness
   1: Extremely verbose, buries the answer   3: Appropriate length
   5: Every word serves a purpose
```

## Template: Code Generation

```
1. Correctness (weight 0.40)
   1: Won't compile/run, fundamental logic errors
   3: Handles common cases correctly
   5: Correct, robust, handles all specified requirements
2. Code Quality (weight 0.25)
   1: Unreadable, no structure   3: Acceptable style, reasonable naming
   5: Exemplary code that teaches best practices
3. Efficiency (weight 0.15)
   1: Exponential complexity or worse   3: Acceptable for typical inputs
   5: Optimal or near-optimal solution
4. Completeness (weight 0.20)
   1: Missing major requirements   3: Core requirements met
   5: Complete with tests, docs, and error handling
```

## Template: Customer Support

```
1. Problem Resolution (weight 0.40)
   1: Does not address the issue   3: Valid but not optimal solution
   5: Resolves issue and prevents related problems
2. Tone & Empathy (weight 0.25)
   1: Rude, dismissive, robotic   3: Friendly and professional
   5: Exceptional rapport while staying professional
3. Accuracy (weight 0.20)
   1: Incorrect product/policy info   3: Factually accurate
   5: Accurate with relevant links/resources
4. Efficiency (weight 0.15)
   1: Multiple follow-ups needed   3: Reasonable steps to resolution
   5: Resolves in minimum interactions
```

## Template: Summarization

```
1. Faithfulness (weight 0.35)
   1: Hallucinates info not in source   3: Faithful to source
   5: Faithful, captures nuance and caveats
2. Coverage (weight 0.30)
   1: Misses most key points   3: Covers main points adequately
   5: Captures all important points and relationships
3. Coherence (weight 0.20)
   1: Disjointed   3: Reads smoothly   5: Exemplary narrative flow
4. Conciseness (weight 0.15)
   1: No compression   3: Reasonable reduction
   5: Maximum information density
```

## Composite weighted score

```python
def weighted_score(scores, weights):
    """scores: {dimension: 1..5}; weights: {dimension: w}, w summing to 1.0."""
    return round(sum(scores[dim] * weights[dim] for dim in scores), 2)

scores = {"correctness": 4, "quality": 3, "efficiency": 5, "completeness": 4}
weights = {"correctness": 0.4, "quality": 0.25, "efficiency": 0.15, "completeness": 0.2}
weighted_score(scores, weights)  # 3.9
```
