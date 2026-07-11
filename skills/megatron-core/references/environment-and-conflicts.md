# Environment & Dependency Conflicts

> Portions adapted from openscience (Apache-2.0).

Megatron-Core is tightly coupled to its native CUDA extensions (NVIDIA Apex,
Transformer Engine) and to a specific PyTorch build. Most setup failures are
version/ABI mismatches between these, not code bugs. Prefer the NGC PyTorch
container (`nvcr.io/nvidia/pytorch:*`), which ships a matched Apex +
Transformer Engine, over building from source.

## Do not co-install DeepSpeed and Megatron in the same environment

Megatron-Core and DeepSpeed both build against Apex and pin specific PyTorch
builds. Installing both into one environment with `pip` frequently produces
Apex/PyTorch ABI or CUDA compilation mismatches — Apex `fused_adam` /
`fused_layer_norm` build errors, or `undefined symbol` at import time. Keep them
in separate virtualenv/conda environments (or separate containers).

**Distinction:** the *integrated* Megatron-DeepSpeed fork used for BLOOM,
MT-NLG, and GPT-NeoX (see `production-examples.md`) pins mutually compatible
versions and is a supported, intentional combination. The conflict above is
about ad-hoc co-installation of the two independent packages — it does not mean
DeepSpeed and Megatron parallelism cannot be combined.

## General dependency hygiene

- Match Apex, Transformer Engine, and the CUDA toolkit to the exact `torch`
  build. Mismatches surface as import-time `undefined symbol` errors rather than
  clear messages.
- After a `torch` upgrade, rebuild Apex and Transformer Engine from the matching
  version — stale extensions silently break FP8 and fused kernels.
- When in doubt, pin the whole stack to one NGC container tag and reproduce from
  there instead of upgrading packages piecemeal.
