---
name: deepspeed
description: >-
  Guidance for memory-efficient distributed training of large models with Microsoft DeepSpeed:
  ZeRO stages 1/2/3 and ZeRO-Infinity CPU/NVMe offload, the deepspeed.initialize engine, the
  ds_config JSON schema, pipeline/tensor parallelism, mixed precision (FP16/BF16/torch.autocast),
  MoE, checkpointing, and the `deepspeed` launcher. Use WHEN the user is configuring or debugging
  DeepSpeed itself — writing a ds_config, choosing a ZeRO stage, fitting a model that does not
  fit in GPU memory, setting up offload, wiring deepspeed.initialize, or running the deepspeed
  launcher. Use WHEN-NOT the goal is plain PyTorch DDP or FSDP without DeepSpeed (use
  pytorch-fsdp2), a high-level Trainer that merely has a DeepSpeed flag (use accelerate or
  pytorch-lightning), Megatron-style 3D parallelism as the primary framework (use megatron-core),
  Ray-orchestrated training (use ray-train), or DeepSpeed-Inference/MII serving rather than training.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [DeepSpeed, Distributed Training, ZeRO, Pipeline Parallelism, Mixed Precision, Offload, MoE, Microsoft]
dependencies: [deepspeed, torch]
---

# DeepSpeed

Router for training large models with [DeepSpeed](https://www.deepspeed.ai/). DeepSpeed wraps a
PyTorch model/optimizer in an engine driven by a single JSON config. Its core value is the **ZeRO**
optimizer-state/gradient/parameter sharding that lets models exceed single-GPU (and single-node)
memory.

## When to Use

Reach for this skill when the task is about DeepSpeed mechanics, specifically:

- Writing or debugging a `ds_config.json` / config dict.
- Picking a **ZeRO stage** (1/2/3) or enabling **ZeRO-Infinity** CPU/NVMe offload to fit a model.
- Wiring `deepspeed.initialize(...)` and converting a training loop to the engine API.
- Pipeline parallelism (`PipelineModule`), tensor parallelism / AutoTP, or MoE layers.
- Mixed precision (`fp16`, `bf16`, `torch_autocast`), gradient accumulation, gradient clipping.
- Checkpointing (`engine.save_checkpoint` / `load_checkpoint`, `zero_to_fp32.py`).
- Launching with `deepspeed --num_gpus ...` or a `hostfile` for multi-node.
- OOM / hang / loss-scale / "untested optimizer" errors under DeepSpeed.

## When NOT to Use (route elsewhere)

- **Plain DDP or FSDP** with no DeepSpeed → `pytorch-fsdp2`.
- **High-level Trainer** where DeepSpeed is just a backend flag → `accelerate` (HF `Accelerator` /
  `Trainer`) or `pytorch-lightning` (`strategy="deepspeed_stage_3"`).
- **Megatron 3D parallelism** as the primary framework → `megatron-core`.
- **Ray-managed** distributed training → `ray-train`.
- **Serving / inference** (DeepSpeed-Inference, DeepSpeed-MII) — this skill is training-focused; see
  `references/mii.md` only for background.

These siblings live alongside this skill under `distributed-training/`.

## Minimal Engine Setup

```python
import deepspeed

# config can be a path or a dict; it is the single source of truth for ZeRO,
# precision, optimizer, scheduler, and batch sizes.
engine, optimizer, _, _ = deepspeed.initialize(
    model=model,
    model_parameters=model.parameters(),
    config=ds_config,           # dict or "ds_config.json"
)

for batch in dataloader:
    loss = engine(batch)        # forward
    engine.backward(loss)       # handles grad accumulation + loss scaling
    engine.step()               # optimizer + scheduler + zero_grad
```

Launch: `deepspeed --num_gpus 8 train.py --deepspeed --deepspeed_config ds_config.json`
(multi-node adds `--hostfile hostfile`). Do not call `loss.backward()`/`optimizer.step()` directly —
the engine owns the step.

## Choosing a ZeRO Stage (decision guide)

| Stage | Shards | Use when |
|-------|--------|----------|
| 0 | nothing (plain DP) | model already fits; baseline |
| 1 | optimizer states | mild memory pressure |
| 2 | + gradients | most common; good speed/memory balance |
| 3 | + parameters | model params don't fit on one GPU |
| Infinity | stage 3 + CPU/NVMe offload | model far exceeds aggregate GPU memory |

Escalate only as far as you must — higher stages add communication overhead. Add
`offload_optimizer`/`offload_param` (`device: cpu` or `nvme`) when even stage 3 OOMs.

## Reference Files

Detailed config schema, verified patterns, and the original documentation scrape live in
`references/` — load on demand, do not inline:

- **`references/config-patterns.md`** — curated, verified `ds_config` snippets: every ZeRO stage,
  offload, fp16/bf16/autocast, optimizer/scheduler, pipeline & AutoTP, gradient checkpointing,
  and the full `zero_optimization` field list. **Start here for configs.**
- **`references/tutorials.md`** — full official tutorials scrape (ZeRO, pipeline, MoE, DeepNVMe,
  1-bit Adam, sparse attention, autotuning). Large; grep for the topic.
- **`references/other.md`** — additional docs (config-json reference pages, API notes).
- **`references/2020.md`, `references/2023.md`, `references/09.md`, `references/08.md`** — DeepSpeed
  blog posts by year (ZeRO-Infinity, MoE, ZeRO++, release notes) — background/perf context.
- **`references/mii.md`** — DeepSpeed-MII / inference background (out of scope for training).
- **`references/assets.md`** — image asset URLs from the docs.

> The dated/numeric reference filenames are an artifact of the doc scrape; `index.md` maps them.

## Common Pitfalls

- **`train_batch_size` mismatch**: it must equal `train_micro_batch_size_per_gpu` ×
  `gradient_accumulation_steps` × world size. Specify any two; let DeepSpeed derive the third.
- **Custom optimizer rejected**: set `"zero_allow_untested_optimizer": true` for non-builtin optimizers.
- **Stage-3 checkpoint is sharded**: to get a single fp32 state_dict, set
  `"stage3_gather_16bit_weights_on_model_save": true` or post-process with `zero_to_fp32.py`.
- **NaN loss with fp16**: tune `fp16.loss_scale` / `initial_scale_power`, or prefer `bf16` on Ampere+.
- **Offload is slow**: NVMe offload needs the `async_io` op built (`ds_report` to verify);
  pin memory and size `nvme` buffers.
- Always run `ds_report` to confirm which C++/CUDA ops compiled before debugging perf.
