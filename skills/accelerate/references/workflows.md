# Accelerate Common Workflows

Detailed, copy-pasteable workflows. SKILL.md holds the 4-line quick start; this file holds the full recipes.

## Workflow 1: From single GPU to multi-GPU

**Original script**:
```python
# train.py
import torch

model = torch.nn.Linear(10, 2).to('cuda')
optimizer = torch.optim.Adam(model.parameters())
dataloader = torch.utils.data.DataLoader(dataset, batch_size=32)

for epoch in range(10):
    for batch in dataloader:
        batch = batch.to('cuda')
        optimizer.zero_grad()
        loss = model(batch).mean()
        loss.backward()
        optimizer.step()
```

**With Accelerate** (4 lines added):
```python
# train.py
import torch
from accelerate import Accelerator  # +1

accelerator = Accelerator()  # +2

model = torch.nn.Linear(10, 2)
optimizer = torch.optim.Adam(model.parameters())
dataloader = torch.utils.data.DataLoader(dataset, batch_size=32)

model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)  # +3

for epoch in range(10):
    for batch in dataloader:
        # No .to('cuda') needed - automatic!
        optimizer.zero_grad()
        loss = model(batch).mean()
        accelerator.backward(loss)  # +4
        optimizer.step()
```

**Configure** (interactive):
```bash
accelerate config
```

**Questions**:
- Which machine? (single/multi GPU/TPU/CPU)
- How many machines? (1)
- Mixed precision? (no/fp16/bf16/fp8)
- DeepSpeed? (no/yes)

**Launch** (works on any setup):
```bash
# Single GPU
accelerate launch train.py

# Multi-GPU (8 GPUs)
accelerate launch --multi_gpu --num_processes 8 train.py

# Multi-node
accelerate launch --multi_gpu --num_processes 16 \
  --num_machines 2 --machine_rank 0 \
  --main_process_ip $MASTER_ADDR \
  train.py
```

## Workflow 2: Mixed precision training

**Enable FP16/BF16**:
```python
from accelerate import Accelerator

# FP16 (with gradient scaling)
accelerator = Accelerator(mixed_precision='fp16')

# BF16 (no scaling, more stable)
accelerator = Accelerator(mixed_precision='bf16')

# FP8 (H100+)
accelerator = Accelerator(mixed_precision='fp8')

model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)

# Everything else is automatic!
for batch in dataloader:
    with accelerator.autocast():  # Optional, done automatically
        loss = model(batch)
    accelerator.backward(loss)
```

## Workflow 3: DeepSpeed ZeRO integration

**Enable DeepSpeed ZeRO-2**:
```python
from accelerate import Accelerator
from accelerate.utils import DeepSpeedPlugin

accelerator = Accelerator(
    mixed_precision='bf16',
    deepspeed_plugin=DeepSpeedPlugin(
        zero_stage=2,  # ZeRO-2
        offload_optimizer_device="none",
        gradient_accumulation_steps=4,
    ),
)

# Same code as before!
model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)
```

**Or via config**:
```bash
accelerate config
# Select: DeepSpeed → ZeRO-2
```

**deepspeed_config.json**:
```json
{
    "fp16": {"enabled": false},
    "bf16": {"enabled": true},
    "zero_optimization": {
        "stage": 2,
        "offload_optimizer": {"device": "cpu"},
        "allgather_bucket_size": 5e8,
        "reduce_bucket_size": 5e8
    }
}
```

**Launch** (point `--config_file` at an `accelerate config` YAML that references the DeepSpeed JSON, or pass the DeepSpeed JSON via the plugin):
```bash
accelerate launch --config_file accelerate_config.yaml train.py
```

## Workflow 4: FSDP (Fully Sharded Data Parallel)

**Enable FSDP**:
```python
from accelerate import Accelerator, FullyShardedDataParallelPlugin

fsdp_plugin = FullyShardedDataParallelPlugin(
    sharding_strategy="FULL_SHARD",  # ZeRO-3 equivalent
    auto_wrap_policy="TRANSFORMER_BASED_WRAP",
    cpu_offload=False,
)

accelerator = Accelerator(
    mixed_precision='bf16',
    fsdp_plugin=fsdp_plugin,
)

model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)
```

**Or via config**:
```bash
accelerate config
# Select: FSDP → Full Shard → No CPU Offload
```

## Workflow 5: Gradient accumulation

**Accumulate gradients**:
```python
from accelerate import Accelerator

accelerator = Accelerator(gradient_accumulation_steps=4)

model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)

for batch in dataloader:
    with accelerator.accumulate(model):  # Handles accumulation
        optimizer.zero_grad()
        loss = model(batch)
        accelerator.backward(loss)
        optimizer.step()
```

**Effective batch size**: `batch_size * num_gpus * gradient_accumulation_steps`

## Common issues

**Wrong device placement** — don't manually move to device:
```python
# WRONG
batch = batch.to('cuda')
# CORRECT: Accelerate handles it automatically after prepare()
```

**Gradient accumulation not working** — use the context manager:
```python
with accelerator.accumulate(model):
    optimizer.zero_grad()
    accelerator.backward(loss)
    optimizer.step()
```

**Checkpointing in distributed** — use accelerator methods:
```python
if accelerator.is_main_process:
    accelerator.save_state('checkpoint/')
accelerator.load_state('checkpoint/')  # load on all processes
```

**Different results with FSDP** — fix the seed across processes:
```python
from accelerate.utils import set_seed
set_seed(42)
```
