# FSDP2 (`fully_shard`) API

FSDP2 is the second-generation, per-parameter-sharded API. Each sharded parameter
becomes a `DTensor` (sharded on dim 0 across the mesh), so there is no opaque flat
parameter, optimizer state is per-parameter, and it composes cleanly with tensor
parallelism and `torch.compile`.

## Import path (version-sensitive)

`fully_shard` and its policy classes lived under `torch.distributed._composable.fsdp`
through roughly PyTorch 2.4–2.5 and were promoted toward the public
`torch.distributed.fsdp` namespace in later releases. Check your installed version:

```python
# PyTorch ~2.4–2.5
from torch.distributed._composable.fsdp import (
    fully_shard, MixedPrecisionPolicy, CPUOffloadPolicy, OffloadPolicy, FSDPModule,
)
# Newer PyTorch may also expose these from torch.distributed.fsdp — verify with your
# version rather than assuming. `python -c "import torch; print(torch.__version__)"`.
```

Do not guess the path; import-test it in the target environment.

## Core call

`fully_shard(module, *, mesh=None, reshard_after_forward=True, mp_policy=..., offload_policy=...)`

Unlike FSDP1, `fully_shard` **mutates the module in place** and returns it (the module
gains `FSDPModule` methods). Apply it **bottom-up**: shard each transformer block
first, then the root module last.

```python
import torch
from torch.distributed.device_mesh import init_device_mesh

mesh = init_device_mesh("cuda", (dist.get_world_size(),))

mp = MixedPrecisionPolicy(param_dtype=torch.bfloat16, reduce_dtype=torch.float32)

for block in model.layers:            # shard each block as its own unit
    fully_shard(block, mesh=mesh, mp_policy=mp, reshard_after_forward=True)
fully_shard(model, mesh=mesh, mp_policy=mp)   # root last

opt = torch.optim.AdamW(model.parameters(), lr=3e-4)  # after sharding
```

### `reshard_after_forward`

- `True` → free the all-gathered params after forward (re-gather in backward). ≈ ZeRO-3
  / `FULL_SHARD`. Lowest memory.
- `False` → keep params resident until backward. ≈ ZeRO-2 / `SHARD_GRAD_OP`. Less comm,
  more memory. Common choice: `False` on the **root/last** block (its params are needed
  immediately in backward), `True` elsewhere.

### `MixedPrecisionPolicy`

Fields: `param_dtype` (compute dtype for params, e.g. `torch.bfloat16`),
`reduce_dtype` (gradient all-reduce dtype — keep `torch.float32` for stability),
`output_dtype`, and `cast_forward_inputs`. Simpler than FSDP1's `MixedPrecision`
because there is no separate buffer sharding.

### `CPUOffloadPolicy` / `OffloadPolicy`

Pass `offload_policy=CPUOffloadPolicy()` to keep sharded params/grads/optimizer state
on host RAM and stream them to GPU on demand. Big memory win, throughput cost. Use only
when you are genuinely param-memory-bound; pin `pin_memory=True` (default) for faster
transfer.

## `FSDPModule` runtime methods

After sharding, the module exposes control methods (call on the module returned by
`fully_shard`):

- `set_requires_gradient_sync(bool)` — turn off the gradient reduce-scatter during
  gradient-accumulation micro-steps; re-enable on the last micro-step. This is the
  FSDP2 replacement for `no_sync()`.
- `set_reshard_after_backward(bool)` — keep params gathered across a backward (used with
  accumulation).
- `set_is_last_backward(bool)` — mark the final backward when multiple backwards run.
- `unshard()` / `reshard()` — manually gather/free (advanced; e.g. custom inference).
- `set_modules_to_forward_prefetch(...)` / `set_modules_to_backward_prefetch(...)` —
  explicit prefetch scheduling to overlap comm with compute.

Gradient accumulation pattern:

```python
for i, micro in enumerate(microbatches):
    is_last = i == len(microbatches) - 1
    model.set_requires_gradient_sync(is_last)   # reduce-scatter only on last
    loss = model(micro).loss / len(microbatches)
    loss.backward()
opt.step(); opt.zero_grad()
```

## DTensor implications

Sharded parameters are `DTensor`s. Consequences:

- Gradient clipping: `torch.nn.utils.clip_grad_norm_` **works** in FSDP2 (it is
  DTensor-aware and reduces across the mesh) — no special `.clip_grad_norm_` method
  needed as in FSDP1.
- To inspect a full tensor, call `param.full_tensor()` (all-gathers) or
  `param.to_local()` (this rank's shard). Don't `.cpu()` a DTensor blindly.
- Custom `.numel()`-based logic must account for local vs global shape.

## 2D / 3D parallelism

Compose with tensor parallelism by building a multi-dim mesh and passing the
data-parallel sub-mesh to `fully_shard` while `parallelize_module` handles the TP dim:

```python
mesh = init_device_mesh("cuda", (dp, tp), mesh_dim_names=("dp", "tp"))
# apply TP on mesh["tp"] with parallelize_module(...), then:
fully_shard(block, mesh=mesh["dp"])
```

For HYBRID_SHARD-style setups, use a 2D `("replicate", "shard")` mesh and pass it to
`fully_shard`; the replicate dim behaves like inter-node replication.

## Meta-device init for huge models

Build on the meta device so no rank ever materializes the full model, then let FSDP2
allocate only each rank's shard:

```python
with torch.device("meta"):
    model = build_model()
for block in model.layers:
    fully_shard(block, mesh=mesh)
fully_shard(model, mesh=mesh)
model.to_empty(device="cuda")     # allocate sharded storage
model.init_weights()              # your own re-init of the now-empty params
```

You must provide a real initialization for the emptied parameters (load a checkpoint or
call your init routine) — `to_empty` leaves them uninitialized.
