---
name: vllm
description: Serves LLMs with high throughput using vLLM's PagedAttention and continuous batching. Use when deploying production LLM APIs, optimizing inference latency/throughput, or serving models with limited GPU memory via OpenAI-compatible endpoints, quantization (GPTQ/AWQ/FP8), and tensor parallelism. Do NOT use for CPU/edge or single-user inference (use llama.cpp), research/prototyping one-off generation (use HuggingFace transformers), or NVIDIA-only absolute-max throughput (use TensorRT-LLM).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [vLLM, Inference Serving, PagedAttention, Continuous Batching, High Throughput, Production, OpenAI API, Quantization, Tensor Parallelism]
dependencies: [vllm, torch, transformers]
---

# vLLM - High-Performance LLM Serving

## Quick start

vLLM achieves 24x higher throughput than standard transformers through PagedAttention (block-based KV cache) and continuous batching (mixing prefill/decode requests).

**Installation**:
```bash
pip install vllm
```

**Basic offline inference**:
```python
from vllm import LLM, SamplingParams

llm = LLM(model="meta-llama/Llama-3-8B-Instruct")
sampling = SamplingParams(temperature=0.7, max_tokens=256)

outputs = llm.generate(["Explain quantum computing"], sampling)
print(outputs[0].outputs[0].text)
```

**OpenAI-compatible server**:
```bash
vllm serve meta-llama/Llama-3-8B-Instruct

# Query with OpenAI SDK
python -c "
from openai import OpenAI
client = OpenAI(base_url='http://localhost:8000/v1', api_key='EMPTY')
print(client.chat.completions.create(
    model='meta-llama/Llama-3-8B-Instruct',
    messages=[{'role': 'user', 'content': 'Hello!'}]
).choices[0].message.content)
"
```

## Common workflows

Step-by-step playbooks live in [references/workflows.md](references/workflows.md):

- **Workflow 1 — Production API deployment**: size-based server config, load
  testing, Prometheus monitoring (`/metrics` on the API port), Docker rollout.
- **Workflow 2 — Offline batch inference**: `LLM`/`SamplingParams` engine setup
  and result extraction for large datasets without server overhead.
- **Workflow 3 — Quantized model serving**: AWQ/GPTQ/FP8 selection and launch to
  fit large models in limited VRAM (see also [references/quantization.md](references/quantization.md)).

## When to use vs alternatives

**Use vLLM when:**
- Deploying production LLM APIs (100+ req/sec)
- Serving OpenAI-compatible endpoints
- Limited GPU memory but need large models
- Multi-user applications (chatbots, assistants)
- Need low latency with high throughput

**Use alternatives instead:**
- **llama.cpp**: CPU/edge inference, single-user
- **HuggingFace transformers**: Research, prototyping, one-off generation
- **TensorRT-LLM**: NVIDIA-only, need absolute maximum performance
- **Text-Generation-Inference**: Already in HuggingFace ecosystem

## Common issues (quick reference)

| Symptom | First fix |
|---------|-----------|
| OOM on model load | `--gpu-memory-utilization 0.7 --max-model-len 4096`, or `--quantization awq` |
| Slow first token (high TTFT) | `--enable-prefix-caching`; for long prompts `--enable-chunked-prefill` |
| Model not found / custom arch | `--trust-remote-code` |
| Low throughput (<50 req/sec) | `--max-num-seqs 512`; check `nvidia-smi` GPU util is >80% |
| Inference slower than expected | tensor parallel must be a power of 2 (`--tensor-parallel-size 4`, not 3); enable speculative decoding via `--speculative-config '{"model": "DRAFT_MODEL", "num_speculative_tokens": 5, "method": "draft_model"}'` |

Full error messages, debugging steps, and performance diagnostics live in
[references/troubleshooting.md](references/troubleshooting.md).

## Advanced topics

**Server deployment patterns**: See [references/server-deployment.md](references/server-deployment.md) for Docker, Kubernetes, and load balancing configurations.

**Performance optimization**: See [references/optimization.md](references/optimization.md) for PagedAttention tuning, continuous batching details, and benchmark results.

**Quantization guide**: See [references/quantization.md](references/quantization.md) for AWQ/GPTQ/FP8 setup, model preparation, and accuracy comparisons.

**Troubleshooting**: See [references/troubleshooting.md](references/troubleshooting.md) for detailed error messages, debugging steps, and performance diagnostics.

## Hardware requirements

- **Small models (7B-13B)**: 1x A10 (24GB) or A100 (40GB)
- **Medium models (30B-40B)**: 2x A100 (40GB) with tensor parallelism
- **Large models (70B+)**: 4x A100 (40GB) or 2x A100 (80GB), use AWQ/GPTQ

Supported platforms: NVIDIA (primary), AMD ROCm, Intel GPUs, TPUs

## Resources

- Official docs: https://docs.vllm.ai
- GitHub: https://github.com/vllm-project/vllm
- Paper: "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023)
- Community: https://discuss.vllm.ai



