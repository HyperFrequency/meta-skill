---
name: hqq
description: Half-Quadratic Quantization (HQQ) for compressing LLM weights to 8/4/3/2/1-bit without any calibration data. Use when you need fast, dataset-free quantization, mixed-precision per-layer configs, or deployment via HuggingFace Transformers/vLLM, including LoRA/PEFT fine-tuning of quantized models. Do NOT use when calibration data is available and you want maximum accuracy (use GPTQ/AWQ), for simple 8/4-bit without custom backends (use bitsandbytes), or for CPU/Apple-Silicon inference (use llama.cpp/GGUF).
version: 1.0.0
author: Orchestra Research
license: Apache-2.0
tags: [Quantization, HQQ, Optimization, Memory Efficiency, Inference, Model Compression]
dependencies: [hqq>=0.2.0, torch>=2.0.0]
---

# HQQ - Half-Quadratic Quantization

Fast, calibration-free weight quantization supporting 8/4/3/2/1-bit precision with
multiple optimized inference backends (PyTorch, ATEN, TorchAO, Marlin, BitBlas, GemLite).

## When to use HQQ

**Use HQQ when:**
- Quantizing without calibration data (no dataset needed) — quantize any model instantly
- You need speed: minutes vs hours for GPTQ/AWQ
- Deploying via HuggingFace Transformers or vLLM
- Fine-tuning quantized models with LoRA/PEFT (QLoRA-style)
- Experimenting with extreme quantization (2-bit, 1-bit) or mixed precision per layer

**Use alternatives instead:**
- **GPTQ / AWQ** — calibration data available and you want maximum accuracy / production serving
- **bitsandbytes** — simple 8-bit/4-bit without custom backends
- **llama.cpp / GGUF** — CPU inference, Apple Silicon deployment

See sibling skills under `neuro-centrifuge/optimization/` for those alternatives.

## Decision logic

| Goal | nbits | group_size | Notes |
|------|-------|-----------|-------|
| Default / best quality-size tradeoff | 4 | 64 | Start here for most models |
| Aggressive memory savings | 2-3 | 16-32 | Smaller groups recover quality at low bits |
| Max fidelity | 8 | 64 | Near-lossless |
| Mixed precision | per-layer | per-layer | Keep attention high, compress MLP/experts (esp. MoEs) |

Backend choice (set via `HQQLinear.set_backend(...)`): `marlin` for fastest 4-bit on
Ampere+ GPUs, `torchao_int4` for flexible 4-bit, `pytorch` for max compatibility.
Full backend table → [references/integration.md](references/integration.md).

## Quick start

```bash
pip install hqq            # add [torchao] / [marlin] / [bitblas] for those backends
```

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, HqqConfig
import torch

# Calibration-free 4-bit quantization at load time
quant_config = HqqConfig(nbits=4, group_size=64)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    dtype=torch.float16,
    quantization_config=quant_config,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

inputs = tokenizer("The capital of France is", return_tensors="pt").to(model.device)
print(tokenizer.decode(model.generate(**inputs, max_new_tokens=20)[0]))

model.save_pretrained("./llama-8b-hqq-4bit")   # reload later, no re-quantization
```

Always verify generation quality after quantizing — low-bit configs can degrade output.

## Best practices

1. Start at 4-bit / group_size=64; only go lower if memory forces it.
2. At 2-bit, drop group_size to 16 to recover quality.
3. Keep attention layers higher-precision; compress MLP/expert layers more.
4. Pick the backend for your hardware (Marlin on Ampere+); `torch.compile` for extra speedup.
5. For fine-tuning, use LoRA with r=16-32.

## References

- **[Integration guide](references/integration.md)** — full HuggingFace / vLLM / PEFT
  usage, low-level `BaseQuantizeConfig`/`HQQLinear` API, backend table, end-to-end workflows
- **[Advanced usage](references/advanced-usage.md)** — custom backends, sensitivity-based
  mixed precision, axis/group-size tuning, ONNX/SafeTensors export, benchmarking
- **[Troubleshooting](references/troubleshooting.md)** — OOM, NaNs, backend errors,
  quality/perplexity degradation, integration fixes

## Resources

- Repository: https://github.com/mobiusml/hqq
- HuggingFace models: https://huggingface.co/mobiuslabsgmbh
- HF Transformers HQQ docs: https://huggingface.co/docs/transformers/quantization/hqq
- Version: 0.2.0+ · License: Apache 2.0
