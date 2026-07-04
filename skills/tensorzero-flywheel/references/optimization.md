# Optimization — GEPA prompt evolution, fine-tune jobs & the Loop-1 workflow

Behavioral spec for the optimization plane (`prompt-evolver` + `model-optimizer`), distilled from
TensorZero-core `optimization/` (`mod.rs`, `gepa.rs`, `dicl.rs`, `openai_sft`, `openai_rft`,
`fireworks_sft`, `together_sft`, `gcp_vertex_gemini_sft`) at pinned SHA `62eb8f63e`, and the PRD §b Loop-1
design. This plane consumes the feedback store and emits new variants back into the registry.

## 1. The optimizer taxonomy

The donor's `OptimizerConfig` enum is the menu of optimization jobs. They split into two families:

**Prompt/inference-strategy optimizers (mutate payloads):**
- **GEPA** — reflective prompt evolution. Analyzes traces, mutates variant prompts, keeps a Pareto frontier.
  Phase-1. *The engine is `gepa-evolve` (gepars); this skill wires it as a job.* See §2.
- **DICL** — dynamic in-context learning: curates an example pool a `dicl` variant retrieves from. Optimizing
  = choosing which curated examples to include. Phase-2 (schema/curation lands earlier).

**Model optimizers (produce new model weights, P2):**
- **OpenAI SFT** (`OpenAISFTConfig`), **OpenAI RFT** (`OpenAIRFTConfig`), **Fireworks SFT**, **Together SFT**,
  **GCP Vertex Gemini SFT** — supervised / reinforcement fine-tune **job launchers**. They take a curated
  dataset (demonstrations + high-reward inferences + DPO pairs from the feedback store) and launch a
  provider-side training job.

### Job lifecycle (uniform across optimizers)

All optimizers share a job-handle lifecycle you should mirror:

```
launch(config, dataset) -> OptimizationJobHandle          // opaque, base64-url-encodable, serializable
poll(handle)            -> OptimizationJobInfo             // Pending{message} | Completed{output} | Failed{message}
                                                           // status = Pending | Completed | Failed
on Completed            -> OptimizerOutput                 // e.g. a new variant, or a fine-tuned model id
```

A job handle round-trips to a URL-safe string so it can be parked in durable Temporal workflow state and
polled across restarts. Model these as three states only (Pending/Completed/Failed) — don't invent
intermediate states the providers don't report.

## 2. GEPA as an optimizer job (the phase-1 workhorse)

`GEPAConfig` (donor `optimization/gepa.rs`) — the concrete fields you configure when launching a GEPA job.
**This skill owns the *wiring*; the reflective-proposer / Pareto / merge *engine* is `gepa-evolve`.**

Key config fields (verified from the donor struct):
- `function_name` — the function whose variants are being optimized.
- `evaluator_names: Vec<String>` — evaluators (defined on the function) that score candidates. *(Legacy
  singular `evaluation_name` is deprecated — prefer the plural.)*
- `initial_variants: Option<Vec<String>>` — seed variants; `None` = use all of the function's variants.
- `variant_prefix` — name prefix for the newly minted optimized variants.
- `batch_size` — training samples analyzed per iteration (the minibatch).
- `max_iterations` — hard iteration cap.
- `max_concurrency` — cap on concurrent inference calls (budget/rate control).
- `analysis_model` / `mutation_model` — the models that analyze failures and propose mutations
  (e.g. `anthropic::claude-sonnet-4-5`).
- `include_inference_for_mutation: bool` — fold inference input/output into the analysis as few-shot context.
  **Warning (donor-documented):** with multi-turn inputs, long outputs, or large batches this overflows the
  mutation model's context — leave off unless you need the examples.
- `max_tokens: Option<u32>`, `seed: Option<u32>` (reproducibility), `timeout: u64`, `retries: RetryConfig`.

GEPA is **durable + sequential** (not the parallel island search — that's `alpha-evolve`/openevolve, a P2
extension). Output = new variants (named `{variant_prefix}…`) registered for the experiment plane to A/B.

## 3. Loop 1 — the EvolutionWorkflow (PRD §b, phase-1)

The durable Temporal orchestration that ties feedback → optimization → experiment together. It **mutates
payloads only** (prompts, graph/workflow specs, skill specs, config genomes) — **never generated code**
(D1-safe; the ADAS caution: evolving code is unsafe, evolving prompts/config is safe).

```
EvolutionWorkflow(spec: EvolutionSpec{ target: PromptRef|GraphSpecRef|SkillRef, adapter, budget, stop })
  state: GEPAState JSON (gepars) persisted in workflow state; continue-as-new every K iterations
  per iteration:
    1. SelectCandidate         — gepars Pareto / TopK / EpsilonGreedy selector (activity)
    2. SampleMinibatch         — pinned-version dataset from experiment-tracker
    3. EvaluateCandidate ×k    — activities; single execution owner per candidate (FIX-18);
                                 adapter = GEPAAdapter over the harness_eval runner (or ProcessAdapter)
    4. BuildReflectiveDataset  — traces from trace-store; failure clustering (opik hierarchical-
                                 reflective root-cause pattern)
    5. ProposeMutation         — gepars reflective proposer; ComponentKind text|code|config
                                 (workflow/graph-spec evolution uses the config meta-prompt)
    6. MergeMaybe              — Algorithm 4, gated on validation-set overlap
    7. UpdateParetoFrontier + PersistLineage — experiment-tracker; config-snapshot hash
    8. Gate                    — n≥3 trials/input (Braintrust); variance-aware compare vs baseline
                                 (hill-climb: gen N winner = gen N+1 baseline)
  HITL:      SignalStopper ↔ Temporal signal; pause/resume/stop via spine signals + SSE
  Promotion: winner flips a prompt-registry LABEL (Langfuse pattern) — deploy = label move, no code change
  Budget:    GEPACallback BudgetUpdated → stop signal; cost sourced from llm-router
```

Donors composed here: **gepars** (canonical GEPA engine), **tensorzero** (GEPA config + experimentation +
config snapshot), **opik** (optimizer trait, OptimizationResult, hierarchical-reflective clustering),
Reflexion (per-candidate episodic reflections), ADAS (archive-conditioned proposal sampling the lineage
store), alpha-evolve/openevolve (island-archive topology — **P2 extension only**).

## 4. Fine-tune loop (P2) — from feedback to weights

When `model-optimizer` lands:
1. **Curate** a pinned dataset from the feedback store (demonstrations → SFT rows; high-reward inferences →
   positive examples; `dispreferred_outputs` → DPO/preference pairs). See `feedback-and-metrics.md` §5.
2. **Launch** the provider SFT/RFT job (`OpenAISFT`/`RFT`, `FireworksSFT`, `TogetherSFT`, `GCPVertexGeminiSFT`).
3. **Poll** the job handle to `Completed{output = fine-tuned model id}`.
4. **Register** a new variant that serves the function via the fine-tuned model.
5. **A/B** it against the incumbent through the experiment plane — a fine-tuned model earns promotion the same
   way a prompt mutation does: variance-aware, regression-gated. No auto-promote on "training finished".

## 5. Cost & budget (the guard on every loop)

Cost is tracked at the `llm-router` layer (donor `cost.rs`: `CostConfigEntry` + `CostRate`, priced per
`cost_per_million` tokens or `cost_per_unit`) and surfaced per-variant in `experiment-tracker`. Every
optimization loop carries a **budget guard**: a `BudgetUpdated → stop` signal that halts the workflow when
spend crosses a cap. `max_concurrency` + `max_iterations` on the GEPA config are the coarse throttles;
the budget signal is the hard stop. Never launch an unbounded loop — an optimizer with no budget guard can
burn the account (real risk; cf. the runaway-fork incident pattern in the memory).

## 6. What to SKIP / defer in the optimization plane

- **ChainOfThought variant** — deprecated upstream (#5298). SKIP.
- **TS-judge v8/SES executor** — TS judges run on the first-party TS spine, not the Rust optimizer. SKIP in
  Rust.
- **Adaptive Track-and-Stop** — port *with its tests* or defer to P2 (see `experimentation.md`).
- **Island-parallel evolution** (alpha-evolve/openevolve) — P2 extension; phase-1 GEPA is durable+sequential.
