---
name: gguf
description: GGUF format and llama.cpp quantization (Q2_K–Q8_0, K-quants, IQ types, imatrix) for efficient CPU/GPU/Apple Silicon inference. Use when converting HuggingFace models to GGUF, quantizing for consumer hardware, or serving local models via llama.cpp/Ollama/LM Studio. Not for NVIDIA-GPU calibration quantization (use AWQ/GPTQ), calibration-free HuggingFace quantization (HQQ), simple transformers integration (bitsandbytes), or max-throughput production serving (TensorRT-LLM/vLLM).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [GGUF, Quantization, llama.cpp, CPU Inference, Apple Silicon, Model Compression, Optimization]
dependencies: [llama-cpp-python>=0.2.0]
---

# GGUF - Quantization Format for llama.cpp

GGUF (GPT-Generated Unified Format) is the standard file format for llama.cpp, enabling efficient
inference on CPUs, Apple Silicon, and GPUs with flexible 2–8 bit quantization. This page is a router:
the quick start gets you to a running quantized model; the references hold the depth.

## When to use GGUF

**Use GGUF when:**
- Deploying on consumer hardware (laptops, desktops) or Apple Silicon (M-series) with Metal
- You need CPU inference without GPU requirements
- You want flexible quantization (Q2_K to Q8_0) with a single portable file
- You target local tools (LM Studio, Ollama, koboldcpp, text-generation-webui)

**Advantages:** universal hardware support, pure C/C++ (no Python runtime), K-quants and IQ types,
broad ecosystem, and imatrix (importance matrix) for better low-bit quality.

**Use alternatives instead:**
- **AWQ / GPTQ** — maximum accuracy with calibration on NVIDIA GPUs
- **HQQ** — fast calibration-free quantization for HuggingFace
- **bitsandbytes** — simple integration with the transformers library
- **TensorRT-LLM / vLLM** — production NVIDIA deployment with maximum throughput

## Quick start

llama.cpp builds with **CMake** (the legacy `make` build is deprecated). Binaries land in `build/bin/`.

```bash
# Build
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build                       # CPU; Metal is on by default on macOS
# cmake -B build -DGGML_CUDA=ON      # NVIDIA CUDA
cmake --build build --config Release -j

pip install -r requirements.txt      # for the conversion script
pip install llama-cpp-python         # optional Python bindings
```

```bash
# Convert HuggingFace model -> GGUF (FP16), then quantize, then run
python convert_hf_to_gguf.py ./path/to/model --outfile model-f16.gguf --outtype f16
./build/bin/llama-quantize model-f16.gguf model-q4_k_m.gguf Q4_K_M
./build/bin/llama-cli -m model-q4_k_m.gguf -ngl 35 -p "Hello, how are you?"
```

For low-bit (Q4 and below), build an importance matrix first for noticeably better quality:

```bash
./build/bin/llama-imatrix -m model-f16.gguf -f calibration.txt -o model.imatrix
./build/bin/llama-quantize --imatrix model.imatrix model-f16.gguf model-q4_k_m.gguf Q4_K_M
```

## Choosing a quantization

- **Q4_K_M** — recommended default (best quality/size balance, ~4.1 GB for 7B).
- **Q5_K_M / Q6_K** — when you have headroom and want near-original quality.
- **Q8_0** — maximum quality, minimal loss; ~7.2 GB for 7B.
- **Q2_K / Q3_K_* / IQ\*** — extreme compression for tight memory; always pair with an imatrix.

Full size/quality table, legacy types, IQ types, and the conversion workflows (HF→GGUF, imatrix,
batch multi-quant) are in **[conversion-and-quantization.md](references/conversion-and-quantization.md)**.

## Best practices

1. **Use K-quants** — Q4_K_M offers the best quality/size balance.
2. **Use imatrix** — always for Q4 and below; it materially reduces quality loss.
3. **GPU offload** — offload as many layers (`-ngl`) as VRAM/unified memory allows (99 on Apple Silicon).
4. **Context length** — start at 4096; raise only if needed (it grows the KV cache).
5. **Threads** — match physical CPU cores, not logical.
6. **Batch size** — increase `n_batch` for faster prompt processing.

## References

- **[conversion-and-quantization.md](references/conversion-and-quantization.md)** — quant type tables (K-quant/legacy/IQ), HF→GGUF / imatrix / multi-quant workflows
- **[inference-and-serving.md](references/inference-and-serving.md)** — llama-cpp-python (completion/chat/streaming), OpenAI-compatible server, hardware tuning, Ollama / LM Studio / text-generation-webui
- **[advanced-usage.md](references/advanced-usage.md)** — speculative decoding, batching, grammars, LoRA, embeddings, KV-cache/memory tuning, multi-GPU, custom builds
- **[troubleshooting.md](references/troubleshooting.md)** — build/conversion/quantization/inference/server/Apple-Silicon issues and debugging

## Resources

- **Repository**: https://github.com/ggml-org/llama.cpp
- **Python bindings**: https://github.com/abetlen/llama-cpp-python
- **Pre-quantized models**: https://huggingface.co/models?library=gguf
- **GGUF converter (web)**: https://huggingface.co/spaces/ggml-org/gguf-my-repo
