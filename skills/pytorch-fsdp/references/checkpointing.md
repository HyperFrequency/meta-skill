# Checkpointing FSDP models

The hard part of FSDP checkpointing is that state is **sharded** across ranks. You must
choose how to materialize it: gather into one full state dict (simple, memory-heavy) or
keep it sharded (scalable, resharding-tolerant). Prefer **Distributed Checkpoint (DCP)**
for anything large or long-running.

## FSDP1: `StateDictType`

Wrap `state_dict()` / `load_state_dict()` calls in a state-dict-type context. Three modes:

| `StateDictType`      | Shape on each rank                    | Use for |
| -------------------- | ------------------------------------- | ------- |
| `FULL_STATE_DICT`    | full unsharded tensors                | export / small models / interop with non-FSDP loaders |
| `SHARDED_STATE_DICT` | this rank's shards (as `DTensor`/ShardedTensor) | large models; resharding-tolerant save/load |
| `LOCAL_STATE_DICT`   | raw local flat shards                 | fastest, but tied to the exact world size / wrap config |

### Full checkpoint, saved from rank 0 only (avoid host-RAM blowup)

```python
from torch.distributed.fsdp import (
    FullyShardedDataParallel as FSDP, StateDictType,
    FullStateDictConfig, FullOptimStateDictConfig,
)

save_policy = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, save_policy):
    cpu_state = model.state_dict()          # gathered, on CPU, populated only on rank 0
if dist.get_rank() == 0:
    torch.save(cpu_state, "model.pt")
```

`offload_to_cpu=True` + `rank0_only=True` is the combination that prevents every rank
from allocating a full copy of the model in host RAM.

### Loading a full checkpoint back

```python
full_state = torch.load("model.pt", map_location="cpu") if rank == 0 else None
with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT,
                          FullStateDictConfig(rank0_only=True)):
    model.load_state_dict(full_state)   # scattered back to shards
```

### Optimizer state (full)

Optimizer state must be gathered/scattered with the FSDP helpers because it is keyed by
the sharded parameters:

```python
optim_state = FSDP.full_optim_state_dict(model, optimizer)   # gather (rank0)
# ...save...
sharded = FSDP.optim_state_dict_to_load(model, optimizer, optim_state)  # on load
optimizer.load_state_dict(sharded)
```

(Exact helper names have varied across releases — `full_optim_state_dict`,
`sharded_optim_state_dict`, `optim_state_dict`, `optim_state_dict_to_load`,
`scatter_full_optim_state_dict`. The unified `torch.distributed.checkpoint.state_dict`
API below is the current recommended path and avoids memorizing these.)

## Distributed Checkpoint (DCP) — recommended

`torch.distributed.checkpoint` saves each rank's shards **in parallel** to a directory,
and can **reshard on load** (save on 8 GPUs, resume on 16). Works for both FSDP1 (with
`SHARDED_STATE_DICT`) and FSDP2 (DTensor state dicts natively).

The modern, generation-agnostic pattern uses the `state_dict` helpers to get/set both
model and optimizer together:

```python
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import (
    get_state_dict, set_state_dict,
)

# SAVE
model_sd, optim_sd = get_state_dict(model, optimizer)
dcp.save({"model": model_sd, "optim": optim_sd}, checkpoint_id="ckpt/step_1000")

# LOAD (into freshly constructed + FSDP-wrapped model/optimizer)
model_sd, optim_sd = get_state_dict(model, optimizer)
state = {"model": model_sd, "optim": optim_sd}
dcp.load(state, checkpoint_id="ckpt/step_1000")
set_state_dict(model, optimizer,
               model_state_dict=state["model"], optim_state_dict=state["optim"])
```

Key properties:

- **Parallel I/O** — no gather bottleneck; scales to large models.
- **Reshardable** — the saved format is world-size-independent.
- Output is a **directory** of shard files, not a single `.pt`. To export a single-file
  full checkpoint (e.g. for HuggingFace), convert with
  `torch.distributed.checkpoint.format_utils` (`dcp_to_torch_save`) or re-save via
  `FULL_STATE_DICT`.

## FSDP2 checkpointing

FSDP2 parameters are already `DTensor`s, so `model.state_dict()` yields a DTensor state
dict that DCP consumes directly — the `get_state_dict` / `dcp.save` / `dcp.load` /
`set_state_dict` flow above is the same. For a full single-tensor export, call
`.full_tensor()` on each DTensor (all-gathers) on the rank(s) doing the export.

## Guidance

- Long training runs: **DCP sharded** checkpoints (fast, reshardable).
- Final export / interop: **FULL_STATE_DICT** with `rank0_only=True, offload_to_cpu=True`,
  or convert a DCP directory afterward.
- Always save **model + optimizer + scheduler + step + RNG** together to resume exactly.
- Never rely on `LOCAL_STATE_DICT` across a change in world size or wrap policy — it is
  not portable.
