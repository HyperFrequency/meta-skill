# PyOD deep-detector API surface (verified against PyOD v2.0+ source)

Signatures below were cross-checked on 2026-06-29 against the upstream
`pyod/models/*.py` on the `master` branch. PyOD ≥ 2.0 uses a PyTorch backend
(older v1.x used Keras/TF and a different kwarg set — `hidden_neurons`,
`epochs`, etc.). Check your version with `import pyod; pyod.__version__`.

## `AutoEncoder` — `pyod.models.auto_encoder.AutoEncoder`

MLP autoencoder, reconstruction-error scoring. Full v2.0+ signature:

```python
AutoEncoder(
    contamination=0.1, preprocessing=True,
    lr=1e-3, epoch_num=10, batch_size=32,
    optimizer_name='adam',
    device=None, random_state=42,
    use_compile=False, compile_mode='default',
    verbose=1,
    optimizer_params={'weight_decay': 1e-5},
    hidden_neuron_list=[64, 32],
    hidden_activation_name='relu',
    batch_norm=True, dropout_rate=0.2,
)
```

- `hidden_neuron_list` — encoder/decoder widths (decoder mirrors automatically).
- `optimizer_params={'weight_decay': 1e-5}` — L2 regularisation lives here, not as a top-level kwarg.
- `device=None` auto-detects GPU via `torch.cuda.is_available()`; pass `"cpu"` or `"cuda:0"` to pin.

## `VAE` — `pyod.models.vae.VAE`

Variational AE; KL + reconstruction loss. Full v2.0+ signature:

```python
VAE(
    contamination=0.1, preprocessing=True,
    lr=1e-3, epoch_num=30, batch_size=32,
    optimizer_name='adam',
    device=None, random_state=42,
    use_compile=False, compile_mode='default',
    verbose=1,
    optimizer_params={'weight_decay': 1e-5},
    beta=1.0, capacity=0.0,
    encoder_neuron_list=[128, 64, 32],
    decoder_neuron_list=[32, 64, 128],
    latent_dim=2,
    hidden_activation_name='relu',
    output_activation_name='identity',
    batch_norm=False, dropout_rate=0.2,
    logvar_clip=(-30.0, 20.0),
)
```

- `beta` — weight on the KL term (β-VAE); `capacity` — target KL capacity.
- `output_activation_name='identity'` is correct for returns (no squashing).

## `MO_GAAL` — `pyod.models.mo_gaal.MO_GAAL`

GAN-based detector with `k` sub-generators to avoid mode collapse. Full v2.0+ signature:

```python
MO_GAAL(k=10, stop_epochs=20, lr_d=0.01, lr_g=0.0001,
        momentum=0.9, contamination=0.1)
```

- `k` — number of sub-generators; `lr_d` / `lr_g` — discriminator / generator learning rates, tuned separately.
- Single-objective variant is `pyod.models.so_gaal.SO_GAAL` (`k=1` equivalent).

## Common detector methods (shared base class)

| Symbol | What it does |
|---|---|
| `.fit(X)` | Train on "normal" data (or mixed with low contamination). |
| `.predict(X)` | Binary labels: 1 = anomaly, 0 = inlier. |
| `.decision_function(X)` | Raw anomaly score (higher = more anomalous). |
| `.threshold_` | Auto-computed cutoff derived from `contamination`. |
| `.decision_scores_` | Training-set anomaly scores (set after `fit`). |
| `pyod.utils.data.generate_data(...)` | Synthetic data helper for sanity checks. |
| `pyod.utils.utility.precision_n_scores(y, scores)` | Precision-at-N evaluation. |
| `pyod.utils.data.evaluate_print(name, y, scores)` | Quick ROC/P@N print. |
