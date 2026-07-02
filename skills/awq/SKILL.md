---
name: awq
description: "Activation-aware weight quantization (AWQ) for 4-bit LLM compression — ~2.5-3x speedup and <5% accuracy loss by protecting the ~1% of salient weights identified from activations. Use when deploying 7B-70B models on limited GPU memory, when you need faster inference than GPTQ with better accuracy on instruction-tuned/chat or multimodal models, or when serving AWQ checkpoints with vLLM/SGLang/TensorRT-LLM on Ampere+ GPUs. Not for: zero-calibration on-the-fly quantization or QLoRA fine-tuning (use bitsandbytes); maximum tool/ecosystem breadth or ExLlamaV2-first stacks (use gptq); sub-4-bit or non-NVIDIA-first targets (use gguf/hqq); CPUs without an AWQ kernel path. MLSys 2024 Best Paper."
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Optimization, AWQ, Quantization, 4-Bit, Activation-Aware, Memory Optimization, Fast Inference, vLLM Integration, Marlin Kernels]
dependencies: [autoawq, transformers>=4.45.0, torch>=2.0.0]
---

# AWQ (Activation-aware Weight Quantization)

4-bit quantization that preserves salient weights based on activation patterns,
achieving ~2.5-3x speedup with minimal accuracy loss. AWQ is the de-facto default
INT4 format for production LLM serving.

## When to use AWQ

**Use AWQ when:**
- You need 4-bit quantization with <5% accuracy loss
- Deploying instruction-tuned, chat, or multimodal models (AWQ generalizes better than GPTQ)
- You want ~2.5-3x inference speedup over FP16
- Serving with vLLM / SGLang / TensorRT-LLM
- You have Ampere+ GPUs (A100, H100, RTX 40xx) for Marlin kernels

**Use a sibling skill instead when:**
- `gptq` — you need maximum ecosystem/tool breadth, an ExLlamaV2-first stack, or older GPUs without Marlin
- `bitsandbytes` — you want zero calibration overhead (on-the-fly), or QLoRA fine-tuning
- `gguf` / `hqq` — sub-4-bit, CPU/Apple-Silicon, or non-NVIDIA-first targets

## AWQ vs GPTQ vs bitsandbytes

| Feature | AWQ | GPTQ | bitsandbytes |
|---------|-----|------|--------------|
| Speedup (4-bit) | ~2.5-3x | ~2x | ~1.5x |
| Accuracy loss | <5% | ~5-10% | ~5-15% |
| Calibration | minimal (128-1K tokens) | more extensive | none |
| Overfitting risk | low | higher | N/A |
| Best for | production inference | GPU inference | easy integration |
| vLLM support | native | yes | limited |

**Key insight**: not all weights are equally important. AWQ protects the ~1% of salient
weights identified from activation statistics, cutting quantization error without
mixed-precision overhead. Algorithm details: `references/advanced-usage.md`.

## Quick start

```bash
pip install autoawq            # Triton kernels (default)
pip install autoawq[kernels]   # optimized CUDA kernels + Flash Attention
pip install autoawq[cpu]       # Intel CPU/XPU
```

**Requirements**: Python 3.8+, CUDA 11.8+, NVIDIA Compute Capability 7.5+.

Load a pre-quantized model:

```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

name = "TheBloke/Mistral-7B-Instruct-v0.2-AWQ"
model = AutoAWQForCausalLM.from_quantized(name, fuse_layers=True)  # fuse = faster
tokenizer = AutoTokenizer.from_pretrained(name)

inputs = tokenizer("Explain quantum computing", return_tensors="pt").to("cuda")
print(tokenizer.decode(model.generate(**inputs, max_new_tokens=200)[0], skip_special_tokens=True))
```

Quantize your own model (uses the `pileval` calibration set by default; ~10-15 min for
7B, ~1 hr for 70B):

```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

path = "mistralai/Mistral-7B-Instruct-v0.2"
model = AutoAWQForCausalLM.from_pretrained(path)
tokenizer = AutoTokenizer.from_pretrained(path)

quant_config = {
    "zero_point": True,    # asymmetric quantization
    "q_group_size": 128,   # 128 is the recommended default
    "w_bit": 4,            # 4-bit weights
    "version": "GEMM",     # GEMM for batch, GEMV for single-token
}
model.quantize(tokenizer, quant_config=quant_config)
model.save_quantized("mistral-7b-awq")
tokenizer.save_pretrained("mistral-7b-awq")
```

## Deeper topics (references/)

- **`advanced-usage.md`** — algorithm/loss formula, full kernel variant matrix
  (GEMM/GEMV/GEMVFast/Marlin/ExLlamaV2/IPEX), group-size & zero-point tuning,
  custom & domain calibration, layer fusion, `modules_to_not_convert`, multi-GPU
  quantization, CPU offload, saving/sharding, benchmarking.
- **`integration-and-benchmarks.md`** — Transformers, vLLM, llm-compressor (maintained
  path), supported architectures, and reference memory/speed/perplexity numbers.
- **`troubleshooting.md`** — install/CUDA/compute-capability errors, OOM, NaN weights,
  garbage output, FlashAttention2 conflicts, AMD/ROCm, loading and vLLM issues.

## Maintenance status

The standalone **AutoAWQ** library (`casper-hansen/AutoAWQ`) was archived in May 2025
and is no longer maintained (last tested on Torch 2.6.0 / Transformers 4.51.3). The
**AWQ format and method are not deprecated** — they remain the default production INT4
format with optimized kernels in vLLM, SGLang, and TensorRT-LLM, and existing AWQ
checkpoints load unchanged.

For **new quantization runs**, prefer the maintained AWQ implementation in
[vLLM llm-compressor](https://github.com/vllm-project/llm-compressor) (derived from
AutoAWQ with its original maintainer); see `references/integration-and-benchmarks.md`.
AutoAWQ remains fine for loading/serving existing models and reproducing prior work.

## References

- **Paper**: AWQ: Activation-aware Weight Quantization (arXiv:2306.00978) — MLSys 2024 Best Paper
- **GitHub (archived)**: https://github.com/casper-hansen/AutoAWQ
- **MIT Han Lab**: https://github.com/mit-han-lab/llm-awq
- **Maintained path**: https://github.com/vllm-project/llm-compressor
- **Models**: https://huggingface.co/models?library=awq
