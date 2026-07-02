# SNN minimal examples

Two runnable starting points: a norse functional LIF pipeline and a shorter snntorch
equivalent. Both build a synthetic price-like signal, rate-encode it to spikes, and train
to predict next-step direction.

## Install / setup

```bash
# norse
uv pip install norse torch

# alternative — snntorch
uv pip install snntorch torch
```

GPU notes:

- Both libraries follow standard PyTorch device placement: `.to("cuda")` / `.to("cpu")`.
  Apple Silicon `mps` works for most operators in snntorch; norse's custom CUDA kernels are
  CPU/CUDA only — verify with a small test.
- SNNs unroll over `T` time steps in the forward pass. Memory grows linearly with `T`; if you
  OOM on GPU, cut `T` first before cutting batch size.

Verify install:

```python
import torch, norse; print(torch.__version__, norse.__version__)
# or
import snntorch as snn; print(snn.__version__)
```

## norse LIF pipeline on a synthetic signal (≤60 lines)

End-to-end: build a synthetic price-like signal → rate-encode to spikes → feed through a
2-layer LIF network → train to predict next-step direction.

```python
import torch, torch.nn as nn
from norse.torch.functional.lif import lif_step, LIFParameters       # unverified — see https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py
from norse.torch.module.leaky_integrator import LICell               # output integrator
# (snntorch alternative: from snntorch import Leaky, surrogate)

T, BATCH, D_IN, D_HID, D_OUT = 50, 64, 8, 64, 2
device = "cuda" if torch.cuda.is_available() else "cpu"

# 1. synthetic signal: noisy sinusoid + lag-1 label (up/down)
t = torch.arange(0, 4000) / 50.0
x = torch.sin(t) + 0.3 * torch.randn_like(t)
ret = torch.diff(x)
y = (ret > 0).long()
windows = torch.stack([x[i:i + D_IN] for i in range(len(ret) - D_IN)])
labels = y[D_IN - 1:][:len(windows)]
split = int(0.8 * len(windows))

# 2. rate-encoding: convert a real-valued window into spike trains over T steps
def rate_encode(x_window, T=T):
    # x_window: (B, D_IN). Normalise to [0,1] then Bernoulli-sample per step
    p = (x_window - x_window.min()) / (x_window.max() - x_window.min() + 1e-6)
    return torch.bernoulli(p.unsqueeze(0).expand(T, *p.shape))         # (T, B, D_IN)

# 3. tiny LIF network
class SNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(D_IN, D_HID)
        self.fc2 = nn.Linear(D_HID, D_OUT)
        self.p = LIFParameters()                                       # default tau_mem, v_th, etc.
        self.li = LICell(D_OUT, D_OUT)                                 # readout integrator
    def forward(self, spikes):
        s1 = s2 = li_state = None
        out_accum = 0.0
        for t in range(spikes.shape[0]):
            z = self.fc1(spikes[t])
            z, s1 = lif_step(z, s1, p=self.p)                          # spike & state
            z = self.fc2(z)
            z, s2 = lif_step(z, s2, p=self.p)
            out, li_state = self.li(z, li_state)
            out_accum = out_accum + out
        return out_accum / spikes.shape[0]                              # average output over T

model = SNN().to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.CrossEntropyLoss()

for epoch in range(10):
    idx = torch.randperm(split)
    for i in range(0, split, BATCH):
        b = idx[i:i + BATCH]
        spikes = rate_encode(windows[b]).to(device)
        yb = labels[b].to(device)
        opt.zero_grad()
        loss = loss_fn(model(spikes), yb)
        loss.backward(); opt.step()
    print(f"epoch {epoch} loss {loss.item():.4f}")

with torch.no_grad():
    test_spikes = rate_encode(windows[split:]).to(device)
    acc = (model(test_spikes).argmax(-1).cpu() == labels[split:]).float().mean()
    print("test acc", acc.item())
```

## snntorch alternative (≤15 lines)

```python
import snntorch as snn
from snntorch import surrogate
beta, spike_grad = 0.9, surrogate.fast_sigmoid()                       # see https://github.com/jeshraghian/snntorch/blob/master/examples/quickstart.ipynb

net = nn.Sequential(
    nn.Linear(D_IN, D_HID),
    snn.Leaky(beta=beta, spike_grad=spike_grad, init_hidden=True),
    nn.Linear(D_HID, D_OUT),
    snn.Leaky(beta=beta, spike_grad=spike_grad, init_hidden=True, output=True),
).to(device)

# forward is unrolled outside by stepping inputs T times and summing outputs
spk_out_sum = 0
for t in range(T):
    spk_out, _ = net(spikes[t])
    spk_out_sum = spk_out_sum + spk_out
loss = nn.functional.cross_entropy(spk_out_sum / T, yb)
```
