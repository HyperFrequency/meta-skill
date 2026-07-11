# FSDP troubleshooting & tuning

## Out-of-memory

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| OOM immediately on wrap / first forward | Model wrapped as one unit — the whole model is all-gathered at once | Add a **block-level auto-wrap policy** (`transformer_auto_wrap_policy` / `ModuleWrapPolicy`, or per-block `fully_shard`) |
| OOM at optimizer `.step()` | Optimizer states not sharded | Use `FULL_SHARD` (FSDP1) / default `reshard_after_forward` (FSDP2), not `NO_SHARD` / `SHARD_GRAD_OP` |
| OOM only in backward | Activations dominate | Enable **activation checkpointing** on the block class (see fsdp1-api.md) |
| OOM at high peak, fine at low | Prefetch pulling too many all-gathers ahead | `BackwardPrefetch.BACKWARD_POST` or `None`; keep `limit_all_gathers=True` |
| Still OOM after all of the above | Genuinely param-memory-bound | Enable **CPU offload** (`CPUOffload(offload_params=True)` / `CPUOffloadPolicy()`); reduce batch; add tensor/pipeline parallelism |

Model-size sanity: with `FULL_SHARD` + bf16 params + fp32 Adam, per-GPU steady-state is
roughly `(2 + 2 + 4 + 4 + 4) * P / world_size` bytes for params/grads/master+moments,
**plus** the transient all-gather of the single largest wrapped unit, **plus**
activations. The transient is why wrap granularity matters.

## Hangs (NCCL / collective deadlocks)

FSDP requires every rank to issue the **same collectives in the same order**. A hang at
the first all-gather almost always means ranks diverged.

- **Data-dependent control flow** — an `if loss > x:` or variable-length loop that
  differs per rank. All ranks must run the same forward/backward structure every step.
- **Uneven batches / early exit** — the last, ragged batch or a rank that returns early.
  Drop the last partial batch or pad so all ranks step equally.
- **Different module trees** — ranks built different models (conditional layers, differing
  configs). Construct identically; use `sync_module_states=True` if building on rank 0.
- **Unused parameters** — a parameter that gets no gradient can stall the reduce. Ensure
  every wrapped unit's params participate, or exclude them via `ignored_modules`.

Debugging env vars:

```bash
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1   # crash instead of hang on collective mismatch
export TORCH_DISTRIBUTED_DEBUG=DETAIL       # log collective shapes/order per rank
export NCCL_DEBUG=WARN                       # NCCL-level diagnostics
```

`TORCH_DISTRIBUTED_DEBUG=DETAIL` will name the parameter/collective where ranks disagree.

## Slow throughput

- **Comm not overlapping compute** — ensure `backward_prefetch=BACKWARD_PRE` and consider
  `forward_prefetch=True` (FSDP1) or explicit
  `set_modules_to_backward_prefetch` (FSDP2).
- **Too-fine wrapping** — thousands of tiny units means many small all-gathers with
  latency overhead. Wrap at the block level, not per-linear.
- **Multi-node bottleneck** — inter-node bandwidth is the limiter. Use `HYBRID_SHARD`
  (FSDP1) or a 2D `("replicate","shard")` mesh (FSDP2) to keep full sharding intra-node
  and only replicate across nodes.
- **fp32 reduce is fine, fp32 compute is not** — verify `param_dtype=torch.bfloat16`
  actually took effect; a stray fp32 param class defeats mixed precision.
- **Small effective batch** — sharding adds comm per step; amortize with gradient
  accumulation (see `set_requires_gradient_sync` / FSDP1 `no_sync()`).
- Profile with `torch.profiler` and look for gaps between kernels = exposed communication.

## Correctness gotchas

- **Gradient clipping**: FSDP1 → `model.clip_grad_norm_(...)`. FSDP2 →
  `torch.nn.utils.clip_grad_norm_` (DTensor-aware). Using the wrong one silently computes
  a per-shard norm.
- **Do not call the optimizer before FSDP wrapping** — it will bind to the wrong (dense)
  parameters.
- **`param.grad` may be `None`/sharded** between steps — inspect gradients through the
  FSDP-aware paths, not raw `.grad` on the original module.
- **Buffers (BatchNorm running stats)** are not sharded and are not synced by default;
  prefer normalization that doesn't accumulate cross-batch state (LayerNorm/RMSNorm), or
  handle BN sync explicitly.
- **`torch.compile`**: wrap with FSDP first, then compile; FSDP1 needs
  `use_orig_params=True`. FSDP2 composes with compile more naturally.

## Common tracebacks

- `RuntimeError: Expected to have finished reduction ... unused parameters` — a param got
  no gradient; add it to `ignored_modules` or ensure it's used.
- `AssertionError: Cannot flatten integer dtype tensors` / dtype flatten errors — a
  non-float parameter/buffer got swept into a flat param; move it to `ignored_modules`.
- NCCL `timeout` / `Watchdog caught collective operation timeout` — a hang from the
  divergence causes above; rerun with `TORCH_DISTRIBUTED_DEBUG=DETAIL`.
- `size mismatch` on checkpoint load — you saved sharded (`LOCAL_STATE_DICT`) and are
  loading into a different world size; use DCP or `FULL_STATE_DICT` instead (see
  checkpointing.md).
