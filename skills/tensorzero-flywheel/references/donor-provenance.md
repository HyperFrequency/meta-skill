# Donor Provenance, License & Full Port Table

The single reference for **where the flywheel spec comes from, what license governs it, and exactly which
donor feature maps to which neuro-centrifuge plane and phase.** Consult before porting any code.

## Donor identity

- **Repo:** TensorZero (`tensorzero`), an open-source LLMOps platform (gateway + observability + evaluation +
  optimization + experimentation).
- **License:** **Apache-2.0** (verified from `LICENSE` in the donor tree). Permissive — code may be adapted
  into neuro-centrifuge repos.
- **Pinned donor SHA:** `62eb8f63e8ec62018d70420dbf1a8c5d1c026315` (short `62eb8f63e`, dated 2026-06-04).
- **Local path:** `/Users/DanBot/neuro-centrifuge-repos/tensorzero/`.
- **Core crate:** `crates/tensorzero-core/` — one large cross-referencing crate. **Port `flywheel-config` +
  inference types first** or extraction fights the dependency graph (explicit PRD risk note).

## Licensing discipline (mandatory)

- **Apache-2.0 → adaptation allowed**, but every ported file **must** carry a provenance header naming the
  donor + the pinned SHA (`62eb8f63e`) (D2 rule). Referencing struct/enum names and behaviors (as this skill
  does) is fine and standard.
- **Do NOT** cross-contaminate from differently-licensed donors while working in this plane:
  - `openobserve` (**AGPL-3.0**) → clean-room reimplementation from observed schemas/behaviors **only**;
    parity tests assert behavior, never share code. (Its concern is `trace-store`, not the flywheel.)
  - `copula-dependency` (**BUSL-1.1**), `gitnexus*` (**PolyForm-NC**), Anthropic-proprietary skills
    (pdf/pptx/docx) → do not copy.
  - `meta_skill` (**MIT + OpenAI/Anthropic rider**) → clean-room behavioral spec only, no copied code.
  - `tensorzero` / `episteme` / `dspy-rs` / `lightspeed` are **Apache-2.0 / MIT** — safe to reference.

## Full port table — tensorzero → neuro-centrifuge

Legend: **P1** = phase 1 (D6 exit path) · **P2** = phase 2 · **REF** = parity/reference only · **SKIP** = not ported.

| Donor feature | Port target | Phase |
|---|---|---|
| Ordered provider routing + fallback (raw failed-provider capture) | `llm-router` | P1 |
| Provider adapter set (openrouter/anthropic/openai-compatible first; rest = parity refs) | `llm-router` | P1 |
| Centralized retry (backon; non-retryable classification) | `llm-router` | P1 |
| Inference caching (CacheKey, read/write modes, streaming chunk replay; Redis backend, D9-allowlisted) | `llm-router` | P1 |
| Config model (functions/variants/metrics/evals; Uninitialized→validated; ts-rs+JsonSchema TS/Rust parity) | `flywheel-config` | P1 |
| Prompt templates + schemas per variant (the GEPA mutation unit) | `experiment-tracker` (prompt registry) | P1 |
| Best-of-N sampling variant (judge-selected) | `harness_deliberation` | P1 |
| Mixture-of-N fusion variant | `harness_deliberation` | P1 |
| Static A/B experimentation (weighted VariantSampler, namespaces) | `experiment-tracker` | P1 |
| Adaptive Track-and-Stop bandit (anytime-valid stopping) — port **with its tests** or defer | `experiment-tracker` | P2 |
| Episode model (UUIDv7 episode_id spanning multi-inference workflows) | `feedback-store` | P1 |
| Inference storage schema (Chat/Json/ModelInference + datapoints) — **Postgres migrations canonical, ClickHouse skipped** | `feedback-store` | P1 |
| Feedback API (boolean/float metrics, comments, demonstrations-as-gold-labels) | `feedback-store` | P1 |
| Variant-performance regression queries (FeedbackByVariant, per-variant mean/variance) | `experiment-tracker` | P1 |
| Dataset/datapoint curation from live inferences (`into_datapoint_insert`) | `feedback-store` | P1 |
| RenderedSample + DPO `dispreferred_outputs` curation | `feedback-store` (schema P1; consumed P2) | P1/P2 |
| GEPA optimizer (analyze/mutate/pareto/evaluate; durable + sequential) | `prompt-evolver` (pattern; engine = gepars) | P1 |
| SFT/RFT fine-tune job launchers (OpenAI/Fireworks/Together/GCP Vertex) | `model-optimizer` | P2 |
| DICL variant + example curation | `harness_deliberation` + Store plane | P2 |
| Config snapshot + canonical hash (re-run any inference under its exact config) | `experiment-tracker` + `flywheel-config` | P1 |
| OTel GenAI conventions serde mapping (dependency-free) + OpenInference companion | `trace-store` telemetry | P1 |
| Hardened OTel export (span-leak detector, in-flight TaskTracker shutdown) | telemetry runtime layer | P1 |
| Cost & usage tracking (CostRate tables, streaming cost) | `llm-router` → surfaced in `experiment-tracker` | P1 |
| Autopilot durable-agent tool surface (InferenceTool/FeedbackTool/RunEvaluationTool/LaunchOptimizationWorkflowTool) | `harness_worker` + `prompt-evolver` | P1 |
| TaskTool/SimpleTool + hidden side-info pattern | `harness_worker` (pattern only) | P1 |
| Rate limiting (scoped rules, token borrows; Postgres/Valkey) | `llm-router` | P2 |
| Batch inference + buffered DB writes | `llm-router` / `feedback-store` | P2 |
| Provider-proxy caching MITM (deterministic provider tests) | dev-tooling (test infra, not shipped) | P1 |
| OpenAI-compatible facade, gateway auth, rmcp MCP surface | optional / REF | P2/REF |
| TS-judge v8/SES executor | **SKIP** in Rust (TS judges run on the first-party TS spine) | — |
| ChainOfThought variant (deprecated upstream #5298) | **SKIP** | — |

## Carried risks (from the PRD)

- **tensorzero-core is one large cross-referencing crate** — port `flywheel-config` + inference types first.
- Treat **`docs/gateway/data-model.mdx` as the schema spec, not the ClickHouse DDL** — the DDL is skipped;
  the *data model it describes* is what you implement in Postgres.
- The scorer **execution** engine (for LLM-judge evals) is enterprise-closed upstream in a sibling donor
  (openobserve); the first-party executor's ground truth is the D13 eval-class specs, not donor parity.

## Verify before you port

The struct/enum/field names cited across these references were read directly from the donor at the pinned SHA.
Before writing a port, re-read the specific donor module (paths below) to confirm the current shape — do not
trust a memory of the API:

- Metrics / config: `crates/tensorzero-core/src/config/mod.rs`, `config/built_in.rs`
- Feedback endpoint: `crates/tensorzero-core/src/endpoints/feedback/mod.rs`
- Storage / datapoints / DPO: `crates/tensorzero-core/src/stored_inference.rs`, `src/db/stored_datapoint.rs`
- Variant stats: `crates/tensorzero-core/src/db/variant_statistics.rs`
- Experimentation: `crates/tensorzero-core/src/experimentation/`
- Optimization / GEPA: `crates/tensorzero-core/src/optimization/` (`gepa.rs`, `mod.rs`)
- Cost: `crates/tensorzero-core/src/cost.rs`
