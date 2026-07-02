# LlamaGuard Deployment Guide

Production deployment patterns for serving LlamaGuard as a moderation service.

## Model IDs

| Version | HuggingFace ID | Params | Categories |
|---------|----------------|--------|------------|
| LlamaGuard 1 | `meta-llama/LlamaGuard-7b` | 7B | 6 (S1-S6) |
| LlamaGuard 2 | `meta-llama/Meta-Llama-Guard-2-8B` | 8B | 11 |
| LlamaGuard 3 | `meta-llama/Llama-Guard-3-8B` | 8B | 14 (MLCommons) |
| LlamaGuard 3 INT8 | `meta-llama/Llama-Guard-3-8B-INT8` | 8B | 14 |

All require accepting Meta's license on the model page and `huggingface-cli login`.

## vLLM serving (recommended)

vLLM provides an OpenAI-compatible server with high throughput batching:

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-Guard-3-8B \
  --tensor-parallel-size 1 \
  --max-model-len 8192 \
  --port 8000
```

Query the chat completions endpoint with the moderation conversation; the model
returns `safe` or `unsafe\n<category>`.

## AWS Sagemaker

Deploy via the HuggingFace Deep Learning Container (TGI backend):

```python
from sagemaker.huggingface import HuggingFaceModel

hub = {
    "HF_MODEL_ID": "meta-llama/Llama-Guard-3-8B",
    "HF_TASK": "text-generation",
    "HUGGING_FACE_HUB_TOKEN": "<token>",  # supply via Secrets Manager, never inline
}

model = HuggingFaceModel(
    image_uri=get_huggingface_llm_image_uri("huggingface", version="2.0.0"),
    env=hub,
    role=role,
)
predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.g5.2xlarge",  # single A10G, fits 8B in FP16
)
```

## Kubernetes / scaling strategies

- Run the vLLM container behind a `Deployment` with a GPU node selector
  (`nvidia.com/gpu: 1`) and an HTTP readiness probe on `/health`.
- Scale horizontally with the Horizontal Pod Autoscaler keyed on request
  latency or GPU utilization (via DCGM exporter + Prometheus).
- Use INT8 weights (`Llama-Guard-3-8B-INT8`) to fit on smaller GPUs (T4/A10)
  and roughly halve VRAM.
- Co-locate the moderation service with the main LLM to minimize network hops,
  or run it as a sidecar so input/output checks add minimal latency.

## Container quickstart (Ollama / llama.cpp)

For lightweight or local deployment, GGUF builds run under Ollama, llama.cpp,
LM Studio, or Jan:

```bash
ollama run llama-guard3
```

This trades throughput for simplicity and CPU/edge compatibility.
