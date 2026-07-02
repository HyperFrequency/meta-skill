# Installation

Tested against **torch-geometric 2.7.x** (Oct 2025). Requires **Python 3.10+** and **PyTorch 2.6+**.

```bash
# 1. Install PyTorch first (match your CUDA/CPU setup — see https://pytorch.org/get-started/locally/)
uv pip install torch

# 2. Core PyG (no extension wheels required for basic usage)
uv pip install torch_geometric
```

Optional accelerated ops (`pyg-lib`, `torch-scatter`, `torch-sparse`, `torch-cluster`) are **not required** for basic PyG usage (since PyG 2.3). Install version-matched wheels from the [PyG wheel index](https://data.pyg.org/whl) after checking your PyTorch and CUDA versions:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda)"
# Then install wheels for your torch+CUDA combo, e.g.:
uv pip install pyg-lib torch-scatter torch-sparse torch-cluster \
  -f https://data.pyg.org/whl/torch-2.8.0+cu128.html
```

Check your installed version:

```python
import torch_geometric
print(torch_geometric.__version__)
```

**Conda:** the `pyg` conda channel is no longer maintained for PyTorch >2.5 — use `uv pip install` and the wheel index above instead.

## PyG 2.7 notes

PyG 2.7 dropped Python 3.9 and PyTorch ≤2.5. See the [2.7.0 release notes](https://github.com/pyg-team/pytorch_geometric/releases/tag/2.7.0) for PyTorch 2.6–2.8 compatibility tables. `torch_geometric.distributed` is deprecated — use standard `torch.distributed` DDP (see `scaling.md`).
