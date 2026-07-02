# Training Loop, Scheduling, Precision & Memory Reference

Core training mechanics: the loop itself, LR scheduling, mixed precision/compilation,
and memory/performance tuning. For optimizer internals see `optimizers.md`; for
architecture code see `architecture.md`.

## Table of Contents

- [Training Loop](#training-loop)
- [Learning Rate Scheduling](#learning-rate-scheduling)
- [Mixed Precision & Compilation](#mixed-precision--compilation)
- [Memory & Performance](#memory--performance)

---

## Training Loop

```python
import gc, time, torch

torch.manual_seed(42)
torch.set_float32_matmul_precision("high")  # TF32 on Ampere+
autocast_ctx = torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16)

grad_accum_steps = total_batch_size // (batch_size * seq_len)
step = 0

while not done:
    t0 = time.time()
    for micro_step in range(grad_accum_steps):
        with autocast_ctx:
            loss = model(x, y)
        (loss / grad_accum_steps).backward()
        x, y = next(train_loader)

    update_lr(optimizer, progress)
    optimizer.step()
    model.zero_grad(set_to_none=True)  # frees memory vs zeroing

    if loss.item() > 100:  # fast-fail on divergence
        print("FAIL: loss exploded"); exit(1)

    torch.cuda.synchronize()
    if step == 0:
        gc.collect(); gc.freeze(); gc.disable()  # avoid ~500ms GC stalls
    step += 1
```

### Key principles

- **Gradient clipping**: `clip_grad_norm_(params, 1.0)` — near-universal for Transformers.
  Exception: Muon optimizer normalizes updates via orthogonalization, so clipping is optional.
- **Tensor Core alignment**: batch size, hidden dims should be multiples of 8 (bf16) or 64 (A100).
- **Time-based budgets** make experiments comparable across hardware.
- **`cudnn.benchmark = True`** for fixed-size vision inputs.

---

## Learning Rate Scheduling

### Time-based (autoresearch style)

```python
def get_lr_multiplier(progress):  # progress = elapsed_time / time_budget
    if progress < warmup_ratio:
        return progress / warmup_ratio
    elif progress < 1.0 - warmdown_ratio:
        return 1.0
    else:
        cooldown = (1.0 - progress) / warmdown_ratio
        return cooldown + (1 - cooldown) * final_lr_frac
```

### Cosine decay

```python
def get_lr(step, total_steps, max_lr, min_lr, warmup_steps):
    if step < warmup_steps:
        return max_lr * step / warmup_steps
    progress = (step - warmup_steps) / (total_steps - warmup_steps)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))
```

**WSD (Warmup-Stable-Decay)**: gaining traction — easier to resume training mid-run.

### Guidance

- **Warmup**: 1-5% of training. Zero warmup valid with Muon (autoresearch uses `WARMUP_RATIO=0.0`).
- **Warmdown**: 30-50% of training in LR decay. Matters more than warmup for final quality.
- **Final LR**: 0 or ~10% of peak. Zero is simpler.

---

## Mixed Precision & Compilation

```python
import os
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"  # before torch import

import torch
torch.set_float32_matmul_precision("high")
autocast_ctx = torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16)
model = torch.compile(model, dynamic=False)
```

- **bf16** (Ampere+): same exponent as fp32, no loss scaling needed. Preferred over fp16.
- **fp16**: needs GradScaler. Use only on V100 or older.
- `dynamic=False` enables max optimization. Add `fullgraph=True` if no graph breaks.
- First steps are slow (JIT) — exclude from timing.

---

## Memory & Performance

### Meta device init (large models)

```python
with torch.device("meta"):
    model = GPT(config)          # zero memory
model.to_empty(device="cuda")
model.init_weights()
```

### MFU (Model FLOPs Utilization)

```python
achieved_flops = model_flops_per_token * batch_tokens / step_time
mfu = achieved_flops / gpu_peak_flops
# H100 SXM: 989.5 TFLOPS | A100: 312 | RTX 4090: 165
```

Good targets: >30% decent, >40% good, >50% excellent (single-GPU).

### OOM solutions (in order)

1. Reduce `DEVICE_BATCH_SIZE`, increase `grad_accum_steps`
2. `PYTORCH_ALLOC_CONF=expandable_segments:True`
3. `model.zero_grad(set_to_none=True)`
4. Meta device init → `to_empty`
5. Activation checkpointing: `torch.utils.checkpoint.checkpoint()`
6. 8-bit optimizer (bitsandbytes): ~30% savings on optimizer states
