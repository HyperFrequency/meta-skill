# FSDP1 (`FullyShardedDataParallel`) API

The original wrapper. Wrapping a submodule flattens its parameters into a single
`FlatParameter` bucket that is all-gathered/freed as one unit.

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
```

## Constructor (the arguments that matter)

```python
FSDP(
    module,
    sharding_strategy=ShardingStrategy.FULL_SHARD,   # ZeRO stage — see SKILL.md table
    auto_wrap_policy=None,                            # wrap boundary; almost always set this
    mixed_precision=None,                            # MixedPrecision(...)
    cpu_offload=None,                                # CPUOffload(offload_params=True)
    backward_prefetch=BackwardPrefetch.BACKWARD_PRE, # overlap next all-gather with current bwd
    forward_prefetch=False,                          # prefetch next unit's all-gather in fwd
    limit_all_gathers=True,                          # rate-limiter to avoid CUDA malloc storms
    sync_module_states=False,                        # broadcast rank0 weights to all ranks at init
    param_init_fn=None,                              # for meta-device init
    device_id=None,                                  # torch.cuda.current_device()
    ignored_modules=None,                            # keep some submodules unsharded
    use_orig_params=False,                           # expose real nn.Parameters (see below)
)
```

### `use_orig_params=True`

Strongly recommended. Without it, FSDP replaces parameters with opaque `FlatParameter`s,
which breaks per-parameter optimizer **param groups**, `torch.compile`, and any code that
iterates real `nn.Parameter`s. With it, `model.parameters()` yields the original
parameters (as views into the flat buffer). Required for weight decay exclusions,
LR groups, and compiling FSDP-wrapped models.

## Auto-wrap policies

Import from `torch.distributed.fsdp.wrap`. The policy decides which submodules become
their own FSDP unit — **wrap each transformer block**.

```python
import functools
from torch.distributed.fsdp.wrap import (
    transformer_auto_wrap_policy, size_based_auto_wrap_policy, ModuleWrapPolicy,
)

# By transformer layer class (preferred for LLMs):
policy = functools.partial(
    transformer_auto_wrap_policy,
    transformer_layer_cls={LlamaDecoderLayer},   # the block class(es) to wrap
)

# Equivalent, newer callable form:
policy = ModuleWrapPolicy({LlamaDecoderLayer})

# By parameter count (generic fallback):
policy = functools.partial(size_based_auto_wrap_policy, min_num_params=1_000_000)
```

Manual wrapping is also possible with `enable_wrap` / `wrap`, but auto-wrap by block
class is the standard for transformers.

## `MixedPrecision`

```python
from torch.distributed.fsdp import MixedPrecision
MixedPrecision(
    param_dtype=torch.bfloat16,     # all-gather + compute dtype
    reduce_dtype=torch.float32,     # gradient reduce-scatter dtype (keep fp32 for stability)
    buffer_dtype=torch.bfloat16,    # e.g. batchnorm/layernorm buffers
    keep_low_precision_grads=False,
    cast_forward_inputs=False,      # auto-cast module inputs to param_dtype
)
```

Prefer **bf16** over fp16 (no loss scaler needed). If you must use fp16, pair with a
`torch.cuda.amp.GradScaler` variant that is FSDP-aware (`ShardedGradScaler` from
`torch.distributed.fsdp.sharded_grad_scaler`).

## `CPUOffload`

```python
from torch.distributed.fsdp import CPUOffload
CPUOffload(offload_params=True)   # params + grads live on CPU, streamed to GPU on demand
```

Large memory savings, meaningful throughput cost. Combine with `FULL_SHARD`.

## `sync_module_states` and initialization order

- If you build the model on **rank 0 only** (e.g. load pretrained weights there) and
  leave other ranks on meta/empty, set `sync_module_states=True` so FSDP broadcasts
  rank-0 weights to all ranks at wrap time. Otherwise every rank must build identical
  weights (same seed) independently.
- Always pass `device_id=torch.cuda.current_device()` so FSDP shards onto the right GPU.

## Meta-device init for models too big to fit on one GPU

```python
with torch.device("meta"):
    model = build_model()

def init_fn(module):
    module.to_empty(device=torch.cuda.current_device(), recurse=False)
    # then re-initialize / load weights for `module`

model = FSDP(model, auto_wrap_policy=policy, param_init_fn=init_fn,
             device_id=torch.cuda.current_device(), sync_module_states=True)
```

`param_init_fn` runs per wrapped unit, so no rank ever holds the whole model densely.

## Activation (gradient) checkpointing

Orthogonal to FSDP and usually essential for large models — recomputes activations in
backward to trade compute for memory. Apply it to the same block class you shard:

```python
from torch.distributed.algorithms._checkpoint.checkpoint_wrapper import (
    checkpoint_wrapper, apply_activation_checkpointing, CheckpointImpl,
)
import functools

non_reentrant = functools.partial(checkpoint_wrapper,
                                  checkpoint_impl=CheckpointImpl.NO_REENTRANT)
apply_activation_checkpointing(
    model,
    checkpoint_wrapper_fn=non_reentrant,
    check_fn=lambda m: isinstance(m, LlamaDecoderLayer),
)
```

Use `NO_REENTRANT` (the modern implementation); reentrant checkpointing has known
interactions with FSDP and complex autograd. Apply activation checkpointing **before**
or in coordination with FSDP wrapping so the boundaries align.

## Gradient clipping

Use FSDP's method, which reduces the norm across shards:

```python
model.clip_grad_norm_(max_norm=1.0)   # NOT torch.nn.utils.clip_grad_norm_
```

(FSDP2 differs — plain `clip_grad_norm_` works there because params are DTensors.)

## `BackwardPrefetch`

- `BACKWARD_PRE` (default) — all-gather the next unit's params *before* computing the
  current unit's gradients. Best overlap, slightly higher peak memory.
- `BACKWARD_POST` — all-gather *after*. Lower memory, less overlap.
- `None` — disable prefetch (debugging / extreme memory pressure).
