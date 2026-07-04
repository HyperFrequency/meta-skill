---
name: tensorzero-flywheel
version: 0.1.0
description: Design and build the neuro-centrifuge inference-to-feedback-to-optimization FLYWHEEL — metrics/feedback tables, episode reward model, variant A/B experimentation, and curated fine-tune/prompt-evolution loops that turn logged LLM inferences into measurable, regression-gated improvements. Distilled from the TensorZero donor (Apache-2.0, pinned 62eb8f63e). Use WHEN wiring the feedback-store / experiment-tracker / model-optimizer / prompt-evolver planes, defining boolean/float metrics at inference or episode level, curating datapoints (incl. DPO dispreferred outputs) from live traffic, standing up weighted or Track-and-Stop variant experiments, running per-variant regression queries, or launching GEPA/SFT/RFT optimization jobs against collected feedback. NOT for GEPA search-engine internals (use gepa-evolve), single-prompt optimization with no feedback store (use prompt-optimize), backtest/purged-CV strategy evaluation (use model-evaluation), or generic tracing setup (use instrument).
compatibility: Works with Claude Code, OpenAI Codex, Cursor, and any Agent Skills-compatible tool. Reasoning/design skill — no runtime deps.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - Bash
---

# TensorZero Flywheel — Inference → Feedback → Optimization

You are designing or building the **neuro-centrifuge LLMOps flywheel**: the closed loop where every LLM
inference is stored, attached to feedback/metrics, and mined to improve the prompts, variants, and models
that produced it. This skill is the **behavioral spec** for that loop, distilled clean-room from the
TensorZero donor. It does not ship TensorZero — it tells you what to build in the neuro-centrifuge planes.

## The flywheel in one turn

```
        ┌──────────────────────────────────────────────────────────┐
        │                                                          ▼
   [Inference]  →  [Store]  →  [Feedback/Metrics]  →  [Experiment]  →  [Optimize]
   llm-router      feedback-     feedback-store        experiment-      model-optimizer
   (variant           store       (boolean/float,        tracker         (SFT/RFT/DICL)
    sampled,       (Chat/Json/    comments,             (weighted A/B,   prompt-evolver
    cached,         ModelInf,      demonstrations,       Track-&-Stop,   (GEPA loop)
    cost-tracked)   episodes)      DPO pairs)            regression         │
        ▲                                                queries)           │
        └────────────── promote winner (label move, no code change) ◀───────┘
```

Turn is closed when a winning variant/prompt/model is **promoted by moving a registry label** — never by
editing generated code (D1-safe; see `references/optimization.md` on the ADAS caution).

## Route by what you're doing

Read the SKILL through, then open **only** the reference(s) your task needs. Do not read all four by default.

| Your task | Read |
|---|---|
| Understand the whole loop, the four planes, and which TensorZero feature maps to which plane | `references/flywheel-architecture.md` |
| Define metrics; design feedback/metric tables; episode reward model; curate datapoints & DPO pairs from live traffic | `references/feedback-and-metrics.md` |
| Stand up variants, weighted A/B, Track-and-Stop bandit, per-variant regression queries | `references/experimentation.md` |
| Launch GEPA prompt evolution, SFT/RFT/DICL fine-tune jobs, wire the Loop-1 EvolutionWorkflow | `references/optimization.md` |
| Provenance, license boundaries, pinned SHA, full port table, what to SKIP | `references/donor-provenance.md` |

## First principles (apply before touching any plane)

1. **Config first.** neuro-centrifuge's `flywheel-config` (functions / variants / metrics / evals) is one
   large cross-referencing model. Port/define config + inference types **before** anything else — extraction
   fights the dependency graph otherwise. See `references/flywheel-architecture.md`.
2. **Postgres is canonical; ClickHouse is skipped.** Treat the donor's `docs/gateway/data-model.mdx` as the
   schema *spec*, not its ClickHouse DDL. All the flywheel tables land in Postgres migrations.
3. **Metrics are typed and leveled.** Every metric is `boolean|float` × `min|max` (optimize direction) ×
   `inference|episode` (level). This triple is what the whole loop keys on — get it right first.
4. **Episodes span workflows.** A UUIDv7 `episode_id` groups many inferences into one multi-step task, so
   episode-level feedback becomes the **reward signal** for the whole trajectory, not a single call.
5. **Everything is regression-gated.** No promotion without a variance-aware compare vs the current baseline
   (n≥3 trials/input). The experiment plane owns this gate; see `references/experimentation.md`.
6. **Loops mutate payloads, never code.** Prompt/variant/config genomes evolve; generated code does not.

## Boundaries — do NOT

- Do **not** re-implement the GEPA reflective-proposer/Pareto **engine** here — that is `gepa-evolve`
  (canonical engine = gepars). This skill wires GEPA *as an optimizer job* against the feedback store and
  describes the Loop-1 orchestration only.
- Do **not** use this for optimizing a single prompt with no stored feedback/metrics — that is
  `prompt-optimize`.
- Do **not** use this for trading-strategy evaluation (purged CV, PBO, deflated Sharpe) — that is
  `model-evaluation`. The word "evaluation" here means LLM-inference scoring, a different domain.
- Do **not** add ClickHouse, the OpenAI-compatible gateway facade, gateway auth, or the TS/v8 judge executor
  to the Rust planes — all SKIP/deferred. See `references/donor-provenance.md`.
- Do **not** copy TensorZero source into neuro-centrifuge repos without a provenance header + the pinned
  donor SHA (`62eb8f63e`). It is Apache-2.0 (permissive) but provenance is mandatory (D2).

## Cross-links

- **gepa-evolve** — the population/reflective GEPA search engine this loop *invokes* as an optimizer.
- **prompt-optimize** — single-prompt optimization; the leaf this scales up into a feedback-driven loop.
- **model-evaluation** — quant strategy evaluation; namesake but a distinct domain, not the LLM-eval here.
- **instrument** / **model-evaluation** siblings in neuro-centrifuge handle tracing and scoring convention;
  this skill consumes their scores, it does not define the OTel/semconv layer.
