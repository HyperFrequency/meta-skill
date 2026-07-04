# GenAI Metric Conventions

Spans answer "what happened in this one run"; **metrics** answer "how is the fleet
behaving over time". The `gen_ai.*` metric conventions define a small set of instruments
so token spend and latency aggregate across every model call regardless of provider.

Metric names are stable-ish but still Development-status in OTel semconv; the instrument
*kinds* and unit codes below are the load-bearing part.

## Client-side instruments (the emitter of the request)

| Instrument | Kind | Unit | Meaning |
|---|---|---|---|
| `gen_ai.client.token.usage` | Histogram | `{token}` | Tokens per operation. Recorded **once per token type** — emit twice per call (input, output), distinguished by `gen_ai.token.type`. |
| `gen_ai.client.operation.duration` | Histogram | `s` | End-to-end client-observed duration of the operation (seconds, not ms). |

**Do not** compute your own token counters by summing histograms in app code — record the
histogram and let the backend aggregate. A separate cost counter is an extension, not
spec (see below).

### Required/recommended attributes on client metrics

Keep metric attributes **low-cardinality** — never attach request ids, user ids, or
content. Use:

- `gen_ai.operation.name` (`chat`, `embeddings`, `execute_tool`, …)
- `gen_ai.provider.name` (renamed from `gen_ai.system`)
- `gen_ai.request.model`
- `gen_ai.response.model` (when it differs from request)
- `gen_ai.token.type` — `input` | `output` — **only on `gen_ai.client.token.usage`**
- `error.type` — present only on failed operations
- `server.address`, `server.port` — the inference endpoint

The histogram buckets: OTel provides advisory bucket boundaries for token usage
(coarse, spanning single tokens to large contexts) and for duration; if your SDK lets you
set explicit bucket hints, use the semconv advisory rather than the default linear
buckets, or your token histogram will be near-useless at LLM scale.

## Server-side instruments (an inference server / gateway you operate)

Only emit these if *you* are the server (e.g. a self-hosted gateway or `llm-router`
fronting providers). A pure client must not emit server metrics.

| Instrument | Kind | Unit | Meaning |
|---|---|---|---|
| `gen_ai.server.request.duration` | Histogram | `s` | Server-side request duration. |
| `gen_ai.server.time_to_first_token` | Histogram | `s` | TTFT for streamed responses. |
| `gen_ai.server.time_per_output_token` | Histogram | `s` | Inter-token latency (steady-state generation speed). |

These pair with the streaming span field commonly recorded as
`time_to_first_token` / `gen_ai.response.time_to_first_chunk` on the span itself.

## Cost (extension — not stable spec)

There is no stable cost metric. Widely-adopted practice, and what the donor stack does,
is to compute cost **at ingest** from a versioned pricing table (regex-tiered model match,
`valid_from` timestamps so historical traces price against the rate in effect then) and
surface it as either:

- span attributes `gen_ai.usage.cost`, `gen_ai.usage.cost.input`, `gen_ai.usage.cost.output`, or
- a backend-derived metric / rollup.

Rules if you emit cost:
- Keep it in the `gen_ai.usage.` namespace so backends group it with tokens.
- Document the **currency and unit** (e.g. USD, dollars-not-cents) in a NOTICE or a
  sibling attribute — the number is meaningless otherwise.
- Prefer computing cost **once, at ingest, from tokens + a time-versioned rate table**
  rather than trusting per-provider cost fields, which are inconsistent and unversioned.
  Never recompute historical cost against today's prices.

## Metrics vs. spans — when to use which

- **Latency SLOs, token-spend dashboards, error-rate alerts** → metrics
  (`gen_ai.client.operation.duration`, `gen_ai.client.token.usage`, `error.type`).
- **"Why did *this* run cost 40k tokens / fail / loop"** → spans (`span-conventions.md`).
- Do not try to reconstruct fleet aggregates from spans (sampling makes span-derived
  totals wrong) or to debug a single run from metrics (no per-run identity).

## Emission checklist for one `chat` call

1. Start timer; open the `chat` span (`span-conventions.md`).
2. On completion, record `gen_ai.client.operation.duration` with op/provider/model attrs.
3. Record `gen_ai.client.token.usage` **twice**: `token.type=input` with input tokens,
   `token.type=output` with output tokens.
4. On error, add `error.type` to both instruments' attribute sets for that recording.
5. If you are the server, also record `gen_ai.server.*` (TTFT / per-output-token).
