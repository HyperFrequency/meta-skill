# FNO end-to-end workflow

Full worked pipeline for a Fourier Neural Operator: generate solved instances,
normalize, train (both a manual loop and the library `Trainer`), evaluate with
relative L2, and exploit zero-shot super-resolution.

All FNO tensors are **channel-first**: `(batch, channels, *spatial)`. A 1D field of
length `N` is `(B, in_channels, N)`; a 2D field is `(B, in_channels, H, W)`.

## 1. Generate training data (1D Burgers, pseudospectral)

Learn the map from an initial condition `u(x, 0)` to the solution `u(x, T)` of the
viscous Burgers equation `u_t + u·u_x = ν·u_xx` on a periodic domain.

```python
import numpy as np
from scipy.integrate import solve_ivp
from scipy.fft import fft, ifft, fftfreq

def solve_burgers(u0, nu=0.01, T=1.0, N=256):
    """Reference solution via a pseudospectral method (training-data generator)."""
    dx = 2 * np.pi / N
    k = fftfreq(N, d=dx) * 2 * np.pi
    def rhs(t, u_hat):
        u = np.real(ifft(u_hat))
        u_x = np.real(ifft(1j * k * u_hat))
        return -fft(u * u_x) - nu * k**2 * u_hat
    sol = solve_ivp(rhs, (0, T), fft(u0), method="RK45", rtol=1e-8, atol=1e-10)
    return np.real(ifft(sol.y[:, -1]))

N, n_train, n_test = 256, 1000, 200
x = np.linspace(0, 2 * np.pi, N, endpoint=False)
rng = np.random.default_rng(0)

inputs, outputs = [], []
for _ in range(n_train + n_test):
    u0 = np.zeros(N)                      # random low-frequency initial condition
    for kmode in range(1, 8):
        u0 += rng.standard_normal() * np.sin(kmode * x)
        u0 += rng.standard_normal() * np.cos(kmode * x)
    u0 *= 0.5
    inputs.append(u0)
    outputs.append(solve_burgers(u0))

inputs, outputs = np.array(inputs), np.array(outputs)
```

Any solver works here — finite differences, spectral, or FEM. Delegate this to
`pde-solver` and sample the parameters (viscosity, forcing, boundary values) you
want the operator to generalize over.

## 2. Normalize and shape into tensors

Normalization is not optional: FNO trains far better on zero-mean, unit-variance
data. Fit statistics on the **training split only**, then de-normalize predictions
before reporting physical error.

```python
import torch

in_mean, in_std = inputs[:n_train].mean(), inputs[:n_train].std()
out_mean, out_std = outputs[:n_train].mean(), outputs[:n_train].std()

def to_tensor(arr, mean, std):
    t = torch.tensor((arr - mean) / std, dtype=torch.float32)
    return t.unsqueeze(1)                 # (N, 1, grid) -> channel-first

x_train = to_tensor(inputs[:n_train],  in_mean,  in_std)
y_train = to_tensor(outputs[:n_train], out_mean, out_std)
x_test  = to_tensor(inputs[n_train:],  in_mean,  in_std)
y_test  = to_tensor(outputs[n_train:], out_mean, out_std)
```

## 3. Train — manual loop

Version-robust and dependency-light. Report **relative L2**, not raw MSE.

```python
from neuralop.models import FNO

model = FNO(n_modes=(16,), hidden_channels=64,
            in_channels=1, out_channels=1, n_layers=4)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.5)

def relative_l2(pred, target):
    num = torch.linalg.norm((pred - target).flatten(1), dim=1)
    den = torch.linalg.norm(target.flatten(1), dim=1)
    return (num / den).mean()

batch_size = 32
for epoch in range(500):
    model.train()
    perm = torch.randperm(len(x_train))
    for i in range(0, len(x_train), batch_size):
        idx = perm[i:i + batch_size]
        loss = torch.nn.functional.mse_loss(model(x_train[idx]), y_train[idx])
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    scheduler.step()
    if (epoch + 1) % 50 == 0:
        model.eval()
        with torch.no_grad():
            print(f"epoch {epoch+1}: rel_L2={relative_l2(model(x_test), y_test):.4f}")
```

## 4. Train — library `Trainer` (recommended for 2D)

The library ships a `Trainer` plus operator-aware losses and a `data_processor`
that handles normalization automatically. Import names by module:

```python
from neuralop.models import FNO
from neuralop.training import Trainer
from neuralop import LpLoss, H1Loss          # also: from neuralop.losses import LpLoss, H1Loss
from neuralop.data.datasets import load_darcy_flow_small

train_loader, test_loaders, data_processor = load_darcy_flow_small(
    n_train=1000, batch_size=32,
    n_tests=[100], test_resolutions=[32], test_batch_sizes=[32],
)

model = FNO(n_modes=(16, 16), hidden_channels=64, in_channels=1, out_channels=1)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=30)

l2loss = LpLoss(d=2, p=2)                    # d = number of spatial dims
h1loss = H1Loss(d=2)

trainer = Trainer(model=model, n_epochs=30,
                  data_processor=data_processor, verbose=True)
trainer.train(train_loader=train_loader, test_loaders=test_loaders,
              optimizer=optimizer, scheduler=scheduler, regularizer=False,
              training_loss=h1loss, eval_losses={"l2": l2loss, "h1": h1loss})
```

`LpLoss(d, p)` is the discrete relative Lp norm; `H1Loss(d)` also penalizes the
gradient (a Sobolev norm), which sharpens fine-scale structure. Training on `H1Loss`
and evaluating on both is a common, robust choice.

## 5. Evaluate and visualize

```python
import matplotlib.pyplot as plt

model.eval()
with torch.no_grad():
    pred = model(x_test)

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax in axes:
    j = int(torch.randint(len(x_test), (1,)))
    ax.plot(x, x_test[j, 0], "b-",  label="input IC")
    ax.plot(x, y_test[j, 0], "k-",  lw=2, label="true")
    ax.plot(x, pred[j, 0],   "r--", lw=2, label="FNO")
    err = relative_l2(pred[j:j+1], y_test[j:j+1])
    ax.set_title(f"rel. L2 = {err:.3f}"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig("fno_predictions.png", dpi=150)
```

## Zero-shot super-resolution

Because FNO parameterizes filters in the Fourier domain, a model trained at one
resolution can be **evaluated on a finer grid without retraining** — feed a
higher-resolution input tensor and the output follows. This is FNO's headline
property and a reason to prefer it when you train cheaply on coarse data but need
fine-grid predictions. Accuracy still degrades if the finer grid exposes
frequencies beyond the `n_modes` the model kept, so validate on a held-out
high-resolution set before trusting it.
