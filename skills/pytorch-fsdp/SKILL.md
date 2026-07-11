---
name: pytorch-fsdp
version: 0.1.0
description: >-
  Shard a PyTorch model's parameters, gradients, and optimizer states across
  data-parallel ranks with Fully Sharded Data Parallel (FSDP1 and FSDP2) to train
  models too large for one GPU. Use when a model or its optimizer states OOM under
  DDP, when scaling billion-parameter training across many GPUs/nodes, or when you
  need ZeRO-style sharding, mixed precision, CPU offload, activation checkpointing,
  or sharded/distributed checkpoints in native PyTorch. Covers choosing FSDP1 vs
  FSDP2 (fully_shard), auto-wrap policies, HYBRID_SHARD, meta-device init, and
  save/load. Do NOT use when the model already fits comfortably under DDP (use plain
  DDP), for pipeline/tensor parallelism alone (use those directly), for TPU/JAX, or
  when a higher-level trainer already manages sharding — configure it via
  `pytorch-lightning` or `transformers` instead of hand-wiring FSDP.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "PyTorch BSD-3-Clause"
---

# PyTorch FSDP

## Overview

Fully Sharded Data Parallel (FSDP) is PyTorch's native ZeRO-style data
parallelism. Instead of replicating the full model on every rank (as DDP does),
FSDP **shards** parameters, gradients, and optimizer states across the data-parallel
group. Each rank stores only a slice; a layer's full parameters are reconstructed
just-in-time via an all-gather before its forward/backward, then freed again. This
cuts per-GPU memory roughly by the world size, at the cost of extra communication.

Two generations exist:

- **FSDP1** — `torch.distributed.fsdp.FullyShardedDataParallel` (the `FSDP` wrapper).
  Mature, wraps whole submodule subtrees into flat parameter buckets.
- **FSDP2** — `fully_shard(...)`, a per-parameter-sharded rewrite built on `DTensor`.
  Cleaner composition with tensor parallelism / `torch.compile`, per-parameter
  optimizer state, simpler mixed precision, no flat-parameter footguns. Prefer it on
  recent PyTorch (roughly 2.4+; API stabilized through 2.6/2.7). See
  [references/fsdp2-api.md](references/fsdp2-api.md).

This skill covers choosing a sharding strategy, wrapping the model correctly,
mixed precision, offload, initializing models too big for one GPU, and
checkpointing. It is scoped to native PyTorch FSDP, not the trainers that wrap it.

## When to Use This Skill

Use FSDP when:

- A model, its gradients, or (most often) its **optimizer states** OOM under DDP —
  Adam alone needs ~12 bytes/param in fp32 (2 moments + master weights).
- You are training a **billion-parameter+** model across multiple GPUs or nodes.
- You want **ZeRO-2 / ZeRO-3** sharding in pure PyTorch without DeepSpeed.
- You need mixed precision, CPU offload, activation checkpointing, or
  sharded/distributed checkpoints wired into data-parallel training.
- You are on a single multi-GPU node and want the memory headroom of sharding.

## When NOT to Use This Skill

- **The model fits comfortably under DDP** — DDP has less communication overhead
  and simpler semantics. Only reach for FSDP when memory is the constraint.
- You need **pipeline or tensor parallelism by itself** — use `torch.distributed.pipelining`
  or `DTensor`/`parallelize_module` directly. (FSDP composes *with* TP in 2D/3D
  parallel setups — see [references/fsdp2-api.md](references/fsdp2-api.md) — but is
  not a substitute for them.)
- You are on **TPU or JAX** — this is CUDA/NCCL-oriented (Gloo CPU works but is slow).
- A **higher-level trainer already manages sharding** — do not hand-wire FSDP under
  it. Configure the `pytorch-lightning` `FSDPStrategy` or the HuggingFace
  `transformers` / `accelerate` FSDP plugin instead, and use this skill to reason
  about the *settings* they expose.
- You want DeepSpeed ZeRO specifically (different ecosystem, own offload engine).

## Core Concepts

**Sharding strategy = ZeRO stage.** Pick based on the memory/communication tradeoff:

| Strategy (FSDP1)            | Shards                          | ZeRO | Notes |
| --------------------------- | ------------------------------- | ---- | ----- |
| `FULL_SHARD`                | params + grads + optimizer      | 3    | Max memory savings; all-gather in both fwd and bwd. Default choice. |
| `SHARD_GRAD_OP`             | grads + optimizer (params kept) | 2    | Less comm; params stay resident after forward. |
| `HYBRID_SHARD`              | full-shard within node, replicate across | 3 intra | Cuts inter-node traffic on multi-node runs. |
| `_HYBRID_SHARD_ZERO2`       | shard-grad-op intra, replicate across | 2 intra | Hybrid variant of ZeRO-2. |
| `NO_SHARD`                  | nothing (DDP-like)              | 0    | Deprecated; use DDP. |

In **FSDP2** the equivalent knob is `reshard_after_forward`: `True` ≈ FULL_SHARD,
`False` ≈ SHARD_GRAD_OP, and hybrid sharding is expressed via a 2D `DeviceMesh`.

**Wrapping granularity is the key decision.** FSDP shards at wrap boundaries: the
whole wrapped unit's parameters are all-gathered together. Wrap **each transformer
block** as its own unit so only one block is materialized at a time. Wrapping the
whole model as one unit defeats the purpose (peak memory ≈ full model). Under-wrapping
(too many tiny units) adds all-gather latency. See auto-wrap policies in
[references/fsdp1-api.md](references/fsdp1-api.md).

## Minimal Setup

Every FSDP run is a distributed program. Launch with `torchrun`:

```bash
# single node, 8 GPUs
torchrun --standalone --nproc_per_node=8 train.py
# multi-node
torchrun --nnodes=2 --node_rank=$RANK --nproc_per_node=8 \
         --rdzv_backend=c10d --rdzv_endpoint=$MASTER:29500 train.py
```

Skeleton (FSDP1):

```python
import torch, torch.distributed as dist
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import ShardingStrategy, MixedPrecision

dist.init_process_group("nccl")
rank = dist.get_rank()
torch.cuda.set_device(rank % torch.cuda.device_count())

model = build_model()  # on CPU or meta device
model = FSDP(
    model,
    sharding_strategy=ShardingStrategy.FULL_SHARD,
    auto_wrap_policy=my_transformer_policy,      # wrap each block — see references
    mixed_precision=MixedPrecision(param_dtype=torch.bfloat16,
                                   reduce_dtype=torch.float32),
    device_id=torch.cuda.current_device(),
    use_orig_params=True,                        # needed for param groups / compile
)
opt = torch.optim.AdamW(model.parameters(), lr=3e-4)  # create AFTER wrapping
```

Two rules that bite everyone: **create the optimizer *after* FSDP-wrapping** (it must
see the sharded `FlatParameter`s / DTensors), and **wrap at the transformer-block
level** via an auto-wrap policy.

## Capabilities → References

Deep API detail, exact constructor arguments, and worked examples live in references:

- **FSDP2 (`fully_shard`)** — per-parameter sharding, `MixedPrecisionPolicy`,
  `CPUOffloadPolicy`, `reshard_after_forward`, DTensor params, gradient-accumulation
  toggles, 2D parallel with a `DeviceMesh`:
  [references/fsdp2-api.md](references/fsdp2-api.md)
- **FSDP1 API** — full `FullyShardedDataParallel` constructor, auto-wrap policies
  (`transformer_auto_wrap_policy`, `size_based_auto_wrap_policy`, `ModuleWrapPolicy`),
  `MixedPrecision`, `CPUOffload`, `BackwardPrefetch`, `sync_module_states`,
  activation checkpointing, meta-device init for huge models:
  [references/fsdp1-api.md](references/fsdp1-api.md)
- **Checkpointing** — `StateDictType` (FULL / SHARDED / LOCAL), rank0-only full
  save, Distributed Checkpoint (`torch.distributed.checkpoint` / DCP) for
  resharding-tolerant save/load, optimizer state, FSDP2 checkpointing:
  [references/checkpointing.md](references/checkpointing.md)
- **Troubleshooting & tuning** — OOM, NCCL hangs and mismatched collectives, slow
  throughput, `find_unused_parameters` analogs, prefetch/limit_all_gathers, gradient
  clipping under sharding, common tracebacks:
  [references/troubleshooting.md](references/troubleshooting.md)

## Common Pitfalls (quick)

- **OOM on wrap** → wrapping the whole model as one unit; add a block-level auto-wrap
  policy. **OOM during step** → optimizer states aren't sharded; use `FULL_SHARD`, not
  `SHARD_GRAD_OP` or `NO_SHARD`.
- **Hang at first collective** → ranks took different control-flow paths, or one rank
  built a different module tree; all ranks must call the same collectives in the same
  order. Set `TORCH_NCCL_ASYNC_ERROR_HANDLING=1` to surface it.
- **`grad clip` errors / wrong norms** → use `model.clip_grad_norm_(...)` (FSDP1) which
  reduces across shards, not `torch.nn.utils.clip_grad_norm_` on local params.
- **Loading a full checkpoint everywhere blows host RAM** → use `rank0_only=True` +
  `offload_to_cpu=True`, or DCP sharded checkpoints. See
  [references/checkpointing.md](references/checkpointing.md).

For higher-level orchestration that sits on top of FSDP, see the `pytorch-lightning`
and `transformers` skills.
