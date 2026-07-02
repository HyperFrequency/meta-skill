# vLLM Common Workflows

Step-by-step playbooks for the three most common vLLM tasks. Pair these with
[server-deployment.md](server-deployment.md), [optimization.md](optimization.md),
[quantization.md](quantization.md), and [troubleshooting.md](troubleshooting.md).

## Workflow 1: Production API deployment

Copy this checklist and track progress:

```
Deployment Progress:
- [ ] Step 1: Configure server settings
- [ ] Step 2: Test with limited traffic
- [ ] Step 3: Enable monitoring
- [ ] Step 4: Deploy to production
- [ ] Step 5: Verify performance metrics
```

**Step 1: Configure server settings** — choose configuration by model size:

```bash
# For 7B-13B models on single GPU
vllm serve meta-llama/Llama-3-8B-Instruct \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192 \
  --port 8000

# For 30B-70B models with tensor parallelism
vllm serve meta-llama/Llama-2-70b-hf \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.9 \
  --quantization awq \
  --port 8000

# For production with prefix caching
vllm serve meta-llama/Llama-3-8B-Instruct \
  --gpu-memory-utilization 0.9 \
  --enable-prefix-caching \
  --port 8000 \
  --host 0.0.0.0
```

**Step 2: Test with limited traffic** — run a load test before production:

```bash
pip install locust
# Create test_load.py with sample requests, then:
locust -f test_load.py --host http://localhost:8000
```

Verify TTFT (time to first token) < 500ms and throughput meets your target.

**Step 3: Enable monitoring** — vLLM exposes Prometheus metrics at `/metrics`
on the API server port (default 8000); no extra flag is required:

```bash
curl http://localhost:8000/metrics | grep vllm
```

Key metrics to monitor:
- `vllm:time_to_first_token_seconds` - Latency
- `vllm:num_requests_running` - Active requests
- `vllm:gpu_cache_usage_perc` - KV cache utilization

**Step 4: Deploy to production** — use the official Docker image for consistency:

```bash
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3-8B-Instruct \
  --gpu-memory-utilization 0.9 \
  --enable-prefix-caching
```

**Step 5: Verify performance metrics** — confirm the deployment meets targets:
TTFT < 500ms (short prompts), throughput at/above target req/sec, GPU
utilization > 80%, and no OOM errors in logs.

## Workflow 2: Offline batch inference

For processing large datasets without server overhead.

```
Batch Processing:
- [ ] Step 1: Prepare input data
- [ ] Step 2: Configure LLM engine
- [ ] Step 3: Run batch inference
- [ ] Step 4: Process results
```

**Step 1: Prepare input data**

```python
prompts = []
with open("prompts.txt") as f:
    prompts = [line.strip() for line in f]
print(f"Loaded {len(prompts)} prompts")
```

**Step 2: Configure LLM engine**

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-3-8B-Instruct",
    tensor_parallel_size=2,  # Use 2 GPUs
    gpu_memory_utilization=0.9,
    max_model_len=4096,
)

sampling = SamplingParams(
    temperature=0.7,
    top_p=0.95,
    max_tokens=512,
    stop=["</s>", "\n\n"],
)
```

**Step 3: Run batch inference** — vLLM batches internally, no manual chunking:

```python
outputs = llm.generate(prompts, sampling)
```

**Step 4: Process results**

```python
import json

results = []
for output in outputs:
    results.append({
        "prompt": output.prompt,
        "generated": output.outputs[0].text,
        "tokens": len(output.outputs[0].token_ids),
    })

with open("results.jsonl", "w") as f:
    for result in results:
        f.write(json.dumps(result) + "\n")
print(f"Processed {len(results)} prompts")
```

## Workflow 3: Quantized model serving

Fit large models in limited GPU memory. See [quantization.md](quantization.md)
for the full method comparison and accuracy notes.

```
Quantization Setup:
- [ ] Step 1: Choose quantization method
- [ ] Step 2: Find or create quantized model
- [ ] Step 3: Launch with quantization flag
- [ ] Step 4: Verify accuracy
```

**Step 1: Choose quantization method**
- **AWQ**: Best for 70B models, minimal accuracy loss
- **GPTQ**: Wide model support, good compression
- **FP8**: Fastest on H100 GPUs

**Step 2: Find or create quantized model** — use pre-quantized HuggingFace
models (e.g. `TheBloke/Llama-2-70B-AWQ`) or quantize your own.

**Step 3: Launch with quantization flag**

```bash
vllm serve TheBloke/Llama-2-70B-AWQ \
  --quantization awq \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.95
# Result: 70B model in ~40GB VRAM
```

**Step 4: Verify accuracy** — compare quantized vs non-quantized responses on
your task-specific evaluation set before shipping.
