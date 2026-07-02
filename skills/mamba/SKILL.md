---
name: mamba
description: Selective state-space model (SSM) architecture with O(n) linear complexity vs Transformers' O(n²); ~5× faster autoregressive inference, no KV cache, constant memory per token. Covers Mamba-1 (d_state=16) and Mamba-2 (d_state=128, multi-head), the mamba-ssm package, and pretrained state-spaces models (130M-2.8B). USE WHEN building, fine-tuning, or serving long-context (100K+ token) sequence models, streaming/low-memory inference, or comparing SSMs to attention. NOT FOR short-context tasks where Transformers win on quality, RNN-Transformer hybrids (use RWKV), retention networks (RetNet), or long-convolution models (Hyena); not a trading/backtest skill.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Model Architecture, Mamba, State Space Models, SSM, Linear Complexity, Long Context, Efficient Inference, Hardware-Aware, Alternative To Transformers]
dependencies: [mamba-ssm, torch, transformers, causal-conv1d]
---

# Mamba - Selective State Space Models

## Quick start

Mamba is a state-space model architecture achieving O(n) linear complexity for sequence modeling.

**Installation**:
```bash
# Install causal-conv1d (optional, for efficiency)
pip install causal-conv1d>=1.4.0

# Install Mamba
pip install mamba-ssm
# Or both together
pip install mamba-ssm[causal-conv1d]
```

**Prerequisites**: Linux, NVIDIA GPU, PyTorch 1.12+, CUDA 11.6+

**Basic usage** (Mamba block):
```python
import torch
from mamba_ssm import Mamba

batch, length, dim = 2, 64, 16
x = torch.randn(batch, length, dim).to("cuda")

model = Mamba(
    d_model=dim,      # Model dimension
    d_state=16,       # SSM state dimension
    d_conv=4,         # Conv1d kernel size
    expand=2          # Expansion factor
).to("cuda")

y = model(x)  # O(n) complexity!
assert y.shape == x.shape
```

## Common workflows

Full runnable code for each lives in
[references/usage-examples.md](references/usage-examples.md). Summary:

- **Build a Mamba-2 LM + generate** — `MambaLMHeadModel(MambaConfig(...,
  ssm_cfg=dict(layer="Mamba2", d_state=128, headdim=64)))`, then `model.generate(...)`.
- **Load pretrained** — `MambaLMHeadModel.from_pretrained("state-spaces/mamba-2.8b")`
  (NOT HF `AutoModel`); pair with the GPT-NeoX tokenizer
  (`EleutherAI/gpt-neox-20b`). Sizes: 130m / 370m / 790m / 1.4b / 2.8b.
- **Mamba-1 vs Mamba-2 block** — `Mamba(d_state=16)` vs `Mamba2(d_state=128,
  headdim=64, ngroups=1)`; Mamba-2 adds multi-head structure, RMSNorm, and
  tensor parallelism.
- **Benchmark vs Transformers** — run the repo's
  `benchmarks/benchmark_generation_mamba_simple.py` comparing
  `state-spaces/mamba-2.8b` vs `EleutherAI/pythia-2.8b` with matched
  `--topp/--temperature/--repetition-penalty`; speedup grows with sequence
  length. Measured numbers in [references/benchmarks.md](references/benchmarks.md).

## When to use vs alternatives

**Use Mamba when**:
- Need long sequences (100K+ tokens)
- Want faster inference than Transformers
- Memory-constrained (no KV cache)
- Building streaming applications
- Linear scaling important

**Advantages**:
- **O(n) complexity**: Linear vs quadratic
- **5× faster inference**: No attention overhead
- **No KV cache**: Lower memory usage
- **Million-token sequences**: Hardware-efficient
- **Streaming**: Constant memory per token

**Use alternatives instead**:
- **Transformers**: Need best-in-class performance, have compute
- **RWKV**: Want RNN+Transformer hybrid
- **RetNet**: Need retention-based architecture
- **Hyena**: Want convolution-based approach

## Common issues

**Issue: CUDA out of memory**

Reduce batch size or use gradient checkpointing:
```python
model = MambaLMHeadModel(config, device="cuda", dtype=torch.float16)
model.gradient_checkpointing_enable()  # Enable checkpointing
```

**Issue: Slow installation**

Install binary wheels (not source):
```bash
pip install mamba-ssm --no-build-isolation
```

**Issue: Missing causal-conv1d**

Install separately:
```bash
pip install causal-conv1d>=1.4.0
```

**Issue: Model not loading from HuggingFace**

Use `MambaLMHeadModel.from_pretrained` (not `AutoModel`):
```python
from mamba_ssm.models.mixer_seq_simple import MambaLMHeadModel
model = MambaLMHeadModel.from_pretrained("state-spaces/mamba-2.8b")
```

## Advanced topics

- **Architecture & selective SSM**: [references/architecture-details.md](references/architecture-details.md) — S6 mechanism, state-space equations, Mamba-2 multi-head structure, and how selectivity enables O(n) complexity.
- **Benchmarks & performance**: [references/benchmarks.md](references/benchmarks.md) — measured throughput/latency vs Transformers across sequence lengths, memory profile, hardware-aware design.
- **Training**: [references/training-guide.md](references/training-guide.md) — from-scratch setup, training loop, and distributed/tensor-parallel notes.

## Hardware requirements

- **GPU**: NVIDIA with CUDA 11.6+
- **VRAM**:
  - 130M model: 2GB
  - 370M model: 4GB
  - 790M model: 8GB
  - 1.4B model: 14GB
  - 2.8B model: 28GB (FP16)

See [references/benchmarks.md](references/benchmarks.md) for measured speed/memory
gains vs Transformers across sequence lengths.

## Resources

- Paper (Mamba-1): https://arxiv.org/abs/2312.00752 (Dec 2023)
- Paper (Mamba-2): https://arxiv.org/abs/2405.21060 (May 2024)
- GitHub: https://github.com/state-spaces/mamba ⭐ 13,000+
- Models: https://huggingface.co/state-spaces
- Docs: Repository README and wiki


