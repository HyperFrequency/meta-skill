---
name: neuro-quant-market-research-runtime
version: 0.1.0
description: >
  Validates market hypotheses with runtime evidence across vectorbt.pro,
  hftbacktest, hftbacktest_cpp, quantstats, and pandas-ta BEFORE any execution
  code is written. Routes a research question to the right engine (vectorized
  sweep, L2/queue/latency replay, indicator parity, or return-series tear sheet),
  runs the smallest useful experiment, and emits a handoff brief with explicit
  data provenance and assumptions. Use when the user says "research this
  hypothesis", "hft backtest", "performance proof", "validate before
  implementing", "backtest this strategy", "compare vectorbtpro and nautilus",
  or "produce a tearsheet with proof". For vectorbt strategy AUTHORING use the
  vectorbt skill; for the event-driven execution engine use nautilus-trader; for
  building tearsheets use tearsheet-generator.
allowed-tools: Read, Grep, Glob, Bash
---

# Market Research Runtime

## Scope

Validate market hypotheses across vectorized research, microstructure replay, and
performance-proof surfaces BEFORE any execution code is written. This is a
research-runtime skill: it should produce evidence that an idea is worth
translating into execution code. It must not place orders, manage live services,
or mutate operational dashboards.

Use this skill when the task matches one of these signals:
- research this hypothesis / validate before implementing
- backtest this strategy
- compare vectorbtpro and nautilus trader
- hftbacktest market microstructure / hft backtest
- produce a tearsheet with proof / performance proof
- convert vectorbt to nautilus (research/justification side only)

## Tool Boundary

- Use `vectorbt.pro` for broad vectorized research, portfolio sweeps, signal
  validation, walk-forward evaluation, and fast comparison of many strategy
  variants.
- Use `hftbacktest` when the research question depends on L2 order book replay,
  queue position, maker-fill realism, feed latency, order-entry latency, or
  order-response latency.
- Use `hftbacktest_cpp` when the research question is CME futures or MBO-data
  centric and the priority is a C++ simulator with realistic queue and latency
  modeling.
- Use `pandas-ta` for indicator feature generation, compatibility checks against
  common TA formulas, and non-core indicator variants.
- Use `quantstats` for return-series tear sheets, HTML reports, and metric packs
  after a backtest has emitted clean returns.

Sibling-skill boundary (route OUT when the work is no longer hypothesis
validation):
- For vectorbt strategy **authoring** (writing the production strategy) use the
  `vectorbt` skill.
- For the **event-driven execution engine** use `nautilus-trader`; translate only
  after deciding event-driven execution semantics are required.
- For **building** polished tear sheets use `tearsheet-generator`.
- Hand off to `execution-ui-ops` only after the research output has explicit
  assumptions, data provenance, and execution-relevant constraints.

## Inputs To Request Or Infer

Before running analysis, identify:

- Market and venue: exchange, symbol universe, spot/futures/prediction market,
  contract type, and trading hours if relevant.
- Data granularity: bars, trades, quotes, L2 market-by-price, MBO, snapshots, or
  replay files.
- Execution assumption: bar-close fills, bid/ask fills, custom order function,
  queue model, latency model, or venue-specific fill behavior.
- Research objective: signal discovery, parameter optimization, risk analysis,
  microstructure realism, or report generation.
- Output contract: notebook, script, CSV/Parquet artifacts, metrics table, HTML
  tear sheet, or execution handoff brief.

If any of those affect conclusions and are missing, ask before producing results.

## Required Workflow

1. Restate the goal, target repo/tool, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Open `references/verification-checklist.md` for the smallest relevant proof
   path.
4. Classify the research question and pick the engine:
   - Vectorized hypothesis or large parameter grid: start with `vectorbt.pro`.
   - Technical indicator feature work: start with `pandas-ta`, then wrap or
     compare in `vectorbt.pro` if needed.
   - Fill realism, passive orders, queue position, or latency: start with
     `hftbacktest` or `hftbacktest_cpp`.
   - Performance reporting: start only after returns are available, then use
     `quantstats`.
5. Check the data contract.
   - Confirm timestamp units and timezone.
   - Confirm whether prices are bars, trades, top-of-book, L2 market-by-price, or
     MBO.
   - Confirm fee, funding, borrow, spread, slippage, and latency assumptions.
   - For microstructure work, require separate local and exchange timestamps when
     the model needs latency calibration.
6. Run the smallest useful experiment first.
   - One symbol, one date range, one or two parameter combinations.
   - Verify output shape, timestamp ordering, NaN policy, and return calculation.
   - Only then scale to grids, multi-symbol panels, or parallel sweeps.
7. Separate signal quality from execution quality.
   - `vectorbt.pro` can validate whether a signal has statistical promise.
   - `hftbacktest` and `hftbacktest_cpp` test whether the signal survives
     realistic order placement constraints.
   - `quantstats` summarizes realized return paths; it does not prove fill
     realism.
8. Produce a handoff brief using `references/handoff-template.md` when a long
   workflow should move to another family skill. State the data set and date
   range, the exact execution assumptions, why the selected engine was
   appropriate, and the metrics, failure cases, and any conditions that would
   invalidate the result.
9. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or
   `neuro-link/02-KB-main/<tool>/index.md`.
10. Separate verified facts, assumptions, missing resources, and blocked checks
    in the final answer.

## Verification Gates

At minimum, verify:

- Input rows are non-empty and timestamp-sorted.
- No lookahead columns are used in signal decisions.
- Fees/slippage/latency assumptions are explicit.
- Returns are aligned to the intended bar/event boundary.
- Microstructure simulations use a queue and latency model appropriate to the
  available data.
- Report metrics are generated from returns, not trade counts or marked-up equity
  snapshots.

See `references/verification-checklist.md` for the family-level proof gates.

## Failure Modes To Surface

- Bar-level results being presented as executable maker-order results.
- `vectorbt.pro` parameter sweeps overfitting a single regime without
  walk-forward or holdout checks.
- Indicator libraries producing subtly different formulas or column names across
  versions.
- L2 simulations using market-by-price data when the claim requires MBO queue
  certainty.
- HTML tear sheets hiding bad assumptions because the return series was already
  contaminated.
- C++ HFT runs treated as plug-and-play Python research before bindings and data
  adapters are verified.

## Progressive Disclosure

This skill keeps local resources in its own folder for immediate operation, but
the full documentation belongs in deep-tool-wiki and the navigable leaf docs
belong in 02-KB-main. Do not duplicate long API docs here. If a full doc is
missing, use the generated stub path from the resource map and mark the lookup
incomplete.

## Local Resources

- `references/resource-map.md`: relevant repos, local docs, deep-tool-wiki
  targets, public source URLs, and missing-doc status.
- `references/verification-checklist.md`: proof gates for this family.
- `references/handoff-template.md`: structured handoff for multi-step workflows.
- `evals/evals.json`: trigger, false-positive, and missing-resource cases.
- `agents/openai.yaml`: minimal UI metadata for skill discovery.

## Covered Tools

| Tool | Source | Full docs | KB lookup |
| --- | --- | --- | --- |
| vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` |
| Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` |
| hftbacktest_cpp | `toolbox/hftbacktest_cpp` | `deep-tool-wiki/hftbacktest_cpp/wiki.md` | `neuro-link/02-KB-main/hftbacktest_cpp/index.md` |
| hftbacktest | `deep-tool-wiki/hftbacktest` | `deep-tool-wiki/hftbacktest/wiki.md` | `neuro-link/02-KB-main/hftbacktest/index.md` |
| quantstats / pyfolio | `toolbox/docs/tools/quantstats-pyfolio.md` | `deep-tool-wiki/quantstats-pyfolio/wiki.md` | `neuro-link/02-KB-main/quantstats-pyfolio/index.md` |
| pandas-ta | `toolbox/docs/tools/pandas-ta.md` | `deep-tool-wiki/pandas-ta/wiki.md` | `neuro-link/02-KB-main/pandas-ta/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user
  asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution
  operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate
  from trading logic claims.

## Output Template

```markdown
## Research Runtime Result

Tool path: vectorbt.pro | hftbacktest | hftbacktest_cpp | pandas-ta | quantstats
Market/data: <venue, symbols, date range, granularity>
Execution assumption: <fill model, queue model, latency model, fees>
Result: <concise conclusion>
Evidence: <metrics, artifact paths, report paths>
Limitations: <what this does not prove>
Execution handoff: <what execution-ui-ops or nautilus_trader needs next>
```

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and
the next verification step (the Output Template above is the canonical shape).
