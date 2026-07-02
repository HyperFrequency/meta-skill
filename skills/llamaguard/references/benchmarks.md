# LlamaGuard Benchmarks

Accuracy comparison with other moderation systems and latency optimization notes.

## Accuracy

LlamaGuard reports strong F1 on its own test set and competitive transfer to
public benchmarks (ToxicChat, OpenAI Moderation eval). Approximate figures from
Meta's model cards / paper:

| System | Prompt classification | Response classification |
|--------|----------------------|--------------------------|
| LlamaGuard 1 (7B) | ~94.5% acc | ~95.3% acc |
| LlamaGuard 3 (8B) | Higher F1 + multilingual | Higher F1 |
| OpenAI Moderation API | Lower on adversarial prompts | n/a (input only) |
| Perspective API | Toxicity only, narrower scope | n/a |

LlamaGuard 3 adds multilingual coverage (English, French, German, Hindi,
Italian, Portuguese, Spanish, Thai) and the 14-category MLCommons taxonomy,
improving recall on weapons, privacy, and election-integrity categories that
v1's 6-category taxonomy did not cover.

Always re-measure on your own distribution — published numbers come from
curated test sets and do not guarantee in-domain performance.

## Latency (single GPU)

| Backend | Latency per request |
|---------|--------------------|
| HuggingFace Transformers (FP16) | 300-500 ms |
| vLLM | 50-100 ms |
| vLLM, batched | 20-50 ms per request |

## Latency optimization

1. **Use vLLM, not raw Transformers** — paged attention + continuous batching
   give a roughly 5-10x throughput improvement.
2. **Cap `max_tokens`** — the output is short (`safe` or `unsafe\n<Sx>`), so
   `max_tokens=20` is enough and avoids wasted decoding.
3. **`temperature=0.0`** — deterministic greedy decoding, no sampling overhead.
4. **Tensor parallelism** (`tensor_parallel_size=2`) splits the model across
   GPUs for lower latency on larger batches.
5. **INT8 weights** reduce memory bandwidth pressure and fit smaller GPUs with
   modest accuracy loss.

## Throughput

~50-100 requests/sec on a single A100 with vLLM batching; scales near-linearly
with additional replicas behind a load balancer.
