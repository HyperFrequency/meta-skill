---
name: e2e-agentic-ML
description: End-to-end agentic ML workflow for quant trading — the LLM (Claude) orchestrates the full lifecycle from fuzzy human goal through problem framing, data acquisition, EDA, feature engineering, hypothesis design, model selection, training, evaluation, backtest, live deployment, and monitoring. "Agentic" means the agent makes informed decisions at each stage and routes to the right specialist skill, instead of running a fixed recipe. Triggers on phrases like "end-to-end ML for trading", "agentic ML pipeline", "Claude-driven quant ML", "ML hypothesis to live deployment", "agent-orchestrated training", "build the whole ML pipeline", "I have an idea, take it to production". For pure framing without execution use `ml-hypothesis-design`; for pure evaluation use `model-evaluation`; for a generic autonomous research loop use `autoresearch`. This skill is the glue.
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, WebFetch, WebSearch
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    upstream: none — original orchestration layer
---

# End-to-End Agentic ML for Quant Trading

## Overview

A quant ML project has eleven stages, and most teams blow it on one of them: they pick the wrong model class for the data, they leak look-ahead into features, they run K-fold on time series, they quote a raw Sharpe without deflating for trials, or they deploy without a rollback path. The hard part is not any individual stage — each has a battle-tested skill in this repo. The hard part is **wiring them together with good decisions at each handoff**, which is what an agentic loop is for.

This skill is the orchestration layer. It does not re-implement features, models, or backtests; it sequences the specialist skills, surfaces the decision points where the human must weigh in, and runs the parts that can run autonomously without supervision. The agent — Claude — owns the recipe; the human owns the irreducible judgement calls.

## When to Use This Skill

Use this skill when:

- A user arrives with a fuzzy goal ("predict 15-minute BTC moves", "trade vol carry", "build a market-making bot") and wants the full pipeline, not a single stage.
- An existing pipeline needs a top-to-bottom audit and rebuild rather than a point fix.
- A research session will span hours-to-days and needs orchestration + checkpoints rather than a single shot.
- The team wants the LLM to handle the boring decisions (which CV scheme, which tracker, which hyperparameter prior) and surface the load-bearing ones (which model to deploy, which feature set to commit to).

Do **not** use this for:
- A single stage in isolation — go straight to the relevant skill (`feature-engineering`, `model-evaluation`, `vectorbt`, etc.).
- A pure literature review with no code path — use `autoresearch` or `literature-review`.
- A code port between frameworks — use `strategy-translator`.

This skill **composes** the other skills; if a specialist skill already exists, this one routes to it rather than restating it.

## Lifecycle Overview

```
                                  human goal (fuzzy)
                                          |
        +---------+---------+---------+---+-----+---------+---------+---------+---------+---------+--------+
        | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 | Stage 6 | Stage 7 | Stage 8 | Stage 9 | Stage 10| Stage 11
        |  Frame  |  Data   |   EDA   |Features |  Hypoth |Model    |Training |  Eval   |Backtest |  Live   | Monitor
        |         |         |         |         |         |Select   |         |         |         |  Deploy |+Retrain
        +---------+---------+---------+---------+---------+---------+---------+---------+---------+---------+--------+
            ^                                       ^                                                  ^         |
            |                                       |                                                  |         |
            +--- iterate if EDA invalidates frame  +-- iterate if model picks reject features          rollback  +
                                                                                                       |         |
                                                                                                       +-- drift triggers retrain
```

Eleven stages, two backward arrows. Stage 3 (EDA) is allowed to invalidate Stage 1 (frame); Stage 6 (model selection) may reject Stage 4 features. Stage 11 (monitoring) feeds drift detection back into Stage 7 (retraining loop) or, if severe, all the way back to Stage 1.

The orchestration job: at every stage, the agent decides (a) which specialist skill executes the stage, (b) whether the artifact passes the gate to the next stage, and (c) whether to checkpoint with the human. The gate criteria are listed per stage below.

---

## Stage 1 — Problem Framing

**Goal:** turn a fuzzy human goal into a precise ML formulation.

**What the agent decides:**
- Prediction target: direction (binary classification), magnitude (regression), regime (multiclass), event (triple-barrier).
- Universe + frequency: which instruments, what bar/tick frequency, in-sample window, embargo, out-of-sample hold-out.
- Scoring metric: profit-adjusted (Sharpe net of costs), classification (precision at threshold), or both.
- CV scheme: walk-forward (default for tick/minute), purged + embargoed K-fold (default for daily), CPCV (when N_trials > 50).

**What the human decides:**
- Risk envelope (max gross exposure, max drawdown the strategy is allowed to lose).
- Deployment intent (paper, small live, full size) — this drives the rigor budget.
- Cost assumption (round-trip bps, slippage model).

**Route to:** [`ml-hypothesis-design`](../ml-hypothesis-design/SKILL.md) for the formal H0/H1/power/preregistration framework. That skill is where the frame becomes a falsifiable hypothesis.

**Gate to Stage 2:** a written one-pager containing (universe, frequency, label definition pseudocode, H0, H1 with target effect size, decision rule, multiple-testing budget). If any of those six fields is empty, do not proceed.

---

## Stage 2 — Data Acquisition

**Goal:** assemble the raw inputs at the right venue, granularity, and depth, with leakage-safe alignment.

**Agentic decisions:**

| Goal | Default data source | Skill |
|---|---|---|
| Crypto tick / L2 history | Tardis.dev | [`tardis-data-agent`](../tardis-data-agent/SKILL.md) |
| Crypto OHLCV via exchanges | ccxt | [`ccxt`](../ccxt/SKILL.md) |
| Crypto fundamentals / macro | CoinGecko | [`coingecko`](../coingecko/SKILL.md) |
| Equities / FX / futures bars | NautilusTrader data catalog | [`nautilus-trader`](../nautilus-trader/SKILL.md) |
| Universal scientific lookups | parallel-web / database-lookup | (k-dense skills) |

The agent picks the venue based on the frame:
- Frequency < 1 min → must be tick or L2 (Tardis or NautilusTrader catalog).
- Frequency ≥ 1 min and goal is alpha → OHLCV (ccxt or catalog).
- Goal involves sentiment / macro → augment with CoinGecko + a parallel-web search.

**Storage convention:** all raw data lands as partitioned Parquet under `data/raw/<venue>/<symbol>/<date>.parquet`. The agent writes a one-line manifest (venue, symbol, start, end, rows, sha256) per file. No exception.

**Gate to Stage 3:** manifest written; row counts sanity-checked against the manifest; timezone is explicitly UTC; the agent has run a `df.describe()` and confirmed no nulls in the price column.

---

## Stage 3 — Exploratory Analysis

**Goal:** find out what you actually have before designing features.

**Agent-driven EDA checklist** (auto-run):

1. **Stationarity** — ADF test on returns and log-returns. If raw prices are used as a feature, flag and fix (fractional differencing is the default).
2. **Regime structure** — eyeball rolling volatility; if it spans > 10x across the window, the agent recommends regime conditioning.
3. **Target distribution** — for classification, the class balance; for regression, the skew + kurtosis. Imbalanced classification (>4:1) triggers a meta-labeling recommendation.
4. **Autocorrelation** — ACF / PACF up to lag = 20 × bar period. Heavy positive autocorrelation in returns is rare and exciting; in absolute returns is normal (vol clustering) and informs feature design.
5. **Cross-asset signal-to-noise** — correlation of the target with N candidate features, before any modeling. The agent reports the top 20 by |Spearman ρ| and flags anything > 0.3 as suspect (likely leakage).

**Tooling:** [`polars`](../../k-dense-scientific-agent-skills/polars/SKILL.md) for the heavy frame work, [`seaborn`](../../k-dense-scientific-agent-skills/seaborn/SKILL.md) and [`matplotlib`](../../k-dense-scientific-agent-skills/matplotlib/SKILL.md) for plots, [`exploratory-data-analysis`](../../k-dense-scientific-agent-skills/exploratory-data-analysis/SKILL.md) for the auto-report template.

**Gate to Stage 4:** the agent produces a 1-page EDA summary (HTML or markdown) that the human can scan in 60 seconds. If anything in the summary contradicts the Stage 1 frame, the agent surfaces the conflict via `AskUserQuestion` and pauses.

---

## Stage 4 — Feature Engineering

**Goal:** build a leakage-safe feature matrix with honest labels.

**Routing decision:**

| Data layer | Skill |
|---|---|
| OHLCV bars + technical indicators | [`feature-engineering`](../feature-engineering/SKILL.md) |
| L2 / L3 order book + tick-level signs | [`microstructure-feature-engineering`](../microstructure-analysis/SKILL.md) (see also `microstructure-analysis`) |
| Macro / cross-asset / sentiment | `feature-engineering` + a `parallel-web` call for the news layer |

The agent picks based on the data layer chosen in Stage 2. A mistake here is unforgiving: order-book features computed from OHLCV are fiction.

**Mandatory checks** (the agent runs each before passing the gate):

1. **Label horizon ≠ feature horizon.** Stated explicitly in the manifest.
2. **Triple-barrier labels** for classification unless there is a defensible reason to use fixed-horizon (the agent must write down the reason).
3. **Leakage scan.** For every column, the agent confirms it is computed using only data with `t' ≤ t`. The standard idiom is a left-merge with `pd.merge_asof(direction="backward")` or polars `join_asof(strategy="backward")`.
4. **Fractional differencing** when stationarity fails and the level matters (e.g. spreads, ratios).

**Gate to Stage 5:** a feature manifest (CSV with columns `name, horizon, formula, source, leakage_check_passed`). Every row must have `leakage_check_passed = true`. The agent will refuse to proceed otherwise.

---

## Stage 5 — Hypothesis Formation

**Goal:** state H0/H1, lock the multiple-testing budget, preregister.

This stage is owned end-to-end by [`ml-hypothesis-design`](../ml-hypothesis-design/SKILL.md). The agent's job here is to:

1. Pull the Stage 1 frame and Stage 4 feature manifest.
2. Invoke `ml-hypothesis-design` with the two artifacts.
3. Get back a preregistration document (effect size, power, N_trials budget, DSR threshold).
4. Commit the preregistration to the project's git history as `preregistration_<utc_iso>.md`. Once committed, the agent treats it as immutable.

**Anti-pattern:** the agent must not pick a multiple-testing correction after seeing results. The correction is locked here, before Stage 7 begins.

**Gate to Stage 6:** preregistration committed; the agent has computed the minimum backtest length and confirmed Stage 2 actually fetched enough data. If not, loop back to Stage 2.

---

## Stage 6 — Model Selection

**Goal:** pick the right model class for the problem.

**Decision tree** (the agent walks this, top-down):

```
Is the prediction problem sequential decisions (allocation, order placement)?
├── yes → RL.  Use SB3 PPO/DQN (k-dense `stable-baselines3`) or
│                policy-gradients / deep-q-learning (this repo).
│                Cross-link: ../q-learning/, ../deep-q-learning/,
│                ../policy-gradients/, ../../k-dense-scientific-agent-skills/stable-baselines3/.
└── no → it's a prediction problem.

   Is the input tabular + structured (engineered features, < 1000 cols)?
   ├── yes → gradient-boosted trees.
   │         ../xgboost/  (default; widest ecosystem)
   │         ../lightgbm/ (fastest on > 1M rows)
   │         ../catboost/ (best with categorical features)
   └── no → it's sequential / unstructured.

      Is there strong seasonality / known periodicity?
      ├── yes → classical forecast.
      │         ../arima-forecast/, ../prophet-forecast/, ../transformer-forecast/
      └── no → sequence model.
                ../lstm-forecast/, ../transformer-forecast/

      Is the goal unsupervised regime / anomaly detection?
      ├── yes → ../markov-regime-detection/, ../autoencoder-anomaly-detection/
      └── (otherwise pick from above)
```

The agent picks the **simplest viable** branch. The default for "I have engineered features and want a baseline" is `xgboost`. Going to LSTM/Transformer before exhausting GBT is a smell.

**Gate to Stage 7:** three candidates ranked. The agent surfaces them and asks the human via `AskUserQuestion` only if the top three are within 5% of each other on the chosen scoring metric; otherwise it proceeds with the leader.

---

## Stage 7 — Training

**Goal:** fit the chosen model with experiment tracking, principled hyperparameter search, and a reproducible config.

**Required tooling:**

- **Experiment tracking** — [`mlops/mlflow`](../mlops/mlflow/SKILL.md) (default) or [`mlops/weights-and-biases`](../mlops/weights-and-biases/SKILL.md). One run per (model, hyperparams, seed, data window). Tag with the preregistration hash.
- **Hyperparameter search** — Optuna with TPE sampler. The agent constrains the prior using LLM judgement (see code below). Cross-link: [`optimization`](../optimization/SKILL.md) for the broader optimization recipes.
- **Distributed training** — if model size or epoch budget warrants it, route to [`distributed-training`](../distributed-training/) (accelerate, ray-train, deepspeed, pytorch-fsdp2). The agent decides based on a 5-minute single-GPU benchmark.
- **Config** — Hydra with a per-experiment YAML. The agent generates the YAML from the Stage 1 frame.

**Anti-pattern:** training before tracking is set up. The agent will refuse to call `.fit()` until `mlflow.set_experiment(...)` has succeeded.

### Code — LLM-augmented hyperparameter range selection

A minimal Anthropic SDK call that wraps an XGBoost training step. Claude reads a feature-importance summary and proposes hyperparameter ranges. The system prompt is cached so the spec only pays once across iterations.

```python
# stage7_llm_hparam.py — Claude picks Optuna search ranges from a feature summary.
import json, anthropic, optuna, xgboost as xgb, mlflow

SPEC = open("preregistration.md").read()  # immutable from Stage 5
client = anthropic.Anthropic()

def llm_propose_ranges(feature_summary: dict) -> dict:
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[{"type": "text", "text": SPEC,
                 "cache_control": {"type": "ephemeral", "ttl": "5m"}}],
        messages=[{"role": "user", "content": json.dumps({
            "task": "propose_xgb_ranges",
            "feature_importance": feature_summary,
            "n_trials_budget": 50,
        })}],
        tools=[{"name": "ranges", "input_schema": {"type": "object", "properties": {
            "max_depth": {"type": "array", "items": {"type": "integer"}},
            "learning_rate": {"type": "array", "items": {"type": "number"}},
            "subsample": {"type": "array", "items": {"type": "number"}},
        }, "required": ["max_depth", "learning_rate", "subsample"]}}],
        tool_choice={"type": "tool", "name": "ranges"},
    )
    return next(b.input for b in msg.content if b.type == "tool_use")

def objective(trial, X, y, ranges):
    params = {
        "max_depth": trial.suggest_int("max_depth", *ranges["max_depth"]),
        "learning_rate": trial.suggest_float("learning_rate", *ranges["learning_rate"], log=True),
        "subsample": trial.suggest_float("subsample", *ranges["subsample"]),
    }
    with mlflow.start_run(nested=True):
        mlflow.log_params(params)
        # purged CV split assumed (see Stage 8) — pseudo:
        score = purged_cv_score(xgb.XGBClassifier(**params), X, y)
        mlflow.log_metric("cv_sharpe", score)
        return score
```

The pattern: `cache_control` on the system block means the long spec is read once; subsequent iterations of the search loop pay only the input tokens for the changing user message. Tool use with `tool_choice` forces structured JSON output the search loop can consume.

**Gate to Stage 8:** a trained model artifact logged to MLflow with `mlflow.xgboost.log_model(...)` (or the equivalent for the chosen framework), input example attached, signature inferred. The agent records the model URI.

---

## Stage 8 — Evaluation

**Goal:** validate the model under the temporal-data discipline that trading demands.

Owned end-to-end by [`model-evaluation`](../model-evaluation/SKILL.md). The agent:

1. Runs **purged + embargoed K-fold** (default) or **CPCV** (when N_trials > 50).
2. Computes **trading metrics** (Sharpe, Calmar, Sortino, max drawdown, hit rate) — these dominate. ML metrics (accuracy, F1, AUC) are diagnostic only.
3. Applies the multiple-testing correction locked in Stage 5: deflated Sharpe (Bailey & Lopez de Prado 2014) and PBO (Probability of Backtest Overfitting).
4. Refuses to report a raw Sharpe without DSR alongside.

**Anti-pattern:** k-fold without purging, train_test_split with shuffle, or quoting accuracy on returns. The agent will refuse to ship any of those.

**Gate to Stage 9:** evaluation report. Three numbers gate the next stage:
- DSR ≥ threshold from preregistration → pass.
- PBO ≤ 0.5 → pass.
- Max drawdown ≤ envelope from Stage 1 → pass.

If any fails, loop back. Common loops: insufficient signal (back to Stage 4), wrong model class (back to Stage 6), insufficient data (back to Stage 2).

---

## Stage 9 — Backtest

**Goal:** simulate the strategy against historical data with realistic execution and cost models.

Two backtests, in this order:

1. **Vectorized** with [`vectorbt`](../vectorbt/SKILL.md) — fast, broad parameter sweeps, walk-forward optimization, tearsheet generation. Use this for the parameter robustness check and the Pareto frontier across `(Sharpe, max DD)`. Cross-link [`tearsheet-generator`](../tearsheet-generator/SKILL.md).
2. **Event-driven** with [`nautilus-trader`](../nautilus-trader/SKILL.md) backtest engine — slow, but exchange-accurate, with realistic order matching, latency, and fill models. Use this as the final go/no-go gate before live.

The agent picks parameter robustness via vectorbt sweeps first; the chosen parameter set is then re-run in NautilusTrader for the event-accurate confirmation.

**Anti-pattern:** going live off a vectorbt backtest alone. Vectorbt's fill model assumes perfect liquidity at the bar's close; that assumption breaks under stress. NautilusTrader's event model catches what vectorbt smooths over.

**Gate to Stage 10:** the NautilusTrader backtest's Sharpe is within 1σ of the vectorbt backtest's. If they diverge, the discrepancy is investigated (latency, queue position, partial fills) before any deployment talk.

---

## Stage 10 — Live Deployment

**Goal:** deploy the strategy to a live venue with monitored capital.

Owned by [`nautilus-trader`](../nautilus-trader/SKILL.md). The agent assembles a `TradingNode` config that points to the live venue, with the same strategy class used in the Stage 9 backtest.

References:
- NautilusTrader Python: [`nautilus-trader/references/`](../nautilus-trader/references/) for the `TradingNode` config schema.
- NautilusTrader Rust: same references — Rust-core actors handle the hot path.
- Hyperliquid mainnet integration is pre-built (see the `nautilus-trader` skill for the SDK patch).

**Mandatory pre-deploy checklist** (the agent runs each):

1. Paper-trade run for at least the embargo window (default 1 trading week).
2. Risk limits configured at the venue level (max position, max loss per day, max gross).
3. Kill-switch wired (a single CLI command or webhook that flattens the book and disables the strategy).
4. Rollback path documented: how to revert to the previous model version in under 5 minutes.

The agent **must** route this gate through `AskUserQuestion`. No autonomous push to live trading — ever. See the checkpoint code in the orchestration patterns section.

**Gate to Stage 11:** signed-off deployment manifest committed; first 24h of live PnL recorded.

---

## Stage 11 — Monitoring and Retraining

**Goal:** detect drift, schedule retraining, define rollback triggers.

Owned by [`mlops`](../mlops/) (the suite). Three loops run in parallel after deployment:

1. **Performance monitor** — live Sharpe rolling over the last N bars, compared to the backtest's IS+OOS distribution. Z-score of live-vs-expected > 2 is yellow; > 3 is red.
2. **Drift monitor** — KS test and PSI on incoming features vs the training distribution, per feature, daily. Any feature with PSI > 0.25 is flagged.
3. **Retraining heartbeat** — refit the model on the rolling window once a day (default) or once a week (lower frequency strategies). Compare new-model vs deployed-model on the most recent hold-out. Promote only if DSR-deflated.

**Rollback procedure:**

- Red flag fires → kill-switch → flatten book.
- Within 1h, the agent assembles a diagnostic: which monitor fired, what changed, which feature(s) drifted, what the retrained model's OOS metrics say.
- If retraining recovers metrics → redeploy with the new model after a human ack via `AskUserQuestion`.
- If retraining doesn't recover → loop all the way back to Stage 1 (the frame may no longer hold).

The retraining heartbeat is the canonical use of [`/loop`](#orchestration-pattern-3---loop-driven-heartbeat).

---

## Agent Orchestration Patterns

Five patterns, picked based on the project's tempo and the team's bandwidth.

### Pattern 1 — Single-shot pipeline

The agent runs all 11 stages end-to-end with minimal user input. Each stage's gate is checked autonomously; failures roll back one stage at a time. The agent reports a final tearsheet.

**When:** first-pass exploration. The cost of being wrong is low (no live capital), the team wants a baseline.

**Failure mode:** the agent picks a defensible default at every fork, which is rarely the team's best choice. Use this for a baseline, not for the model you'll deploy.

### Pattern 2 — Iterative with checkpoints

The agent runs autonomously until it hits a decision the human should own, then pauses with `AskUserQuestion`. The canonical pauses are: post-EDA (does the data match the frame?), post-Stage 6 (which of N candidate models?), pre-deploy (sign off?).

**Code — the model-selection checkpoint:**

```python
# stage6_checkpoint.py — Claude surfaces three candidates and asks the human.
# AskUserQuestion is a Claude Code tool; the wrapper here is illustrative.
candidates = [
    {"name": "xgb_v1",   "cv_sharpe": 1.82, "max_dd": 0.11, "n_features": 27},
    {"name": "lgbm_v1",  "cv_sharpe": 1.76, "max_dd": 0.09, "n_features": 27},
    {"name": "lstm_v1",  "cv_sharpe": 1.91, "max_dd": 0.18, "n_features": 14},
]

prompt = {
    "question": "Three candidates within 5% on OOS Sharpe but different drawdown profiles. Which to deploy?",
    "header": "Stage 6 — model selection checkpoint",
    "multi_select": False,
    "options": [
        {"label": f"{c['name']}: Sharpe={c['cv_sharpe']:.2f}, DD={c['max_dd']:.1%}, features={c['n_features']}",
         "description": "Higher Sharpe but deeper drawdown" if c['name'] == 'lstm_v1'
                        else "Lower Sharpe, gentler drawdown" if c['name'] == 'lgbm_v1'
                        else "Baseline GBT, widely understood"}
        for c in candidates
    ],
}
# In Claude Code: ask_user_question(questions=[prompt]) -> {"answer": "lgbm_v1: ..."}
```

The agent **must** use this pattern any time the gate criteria are within tolerance (default 5%) of each other; it must not silently pick.

**When:** the project will be deployed; the human is the ultimate gatekeeper for irreversible decisions (Stage 10 deploy, Stage 6 model commit).

### Pattern 3 — Parallel-agents fan-out

Claude spawns N parallel `Agent` sub-tasks for independent steps. Canonical uses: feature-set ablations, hyperparameter sweeps (when Optuna parallelism isn't enough), or multi-model comparisons.

**Code — parallel feature-set evaluation:**

```python
# stage4_parallel_feature_eval.py — fan out 4 subagents to score 4 candidate feature sets.
# Pseudocode for the Claude Code Agent tool.
feature_sets = ["technical_only", "technical_plus_micro", "technical_plus_macro", "full_kitchen_sink"]
subagent_prompts = [
    {
        "description": f"Eval feature set: {fs}",
        "prompt": f"""Load /data/features/{fs}.parquet.
Fit XGBoost with default hparams. Score under purged 5-fold CV.
Return JSON: {{set_name, cv_sharpe, cv_sharpe_std, n_features, top_features}}.
Do NOT modify state outside /tmp/agent_{fs}/.""",
        "subagent_type": "general-purpose",
    }
    for fs in feature_sets
]
# In Claude Code: Agent(subagent_prompts) launches 4 in parallel. Each runs in its own context.
# The main agent collects JSON results and ranks.
```

Cross-link to [`relentless-inception`](../relentless-inception/SKILL.md) for the multi-stage parallel orchestrator pattern (planning + executor + review subagents).

**When:** the inner work is embarrassingly parallel and per-task context is heavy enough that one Claude doing it serially would thrash. Three+ independent stages → fan out.

**Anti-pattern:** fanning out work that has cross-dependencies. Subagents share no state; if step B depends on step A's intermediate decision, run them in one agent.

### Pattern 4 — `/loop`-driven heartbeat

For Stage 11 retraining and monitoring. The Claude Code `/loop` skill runs a prompt or slash-command on a recurring interval; pair with `CronCreate` for stricter scheduling.

**Code — daily retraining heartbeat:**

```python
# stage11_retrain_loop.sh — invoked by `/loop 24h /retrain-heartbeat`.
# The `/retrain-heartbeat` command is a thin wrapper around:
python -m e2e_agentic_ml.retrain \
    --model-uri "models:/btc_dir_15m/Production" \
    --window 90d \
    --eval-window 7d \
    --promote-threshold 0.05 \
    --mlflow-tracking-uri "http://mlflow:5000" \
    --rollback-if-worse
```

```python
# python -m e2e_agentic_ml.retrain — the heartbeat itself.
def heartbeat(model_uri, window_days, eval_window_days, promote_threshold):
    df = load_rolling_window(window_days)
    new_model = retrain(df)
    deployed = mlflow.xgboost.load_model(model_uri)
    new_score = walk_forward_sharpe(new_model, df.tail_n_days(eval_window_days))
    old_score = walk_forward_sharpe(deployed, df.tail_n_days(eval_window_days))
    if new_score > old_score * (1 + promote_threshold):
        # Promote with human ack — AskUserQuestion in the orchestrating session.
        mlflow.register_model(new_model.uri, "btc_dir_15m", stage="Staging")
    else:
        mlflow.log_metric("rejected_retrain_score", new_score)
```

Cross-link: [`loop`](#) (Claude Code skill), `schedule` (CronCreate-style remote agents).

**When:** any continuous job — retraining, monitoring, drift detection. Long-running by design.

### Pattern 5 — Two-loop research orchestration

Borrowed from [`autoresearch`](../autoresearch/SKILL.md): an inner loop runs rapid experiments with a fixed scoring target; an outer loop synthesizes the results, identifies patterns across runs, and steers the next batch of experiments.

For e2e-agentic-ML this maps onto Stages 4–8 (inner = feature/model/hparam iteration; outer = "should we abandon this frame and revisit Stage 1?"). The pattern shines when the team has more than one viable hypothesis and wants to A/B them rigorously.

The agent maintains a `research-state.yaml` à la `autoresearch`; every inner-loop run mutates it; the outer loop reads it at the end of each batch.

**When:** the project is open-ended ("what predicts BTC moves?") rather than scoped ("fit a model to this preregistered hypothesis"). The outer loop is what keeps the team from chasing a single dead hypothesis for weeks.

---

## LLM-Tooling Layer

Concrete tools the agent uses across the eleven stages.

### Anthropic Claude API features

Use the [`claude-api`](#) skill (built-in) for any application-level Claude integration. The features that matter for e2e-agentic-ML:

- **Prompt caching** — the Stage 1 frame, Stage 4 feature manifest, and Stage 5 preregistration are all stable across iterations. Put them in the `system` block with `cache_control={"type": "ephemeral", "ttl": "5m"}` (or `"1h"` for longer sessions). Across 50 Optuna trials, this is the difference between paying input tokens once and paying them 50 times.
- **Thinking blocks** — set `thinking={"type": "enabled", "budget_tokens": 8000}` (or `"adaptive"`) for Stage 6 model ranking and Stage 8 evaluation diagnostics. The reasoning step matters there; for boilerplate stages it doesn't.
- **Tool use with `tool_choice`** — force structured JSON for any decision the orchestration loop must consume (hyperparameter ranges, model rankings, gate verdicts). See the Stage 7 code.
- **Batch API** — when running > 1000 independent LLM calls (e.g. Pattern 5 outer loop scoring 1000 candidate hypotheses), `client.messages.batches.create(...)` cuts cost ~50% and rate-limit pressure to zero. Verify current pricing at deploy time — unverified beyond Jan 2026.
- **Files API** — cache parquet pointers and large preregistration PDFs for the duration of a session. Upload once, reference by file ID. Verify availability for non-beta accounts — currently a beta feature.
- **Code execution sandbox** — `code_execution_20260120` (or later) lets Claude run Python in a sandbox for self-validation (e.g. "verify the feature manifest passes a leakage scan"). Cheaper and faster than spinning up Bash for small checks.

The exact field names above match the current `anthropic-sdk-python` (verified via Context7); structures like `{"type": "ephemeral", "ttl": "..."}` and `thinking={"type": "adaptive", "display": "summarized"}` are pulled from the SDK's type definitions.

### DSPy — prompt-as-program

Use [`prompt-engineering/dspy`](../prompt-engineering/dspy/SKILL.md) when the LLM is choosing features, hyperparameters, or models often enough that the prompt deserves to be optimized (BootstrapFewShot, MIPRO). The API surface:

```python
import dspy
dspy.configure(lm=dspy.LM("anthropic/claude-opus-4-7"))

class FeaturePicker(dspy.Signature):
    """Pick the top-k most informative features given a feature-importance dict."""
    feature_summary: dict = dspy.InputField()
    k: int = dspy.InputField()
    picked: list[str] = dspy.OutputField()
    reasoning: str = dspy.OutputField()

picker = dspy.ChainOfThought(FeaturePicker)
result = picker(feature_summary=imp, k=20)
```

The win: when 100+ runs of `picker` accumulate, run `dspy.MIPROv2` over the trace and the prompt self-optimizes. The agent uses DSPy where the prompt is the program; it uses raw Anthropic SDK calls where the prompt is a one-off.

### LangGraph / LlamaIndex

[`agents/langchain`](../agents/langchain/SKILL.md) and [`agents/llamaindex`](../agents/llamaindex/SKILL.md) host the state-machine and RAG-over-research-vault patterns. Use:

- **LangGraph** when the orchestration is a true state machine with cycles (Stage 11 monitor → retrain → promote → monitor). For linear pipelines, plain Claude Code Skill+Agent calls are simpler.
- **LlamaIndex / RAG** when the team has a deep research vault (papers, notes, previous backtest tearsheets) and Stage 1 framing should pull from it. Cross-link [`infranodus`](../infranodus/SKILL.md), [`ontology-creator`](../ontology-creator/SKILL.md) for the knowledge-graph layer; cross-link [`deep-tool-wiki`](../deep-tool-wiki/SKILL.md) for the curated wiki layer.

### MLflow + W&B

- [`mlops/mlflow`](../mlops/mlflow/SKILL.md) for tracking (`mlflow.start_run`, `mlflow.log_params`, `mlflow.xgboost.log_model`). The default. Self-hosted, no per-call cost.
- [`mlops/weights-and-biases`](../mlops/weights-and-biases/SKILL.md) when the team wants the hosted UI and richer artifact comparison. Use one or the other, not both; double-tracking is a maintenance liability.

Tag every run with the preregistration hash, the data manifest sha256, and the git commit. Three tags, no exceptions — the agent enforces this on `mlflow.start_run(...)`.

### Hydra

For config. One YAML per experiment, composed from a base config. Cross-link [`infrastructure`](../infrastructure/SKILL.md) for the broader infra patterns. The agent generates the YAML from the Stage 1 frame so that "rerun the whole pipeline" is `python -m e2e_agentic_ml +experiment=exp_2026_05_20`.

### MCP gateway

For any external tool — Tardis, CCXT, exchange APIs, news feeds — route through the project's MCP gateway when one is configured (the `tardis-data-agent` and `coingecko` skills assume the gateway). Direct API calls work but lose the unified caching, retry, and credential layer.

---

## Drift Detection Skeleton

A minimal drift monitor for Stage 11. Uses KS test for continuous features and PSI for distribution shift.

```python
# stage11_drift.py — daily drift check on a deployed model's features.
import numpy as np, polars as pl
from scipy.stats import ks_2samp

def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index. > 0.25 = significant shift, action required."""
    cuts = np.quantile(reference, np.linspace(0, 1, bins + 1))
    cuts[0], cuts[-1] = -np.inf, np.inf
    ref_pct = np.histogram(reference, cuts)[0] / len(reference) + 1e-6
    cur_pct = np.histogram(current,   cuts)[0] / len(current)   + 1e-6
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

def drift_report(ref_df: pl.DataFrame, cur_df: pl.DataFrame, features: list[str]):
    rows = []
    for f in features:
        r, c = ref_df[f].to_numpy(), cur_df[f].to_numpy()
        ks_stat, ks_p = ks_2samp(r, c)
        rows.append({"feature": f, "psi": psi(r, c), "ks_stat": ks_stat, "ks_p": ks_p,
                     "flag": "RED" if psi(r, c) > 0.25 or ks_p < 0.01 else "OK"})
    return pl.DataFrame(rows).sort("psi", descending=True)

# Usage in the heartbeat:
# rep = drift_report(training_features, this_week_features, FEATURES)
# if (rep["flag"] == "RED").any(): trigger_retrain_or_rollback()
```

The thresholds (PSI > 0.25, KS p < 0.01) are conservative defaults. Tune per project; document the tune.

---

## Anti-Patterns

The agent **will refuse** the following without explicit user override:

1. **Auto-deploy without human approval.** Stage 10 always routes through `AskUserQuestion`. Even with full automation enabled. The kill-switch and the deploy switch are human-only.
2. **Skipping purged CV.** Plain K-fold on time series leaks labels across folds via temporal autocorrelation. The agent will refuse `cross_val_score` with `KFold(shuffle=True)` on any returns-derived target.
3. **Reporting raw Sharpe without DSR + PBO.** Stage 8 enforces this. A Sharpe number without (a) the trials count and (b) the deflated value is not a result.
4. **Random train/test split on prices.** Same failure mode as #2. `train_test_split(shuffle=True)` is banned on temporal data.
5. **Look-ahead leakage in features.** Stage 4 enforces this via the leakage_check_passed manifest. The agent will not pass the gate without it.
6. **Going live off a vectorbt-only backtest.** Stage 9 requires the NautilusTrader event-driven confirmation. The agent will refuse to skip it.
7. **Picking a multiple-testing correction after seeing results.** Stage 5 locks it; once committed it is immutable for the project.
8. **Training before tracking is wired.** `mlflow.set_experiment(...)` must succeed before `.fit()` is called.
9. **One-off `.fit()` calls without a config.** All training goes through Hydra. The agent rewrites stray calls into config-driven invocations.
10. **Silently picking a model when candidates are within tolerance.** Use `AskUserQuestion`. The agent will not gamble with the team's bankroll.

---

## What the Agent Does NOT Decide Alone

Three classes of decision are reserved for the human:

1. **Capital allocation.** The agent designs strategies; the human funds them.
2. **Stage 10 deploy.** Always routed through `AskUserQuestion`.
3. **Stage 1 frame override.** If the agent's framing of a fuzzy goal doesn't match the human's intent, the human's intent wins. The agent surfaces its frame as a one-pager and asks for sign-off before Stage 2 begins.

Everything else (CV scheme, hyperparameter prior, feature pruning threshold, retrain frequency) the agent picks defensibly and reports.

---

## References

- **Specialist skills cross-linked from this orchestrator:**
  - Stage 1, 5: [`ml-hypothesis-design`](../ml-hypothesis-design/SKILL.md)
  - Stage 2: [`tardis-data-agent`](../tardis-data-agent/SKILL.md), [`ccxt`](../ccxt/SKILL.md), [`coingecko`](../coingecko/SKILL.md), [`nautilus-trader`](../nautilus-trader/SKILL.md)
  - Stage 3: [`exploratory-data-analysis`](../../k-dense-scientific-agent-skills/exploratory-data-analysis/SKILL.md), [`polars`](../../k-dense-scientific-agent-skills/polars/SKILL.md), [`seaborn`](../../k-dense-scientific-agent-skills/seaborn/SKILL.md), [`matplotlib`](../../k-dense-scientific-agent-skills/matplotlib/SKILL.md)
  - Stage 4: [`feature-engineering`](../feature-engineering/SKILL.md), [`microstructure-analysis`](../microstructure-analysis/SKILL.md)
  - Stage 6: [`xgboost`](../xgboost/SKILL.md), [`lightgbm`](../lightgbm/SKILL.md), [`catboost`](../catboost/SKILL.md), [`lstm-forecast`](../lstm-forecast/SKILL.md), [`transformer-forecast`](../transformer-forecast/SKILL.md), [`arima-forecast`](../arima-forecast/SKILL.md), [`prophet-forecast`](../prophet-forecast/SKILL.md), [`markov-regime-detection`](../markov-regime-detection/SKILL.md), [`autoencoder-anomaly-detection`](../autoencoder-anomaly-detection/SKILL.md), [`q-learning`](../q-learning/SKILL.md), [`deep-q-learning`](../deep-q-learning/SKILL.md), [`policy-gradients`](../policy-gradients/SKILL.md), [`stable-baselines3`](../../k-dense-scientific-agent-skills/stable-baselines3/SKILL.md)
  - Stage 7: [`mlops/mlflow`](../mlops/mlflow/SKILL.md), [`mlops/weights-and-biases`](../mlops/weights-and-biases/SKILL.md), [`distributed-training`](../distributed-training/), [`optimization`](../optimization/SKILL.md), [`adaptive-wfo-epoch`](../adaptive-wfo-epoch/SKILL.md)
  - Stage 8: [`model-evaluation`](../model-evaluation/SKILL.md)
  - Stage 9: [`vectorbt`](../vectorbt/SKILL.md), [`nautilus-trader`](../nautilus-trader/SKILL.md), [`tearsheet-generator`](../tearsheet-generator/SKILL.md), [`strategy-verify`](../strategy-verify/SKILL.md)
  - Stage 10: [`nautilus-trader`](../nautilus-trader/SKILL.md)
  - Stage 11: [`mlops`](../mlops/), [`observability`](../observability/SKILL.md)
- **Orchestration patterns:**
  - [`autoresearch`](../autoresearch/SKILL.md) (two-loop research)
  - [`relentless-inception`](../relentless-inception/SKILL.md) (parallel subagents + adversarial gates)
  - `/loop`, `schedule` (Claude Code built-in scheduling)
- **LLM tooling:**
  - [`prompt-engineering/dspy`](../prompt-engineering/dspy/SKILL.md)
  - [`agents/langchain`](../agents/langchain/SKILL.md), [`agents/llamaindex`](../agents/llamaindex/SKILL.md)
  - [`infranodus`](../infranodus/SKILL.md), [`ontology-creator`](../ontology-creator/SKILL.md), [`infranodus-cli`](../infranodus-cli/SKILL.md) (research-vault layer)
- **Foundational literature** (the agent quotes from these in preregistrations):
  - Bailey & López de Prado (2014), "The Deflated Sharpe Ratio."
  - Bailey, Borwein, López de Prado, Zhu (2017), "The Probability of Backtest Overfitting."
  - López de Prado (2018), *Advances in Financial Machine Learning*, esp. Ch. 4 (purged + embargoed CV) and Ch. 7 (triple-barrier labeling).
  - Lopez de Prado (2020), *Machine Learning for Asset Managers*.
- **SDK / framework references used to build this skill** (verified Jan 2026 via Context7):
  - `anthropic-sdk-python` — `cache_control`, `thinking`, `tool_choice`, `messages.create`, `code_execution_*` types confirmed.
  - `dspy` (Stanford NLP) — `Signature`, `Predict`, `ChainOfThought`, `MIPROv2` API confirmed.
  - `mlflow` — `start_run`, `log_params`, `log_metric`, `xgboost.log_model`, `xgboost.autolog` API confirmed.
  - NautilusTrader `TradingNode` schema — see the `nautilus-trader` skill's `references/` directory for the current Python and Rust references.

---

## Unverified / Caveats

- The Anthropic **Files API** is referenced as currently a beta feature; confirm general availability for your account before relying on it in a production heartbeat.
- The Anthropic **Batch API** pricing discount (~50%) is current as of Jan 2026; re-verify at deploy time.
- The `code_execution_20260120` tool type is the latest verified version in the SDK; if a newer version is in your installed SDK, prefer that.
- The "5% within-tolerance" rule for forcing `AskUserQuestion` in Pattern 2 is a heuristic; tune per project after a half-dozen runs.
- The PSI > 0.25 threshold for drift is a common industry default; the formal rationale (logarithmic in distribution shift) holds but the threshold itself is conventional, not derived.
- Confirmed cross-link targets (2026-05-20): [`microstructure-analysis`](../microstructure-analysis/SKILL.md) (methodology), [`microstructure-analyst`](../microstructure-analyst/SKILL.md) (workflow), and [`microstructure-feature-engineering`](../microstructure-feature-engineering/SKILL.md) (feature layer) all exist as distinct skills. Match the right one for the task.
- `llm-wiki` was deleted in the 2026-05-20 cleanup. Use [`deep-tool-wiki`](../deep-tool-wiki/SKILL.md), [`infranodus`](../infranodus/SKILL.md), and [`ontology-creator`](../ontology-creator/SKILL.md) as the vault layer instead.
