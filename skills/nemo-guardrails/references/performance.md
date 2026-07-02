# Performance & Latency Optimization

Guardrails add LLM and model-server calls around your main generation, so latency
is the primary cost. The goal is to minimize extra round trips and keep heavy
checks off the critical path.

## Where the latency goes

- **Pattern / heuristic checks**: <1 ms (no model call).
- **Embedding intent matching**: a few ms (local embedding model).
- **LLM-based rails** (self-check input/output, fact-check): 50-200 ms each,
  dominated by the judging LLM round trip.
- **Model-server rails** (Llama Guard, jailbreak detection model): 100-300 ms on
  a T4-class GPU.

A naive config (dialog + input self-check + output self-check + fact-check) can
issue 4-5 sequential LLM calls per turn. Reducing call count matters most.

## Single LLM call mode

The biggest single win for Colang 1.0 dialog rails. Setting
`single_llm_call.enabled: true` collapses the canonical-form prediction, next-step
decision, and bot message generation into one LLM call instead of three:

```yaml
rails:
  dialog:
    single_call:
      enabled: true
```

Tradeoff: output quality can drop slightly because the model decides intent and
response simultaneously. Benchmark on your prompts before enabling in production.

## Choose cheaper judges

Input/output rails do not need your most expensive model. Point safety rails at a
smaller/faster model:

```yaml
models:
  - type: main
    engine: openai
    model: gpt-4o
  - type: self_check_input
    engine: openai
    model: gpt-4o-mini
```

LLM-as-judge tasks (toxicity, jailbreak yes/no) are well within the reach of
small models and cut latency and cost substantially.

## Use embeddings & local caching

- Embedding-based intent matching avoids an LLM call for routing; keep example
  utterances tight so matches are confident.
- The embeddings search provider can be swapped (e.g. FastEmbed, or a vector
  store like Annoy) for faster startup and lookup.
- Prompt/response caching at the LLM client layer (e.g. an LLM proxy with a cache)
  avoids re-judging identical inputs.

## Keep cheap checks first, expensive checks last

Order input flows so deterministic, near-zero-cost checks (regex jailbreak
heuristics, blocklists, PII pattern match) run before any LLM/model-server call.
A request blocked by a heuristic never pays for the LLM judge.

```yaml
rails:
  input:
    flows:
      - jailbreak detection heuristics   # fast, no model call
      - self check input                 # LLM, only if it passes heuristics
```

## Streaming and output rails

Output rails normally require the full bot message before judging, which adds
latency on top of generation. NeMo supports **streaming output rails** that
validate chunks as they arrive, so the user sees tokens sooner. Enable streaming
on the main model and configure output-rail streaming where supported.

## Scaling

- LLM-based and model-server rails are the bottleneck under load; run Llama Guard
  / judge models behind a batching server (vLLM) and size GPU capacity to peak QPS.
- Cache aggressively for high-duplication traffic (FAQs, repeated prompts).
- Profile end-to-end: measure added latency per rail and drop or downgrade rails
  that do not earn their cost.

## References

- Generation options & single-call: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/advanced/generation-options.html
- Streaming: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/advanced/streaming.html
- Embedding search providers: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/advanced/embedding-search-providers.html
