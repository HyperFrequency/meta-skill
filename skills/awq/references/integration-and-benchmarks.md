# AWQ Integration & Benchmarks

Framework integration patterns and reference performance numbers for AWQ 4-bit models.
For kernel internals, calibration tuning, fusion, and multi-GPU quantization see
`advanced-usage.md`. For errors see `troubleshooting.md`.

## Kernel backends (quick reference)

| Backend | Best for | Requirement |
|---------|----------|-------------|
| `GEMM` (default) | batch size > 1, throughput | CC 7.5+ |
| `GEMV` | single-token decode (~20% faster, batch=1 only) | CC 7.5+ |
| `marlin` | high-throughput on Ampere+ (~2x) | CC 8.0+ (A100/H100/RTX40xx) |
| `exllama` | faster prefill, AMD/ROCm | ROCm or NVIDIA |

```python
# AutoAWQ quantize-time selection
quant_config = {"zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM"}

# transformers load-time selection
from transformers import AwqConfig
config = AwqConfig(bits=4, version="marlin")
```

Full kernel variant matrix (GEMVFast, IPEX, Marlin, ExLlamaV2) lives in `advanced-usage.md`.

## HuggingFace Transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/zephyr-7B-alpha-AWQ",
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("TheBloke/zephyr-7B-alpha-AWQ")
```

Fused modules (faster, but cannot combine with FlashAttention2):

```python
from transformers import AwqConfig, AutoModelForCausalLM

config = AwqConfig(bits=4, fuse_max_seq_len=512, do_fuse=True)
model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Mistral-7B-OpenOrca-AWQ", quantization_config=config
)
```

## vLLM

```python
from vllm import LLM, SamplingParams

llm = LLM(model="TheBloke/Llama-2-7B-AWQ", quantization="awq", dtype="half")
out = llm.generate(["Explain AI"], SamplingParams(temperature=0.7, max_tokens=200))
```

vLLM, SGLang, and TensorRT-LLM all ship optimized AWQ kernels and auto-detect the
format from the model's `quantization_config`. AWQ is the default production INT4 format.

## Maintained quantization path (llm-compressor)

The standalone AutoAWQ library is archived (see SKILL.md "Maintenance status").
For new quantization runs, the maintained AWQ implementation lives in
[llm-compressor](https://github.com/vllm-project/llm-compressor) (derived from AutoAWQ
with help from its original maintainer):

```python
from llmcompressor import oneshot
from llmcompressor.modifiers.awq import AWQModifier

oneshot(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    recipe=AWQModifier(bits=4, group_size=128),
    dataset="ultrachat_200k",
)
```

The output is a `compressed-tensors` checkpoint loadable directly by vLLM and
Transformers. Verify the current API against the llm-compressor AWQ example before use.

## Supported model architectures

35+ architectures, including:
- **Llama family**: Llama 2/3, Code Llama, Mistral, Mixtral
- **Qwen**: Qwen, Qwen2, Qwen2.5, Qwen2.5-VL
- **Others**: Falcon, MPT, Phi, Yi, DeepSeek, Gemma
- **Multimodal**: LLaVA, LLaVA-Next, Qwen2-VL

```python
# Enumerate AutoAWQ's registry
from awq.models import AWQ_CAUSAL_LM_MODEL_MAP
print(list(AWQ_CAUSAL_LM_MODEL_MAP.keys()))
```

## Reference benchmarks

These are indicative figures from published AWQ benchmarks; measure on your own
hardware before relying on them.

### Memory reduction

| Model | FP16 | AWQ 4-bit | Reduction |
|-------|------|-----------|-----------|
| Mistral 7B | 14 GB | 5.5 GB | 2.5x |
| Llama 2-13B | 26 GB | 10 GB | 2.6x |
| Llama 2-70B | 140 GB | 35 GB | 4x |

### Inference speed (RTX 4090)

| Model | Prefill (tok/s) | Decode (tok/s) | Memory |
|-------|-----------------|----------------|--------|
| Mistral 7B GEMM | 3,897 | 114 | 5.55 GB |
| TinyLlama 1B GEMV | 5,179 | 431 | 2.10 GB |
| Llama 2-13B GEMM | 2,279 | 74 | 10.28 GB |

### Accuracy (perplexity, lower is better)

| Model | FP16 | AWQ 4-bit | Degradation |
|-------|------|-----------|-------------|
| Llama 3 8B | 8.20 | 8.48 | +3.4% |
| Mistral 7B | 5.25 | 5.42 | +3.2% |
| Qwen2 72B | 4.85 | 4.95 | +2.1% |
