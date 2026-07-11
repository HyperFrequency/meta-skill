# Tinker Pricing Reference

All rates are in **USD per million tokens**.

> **Snapshot as of January 5, 2026.** Prices change without notice — re-verify
> against the live pricing page before quoting or spending, and update the
> `MODELS` table in `scripts/estimate_tinker_cost.py` to match.
>
> Source: https://thinkingmachines.ai/tinker/

## The three rate categories

| Category    | Meaning                                          | Used by this skill? |
| ----------- | ------------------------------------------------ | ------------------- |
| **Prefill** | Processing input context (inference)             | No — inference only |
| **Sample**  | Generating output tokens (inference)             | No — inference only |
| **Train**   | Training / fine-tuning tokens                    | **Yes**             |

The cost estimator multiplies dataset tokens × epochs × the **Train** rate.
Prefill and Sample are listed so you can separately reason about serving the
fine-tuned model later.

## Qwen models

| Model                         | Prefill | Sample | Train |
| ----------------------------- | ------- | ------ | ----- |
| Qwen3-4B-Instruct-2507        | $0.07   | $0.22  | $0.22 |
| Qwen3-8B                      | $0.13   | $0.40  | $0.40 |
| Qwen3-30B-A3B                 | $0.12   | $0.30  | $0.36 |
| Qwen3-VL-30B-A3B-Instruct     | $0.18   | $0.44  | $0.53 |
| Qwen3-32B                     | $0.49   | $1.47  | $1.47 |
| Qwen3-235B-Instruct-2507      | $0.68   | $1.70  | $2.04 |
| Qwen3-VL-235B-A22B-Instruct   | $1.02   | $2.56  | $3.07 |

## Llama models

| Model         | Prefill | Sample | Train |
| ------------- | ------- | ------ | ----- |
| Llama-3.2-1B  | $0.03   | $0.09  | $0.09 |
| Llama-3.2-3B  | $0.06   | $0.18  | $0.18 |
| Llama-3.1-8B  | $0.13   | $0.40  | $0.40 |
| Llama-3.1-70B | $1.05   | $3.16  | $3.16 |

## DeepSeek models

| Model        | Prefill | Sample | Train |
| ------------ | ------- | ------ | ----- |
| DeepSeek-V3.1 | $1.13  | $2.81  | $3.38 |

## GPT-OSS models

| Model       | Prefill | Sample | Train |
| ----------- | ------- | ------ | ----- |
| GPT-OSS-120B | $0.18  | $0.44  | $0.52 |
| GPT-OSS-20B  | $0.12  | $0.30  | $0.36 |

## Moonshot models

| Model            | Prefill | Sample | Train |
| ---------------- | ------- | ------ | ----- |
| Kimi-K2-Thinking | $0.98   | $2.44  | $2.93 |

## Worked cost examples

Formula: `training_cost = dataset_tokens × epochs × train_rate / 1_000_000`.

**Qwen3-8B, 1M tokens, 3 epochs**
```
training_tokens = 1,000,000 × 3 = 3,000,000
cost = 3.0M × $0.40/M = $1.20
```

**Llama-3.1-70B, 5M tokens, 2 epochs**
```
training_tokens = 5,000,000 × 2 = 10,000,000
cost = 10.0M × $3.16/M = $31.60
```

**Qwen3-235B-Instruct-2507, 2M tokens, 4 epochs**
```
training_tokens = 2,000,000 × 4 = 8,000,000
cost = 8.0M × $2.04/M = $16.32
```

## Refreshing the table

When Tinker updates pricing:

1. Read the current rates from the source URL above.
2. Edit the `MODELS` dict in `scripts/estimate_tinker_cost.py` — the `prefill`,
   `sample`, and `train` fields per model.
3. Update the snapshot date at the top of this file.
