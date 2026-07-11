# Statistics and Preference Data Reference

## Bootstrap confidence interval on a win rate

A raw win rate hides its uncertainty. Resample under the observed rate to get a
confidence interval, and only act when the interval clears 50%.

```python
import numpy as np

def bootstrap_win_rate(wins, total, n_bootstrap=10000, ci=0.95):
    win_rate = wins / total
    samples = np.random.binomial(total, win_rate, n_bootstrap) / total
    alpha = (1 - ci) / 2
    lower = np.percentile(samples, alpha * 100)
    upper = np.percentile(samples, (1 - alpha) * 100)
    return {
        "win_rate": win_rate,
        "ci_lower": lower,
        "ci_upper": upper,
        # Significantly different from a coin flip in either direction.
        "significant": lower > 0.5 or upper < 0.5,
    }
```

Ties complicate the denominator. Two conventions: (a) drop ties and compute the win
rate over decisive comparisons only, or (b) count a tie as half a win for each side.
Pick one and report it — they answer slightly different questions.

## Minimum sample size

| Desired precision | Minimum samples | Notes |
|-------------------|-----------------|-------|
| Directional (which is better) | 50-100 | Rough signal only |
| Reliable estimate (±5%) | 200-400 | Standard evaluation |
| High confidence (±2%) | 500-1000 | Production decisions |
| Publication quality | 1000+ | Statistical rigor |

**Rule of thumb**: at least 100 examples for a deployment call, 200+ for a win rate
you will quote. Underpowered evals produce win rates that flip sign on re-run.

## Generating preference data for DPO/RLHF

Each decisive pairwise comparison is a training pair: the winning response is
`chosen`, the loser is `rejected`. Discard ties (they carry no preference signal).

```python
def generate_dpo_pairs(eval_set, model_a_fn, model_b_fn, task_description, criteria,
                       judge_model="gpt-4o"):
    """Emit {"prompt", "chosen", "rejected"} records from pairwise judgments.

    Reuses pairwise_compare (with position-swap mitigation) from
    references/pairwise-comparison.md.
    """
    pairs = []
    for example in eval_set:
        resp_a = model_a_fn(example["input"])
        resp_b = model_b_fn(example["input"])
        winner = pairwise_compare(example["input"], resp_a, resp_b,
                                  task_description, criteria, judge_model)
        if winner == "tie":
            continue
        chosen = resp_a if winner == "A" else resp_b
        rejected = resp_b if winner == "A" else resp_a
        pairs.append({"prompt": example["input"], "chosen": chosen, "rejected": rejected})
    print(f"Generated {len(pairs)} DPO pairs from {len(eval_set)} examples "
          f"({len(eval_set) - len(pairs)} ties skipped)")
    return pairs
```

Quality notes for preference data:

- **High tie rate wastes labels** — if >30% of comparisons tie, sharpen the rubric
  (see the tie-rate table in references/pairwise-comparison.md) before generating
  at scale.
- **Keep the judge frozen** — a judge that drifts mid-run produces inconsistent
  preferences that confuse DPO training.
- **Guard against reward hacking** — if the judge rewards length or format, the
  model you train on these pairs will learn exactly that. Fix the bias in the judge
  first (see the bias pitfalls section) or the preference data bakes it in.
- **For >2 candidates or higher-stakes labels**, aggregate multiple judges via
  `judge-panel` instead of a single model, then export the panel's verdict as the
  preference label.
