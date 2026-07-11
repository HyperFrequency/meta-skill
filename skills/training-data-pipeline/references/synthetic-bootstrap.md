# Path C — Synthetic Bootstrapping

Generate training data from scratch when you have fewer than ~1000 real examples. Treat it as
a cold-start scaffold, not a destination: as production data (Path A) accumulates, replace
synthetic examples with real ones. Synthetic data inherits the generator's biases and blind
spots, so a model trained only on it plateaus at the teacher's behavior on the teacher's
imagined input distribution — which is rarely your real one.

## When synthetic helps vs. hurts

- **Helps**: bootstrapping a brand-new task, filling rare/edge categories your real data
  under-represents, adversarial examples you can describe but haven't collected.
- **Hurts**: as the majority of a dataset for a task where real inputs are available; it
  narrows diversity and bakes in generator artifacts. Cap synthetic share and keep real
  examples in eval so you can measure the gap.

## Seed-prompt strategy

Anchor generation on a handful of real examples so outputs match your true style and quality,
and explicitly ask for a *different* scenario each time to spread coverage.

```python
import json, openai

client = openai.OpenAI()

def generate_synthetic_examples(task_description, seed_examples, n=500, model="gpt-4o"):
    meta_prompt = f"""You are generating training data for an LLM fine-tuned for:
{task_description}

Here are {len(seed_examples)} real examples of the desired behavior:
{json.dumps(seed_examples[:5], indent=2)}

Generate a NEW, diverse example covering a DIFFERENT scenario than the seeds.
Match the quality and style above.

Return JSON: {{"input": "...", "output": "..."}}"""

    examples = []
    for _ in range(n):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": meta_prompt}],
            response_format={"type": "json_object"},
            temperature=0.9,          # high temp for diversity
        )
        ex = json.loads(response.choices[0].message.content)
        examples.append({"messages": [
            {"role": "user", "content": ex["input"]},
            {"role": "assistant", "content": ex["output"]},
        ]})
    return examples
```

## Diversity levers

Low-diversity synthetic data is the main failure mode — the generator collapses onto a few
templates and the student overfits them. Push variety with:

- **Temperature sweep** — vary 0.7–1.0 across generation batches rather than one fixed value.
- **Multiple generators** — mix GPT / Claude / Gemini to dilute any single model's stylistic
  fingerprint.
- **Stratified seeds** — seed from different categories, difficulty tiers, and formats so each
  region of the input space is represented.
- **Explicit edge/adversarial cases** — name the hard cases in the prompt; models rarely
  invent them unprompted.

After generation, always run the diversity report in
[data-quality.md](data-quality.md) — if `distinct-2` is below ~0.5 you are generating
near-duplicates and should widen the seeds or raise temperature before scaling up. Then dedup
(MinHash) as usual, since high-temperature generation still produces collisions.
