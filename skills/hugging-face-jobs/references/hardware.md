# Hardware (Flavor) Selection

Choosing the right flavor is the main cost/performance lever. Pick the smallest
flavor that fits the model in memory, verify on it, then scale up only if you
need more speed or VRAM.

> The authoritative, always-current list and prices come from
> `hf jobs hardware` or `list_jobs_hardware()`. The table below reflects the
> huggingface_hub Jobs guide and is a snapshot — treat the live command as
> ground truth.

## Available flavors (snapshot)

### CPU

| Flavor | vCPU | RAM | Cost/hr | Use |
|--------|------|-----|---------|-----|
| `cpu-basic` | 2 | 16 GB | ~$0.01 | Testing, lightweight scripts |
| `cpu-upgrade` | 8 | 32 GB | ~$0.03 | Data processing, parallel CPU work |
| `cpu-xl` | 16 | 124 GB | ~$1.00 | Big in-memory data jobs |
| `cpu-performance` | 32 | 256 GB | ~$1.90 | Heavy CPU / large streaming scans |

### GPU (single)

| Flavor | GPU (VRAM) | Cost/hr | Use |
|--------|-----------|---------|-----|
| `t4-small` | 1× T4 (16 GB) | ~$0.40 | <1B models, demos |
| `t4-medium` | 1× T4 (16 GB) | ~$0.60 | 1–3B models, dev |
| `l4x1` | 1× L4 (24 GB) | ~$0.80 | 3–7B, efficient inference |
| `a10g-small` | 1× A10G (24 GB) | ~$1.00 | 3–7B, production |
| `a10g-large` | 1× A10G (24 GB) | ~$1.50 | 7–13B, batch inference |
| `l40sx1` | 1× L40S (48 GB) | ~$1.80 | 13B-class, larger context |
| `a100-large` | 1× A100 (80 GB) | ~$2.50 | 13B+, fastest common GPU |
| `rtx-pro-6000` | 1× RTX PRO 6000 (96 GB) | ~$2.75 | Large single-GPU |
| `h200` | 1× H200 (141 GB) | ~$5.00 | Very large / fastest |

### GPU (multi)

| Flavor | GPUs (total VRAM) | Cost/hr | Use |
|--------|-------------------|---------|-----|
| `l4x4` | 4× L4 (96 GB) | ~$3.80 | Parallel / tensor-parallel |
| `a10g-largex2` | 2× A10G (48 GB) | ~$3.00 | Multi-GPU mid-size |
| `a10g-largex4` | 4× A10G (96 GB) | ~$5.00 | Multi-GPU large |
| `l40sx4` / `l40sx8` | 4–8× L40S | ~$8.30 / ~$23.50 | Large multi-GPU |
| `a100x4` / `a100x8` | 4–8× A100 (320/640 GB) | ~$10 / ~$20 | 70B+, sharded |
| `h200x2`…`h200x8` | 2–8× H200 | ~$10 … ~$40 | Frontier-scale |
| `rtx-pro-6000x2`…`x8` | 2–8× RTX PRO 6000 | ~$5.50 … ~$22 | Large multi-GPU |

> Note: earlier (2025-era) docs listed TPU `v5e-*` flavors; these are **not**
> in the current flavor list. Do not assume TPU availability — confirm with
> `hf jobs hardware`.

## Sizing memory

Rough VRAM needs:

- **Inference:** `GB ≈ params(B) × 2` (fp16), or `× ~1` for 8-bit, `× ~0.5` for 4-bit.
- **Full fine-tune:** `GB ≈ params(B) × ~16–20` (weights + grads + optimizer states).
- **LoRA/QLoRA fine-tune:** `GB ≈ params(B) × ~2–4`.

Examples: a 7B model needs ~14 GB for fp16 inference (fits `a10g-large`); full
7B training (~140 GB) is infeasible on a single common GPU — use LoRA or shard
across a multi-GPU flavor.

## Selection heuristics

| Model size (inference) | Start with |
|------------------------|-----------|
| <1B | `t4-small` |
| 1–3B | `t4-medium`, `a10g-small` |
| 3–7B | `a10g-small`, `l4x1` |
| 7–13B | `a10g-large` |
| 13–34B | `a100-large`, `l40sx1` |
| 34B+ / sharded | `a100x4`, `h200x2`, `l40sx4` |

- **CPU vs GPU:** CPU for pure data wrangling and I/O-bound streaming; GPU only when you actually run model math.
- **Single vs multi-GPU:** go multi-GPU for tensor parallelism, models too big for one card, or when linear speedup pays for itself on a large batch.

## Cost

`Total cost ≈ runtime_hours × cost_per_hour`. Levers to reduce spend:

1. Prototype on `cpu-basic` / `t4-small` before scaling.
2. Set a tight `timeout` with a 20–30% buffer so runaways get killed.
3. Use a pre-built framework image to shorten startup billing.
4. Right-size the flavor — do not over-provision VRAM you will not use.
5. Checkpoint long jobs so a failure does not force a full re-run.
