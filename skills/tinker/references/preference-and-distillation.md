# Preference Learning & Distillation

## Direct Preference Optimization (DPO)

DPO trains a model to prefer chosen over rejected responses with a classification loss — no separate
reward model.

```bash
python -m tinker_cookbook.recipes.preference.train \
    log_path=/tmp/dpo-experiment model_name=meta-llama/Llama-3.2-1B \
    dataset=hhh renderer_name=role_colon learning_rate=1e-5 dpo_beta=0.1
```

### Parameters

| Parameter | Notes | Recommended |
|-----------|-------|-------------|
| `model_name` | Base model, also the reference policy | 1B–8B to start |
| `dataset` | Preference dataset | `hhh`, `helpsteer3`, `ultrafeedback` |
| `renderer_name` | Match model family | — |
| `learning_rate` | Lower than SFT | 1e-5 to 1e-6 |
| `dpo_beta` | Preference strength | start 0.1 |
| `log_path` | Output dir | required |

Custom datasets: implement `DPODatasetBuilder` from
`tinker_cookbook.preference.preference_datasets`.

### Datasets

| Name | Source | Notes |
|------|--------|-------|
| `hhh` | Anthropic | Helpful-Harmless-Honest pairwise |
| `helpsteer3` | NVIDIA | HelpSteer3 preferences |
| `ultrafeedback` | UltraFeedback | Binarized preferences |

### Metrics

| Metric | Watch |
|--------|-------|
| `dpo_loss` | should decrease |
| `accuracy` | implicit reward-model accuracy — should increase |
| `margin` | chosen − rejected reward gap — should increase |
| `chosen_reward` / `rejected_reward` | up / down |

### Tips

- Start `dpo_beta=0.1`; adjust per dataset.
- Use a lower LR than SFT.
- **The base model must be in-distribution with the preference data.** Run a light SFT phase first or
  collect on-policy preferences; a sharp mismatch produces strange behavior.
- Evaluate with Inspect AI afterward — see [Evaluations](evaluations.md).

## Full RLHF pipeline (SL → preference model → RL)

Implemented in `recipes/preference/rlhf/rlhf_pipeline.py`:

```bash
python -m recipes.preference.rlhf.rlhf_pipeline
```

1. **Train the initial policy (SL)** on instruction data (e.g. `no_robots`), InstructGPT-style.
2. **Train a preference model (SL)** on pairwise comparisons (e.g. HHH) — sees completions A and B,
   predicts which is preferred.
3. **Train the policy via RL** using the preference model as reward: sample multiple completions,
   grade all pairs, reward by win-fraction (self-play).

## Prompt distillation

Train a student to behave as if it received a long teacher prompt — without that prompt at inference.

1. **Teacher generates data:** long detailed prompt + queries → responses.
2. **Student trains** on `(query, response)` pairs **without** the teacher prompt.

```bash
python -m tinker_cookbook.recipes.prompt_distillation.create_data \
    output_file=/tmp/tinker-datasets/prompt_distillation_lang.jsonl
python -m tinker_cookbook.recipes.prompt_distillation.train
```

**Use when:** the system prompt is growing impractically long and being ignored; you need fast
inference without long-context overhead; you're specializing a model to a narrow task distribution.
Teacher and student may be the same model (self-distillation).

## Learning-rate sweep

Find a task-specific optimum by sweeping one order of magnitude around `get_lr()`.

```python
from tinker_cookbook.hyperparam_utils import get_lr
default_lr = get_lr("meta-llama/Llama-3.1-8B")   # ~2.8e-4
```

Launch runs in parallel across `learning_rate ∈ {3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5}` with distinct
`log_path`s, then collect final losses:

```python
from glob import glob
import pandas, json

rows = []
for fname in sorted(glob("/tmp/sweep/*/metrics.jsonl")):
    df = pandas.read_json(fname, lines=True)
    if len(df) == 0 or df["progress"].iloc[-1] < 0.98:
        continue
    cfg = json.load(open(fname.replace("metrics.jsonl", "config.json")))
    rows.append({"learning_rate": cfg["learning_rate"], "final_loss": df["train_mean_nll"].iloc[-1].item()})

df = pandas.DataFrame(rows)
optimal_lr = df["learning_rate"][df["final_loss"].idxmin()]
```

Expect a U-shaped curve with the minimum near the `get_lr()` default.
