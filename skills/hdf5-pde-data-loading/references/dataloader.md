# PyTorch DataLoader for Neural-Operator Training

Once `load_pde_hdf5` returns `data[N, X, T, C]` and `grid[X]`, wrap it in a
`Dataset` that yields what an autoregressive neural operator needs: a short
**input window** of early timesteps, the **full trajectory** as the rollout
target, and the **grid** as coordinate features.

## Dataset

```python
import torch
from torch.utils.data import Dataset, DataLoader


class PDEDataset(Dataset):
    """Yields (input_window, full_trajectory, grid) per trajectory.

    data: float32 [N, X, T, C]  spatial-major (see layout-and-loading.md)
    grid: float32 [X] or [X, 1]
    init_step: number of leading timesteps fed as input; the remaining
               timesteps are what the model must roll out and predict.
    """

    def __init__(self, data, grid, init_step=10):
        self.data = torch.as_tensor(data, dtype=torch.float32)
        grid = torch.as_tensor(grid, dtype=torch.float32)
        self.grid = grid if grid.ndim == 2 else grid[:, None]   # [X, 1]
        self.init_step = init_step

    def __len__(self):
        return self.data.shape[0]

    def __getitem__(self, i):
        x = self.data[i, :, : self.init_step, :]   # [X, init_step, C]  input window
        y = self.data[i]                           # [X, T, C]          full target
        return x, y, self.grid
```

`init_step` is the split between "given" and "predicted". A common PDEBench recipe
is 10 input timesteps and 30 rollout steps (total T = 40 after temporal
downsampling); adjust to your horizon. Returning the full `y` lets the training
loop compute an autoregressive/pushforward loss over the whole trajectory rather
than a single next step.

## Train / validation split and DataLoaders

Split along the trajectory (N) axis so no trajectory leaks between train and val:

```python
N = data.shape[0]
n_train = int(0.9 * N)

train_ds = PDEDataset(data[:n_train], grid, init_step=10)
val_ds   = PDEDataset(data[n_train:], grid, init_step=10)

train_loader = DataLoader(
    train_ds,
    batch_size=32,
    shuffle=True,          # shuffle trajectories for training
    num_workers=2,         # parallel host-side loading
    pin_memory=True,       # faster host->GPU copies
    drop_last=True,        # keep batch shapes uniform
)
val_loader = DataLoader(
    val_ds,
    batch_size=32,
    shuffle=False,
    num_workers=2,
    pin_memory=True,
)
```

## Notes

- **Batch shapes.** A batch is `x: [B, X, init_step, C]`, `y: [B, X, T, C]`,
  `grid: [B, X, 1]`. If your operator expects channels-first, permute inside the
  model's `forward`, not in the `Dataset`, so the storage convention stays in one
  place.
- **`num_workers` and HDF5.** The loader above holds decoded NumPy/torch tensors
  in memory, so multiprocessing workers are safe. If you instead lazily read from
  an open `h5py.File` inside `__getitem__`, open the file **per worker** (in
  `worker_init_fn` or lazily on first access) — a single `h5py.File` handle shared
  across forked workers corrupts reads. Prefer eager loading unless the data does
  not fit in RAM.
- **`pin_memory`** only helps when you move batches to CUDA; leave it off for
  CPU-only runs.
- Hand `train_loader`/`val_loader` to `pytorch-lightning` (or a raw loop) to train
  the operator — model definition and optimization are out of scope for this
  skill.
