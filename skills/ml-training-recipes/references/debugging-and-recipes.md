# Debugging, Hyperparameters & Default Recipe Reference

Diagnostic checklists, hyperparameter search priorities, the 2025 default recipe,
and evaluation metrics by domain. For the systematic agent-driven experiment loop
see `experiment-loop.md`.

## Table of Contents

- [Hyperparameter Search](#hyperparameter-search)
- [The 2025 Default Recipe](#the-2025-default-recipe)
- [Debugging Checklist](#debugging-checklist)
- [Evaluation Metrics by Domain](#evaluation-metrics-by-domain)

---

## Hyperparameter Search

### Priority order (tune first → last)

1. **Learning rate** — most impactful. Always tune first.
2. **Batch size** — largest that fits. Speed knob, not quality knob.
3. **Weight decay** — 0.01-0.1 for AdamW.
4. **Warmup steps** — 1-5% of training.

## The 2025 Default Recipe

| Setting | Value |
|---------|-------|
| Optimizer | AdamW (β1=0.9, β2=0.95, eps=1e-10) |
| Weight decay | 0.1 |
| LR schedule | Cosine decay or WSD |
| Peak LR | 3e-4 (scale down for larger models) |
| Precision | bf16 |
| Grad clipping | max_norm=1.0 |
| Normalization | RMSNorm (pre-norm) |
| Activation | SwiGLU |
| Position encoding | RoPE |
| Attention | Flash Attention, optionally GQA |

---

## Debugging Checklist

### Karpathy's recipe (still canonical)

1. **Become one with the data** — visualize, check distributions, verify labels
2. **Get end-to-end running first** — verify on a trivial case
3. **Overfit one batch** — if you can't, you have a bug
4. **Then regularize** — add regularization only after overfitting works
5. **Tune hyperparameters** — start with known defaults

### Loss exploding / NaN

1. Reduce LR (3-10× smaller)
2. Add gradient clipping: `clip_grad_norm_(params, 1.0)`
3. Check for inf/nan in inputs
4. Add logit soft capping: `softcap * tanh(logits / softcap)`
5. Add QK-norm in attention
6. Verify weight init (zero-init output projections?)
7. Check loss reduction with gradient accumulation (`loss / grad_accum_steps`)

### Slow training / Low MFU

1. Verify `torch.compile` is active
2. Check `torch.set_float32_matmul_precision("high")`
3. Pin memory + non_blocking transfers
4. Profile with `torch.profiler`
5. GC stalls? `gc.freeze(); gc.disable()`
6. Tensor Core alignment: dims multiples of 8/64

### Loss plateau / Slow convergence

1. LR too low — try 2-5× larger
2. Warmup too long
3. Weight decay too high
4. Verify LR schedule is actually applied (print each step)
5. Model too small for task

### Silent failures

1. **Data leakage** between train/val
2. **Wrong preprocessing at inference** — augmentation mismatch
3. **Label errors** — use cleanlab to detect
4. **Shuffling bugs** — correlated batches
5. **Tokenizer mismatch** with pretrained model

### What to monitor

- **Gradient norms** — spike precedes loss spike
- **Per-layer activation stats** — reveals exploding/vanishing
- **Dead neurons** — >50% zero ReLU = dying ReLU problem
- **Learning rate** — verify schedule applied (common silent bug)

---

## Evaluation Metrics by Domain

| Domain | Primary Metric | Notes |
|--------|---------------|-------|
| LLM | BPB (bits per byte) | Vocab-size-independent |
| Classification | Accuracy / F1 | Macro-F1 for imbalanced |
| Segmentation | mIoU / Dice | Per-class IoU reveals weak spots |
| Generation | FID | Needs >10k samples |
| Regression | RMSE / MAE | Log-transform skewed targets |
