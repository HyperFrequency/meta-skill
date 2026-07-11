# Fireworks AI — Fine-Tuning

Fireworks offers three managed fine-tuning methods, all producing LoRA adapters
by default:

- **SFT** — Supervised Fine-Tuning on instruction/response data.
- **DPO** — Direct Preference Optimization on chosen/rejected pairs.
- **RL** — Reinforcement Fine-Tuning against a reward model or reward function
  (runs on on-demand GPUs, billed at GPU-hour rates).

Two ways to launch a job: the `firectl` CLI (more stable, recommended — see
[integration-and-troubleshooting.md](integration-and-troubleshooting.md)) or the
control-plane REST API. The REST paths below live under
`https://api.fireworks.ai/v1/accounts/{account_id}/...`; **confirm exact
endpoint names and payload fields against https://docs.fireworks.ai/api-reference
before scripting** — control-plane shapes have changed over releases.

Shared REST headers:

```python
import os, requests
headers = {
    "Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}",
    "Content-Type": "application/json",
}
```

## SFT — Supervised Fine-Tuning

Data format (JSONL) — one conversation per line under a `messages` array:

```json
{"messages": [{"role": "system", "content": "You are a coding assistant."}, {"role": "user", "content": "Write a Python hello world."}, {"role": "assistant", "content": "print('Hello, world!')"}]}
{"messages": [{"role": "user", "content": "What is 2+2?"}, {"role": "assistant", "content": "4"}]}
```

Create the job (REST):

```python
url = "https://api.fireworks.ai/v1/accounts/{account_id}/supervisedFineTuningJobs"
payload = {
    "displayName": "my-sft-job",
    "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "dataset": "accounts/{account_id}/datasets/{dataset_id}",
    "hyperparameters": {
        "epochs": 3,
        "learning_rate": 1e-4,
        "batch_size": 8,
        "lora_rank": 16,
    },
}
job = requests.post(url, headers=headers, json=payload).json()
print(f"Job: {job['name']}")
```

Monitor:

```python
status = requests.get(f"https://api.fireworks.ai/v1/{job['name']}", headers=headers).json()
print(f"State: {status['state']}, Progress: {status.get('progress', 'N/A')}")
```

## DPO — Direct Preference Optimization

Data format (JSONL) — each line pairs a `chosen` and a `rejected` conversation:

```json
{"chosen": [{"role": "user", "content": "Explain ML"}, {"role": "assistant", "content": "Machine learning is..."}], "rejected": [{"role": "user", "content": "Explain ML"}, {"role": "assistant", "content": "ML is complicated..."}]}
```

Create the job:

```python
url = "https://api.fireworks.ai/v1/accounts/{account_id}/dpoFineTuningJobs"
payload = {
    "displayName": "my-dpo-job",
    "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "dataset": "accounts/{account_id}/datasets/{dataset_id}",
    "hyperparameters": {"epochs": 2, "learning_rate": 5e-5, "beta": 0.1},
}
requests.post(url, headers=headers, json=payload)
```

`beta` is the DPO temperature — lower keeps the tuned policy closer to the
reference model.

## RL — Reinforcement Fine-Tuning

Optimizes the base model against a reward model (or reward function). Because it
schedules on-demand GPUs, expect GPU-hour billing rather than a flat tuning fee.

```python
url = "https://api.fireworks.ai/v1/accounts/{account_id}/reinforcementFineTuningJobs"
payload = {
    "displayName": "my-rl-job",
    "baseModel": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "rewardModel": "accounts/{account_id}/models/{reward_model_id}",
    "dataset": "accounts/{account_id}/datasets/{dataset_id}",
}
requests.post(url, headers=headers, json=payload)
```

## Pricing (approximate)

Per training-GPU-hour; verify at https://fireworks.ai/pricing.

| Base model size | SFT ($/hr) | DPO ($/hr) |
|-----------------|-----------|-----------|
| Up to 16B  | 0.50  | 1.00  |
| 16B – 80B  | 3.00  | 6.00  |
| 80B – 300B | 6.00  | 12.00 |
| 300B+      | 10.00 | 20.00 |

RL fine-tuning is billed at on-demand GPU rates (see
[deployments.md](deployments.md) for GPU/hr figures).

## After training

A finished job yields a fine-tuned model (a LoRA adapter over the base). Serve
it serverless by its model ID, or attach it to an on-demand deployment for
predictable latency — see [deployments.md](deployments.md). Query it through the
same OpenAI-compatible `chat.completions` call, passing the fine-tuned model ID.

## Failure modes

- **Job stuck / rejected**: dataset does not match the expected JSONL schema for
  the method (SFT `messages`, DPO `chosen`/`rejected`). Inspect with
  `firectl fine-tuning-job get <id>`.
- **Wrong method for the data**: preference pairs require DPO, not SFT.
- **RL cost surprise**: RL bills GPU-hours, not the flat SFT/DPO table — budget
  accordingly.
