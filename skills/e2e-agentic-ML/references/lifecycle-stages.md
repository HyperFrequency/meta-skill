# Lifecycle Stages — Detailed Reference

The eleven stages, their agentic decisions, the specialist skill each routes to, and the gate criteria that must pass before advancing. Referenced from `SKILL.md`.

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

The orchestration job: at every stage, the agent decides (a) which specialist skill executes the stage, (b) whether the artifact passes the gate to the next stage, and (c) whether to checkpoint with the human.

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

**Route to:** [`ml-hypothesis-design`](../../ml-hypothesis-design/SKILL.md) for the formal H0/H1/power/preregistration framework. That skill is where the frame becomes a falsifiable hypothesis.

**Gate to Stage 2:** a written one-pager containing (universe, frequency, label definition pseudocode, H0, H1 with target effect size, decision rule, multiple-testing budget). If any of those six fields is empty, do not proceed.

---

## Stage 2 — Data Acquisition

**Goal:** assemble the raw inputs at the right venue, granularity, and depth, with leakage-safe alignment.

**Agentic decisions:**

| Goal | Default data source | Skill |
|---|---|---|
| Crypto tick / L2 history | Tardis.dev | [`tardis-data-agent`](../../tardis-data-agent/SKILL.md) |
| Crypto OHLCV via exchanges | ccxt | [`ccxt`](../../ccxt/SKILL.md) |
| Crypto fundamentals / macro | CoinGecko | [`coingecko`](../../coingecko/SKILL.md) |
| Equities / FX / futures bars | NautilusTrader data catalog | [`nautilus-trader`](../../nautilus-trader/SKILL.md) |
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

**Tooling:** [`polars`](../../../k-dense-scientific-agent-skills/polars/SKILL.md) for the heavy frame work, [`seaborn`](../../../k-dense-scientific-agent-skills/seaborn/SKILL.md) and [`matplotlib`](../../../k-dense-scientific-agent-skills/matplotlib/SKILL.md) for plots, [`exploratory-data-analysis`](../../../k-dense-scientific-agent-skills/exploratory-data-analysis/SKILL.md) for the auto-report template.

**Gate to Stage 4:** the agent produces a 1-page EDA summary (HTML or markdown) that the human can scan in 60 seconds. If anything in the summary contradicts the Stage 1 frame, the agent surfaces the conflict via `AskUserQuestion` and pauses.

---

## Stage 4 — Feature Engineering

**Goal:** build a leakage-safe feature matrix with honest labels.

**Routing decision:**

| Data layer | Skill |
|---|---|
| OHLCV bars + technical indicators | [`feature-engineering`](../../feature-engineering/SKILL.md) |
| L2 / L3 order book + tick-level signs | [`microstructure-feature-engineering`](../../microstructure-feature-engineering/SKILL.md) (see also `microstructure-analysis`) |
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

This stage is owned end-to-end by [`ml-hypothesis-design`](../../ml-hypothesis-design/SKILL.md). The agent's job here is to:

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
│                Cross-link: ../../q-learning/, ../../deep-q-learning/,
│                ../../policy-gradients/, ../../../k-dense-scientific-agent-skills/stable-baselines3/.
└── no → it's a prediction problem.

   Is the input tabular + structured (engineered features, < 1000 cols)?
   ├── yes → gradient-boosted trees.
   │         ../../xgboost/  (default; widest ecosystem)
   │         ../../lightgbm/ (fastest on > 1M rows)
   │         ../../catboost/ (best with categorical features)
   └── no → it's sequential / unstructured.

      Is there strong seasonality / known periodicity?
      ├── yes → classical forecast.
      │         ../../arima-forecast/, ../../prophet-forecast/, ../../transformer-forecast/
      └── no → sequence model.
                ../../lstm-forecast/, ../../transformer-forecast/

      Is the goal unsupervised regime / anomaly detection?
      ├── yes → ../../markov-regime-detection/, ../../autoencoder-anomaly-detection/
      └── (otherwise pick from above)
```

The agent picks the **simplest viable** branch. The default for "I have engineered features and want a baseline" is `xgboost`. Going to LSTM/Transformer before exhausting GBT is a smell.

**Gate to Stage 7:** three candidates ranked. The agent surfaces them and asks the human via `AskUserQuestion` only if the top three are within 5% of each other on the chosen scoring metric; otherwise it proceeds with the leader.

---

## Stage 7 — Training

**Goal:** fit the chosen model with experiment tracking, principled hyperparameter search, and a reproducible config.

**Required tooling:**

- **Experiment tracking** — [`mlops/mlflow`](../../mlops/mlflow/SKILL.md) (default) or [`mlops/weights-and-biases`](../../mlops/weights-and-biases/SKILL.md). One run per (model, hyperparams, seed, data window). Tag with the preregistration hash.
- **Hyperparameter search** — Optuna with TPE sampler. The agent constrains the prior using LLM judgement (see code below). Cross-link: [`optimization`](../../optimization/SKILL.md) for the broader optimization recipes.
- **Distributed training** — if model size or epoch budget warrants it, route to [`distributed-training`](../../distributed-training/) (accelerate, ray-train, deepspeed, pytorch-fsdp2). The agent decides based on a 5-minute single-GPU benchmark.
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

Owned end-to-end by [`model-evaluation`](../../model-evaluation/SKILL.md). The agent:

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

1. **Vectorized** with [`vectorbt`](../../vectorbt/SKILL.md) — fast, broad parameter sweeps, walk-forward optimization, tearsheet generation. Use this for the parameter robustness check and the Pareto frontier across `(Sharpe, max DD)`. Cross-link [`tearsheet-generator`](../../tearsheet-generator/SKILL.md).
2. **Event-driven** with [`nautilus-trader`](../../nautilus-trader/SKILL.md) backtest engine — slow, but exchange-accurate, with realistic order matching, latency, and fill models. Use this as the final go/no-go gate before live.

The agent picks parameter robustness via vectorbt sweeps first; the chosen parameter set is then re-run in NautilusTrader for the event-accurate confirmation.

**Anti-pattern:** going live off a vectorbt backtest alone. Vectorbt's fill model assumes perfect liquidity at the bar's close; that assumption breaks under stress. NautilusTrader's event model catches what vectorbt smooths over.

**Gate to Stage 10:** the NautilusTrader backtest's Sharpe is within 1σ of the vectorbt backtest's. If they diverge, the discrepancy is investigated (latency, queue position, partial fills) before any deployment talk.

---

## Stage 10 — Live Deployment

**Goal:** deploy the strategy to a live venue with monitored capital.

Owned by [`nautilus-trader`](../../nautilus-trader/SKILL.md). The agent assembles a `TradingNode` config that points to the live venue, with the same strategy class used in the Stage 9 backtest.

References:
- NautilusTrader Python: [`nautilus-trader/references/`](../../nautilus-trader/references/) for the `TradingNode` config schema.
- NautilusTrader Rust: same references — Rust-core actors handle the hot path.
- Hyperliquid mainnet integration is pre-built (see the `nautilus-trader` skill for the SDK patch).

**Mandatory pre-deploy checklist** (the agent runs each):

1. Paper-trade run for at least the embargo window (default 1 trading week).
2. Risk limits configured at the venue level (max position, max loss per day, max gross).
3. Kill-switch wired (a single CLI command or webhook that flattens the book and disables the strategy).
4. Rollback path documented: how to revert to the previous model version in under 5 minutes.

The agent **must** route this gate through `AskUserQuestion`. No autonomous push to live trading — ever. See the checkpoint code in `orchestration-patterns.md`.

**Gate to Stage 11:** signed-off deployment manifest committed; first 24h of live PnL recorded.

---

## Stage 11 — Monitoring and Retraining

**Goal:** detect drift, schedule retraining, define rollback triggers.

Owned by [`mlops`](../../mlops/) (the suite). Three loops run in parallel after deployment:

1. **Performance monitor** — live Sharpe rolling over the last N bars, compared to the backtest's IS+OOS distribution. Z-score of live-vs-expected > 2 is yellow; > 3 is red.
2. **Drift monitor** — KS test and PSI on incoming features vs the training distribution, per feature, daily. Any feature with PSI > 0.25 is flagged. See `drift-detection.md` for the skeleton.
3. **Retraining heartbeat** — refit the model on the rolling window once a day (default) or once a week (lower frequency strategies). Compare new-model vs deployed-model on the most recent hold-out. Promote only if DSR-deflated.

**Rollback procedure:**

- Red flag fires → kill-switch → flatten book.
- Within 1h, the agent assembles a diagnostic: which monitor fired, what changed, which feature(s) drifted, what the retrained model's OOS metrics say.
- If retraining recovers metrics → redeploy with the new model after a human ack via `AskUserQuestion`.
- If retraining doesn't recover → loop all the way back to Stage 1 (the frame may no longer hold).

The retraining heartbeat is the canonical use of the `/loop`-driven heartbeat pattern (see `orchestration-patterns.md`).
