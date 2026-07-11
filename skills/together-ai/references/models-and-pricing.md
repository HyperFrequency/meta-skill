# Models & pricing

All prices below are **approximate USD per million tokens** and change
frequently. Treat them as relative guides, not quotes — verify current rates at
https://www.together.ai/pricing and confirm model IDs at
https://docs.together.ai/docs/serverless-models.

## Chat / instruct models

| Model ID | Params | In $/M | Out $/M | Context | Best for |
|----------|--------|--------|---------|---------|----------|
| `meta-llama/Meta-Llama-3.1-8B-Instruct-Reference` | 8B | 0.18 | 0.18 | 131k | Fast, cheap general tasks |
| `meta-llama/Llama-3.3-70B-Instruct-Reference` | 70B | 0.88 | 0.88 | 131k | High-quality general purpose |
| `meta-llama/Llama-4-Maverick-17B-128E-Instruct` | 400B MoE | 0.27 | 0.85 | 1M | Cost-effective large model |
| `deepseek-ai/DeepSeek-V3` | 671B MoE | 1.25 | 1.25 | 128k | Top-tier reasoning and code |
| `deepseek-ai/DeepSeek-R1` | 671B MoE | 3.00 | 7.00 | 128k | Complex chain-of-thought |
| `Qwen/Qwen3-Next-80B-A3B-Instruct` | 80B MoE | 0.15 | 1.50 | 128k | Ultra-cheap MoE inference |
| `Qwen/Qwen3-235B-A22B` | 235B MoE | 0.50 | 1.50 | 128k | Powerful open-weight MoE |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | 46B MoE | 0.60 | 0.60 | 32k | Balanced MoE |
| `Qwen/Qwen3-Coder-480B-A35B-Instruct` | 480B MoE | 0.60 | 1.80 | 256k | Code generation and review |
| `google/gemma-3-27b-it` | 27B | 0.30 | 0.30 | 128k | Efficient mid-size model |

## Reasoning models

| Model ID | In $/M | Out $/M | Notes |
|----------|--------|---------|-------|
| `deepseek-ai/DeepSeek-R1` | 3.00 | 7.00 | Chain-of-thought; high output cost |
| `deepseek-ai/DeepSeek-R1-0528` | 3.00 | 7.00 | Updated R1 variant |
| `Qwen/Qwen3-Next-80B-A3B-Thinking` | 0.15 | 1.50 | MoE reasoning, very cheap |

Reasoning models emit long hidden/visible chains, so output tokens dominate the
bill — watch the output column, not the input one.

## Code models

| Model ID | In $/M | Out $/M | Notes |
|----------|--------|---------|-------|
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | 0.15 | 1.50 | Fast code MoE |
| `Qwen/Qwen3-Coder-480B-A35B-Instruct` | 0.60 | 1.80 | Largest code model |

## Cost-optimization checklist

1. **Prefer MoE models.** Mixture-of-experts activate only a fraction of
   parameters per token, giving strong price-to-performance:

   | Model | Active params | In $/M |
   |-------|---------------|--------|
   | Qwen3-Next-80B-A3B | 3B of 80B | 0.15 |
   | Llama-4-Maverick | 17B of 400B | 0.27 |
   | DeepSeek-V3 | ~37B of 671B | 1.25 |

2. **Batch non-urgent work** through the batch API for ~50% off
   (see [batch-inference.md](batch-inference.md)).

3. **Constrain output** with JSON mode to avoid retry loops
   (see [inference.md](inference.md)).

4. **Right-size the model:**
   - Simple classification/extraction → 8B (~0.18 $/M)
   - General chat/instruction → 70B (~0.88 $/M)
   - Complex reasoning/code → DeepSeek-V3 (~1.25 $/M) or R1 (~3.00 $/M)
   - Cost-sensitive high volume → cheap MoE (~0.15 $/M)

5. **Minimize `max_tokens`.** You pay for tokens actually generated, but a tight
   ceiling caps runaway generations.

6. **Stream long outputs.** Same price, faster first token, and you can abort
   early when output drifts off track.

When per-token pricing stops making sense — sustained high QPS, strict latency
SLAs, or a model you must run privately — move to dedicated or self-hosted
serving (`lambda-labs`, `modal`, `skypilot`, `vllm`, `tensorrt-llm`, `sglang`).
