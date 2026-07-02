# torchforge Workflows

Step-by-step recipes for common torchforge tasks. For class/config APIs see
`api-reference.md`; for error fixes see `troubleshooting.md`.

## Workflow 1: GRPO Training for Math Reasoning

Use for training reasoning models with group-relative advantages.

### Prerequisites Checklist
- [ ] 3+ GPUs (GPU0: trainer, GPU1: ref_model, GPU2: generator)
- [ ] Model from HuggingFace Hub
- [ ] Training dataset (GSM8K, MATH, etc.)

### Step 1: Create Configuration

```yaml
# config/grpo_math.yaml
model: "Qwen/Qwen2.5-7B-Instruct"

dataset:
  path: "openai/gsm8k"
  split: "train"
  streaming: true

training:
  batch_size: 4
  learning_rate: 1e-6
  seq_len: 4096
  dtype: bfloat16
  gradient_accumulation_steps: 4

grpo:
  n_samples: 8           # Responses per prompt
  clip_low: 0.2
  clip_high: 0.28
  beta: 0.1              # KL penalty coefficient
  temperature: 0.7

services:
  generator:
    procs: 1
    num_replicas: 1
    with_gpus: true
  trainer:
    procs: 1
    num_replicas: 1
    with_gpus: true
  ref_model:
    procs: 1
    num_replicas: 1
    with_gpus: true
```

### Step 2: Define Reward Function

```python
# rewards.py
# Reward functions are in forge.data.rewards
from forge.data.rewards import MathReward, ThinkingReward
import re

# Or define your own reward function
class CustomMathReward:
    def __call__(self, prompt: str, response: str, target: str) -> float:
        # Extract answer from response
        match = re.search(r'\\boxed{([^}]+)}', response)
        if not match:
            return 0.0

        answer = match.group(1).strip()
        return 1.0 if answer == target else 0.0
```

### Step 3: Launch Training

```bash
python -m apps.grpo.main --config config/grpo_math.yaml
```

### Step 4: Monitor Progress
- [ ] Check W&B dashboard for loss curves
- [ ] Verify entropy is decreasing (policy becoming more deterministic)
- [ ] Monitor KL divergence (should stay bounded)

## Workflow 2: Custom Loss Function

Use to implement new RL algorithms.

### Step 1: Create Loss Class

```python
# src/forge/losses/custom_loss.py
import torch
import torch.nn as nn

class CustomLoss(nn.Module):
    def __init__(self, clip_range: float = 0.2, beta: float = 0.1):
        super().__init__()
        self.clip_range = clip_range
        self.beta = beta

    def forward(
        self,
        logprobs: torch.Tensor,
        ref_logprobs: torch.Tensor,
        advantages: torch.Tensor,
        padding_mask: torch.Tensor,
    ) -> torch.Tensor:
        # Compute importance ratio
        ratio = torch.exp(logprobs - ref_logprobs)

        # Clipped policy gradient
        clipped_ratio = torch.clamp(
            ratio,
            1 - self.clip_range,
            1 + self.clip_range
        )
        pg_loss = -torch.min(ratio * advantages, clipped_ratio * advantages)

        # KL penalty
        kl = ref_logprobs - logprobs

        # Apply mask and aggregate
        masked_loss = (pg_loss + self.beta * kl) * padding_mask
        loss = masked_loss.sum() / padding_mask.sum()

        return loss
```

### Step 2: Integrate into Application

```python
# apps/custom/main.py
from forge.losses.custom_loss import CustomLoss

loss_fn = CustomLoss(clip_range=0.2, beta=0.1)

# In training loop
loss = loss_fn(
    logprobs=logprobs,
    ref_logprobs=ref_logprobs,
    advantages=advantages,
    padding_mask=padding_mask,
)
```

## Workflow 3: Multi-GPU Distributed Training

Use for scaling to multiple GPUs or nodes.

### Configuration for Distributed

```yaml
# config/distributed.yaml
model: "meta-llama/Meta-Llama-3.1-8B-Instruct"

parallelism:
  tensor_parallel_degree: 2    # Split model across GPUs
  pipeline_parallel_degree: 1
  data_parallel_shard_degree: 2

services:
  generator:
    procs: 2                   # 2 processes for TP=2
    num_replicas: 1
    with_gpus: true
  trainer:
    procs: 2
    num_replicas: 1
    with_gpus: true
```

### Launch with SLURM

```bash
# Submit job
sbatch --nodes=2 --gpus-per-node=8 run_grpo.sh
```

### Launch Locally (Multi-GPU)

```bash
# 8 GPU setup
python -m apps.grpo.main \
    --config config/distributed.yaml \
    --trainer.procs 4 \
    --generator.procs 4
```

## Built-in Loss Functions

Loss functions live in the `forge.losses` module:

```python
from forge.losses import SimpleGRPOLoss, ReinforceLoss

# SimpleGRPOLoss for GRPO training
loss_fn = SimpleGRPOLoss(beta=0.1)

loss = loss_fn(
    logprobs=logprobs,
    ref_logprobs=ref_logprobs,
    advantages=advantages,
    padding_mask=padding_mask
)

# ReinforceLoss with optional importance ratio clipping
from forge.losses.reinforce_loss import ReinforceLoss
loss_fn = ReinforceLoss(clip_ratio=0.2)
```

Built-in loss families: GRPO, DAPO, CISPO, GSPO, SAPO.

## Training Batch Format

torchforge uses dictionary-based batches for training:

```python
# inputs: list of dicts with torch.Tensor values
inputs = [{"tokens": torch.Tensor}]

# targets: list of dicts with training signals
targets = [{
    "response": torch.Tensor,
    "ref_logprobs": torch.Tensor,
    "advantages": torch.Tensor,
    "padding_mask": torch.Tensor
}]

# train_step returns loss as float
loss = trainer.train_step(inputs, targets)
```
