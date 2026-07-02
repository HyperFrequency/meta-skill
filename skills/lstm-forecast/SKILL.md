---
name: lstm-forecast
version: 0.1.0
description: LSTM (long short-term memory) forecasting for univariate or multivariate price/return time series, using either Keras 3 (TensorFlow/JAX/PyTorch backends) or plain PyTorch nn.LSTM / nn.LSTMCell. Trigger on phrases like "fit an LSTM to this series", "next-day price LSTM", "sequence model forecast", "Keras 3 LSTM example", "PyTorch LSTM forecast", "predict the next N steps with a recurrent net". Use when the user wants a deep recurrent baseline before reaching for transformers or foundation models. For Transformer / TFT see `transformer-forecast`; for classical models see `arima-forecast` / `prophet-forecast`. Not for attention-based or probabilistic forecasts — use `transformer-forecast` for those.
license: Apache-2.0 (Keras), BSD-3-Clause (PyTorch)
metadata:
    skill-author: HyperFrequency
---

# LSTM Forecasting (Keras 3 + PyTorch)

## When to use this skill

- You have a univariate or multivariate price/return series and want a recurrent neural baseline.
- You need to compare an RNN against ARIMA / Prophet / Transformer with the same train/test split.
- You want a Keras 3 model that runs on TensorFlow, JAX, *or* PyTorch by flipping `KERAS_BACKEND`.
- You want a small from-scratch PyTorch LSTM for full control (custom loss, custom autoregressive rollout).

If you specifically want attention-based or quantile forecasts, prefer `transformer-forecast` (TFT / HF Time Series Transformer).

## Install / setup

```bash
# Keras 3 path (pick one backend; tensorflow is the most batteries-included)
uv add keras tensorflow numpy pandas scikit-learn matplotlib
# or: uv add keras jax jaxlib   # JAX backend
# or: uv add keras torch        # PyTorch backend

# Pure PyTorch path
uv add torch numpy pandas scikit-learn matplotlib
```

Keras 3 chooses backend from the `KERAS_BACKEND` env var. Set it *before* `import keras`:

```python
import os
os.environ["KERAS_BACKEND"] = "tensorflow"  # or "torch" or "jax"
import keras
```

## Minimal working example - Keras 3 LSTM

```python
import os
os.environ["KERAS_BACKEND"] = "tensorflow"  # set BEFORE importing keras

import numpy as np
import pandas as pd
import keras
from keras import layers
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt

keras.utils.set_random_seed(42)

# 1. Load a price series (replace with your CSV / API)
rng = np.random.default_rng(0)
price = pd.Series(100 + np.cumsum(rng.normal(0, 1, 1000)), name="close")

# 2. Scale and window into (lookback -> 1-step) supervised samples
scaler = MinMaxScaler()
y = scaler.fit_transform(price.values.reshape(-1, 1)).ravel()
LOOKBACK = 30
X = np.stack([y[i:i + LOOKBACK] for i in range(len(y) - LOOKBACK)])
t = y[LOOKBACK:]
X = X[..., None]  # (n_samples, LOOKBACK, 1) - LSTM expects 3D

split = int(0.8 * len(X))
X_tr, X_te, y_tr, y_te = X[:split], X[split:], t[:split], t[split:]

# 3. Build + train
model = keras.Sequential([
    keras.Input(shape=(LOOKBACK, 1)),
    layers.LSTM(32),
    layers.Dense(1),
])
model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
model.fit(X_tr, y_tr, epochs=10, batch_size=32, validation_split=0.1, verbose=0)

# 4. Predict + inverse-scale + evaluate
yhat_scaled = model.predict(X_te, verbose=0).ravel()
yhat = scaler.inverse_transform(yhat_scaled.reshape(-1, 1)).ravel()
ytrue = scaler.inverse_transform(y_te.reshape(-1, 1)).ravel()
print(f"MAE: {mean_absolute_error(ytrue, yhat):.3f}  "
      f"RMSE: {np.sqrt(mean_squared_error(ytrue, yhat)):.3f}")

# 5. Plot
plt.plot(ytrue, label="actual"); plt.plot(yhat, label="predicted"); plt.legend(); plt.show()
```

## Minimal working example - PyTorch LSTM (autoregressive rollout)

This mirrors the `pytorch/examples/time_sequence_prediction` pattern: stacked `LSTMCell`s + scalar projection + a `future=N` autoregressive forecast loop.

```python
import numpy as np, torch, torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error

class Sequence(nn.Module):
    def __init__(self, hidden=51):
        super().__init__()
        self.lstm1 = nn.LSTMCell(1, hidden)
        self.lstm2 = nn.LSTMCell(hidden, hidden)
        self.linear = nn.Linear(hidden, 1)
        self.hidden = hidden

    def forward(self, x, future=0):
        outputs, h1 = [], None
        h_t  = torch.zeros(x.size(0), self.hidden, dtype=x.dtype)
        c_t  = torch.zeros_like(h_t)
        h_t2 = torch.zeros_like(h_t); c_t2 = torch.zeros_like(h_t)
        for step in x.split(1, dim=1):                       # teacher-forced
            h_t,  c_t  = self.lstm1(step.squeeze(1), (h_t,  c_t))
            h_t2, c_t2 = self.lstm2(h_t,             (h_t2, c_t2))
            out = self.linear(h_t2); outputs.append(out)
        for _ in range(future):                              # free-run
            h_t,  c_t  = self.lstm1(out, (h_t,  c_t))
            h_t2, c_t2 = self.lstm2(h_t, (h_t2, c_t2))
            out = self.linear(h_t2); outputs.append(out)
        return torch.cat(outputs, dim=1)

# data
rng = np.random.default_rng(0)
price = 100 + np.cumsum(rng.normal(0, 1, 1000))
scaler = MinMaxScaler(); y = scaler.fit_transform(price.reshape(-1,1)).ravel()
data = torch.from_numpy(y).float().unsqueeze(0)              # (1, T)
inp, tgt = data[:, :-1], data[:, 1:]

# train
model = Sequence(); opt = torch.optim.LBFGS(model.parameters(), lr=0.8)
crit = nn.MSELoss()
for epoch in range(8):
    def closure():
        opt.zero_grad(); out = model(inp); loss = crit(out, tgt); loss.backward(); return loss
    opt.step(closure)

# forecast 50 steps beyond the series
with torch.no_grad():
    pred = model(inp, future=50).numpy().ravel()
print("MAE last 100 steps:", mean_absolute_error(tgt.numpy().ravel()[-100:], pred[-150:-50]))
```

## Key API surface

| Library | Class / function | Purpose |
|---|---|---|
| Keras 3 | `keras.layers.LSTM(units, return_sequences=False)` | Vectorised LSTM layer (preferred for batched training) |
| Keras 3 | `keras.layers.LSTMCell(units)` + `keras.layers.RNN` | Step-wise cell for custom loops |
| Keras 3 | `keras.Sequential` / `keras.Model` + `.compile()` / `.fit()` / `.predict()` | Standard training loop |
| Keras 3 | `keras.callbacks.EarlyStopping(monitor="val_loss", patience=5)` | Stop when val loss plateaus |
| PyTorch | `torch.nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)` | Batched multi-layer LSTM |
| PyTorch | `torch.nn.LSTMCell(input_size, hidden_size)` | Single step - needed for autoregressive rollout |
| PyTorch | `torch.optim.LBFGS` / `Adam` | Optimiser |

## Evaluation

Always evaluate on a *chronological* holdout, never a random split:

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

mae  = mean_absolute_error(ytrue, yhat)
rmse = np.sqrt(mean_squared_error(ytrue, yhat))
mape = np.mean(np.abs((ytrue - yhat) / np.maximum(np.abs(ytrue), 1e-8))) * 100
print(f"MAE {mae:.3f}  RMSE {rmse:.3f}  MAPE {mape:.2f}%")

# Residual diagnostics
import matplotlib.pyplot as plt
resid = ytrue - yhat
fig, ax = plt.subplots(1, 2, figsize=(10, 3))
ax[0].plot(resid); ax[0].axhline(0, color="r"); ax[0].set_title("Residuals over time")
ax[1].hist(resid, bins=30); ax[1].set_title("Residual distribution")
plt.show()
```

For longer horizons compute MAE / RMSE at each step `h = 1, 2, ..., H` and plot error-vs-horizon - error should grow roughly monotonically; if it spikes mid-horizon you likely have a leak or a frequency mismatch.

## Common pitfalls

1. **Forgetting to scale inputs.** LSTM gates saturate fast with raw price levels. Always `MinMaxScaler` or standardise on the *training* window only, then transform train + test with the same scaler.
2. **Random train/test split on time series.** Always split chronologically. A random split leaks future info via the window construction.
3. **Wrong tensor shape.** `keras.layers.LSTM` expects `(batch, time, features)`. A 2D `(batch, time)` array silently broadcasts as `features=1` only if you `[..., None]` first - otherwise you get a shape error.
4. **Setting `KERAS_BACKEND` after `import keras`.** Must be set *before*. Otherwise Keras has already chosen a backend and your env var is ignored.
5. **Treating one-step LSTM output as a multi-step forecast.** A single `model.predict` returns *one* step. For an H-step forecast either (a) train a model with `output_dim=H`, or (b) use an autoregressive loop, feeding predictions back as inputs (drift accumulates - measure it).
6. **Reusing the test scaler.** Inverse-transform must use the scaler fitted on the train window. Refitting on test rescales the answer and inflates accuracy.

## References

### Primary libraries
- [keras-team/keras](https://github.com/keras-team/keras) — Keras 3 multi-backend repo (issues, releases, RFCs)
- [Keras 3 API docs](https://keras.io/api/) — cross-checked against current `keras>=3` (TF / JAX / PyTorch backends)
- [Keras getting started](https://keras.io/getting_started/) — install + backend selection
- [Keras code examples (timeseries)](https://keras.io/examples/timeseries/) — official, runnable
- [pytorch/pytorch](https://github.com/pytorch/pytorch) — PyTorch core repo
- [PyTorch docs index](https://pytorch.org/docs/stable/index.html) — pin against the current stable channel

### Deep-dive docs (specific pages worth bookmarking)
- [`keras.layers.LSTM`](https://keras.io/api/layers/recurrent_layers/lstm/) — the canonical batched LSTM layer; covers `return_sequences`, `stateful`, masking
- [`keras.layers.LSTMCell`](https://keras.io/api/layers/recurrent_layers/lstm_cell/) — single-step cell for custom autoregressive rollouts
- [Working with RNNs guide](https://keras.io/guides/working_with_rnns/) — stateful RNNs, custom cells, masking — required reading for quant rollouts
- [Keras timeseries weather forecasting example](https://keras.io/examples/timeseries/timeseries_weather_forecasting/) — full LSTM workflow on a real multivariate series
- [`torch.nn.LSTM`](https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html) — batched multi-layer LSTM (`batch_first=True` is the modern default)
- [`torch.nn.LSTMCell`](https://pytorch.org/docs/stable/generated/torch.nn.LSTMCell.html) — needed when you control the rollout step-by-step
- [`pytorch/examples` — time_sequence_prediction](https://github.com/pytorch/examples/tree/main/time_sequence_prediction) — stacked `LSTMCell`s + LBFGS + free-run forecast, the pattern the second example mirrors
- [`KERAS_BACKEND` environment variable](https://keras.io/getting_started/) — how Keras 3 picks TF / JAX / PyTorch and why it must be set *before* `import keras`

### Adjacent / alternative libraries
- `transformer-forecast` skill — attention-based + probabilistic + multi-horizon quantile forecasts (TFT, HF TST)
- `arima-forecast` skill — classical baseline you should beat before claiming the LSTM is useful
- [Darts](https://github.com/unit8co/darts) — sklearn-style API with `RNNModel`, `BlockRNNModel`, useful when you want one library for ARIMA + LSTM + N-BEATS on the same dataset
- [GluonTS](https://github.com/awslabs/gluonts) — probabilistic LSTM (`DeepAR`) over the same data contract used by HF Time Series Transformer
- [NeuralForecast](https://github.com/Nixtla/neuralforecast) — Nixtla's stack: LSTM, NHITS, TFT under a unified API, with automatic CV

### Academic papers
- Hochreiter, S. & Schmidhuber, J. (1997). "Long Short-Term Memory." *Neural Computation* 9(8), 1735–1780. [doi:10.1162/neco.1997.9.8.1735](https://doi.org/10.1162/neco.1997.9.8.1735) — original LSTM architecture (constant error carousel + gated cells)
- Salinas, D. et al. (2020). "DeepAR: Probabilistic forecasting with autoregressive recurrent networks." *International Journal of Forecasting* 36(3), 1181–1191. [arXiv:1704.04110](https://arxiv.org/abs/1704.04110) — production-grade probabilistic LSTM; relevant if you outgrow point forecasts

### Tutorials & write-ups
- [Keras 3 announcement](https://keras.io/keras_3/) — the multi-backend story and why `KERAS_BACKEND` exists
- [PyTorch nn.LSTM tutorial in the docs](https://pytorch.org/tutorials/beginner/nlp/sequence_models_tutorial.html) — official intro that introduces the hidden-state shape contract

### Last cross-checked
2026-05-20 — via Context7 `/keras-team/keras-io` + `/websites/keras_io_api` + PyTorch stable docs; Auggie not indexed for these repos.
