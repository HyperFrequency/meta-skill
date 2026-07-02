# CNN Pattern Recognition — Architecture, Ops & Diagnostics

## Architecture choices

- **Depth**: start at 2–4 conv blocks. CNNs over price overfit fast; deeper is rarely better unless you have millions of bars.
- **Channel widths**: `32 -> 64 -> 128` is a safe ladder. Doubling each block keeps receptive-field growth and parameter count balanced.
- **Kernel size**: 1-D over price favours `kernel=3 or 5`. Larger kernels (7, 9) help capture multi-bar patterns; pair with `padding="same"` so the time axis is preserved.
- **Activations**: ReLU by default. `GELU` or `SiLU` sometimes nudges a few bps on noisy financial data — not worth fighting over.
- **Pooling**: prefer `AdaptiveAvgPool` over `MaxPool` for regression-style heads; price noise makes max-pool jumpy.
- **Normalisation**: BatchNorm is fine for big batches; switch to `LayerNorm` or `GroupNorm` if you batch in time-walking blocks where the batch distribution shifts.
- **Head**: 1 hidden FC then logits. Avoid deep MLP heads — the conv stack already did the work.


## Scaling to production

- **Batch the windowing.** The `np.stack([Xz[i-WINDOW:i] ...])` in the minimal example is O(n*WINDOW) memory. For >1M bars switch to a strided view (`np.lib.stride_tricks.sliding_window_view`) or a streaming `IterableDataset`.
- **Mixed precision.** `torch.autocast("cuda")` + `GradScaler` cuts memory ~40% on the 2-D image branch with no accuracy loss. The 1-D branch is usually too small to benefit.
- **Compile.** `model = torch.compile(model)` (PyTorch 2.x) gives a 1.2-2x speedup on these tiny conv stacks. Keras users get the same from `jit_compile=True` in `model.compile`.
- **Walk-forward retrain.** Don't train once and forget. Schedule a retrain every N bars / N days (see `adaptive-wfo-epoch` skill). The CNN's weights go stale faster than people expect.
- **Inference latency.** For real-time signal generation, a 1-D CNN on a 64-bar window runs in <100 us on CPU; the image-rendering branch is the bottleneck — pre-render or skip.

## Diagnostics

When the model trains but performs at chance, the order of investigation:

1. Verify labels: shuffle `y` and confirm acc collapses to ~0.5. If it doesn't, you have leakage.
2. Visualise inputs: plot the first 4 windows. If they all look identical, your normalisation is broken.
3. Check activations: `torchinfo.summary(model, input_size=(1, 5, WINDOW))` to confirm shapes flow correctly.
4. Sanity-check with an MLP baseline. If a flat MLP beats your CNN, the CNN is mis-specified (kernel too big, BN exploding).
5. Loss curve shape: oscillating train loss → LR too high. Flat → LR too low or dead ReLUs.

