# Agent Orchestration Patterns — Detailed Reference

Five patterns, picked based on the project's tempo and the team's bandwidth. Referenced from `SKILL.md`.

## Pattern 1 — Single-shot pipeline

The agent runs all 11 stages end-to-end with minimal user input. Each stage's gate is checked autonomously; failures roll back one stage at a time. The agent reports a final tearsheet.

**When:** first-pass exploration. The cost of being wrong is low (no live capital), the team wants a baseline.

**Failure mode:** the agent picks a defensible default at every fork, which is rarely the team's best choice. Use this for a baseline, not for the model you'll deploy.

## Pattern 2 — Iterative with checkpoints

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

## Pattern 3 — Parallel-agents fan-out

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

Cross-link to [`relentless-inception`](../../relentless-inception/SKILL.md) for the multi-stage parallel orchestrator pattern (planning + executor + review subagents).

**When:** the inner work is embarrassingly parallel and per-task context is heavy enough that one Claude doing it serially would thrash. Three+ independent stages → fan out.

**Anti-pattern:** fanning out work that has cross-dependencies. Subagents share no state; if step B depends on step A's intermediate decision, run them in one agent.

## Pattern 4 — `/loop`-driven heartbeat

For Stage 11 retraining and monitoring. The Claude Code `/loop` skill runs a prompt or slash-command on a recurring interval; pair with `CronCreate` for stricter scheduling.

**Code — daily retraining heartbeat:**

```bash
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

Cross-link: `loop` (Claude Code skill), `schedule` (CronCreate-style remote agents).

**When:** any continuous job — retraining, monitoring, drift detection. Long-running by design.

## Pattern 5 — Two-loop research orchestration

Borrowed from [`autoresearch`](../../autoresearch/SKILL.md): an inner loop runs rapid experiments with a fixed scoring target; an outer loop synthesizes the results, identifies patterns across runs, and steers the next batch of experiments.

For e2e-agentic-ML this maps onto Stages 4–8 (inner = feature/model/hparam iteration; outer = "should we abandon this frame and revisit Stage 1?"). The pattern shines when the team has more than one viable hypothesis and wants to A/B them rigorously.

The agent maintains a `research-state.yaml` à la `autoresearch`; every inner-loop run mutates it; the outer loop reads it at the end of each batch.

**When:** the project is open-ended ("what predicts BTC moves?") rather than scoped ("fit a model to this preregistered hypothesis"). The outer loop is what keeps the team from chasing a single dead hypothesis for weeks.
