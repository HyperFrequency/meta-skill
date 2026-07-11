# Pricing Reference Tables

**All numbers below are volatile.** GPU rental rates, frontier API prices, and managed
training rates change monthly. Treat every figure here as an *order-of-magnitude anchor*,
not a quote. Before you commit a number to a business case, verify it against the
provider's current pricing page (websearch, or the provider console). Prices are
illustrative snapshots and provider/model names are examples of a *tier*, not endorsements.

---

## Frontier API cost tiers (per 1M tokens)

Group hosted models by output-token price, since output usually dominates cost. The point
is the *band*, not the exact cell.

| Tier | Input ($/M) | Output ($/M) | Representative use | Savings potential vs an 8B specialist |
|------|-------------|--------------|--------------------|----------------------------------------|
| Premium / reasoning | ~5–25 | ~25–170 | Hardest reasoning, agentic planning | Highest — a specialist at ~$0.05–0.15/M is 100–500x cheaper |
| Standard | ~1.5–3 | ~6–15 | General-purpose chat, most production traffic | Strong at volume; moderate traffic reaches break-even |
| Budget | ~0.1–0.5 | ~0.3–3 | Fast, cheap, high-volume | Hard to beat on price alone — specialize for *quality*, not cost |
| Open-weight / near-free | ~0 | ~0 | Basic capability, self-hosted | Cost is essentially GPU-only |

Rules of thumb:
- The **premium tier** is where specialization pays off fastest — the price gap is enormous.
- Against the **budget tier**, cost savings alone rarely justify a build. Justify it with a
  quality or latency edge the small model gives you on your specific task.
- Output tokens usually cost 3–8x input tokens. If your workload is output-heavy
  (generation) the frontier bill skews high and specialization looks better; if it is
  input-heavy (long-context classification) it skews the other way.

---

## Training cost anchors

### Managed LoRA services (no GPU ops)
Cheapest path for supported base models; you pay per example/token, provider owns the
fleet. Good when you want a fine-tune without touching infrastructure.

| Base size | Method | Cost / 1K examples (order of magnitude) | Wall-clock |
|-----------|--------|------------------------------------------|-----------|
| 8B  | LoRA | ~$2–5   | 15–30 min |
| 14B | LoRA | ~$5–10  | 30–60 min |
| 32B | LoRA | ~$10–25 | 1–3 h |
| 70B | LoRA | ~$25–60 | 3–8 h |

For exact per-token rates, read the provider's current pricing page — do not extrapolate
from this table for billing.

### Serverless GPU (per-second billing, scale-to-zero)
Best for bursty or one-off training; you pay only for the seconds you run. See the `modal`
sibling skill for how to launch these jobs.

| GPU | ~$/hour | Fits |
|-----|---------|------|
| A100-40GB | ~$1.10 | 7–14B LoRA, 7B full fine-tune |
| A100-80GB | ~$1.60 | 14–32B LoRA, 14B full |
| H100-80GB | ~$3.25 | 32–70B LoRA, large batches |

Typical run costs (LoRA, a few epochs):
- 8B, ~5K examples, 3 epochs → ~1–2 h on A100 → **~$1–3**
- 14B, ~10K examples, 3 epochs → ~3–5 h on A100-80GB → **~$5–8**
- 70B, ~10K examples, 2 epochs → ~8–12 h on H100 → **~$26–39**

### Dedicated / reserved GPU (billed while held)
Best for multi-day training, large-scale RL, or when you also want the box for inference.
You pay for the whole reservation whether or not the GPU is busy — see
`references/decision-framework.md` on utilization risk. See `lambda-labs` and `skypilot`
siblings for provisioning.

| GPU | ~$/hour | Fits |
|-----|---------|------|
| A100-80GB  | ~$1.50 | Standard training |
| H200-141GB | ~$3.00 | Large models, faster training |
| B200-192GB | ~$4.50 | Cutting-edge, maximum throughput |

---

## Self-hosted inference throughput anchors

Reference numbers for a single GPU serving with a batching engine (e.g. vLLM — see the
`vllm`, `sglang`, `tensorrt-llm` siblings). Throughput is **aggregate across a batch**, not
per-request; you only hit these numbers with enough concurrent traffic to fill the batch.

| Model | GPU | Tokens/sec (batched) | Implied $/M tokens |
|-------|-----|----------------------|--------------------|
| 8B  | A100-80GB | ~3,000–5,000 | ~$0.09–0.15 |
| 8B  | H100-80GB | ~5,000–8,000 | ~$0.11–0.18 |
| 14B | A100-80GB | ~1,500–3,000 | ~$0.15–0.30 |
| 14B | H100-80GB | ~3,000–5,000 | ~$0.18–0.30 |
| 32B | H100-80GB | ~800–1,500   | ~$0.60–1.10 |
| 70B | 2×H100    | ~500–1,000   | ~$1.80–3.60 |

Key insight: a specialized **8B** model self-served lands around **$0.05–0.15/M tokens** vs
**$5–25/M** for the premium frontier tier — roughly **50–500x cheaper per request**. The
gap narrows sharply against the budget tier and as model size grows.

Quantization (see `awq`, `gptq`, `gguf`, `bitsandbytes` siblings) and speculative decoding
(`speculative-decoding` sibling) raise tokens/sec and lower $/M further — factor them in if
you have measured them, but do not assume them in a first-pass estimate.

---

## What to verify before quoting any number
1. Current frontier price for the *exact* model + tier you would replace (input and output).
2. Current GPU $/hour on the provider you will actually use, in the region you will use.
3. Your *measured* tokens/sec for your model + batch profile — vendor benchmarks are optimistic.
4. Whether the self-hosted price assumes ~100% GPU utilization (it usually does; real
   utilization is lower — see the utilization failure mode in the decision framework).
