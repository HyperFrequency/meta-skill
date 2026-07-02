# Tuning playbook — recipes and diagnostics

Practical settings for common GEPA runs with the `gepa` crate. Defaults in
`references/config-reference.md`; adapter mechanics in `references/adapter-guide.md`.

## Bring-up: mock-first, then live

1. **Prove the harness offline.** Start with a mock adapter (scores from a cheap heuristic, empty
   reflective dataset) and an unreachable `base_url` (e.g. `http://localhost:19999`). Empty reflective
   records mean the LM is never called, so the loop runs free while you validate data loaders, seed,
   and `GEPAResult` parsing. `examples/minimal.rs` is exactly this shape.
2. **Add real reflection.** Point `base_url` at a **local** Ollama (`http://localhost:11434`) or vLLM
   (`http://localhost:8000`) server with `api_key: ""` — reflection is now real but costs nothing.
3. **Go live** only when the loop is trustworthy: set `model` + `api_key` to a hosted endpoint.

## Budget & minibatch sizing

- Budget is **per-example metric calls** (`max_metric_calls`, default 500), not iterations. Rough cost
  per accepted iteration ≈ `minibatch_size` (evaluate) + `minibatch_size` (re-evaluate the child) +
  `|valset|` (full val eval on acceptance). Rejected iterations skip the val eval.
- Bigger `minibatch_size` → steadier accept/reject signal but faster budget burn. Start at the default
  `3`; raise to 5–8 only if acceptance decisions look noisy.
- Turn on `cache_evaluation = true` when the same candidate revisits the same examples (merge-heavy or
  long runs) — cached pairs are free and don't count against the budget.
- Set `rng_seed` for reproducible minibatch sampling and selection.

## Single-component vs. multi-component

- **Single** (`{"instructions": …}`): leave `component_selector = RoundRobin` (behaves like "always
  this one"); `use_merge` has nothing to combine, leave it `false`.
- **Multi** (`{"parser": …, "solver": …}`): `RoundRobin` alternates focus each iteration (usually what
  you want); `All` mutates everything each round (faster but noisier, more LM cost). This is where
  merge earns its keep — see below.

## Enabling merge (Algorithm 4)

Set `use_merge = true` for multi-component prompts once reflective mutation has produced a few accepted
specialists. Tune `max_merge_invocations` (total merge attempts, default 5) and `val_overlap_floor`
(minimum shared validation IDs before a merge is tried, default 5 — raise it if your valset is large so
merges are decided on solid overlap). `examples/merge_demo.rs` demonstrates the full flow.

## Multi-objective (trading off metrics on a Pareto front)

1. In `evaluate`, attach `.with_objective_scores(vec_of_maps)` — one `HashMap<String,f64>` per example
   with your named objectives (e.g. `{"accuracy": .., "brevity": ..}`).
2. Choose `frontier_type`: `Objective` (frontier per metric), `Hybrid` (per-example **and**
   per-metric), or `Cartesian` (per `(example, metric)` pair). **Not** `Instance` — that ignores
   objective scores.
3. Read the trade-off from `GEPAResult`: `per_objective_best_candidates` and `objective_pareto_front`.

Forgetting step 1 while setting a non-`Instance` frontier is a startup error, not a silent fallback.

## Selector choice

- `Pareto` (default) — best general choice; preserves specialists, feeds merge.
- `CurrentBest` — pure exploitation; use when you trust the average metric and want fast convergence on
  a single prompt (closest to a plain hill-climb).
- `EpsilonGreedy` (tune `epsilon`, default 0.1) — inject exploration when Pareto stalls on a narrow
  frontier; higher ε = more random base picks.

## Reflection-prompt overrides

Use `reflection_prompt_template` only when the built-in Appendix-C meta-prompt misfires for your domain.
`PromptTemplateConfig::Single(s)` swaps the template globally; `PerComponent(map)` overrides specific
components (others keep the default). Prefer instead tagging components via `component_metadata`
(`ComponentMeta::code/config`) so GEPA auto-selects the code/config-aware template — cheaper than
hand-writing a template.

## Diagnostics

| Symptom | Likely cause / fix |
|---|---|
| "No candidate beats the seed" (`best_idx` stays 0) | Feedback in the reflective dataset is too vague — put the *corrective signal* (expected answer, rule violated) in `Feedback`. Or the metric has no diagnosable structure (GEPA can't reflect noise). |
| Run stops almost immediately | `max_metric_calls` too small vs. `minibatch_size` + `|valset|`; raise budget or shrink valset. |
| `RetriesExhausted` / `LmApi` errors | Reflection endpoint unreachable/misconfigured — check `base_url` (no trailing slash), `api_key`, and that a local server is up. |
| Engine errors at startup with a frontier message | Non-`Instance` `frontier_type` but adapter returned no `objective_scores`. |
| Whole run aborts mid-way | Adapter returned `Err` for a single example — return a `0.0` score instead; reserve `Err` for systemic failures. |
| Best prompt is great on train, poor in production | Valset too small/unrepresentative — `best_candidate` is chosen on the valset; enlarge or diversify it. |
| Non-finite score panic/error | A score was `NaN`/`inf`; clamp to a finite failure value in `evaluate`. |

## Cross-checks before trusting a result

- Confirm `total_metric_calls` and `num_full_val_evals` are consistent with the budget you set.
- Inspect `parents` (lineage) to see whether the winner came from mutation or merge.
- Persist the run: `result.to_json()` — reload later with `GEPAResult::from_json` (schema-versioned).
