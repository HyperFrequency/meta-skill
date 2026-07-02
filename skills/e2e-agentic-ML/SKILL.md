---
name: e2e-agentic-ML
version: 0.1.0
description: End-to-end agentic ML orchestration for quant trading — Claude routes a fuzzy human goal through the full lifecycle (framing, data, EDA, features, hypothesis, model selection, training, evaluation, backtest, live deploy, monitoring), picking the right specialist skill and gate at each handoff instead of running a fixed recipe. Use when a user wants the WHOLE pipeline from idea to production, a top-to-bottom audit/rebuild, or a multi-hour orchestrated research session with checkpoints. Triggers on "end-to-end ML for trading", "agentic ML pipeline", "Claude-driven quant ML", "ML hypothesis to live deployment", "build the whole ML pipeline", "I have an idea, take it to production". Do NOT use for a single stage (go straight to feature-engineering / model-evaluation / vectorbt etc.), a pure literature review (use autoresearch or literature-review), or a cross-framework code port (use strategy-translator). This skill is the glue that composes the specialists; it does not re-implement them.
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, WebFetch, WebSearch
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    upstream: none — original orchestration layer
---

# End-to-End Agentic ML for Quant Trading

## Overview

A quant ML project has eleven stages, and most teams blow it on one of them: wrong model class for the data, look-ahead leaked into features, K-fold on time series, a raw Sharpe quoted without deflating for trials, or a deploy with no rollback path. Each individual stage already has a battle-tested specialist skill in this repo. The hard part is **wiring them together with good decisions at each handoff** — which is what this agentic orchestration layer is for.

This skill does not re-implement features, models, or backtests. It sequences the specialist skills, surfaces the decision points where the human must weigh in, and runs the autonomous parts unsupervised. The agent — Claude — owns the recipe; the human owns the irreducible judgement calls.

## When to Use This Skill

Use this skill when:
- A user arrives with a fuzzy goal ("predict 15-minute BTC moves", "trade vol carry", "build a market-making bot") and wants the full pipeline, not a single stage.
- An existing pipeline needs a top-to-bottom audit and rebuild rather than a point fix.
- A research session spans hours-to-days and needs orchestration + checkpoints, not a single shot.
- The team wants the LLM to handle the boring decisions (which CV scheme, which tracker, which hyperparameter prior) and surface the load-bearing ones (which model to deploy, which feature set to commit to).

Do **not** use this for:
- A single stage in isolation — go straight to the relevant skill (`feature-engineering`, `model-evaluation`, `vectorbt`, etc.).
- A pure literature review with no code path — use `autoresearch` or `literature-review`.
- A code port between frameworks — use `strategy-translator`.

This skill **composes** the other skills; if a specialist already exists, this one routes to it rather than restating it.

## Lifecycle at a Glance

```
human goal (fuzzy)
  → 1 Frame → 2 Data → 3 EDA → 4 Features → 5 Hypothesis → 6 Model-select
  → 7 Train → 8 Eval → 9 Backtest → 10 Live-deploy → 11 Monitor+Retrain
```

Eleven stages, three backward arrows: EDA (3) may invalidate the frame (1); model selection (6) may reject features (4); monitoring (11) feeds drift back into retraining (7) or, if severe, all the way back to framing (1).

At every stage the agent decides (a) which specialist skill executes it, (b) whether the artifact passes the gate to the next stage, and (c) whether to checkpoint with the human. **The per-stage decisions, routing, code, and gate criteria live in [`references/lifecycle-stages.md`](references/lifecycle-stages.md) — read it before driving any pipeline.**

## Stage Router

| # | Stage | Routes to (specialist) | Gate to pass |
|---|---|---|---|
| 1 | Frame | [`ml-hypothesis-design`](../ml-hypothesis-design/SKILL.md) | one-pager: universe, freq, label pseudocode, H0/H1+effect size, decision rule, MT budget |
| 2 | Data | [`tardis-data-agent`](../tardis-data-agent/SKILL.md), [`ccxt`](../ccxt/SKILL.md), [`coingecko`](../coingecko/SKILL.md), [`nautilus-trader`](../nautilus-trader/SKILL.md) | Parquet manifest, UTC, no price nulls |
| 3 | EDA | [`exploratory-data-analysis`](../../k-dense-scientific-agent-skills/exploratory-data-analysis/SKILL.md), [`polars`](../../k-dense-scientific-agent-skills/polars/SKILL.md), [`seaborn`](../../k-dense-scientific-agent-skills/seaborn/SKILL.md) | 1-page summary; conflicts with frame → `AskUserQuestion` |
| 4 | Features | [`feature-engineering`](../feature-engineering/SKILL.md), [`microstructure-feature-engineering`](../microstructure-feature-engineering/SKILL.md) | feature manifest, every row `leakage_check_passed=true` |
| 5 | Hypothesis | [`ml-hypothesis-design`](../ml-hypothesis-design/SKILL.md) | preregistration committed, MT correction locked + immutable |
| 6 | Model select | [`xgboost`](../xgboost/SKILL.md) (default), [`lightgbm`](../lightgbm/SKILL.md), [`catboost`](../catboost/SKILL.md), [`lstm-forecast`](../lstm-forecast/SKILL.md), [`stable-baselines3`](../../k-dense-scientific-agent-skills/stable-baselines3/SKILL.md) | 3 candidates ranked; tie within 5% → `AskUserQuestion` |
| 7 | Train | [`mlops/mlflow`](../mlops/mlflow/SKILL.md), [`optimization`](../optimization/SKILL.md), [`distributed-training`](../distributed-training/) | model logged to MLflow w/ signature + URI |
| 8 | Eval | [`model-evaluation`](../model-evaluation/SKILL.md) | DSR ≥ threshold, PBO ≤ 0.5, maxDD ≤ envelope |
| 9 | Backtest | [`vectorbt`](../vectorbt/SKILL.md) then [`nautilus-trader`](../nautilus-trader/SKILL.md), [`tearsheet-generator`](../tearsheet-generator/SKILL.md) | Nautilus Sharpe within 1σ of vectorbt |
| 10 | Live deploy | [`nautilus-trader`](../nautilus-trader/SKILL.md) | pre-deploy checklist + **human sign-off via `AskUserQuestion`** |
| 11 | Monitor | [`mlops`](../mlops/), [`observability`](../observability/SKILL.md) | perf + drift monitors live, retrain heartbeat scheduled |

The Stage 6 model-class decision tree (RL vs GBT vs sequence vs unsupervised), the Stage 7 LLM-augmented hyperparameter code, and all per-stage anti-patterns are in [`references/lifecycle-stages.md`](references/lifecycle-stages.md).

## Orchestration Patterns

Pick by tempo and bandwidth. Full descriptions + code in [`references/orchestration-patterns.md`](references/orchestration-patterns.md).

1. **Single-shot pipeline** — all 11 stages autonomously, defensible defaults. For baselines, not the deployed model.
2. **Iterative with checkpoints** — runs until a human-owned decision (post-EDA, post-Stage-6, pre-deploy), then `AskUserQuestion`. The default for anything that will be deployed.
3. **Parallel-agents fan-out** — N `Agent` subtasks for embarrassingly-parallel work (feature ablations, sweeps). No cross-dependencies. See [`relentless-inception`](../relentless-inception/SKILL.md).
4. **`/loop`-driven heartbeat** — Stage 11 retraining/monitoring on a recurring interval; pair with `CronCreate` / `schedule`.
5. **Two-loop research orchestration** — inner = experiment iteration, outer = "abandon this frame?". Borrowed from [`autoresearch`](../autoresearch/SKILL.md); maps onto Stages 4–8 for open-ended projects.

## LLM-Tooling Layer

The agent leans on Anthropic API features (prompt caching for stable specs, thinking blocks for ranking/diagnostics, `tool_choice` for structured gate verdicts, Batch API for >1000 calls), DSPy where the prompt is the program, LangGraph/LlamaIndex for state machines + RAG, MLflow/W&B for tracking, Hydra for config, and the MCP gateway for external data. Details, code, and the [`claude-api`](#) cross-link are in [`references/llm-tooling.md`](references/llm-tooling.md). Verify any API/pricing claim at deploy time — SDK details confirmed via Context7 as of Jan 2026.

## Hard Rules (the agent refuses these without explicit override)

- **No autonomous live deploy.** Stage 10 always routes through `AskUserQuestion`. Kill-switch and deploy switch are human-only.
- **No K-fold / shuffle split on temporal data** — purged + embargoed CV only.
- **No raw Sharpe without DSR + PBO** and the trials count.
- **No look-ahead leakage** — the Stage 4 `leakage_check_passed` manifest gates this.
- **No going live off a vectorbt-only backtest** — NautilusTrader event-driven confirmation required.
- **No picking the multiple-testing correction after seeing results** — locked in Stage 5.
- **No `.fit()` before tracking is wired** and before a Hydra config exists.

Reserved-for-human decisions: capital allocation, Stage 10 deploy, Stage 1 frame override. Everything else the agent picks defensibly and reports. Full anti-pattern list + the Stage 11 drift-detection skeleton (KS test + PSI) are in [`references/drift-and-anti-patterns.md`](references/drift-and-anti-patterns.md).

## References

- **Detailed stage reference:** [`references/lifecycle-stages.md`](references/lifecycle-stages.md)
- **Orchestration patterns + code:** [`references/orchestration-patterns.md`](references/orchestration-patterns.md)
- **LLM-tooling layer:** [`references/llm-tooling.md`](references/llm-tooling.md)
- **Drift detection + anti-patterns:** [`references/drift-and-anti-patterns.md`](references/drift-and-anti-patterns.md)
- **Foundational literature** (quoted in preregistrations): Bailey & López de Prado (2014) "The Deflated Sharpe Ratio"; Bailey, Borwein, López de Prado, Zhu (2017) "The Probability of Backtest Overfitting"; López de Prado (2018) *Advances in Financial Machine Learning* (Ch. 4 purged+embargoed CV, Ch. 7 triple-barrier); López de Prado (2020) *Machine Learning for Asset Managers*.
- **SDK/framework references** (verified Jan 2026 via Context7): `anthropic-sdk-python` (`cache_control`, `thinking`, `tool_choice`, `code_execution_*`); `dspy` (`Signature`, `ChainOfThought`, `MIPROv2`); `mlflow` (`start_run`, `log_params`, `xgboost.log_model`); NautilusTrader `TradingNode` schema (see the `nautilus-trader` skill's `references/`).

### Caveats / Unverified

- Anthropic **Files API** and **Batch API** ~50% discount are current as of Jan 2026 — re-verify GA + pricing at deploy time.
- `code_execution_20260120` is the latest verified tool version; prefer a newer one if your SDK ships it.
- The "5% within-tolerance" rule (Pattern 2) and PSI > 0.25 drift threshold are conventional defaults, not derived — tune per project.
- Cross-link targets confirmed 2026-05-20: [`microstructure-analysis`](../microstructure-analysis/SKILL.md) (methodology), [`microstructure-analyst`](../microstructure-analyst/SKILL.md) (workflow), [`microstructure-feature-engineering`](../microstructure-feature-engineering/SKILL.md) (feature layer) are distinct skills — match the right one.
- `llm-wiki` was deleted in the 2026-05-20 cleanup; use [`deep-tool-wiki`](../deep-tool-wiki/SKILL.md), [`infranodus`](../infranodus/SKILL.md), [`ontology-creator`](../ontology-creator/SKILL.md) as the vault layer.
