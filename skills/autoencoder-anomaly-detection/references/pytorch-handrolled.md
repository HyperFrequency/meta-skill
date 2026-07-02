# Hand-rolled PyTorch autoencoder

Use this path when PyOD's MLP-style AE isn't flexible enough: non-MLP
architectures (1-D conv AE, recurrent AE for variable-length order-flow),
custom losses (Huber, quantile), or online incremental updates PyOD doesn't ship.

```python
import torch, torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

class AE(nn.Module):
    def __init__(self, d_in, latent=4):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, 16), nn.ReLU(), nn.Linear(16, latent))
        self.dec = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, d_in))
    def forward(self, x):
        z = self.enc(x); return self.dec(z)

device = "cuda" if torch.cuda.is_available() else "cpu"
X = torch.tensor(X_train)                                 # from SKILL.md features()
ds = TensorDataset(X)
loader = DataLoader(ds, batch_size=64, shuffle=True)

model = AE(d_in=X.shape[1], latent=4).to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()

for epoch in range(50):
    for (xb,) in loader:
        xb = xb.to(device)
        opt.zero_grad(); loss = loss_fn(model(xb), xb); loss.backward(); opt.step()

with torch.no_grad():
    test = torch.tensor(X_test).to(device)
    scores = ((model(test) - test) ** 2).mean(dim=1).cpu().numpy()  # per-row recon error

import numpy as np
threshold = np.quantile(scores, 0.95)        # top 5%
anoms = scores > threshold
```

## Hand-rolled building blocks

| Symbol | What it does |
|---|---|
| `nn.Linear / nn.Conv1d` | Encoder/decoder building blocks. |
| `nn.MSELoss / nn.SmoothL1Loss` | Reconstruction loss. Smooth L1 (Huber) is more robust to fat tails. |
| `torch.optim.Adam(lr=1e-3)` | Default optimiser. |
| `torch.no_grad()` + per-row MSE | Compute scores at inference. |

## Architecture choices

- **Latent dim**: set so `latent_dim ≈ effective rank of features / 2`. Too small → underfits and flags *everything*; too large → AE memorises and flags *nothing*. Sweep `latent ∈ {2, 4, 8, 16}` and pick by held-out recon error on clean data.
- **Symmetry**: encoder and decoder mirror layer widths. Asymmetric ("undercomplete" decoder) can help when the true generator is simpler than the observed signal, but start symmetric.
- **Activations**: ReLU in hidden layers, **no activation on the final decoder layer** if features can be negative (returns!). Sigmoid/Tanh outputs squash returns and pollute scores.
- **Loss**: MSE for Gaussian-ish features, Huber/SmoothL1 for fat-tailed financial returns. For binary order-flow events (cancel/trade flags), use BCE.
- **Regularisation**: `dropout_rate=0.2` and L2 weight decay (`weight_decay=1e-5` in Adam) prevent the AE from memorising the train set.
- **Denoising trick**: add Gaussian noise to inputs (`x + 0.05 * randn_like(x)`) but reconstruct the *clean* `x`. Forces the AE to learn the manifold, not the noise — usually +5-10% on AUROC on financial data.

For Keras-based autoencoders (older docs you might find online), install
`tensorflow` and use `keras.Model` directly — this API surface ports cleanly.
