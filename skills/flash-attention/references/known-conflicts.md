# Flash Attention - Known Conflicts & Environment Issues

> Portions adapted from openscience (Apache-2.0).

## flash-attn vs mamba / causal-conv1d

Do not install `flash-attn` alongside `mamba` (or `mamba-ssm` / `causal-conv1d`) in
the same environment. Both packages compile custom CUDA kernels against your local
toolchain, and their build and runtime requirements can clash — producing build
failures or `undefined symbol` errors at import time.

Mitigation:

- Use separate virtual environments — one per kernel-compiling package — or
- Isolate each in its own container image.
