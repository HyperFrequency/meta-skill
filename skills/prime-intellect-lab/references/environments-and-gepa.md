# Custom Environments and GEPA

## Building environments with `verifiers`

```bash
pip install verifiers
```

An environment supplies three things the platform needs: a **dataset** of
prompts, an optional **harness** for how rollouts execute (single-turn,
multi-turn tool loop, sandboxed code), and a **rubric** — one or more reward
functions that map a completion to a scalar in `[0.0, 1.0]`. The rubric is the
heart of a verifiable-reward setup: it must return a *dense enough* signal that
GRPO can climb it.

The `verifiers` package exposes environment base types (single-turn,
multi-turn, tool-use), a `Rubric` for composing reward functions, and dataset
adapters. **Confirm the exact class and function names against the installed
version** (`pip show verifiers`, the package README) before writing code — the
API has changed across releases, so treat the sketch below as the *shape* of a
custom environment, not a frozen signature.

```python
# Illustrative shape — verify names against the installed `verifiers` version.
# The load-time contract: return an environment whose rubric scores each
# completion against a reference answer.

from datasets import load_dataset

def build_dataset():
    ds = load_dataset("openai/gsm8k", "main", split="train")
    return [{"prompt": ex["question"], "reference": ex["answer"]} for ex in ds]

def exact_numeric_match(completion: str, reference: str) -> float:
    """Reward = 1.0 iff the parsed final answer matches the reference."""
    try:
        pred = float(completion.strip().split("####")[-1].strip())
        gold = float(reference.strip().split("####")[-1].strip())
        return 1.0 if abs(pred - gold) < 1e-6 else 0.0
    except (ValueError, IndexError):
        return 0.0
```

Wrap `build_dataset` and `exact_numeric_match` into a `verifiers` environment
(the package's single-turn env + `Rubric` pattern), then register and reference
it by `owner/name`:

```bash
prime env install ./environments/my_math_env.py
```

```toml
[[env]]
id = "my-org/math-problems"
```

### Rubric design tips

- Return partial credit where you can (format bonus, step-match) so early
  training has gradient before the model can solve the full task.
- Guard every parse with `try/except` and return `0.0` on failure — a rubric that
  raises will stall or crash rollouts.
- Test the rubric in isolation with a small `prime eval run` before committing a
  training run to it.

## GEPA — gradient-free prompt optimization

GEPA (Genetic-Pareto) refines an environment's **system prompt** without any
gradient training. Use it when the base model is capable but under-prompted, or
as a cheap first pass before spending on RL.

```bash
prime gepa run configs/gepa/base.toml
```

```toml
environment = "primeintellect/wordle"
model = "Qwen/Qwen3-30B-Instruct-2507"
teacher_model = "Qwen/Qwen3-235B-Instruct-2507"
generations = 10
population_size = 8
n_eval_samples = 50
```

How it works:

1. Evaluate the current system prompt against the environment.
2. A stronger **teacher model** reflects on the failures and proposes improved
   prompts.
3. A genetic algorithm evolves a population of prompt variants.
4. Pareto-optimal prompts are kept across the scored objectives.
5. The best prompt is saved after `generations` rounds.

Because GEPA spends inference (rollouts + a teacher pass per generation) rather
than training compute, cost scales with `generations × population_size ×
n_eval_samples` — keep those modest on the first pass.

## Lab agent-workflow skills

`prime lab setup` also scaffolds bundled workflow skills under `.prime/skills/`
(ideation, environment creation, browsing, review, eval, training, GEPA). These
are Prime Intellect's own agent-facing helpers for the workspace; they are
optional scaffolding, not a dependency of the training commands above.
