# GPU selection, cost, and pitfalls

## GPU selection

Pick the cheapest GPU whose VRAM fits your model plus a realistic batch. Prices below are
**approximate and drift over time** — verify current rates from Modal's pricing before quoting a
budget, and confirm the exact `gpu=` string values (`"T4"`, `"A10G"`, `"A100"`, `"A100-80GB"`,
`"H100"`) against current Modal docs.

| GPU        | VRAM  | ~$/hr | Use when |
|------------|-------|-------|----------|
| T4         | 16 GB | ~$0.59 | Small models, inference, cheap testing |
| A10G       | 24 GB | ~$1.10 | Standard single-GPU training |
| A100-40GB  | 40 GB | ~$3.15 | Larger models, bigger batches |
| A100-80GB  | 80 GB | ~$4.05 | Large models, long sequences, high resolution |
| H100       | 80 GB | ~$4.25 | Fastest training, largest batch sizes |

If a run OOMs, the ladder is: enable gradient checkpointing / mixed precision and shrink the batch
first (cheaper), then step up to the next GPU. For kernel/precision/batching throughput work, use
the `optimize-for-gpu` skill; for sharding one model across multiple GPUs, use a
`distributed-training` skill (`accelerate`, `deepspeed`, `pytorch-fsdp2`, `ray-train`) — this skill
assumes one container per run.

## VRAM sizing heuristic

Rough peak VRAM for training in FP16/BF16 with Adam:

```
weights            ≈ params × 2 bytes
gradients          ≈ params × 2 bytes
Adam optimizer     ≈ params × 8 bytes   (fp32 momentum + variance)
--------------------------------------------------
model+optim total  ≈ params × 12 bytes
plus activations   ≈ grows with batch size × sequence/resolution
```

So a ~1B-param model needs ~12 GB just for weights+grads+optimizer before any activations — which
is why it wants A10G (24 GB) at best, and why activations from a large batch/long sequence push it
to an A100. Measure real peak with `torch.cuda.max_memory_allocated()` on a short run rather than
trusting the estimate; activation memory is the term that surprises people.

## Cost estimation

```
Cost = (seconds_per_epoch × epochs / 3600) × $/hr

Example: 500 epochs × 30 s/epoch = 15,000 s = 4.2 hrs
  A10G:      4.2 × $1.10 = ~$4.62
  A100-80GB: 4.2 × $4.05 = ~$17.01
```

For a parallel sweep, multiply by the number of concurrent runs — N A10G runs for H hours cost
`N × H × $1.10`. Measure `seconds_per_epoch` from a short calibration run before committing to a
full-length job or a wide sweep.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `modal run --detach` with chained `.remote()` | Later calls never execute; half-finished run | Deploy + spawn (see `deploy-spawn.md`) |
| Unpinned PyTorch | `CUDA driver too old` on the GPU node | Pin `torch==` (and `numpy==`) to a known-good version |
| No `volume.reload()` before reading | Stale or missing checkpoint on resume | Always `reload()` before reading the volume |
| No `volume.commit()` after writing | Checkpoint lost on preemption | `commit()` immediately after every `torch.save` |
| Multiple tasks, same volume path | Interleaved/clobbered writes | One subdirectory + one checkpoint file per run |
| Timeout too short | Job killed mid-training | Set `timeout=` generously (max 86400 = 24h) |
| No checkpoint-resume | Preemption wipes the whole run | Checkpoint every N epochs (see `checkpointing.md`) |
| Duplicate `spawn()` of same function | Two identical jobs, double the bill | Check `modal app list` before spawning; stop dupes |
| `weights_only=True` (torch ≥2.6 default) on a full checkpoint | Resume fails to load optimizer/scheduler | Load with `weights_only=False` |
