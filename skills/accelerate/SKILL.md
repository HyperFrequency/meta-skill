---
name: accelerate
description: "HuggingFace Accelerate — the simplest way to add distributed/multi-GPU training to a PyTorch script (~4 lines), with one unified API over DDP, DeepSpeed ZeRO, FSDP, and Megatron plus automatic device placement and mixed precision (FP16/BF16/FP8). Use WHEN you have a plain PyTorch training loop and want it to run unchanged on single-GPU, multi-GPU, multi-node, TPU, or MPS, or want to switch sharding backends via config instead of rewriting code. Do NOT use WHEN you want high-level Trainer abstractions/callbacks (use pytorch-lightning), multi-node job orchestration or HPO (use ray), low-level direct control of ZeRO internals (use deepspeed directly), or a non-PyTorch framework. Triggers - \"accelerate launch\", \"accelerator.prepare\", \"make my training script multi-GPU\", DDP/FSDP/DeepSpeed via Accelerate."
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Distributed Training, HuggingFace, Accelerate, DeepSpeed, FSDP, Mixed Precision, PyTorch, DDP, Unified API, Simple]
dependencies: [accelerate, torch, transformers]
---

# HuggingFace Accelerate - Unified Distributed Training

Router skill. This file is the map; copy-pasteable recipes live in `references/`.

## Quick start

Accelerate turns a single-GPU PyTorch loop into a distributed one with ~4 added lines, then runs anywhere via one launcher.

```bash
pip install accelerate
```

```python
import torch
from accelerate import Accelerator        # 1

accelerator = Accelerator()               # 2

model = torch.nn.Transformer()
optimizer = torch.optim.Adam(model.parameters())
dataloader = torch.utils.data.DataLoader(dataset)

model, optimizer, dataloader = accelerator.prepare(  # 3
    model, optimizer, dataloader)

for batch in dataloader:
    optimizer.zero_grad()
    loss = model(batch)
    accelerator.backward(loss)            # 4 (replaces loss.backward())
    optimizer.step()
```

After `prepare()`, do **not** call `.to(device)` yourself — placement is automatic.

```bash
accelerate config        # one-time interactive setup (hardware, precision, backend)
accelerate launch train.py
```

## Workflows → references/workflows.md

Full, copy-pasteable recipes (originals + diffs, launch commands, configs):

1. Single GPU → multi-GPU / multi-node (`accelerate config`, `accelerate launch`)
2. Mixed precision — `Accelerator(mixed_precision='fp16'|'bf16'|'fp8')`
3. DeepSpeed ZeRO — `DeepSpeedPlugin(zero_stage=...)` or a DeepSpeed JSON
4. FSDP — `FullyShardedDataParallelPlugin(sharding_strategy="FULL_SHARD", ...)`
5. Gradient accumulation — `Accelerator(gradient_accumulation_steps=N)` + `accelerator.accumulate(model)`

Common gotchas (device placement, accumulation context manager, distributed checkpointing with `save_state`/`load_state`, FSDP determinism via `set_seed`) are documented at the end of that file.

## Deeper references

- **Megatron** (tensor / pipeline / sequence parallelism): `references/megatron-integration.md`
- **Custom plugins** and advanced config: `references/custom-plugins.md`
- **Performance** (profiling, memory, throughput tuning): `references/performance.md`

## When to use vs alternatives

**Reach for Accelerate** when you want the smallest diff to make a PyTorch loop distributed, one script that runs on any hardware, or the ability to swap DDP/DeepSpeed/FSDP/Megatron via config rather than code. It is the backbone of HF Transformers, TRL, and PEFT.

**Use a sibling instead** when:
- You want a high-level trainer with callbacks/loggers → `pytorch-lightning`
- You need multi-node job orchestration or hyperparameter search → `ray`
- You need direct, low-level control of ZeRO/offload internals → `deepspeed`
- You want maximum control and minimal abstraction → raw `torch.distributed` DDP

## Hardware & launcher

| Setup | Supported backends |
| --- | --- |
| CPU | works (slow) |
| Single GPU | works |
| Multi-GPU | DDP (default), DeepSpeed, FSDP |
| Multi-node | DDP, DeepSpeed, FSDP, Megatron |
| TPU | supported |
| Apple MPS | supported |

Launcher notes: DDP and FSDP use PyTorch built-ins (FSDP needs PyTorch ≥ 1.12); DeepSpeed needs `pip install deepspeed`; Megatron needs a custom setup (see reference).

## Resources

- Docs: https://huggingface.co/docs/accelerate
- GitHub: https://github.com/huggingface/accelerate
- Latest version: 1.14.0 (verified on PyPI 2026-06)
- Examples: https://github.com/huggingface/accelerate/tree/main/examples
- Used by: HuggingFace Transformers, TRL, PEFT
