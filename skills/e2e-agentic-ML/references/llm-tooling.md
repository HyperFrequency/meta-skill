# LLM-Tooling Layer — Detailed Reference

Concrete tools the agent uses across the eleven stages. Referenced from `SKILL.md`.

## Anthropic Claude API features

Use the [`claude-api`](#) skill (built-in) for any application-level Claude integration. The features that matter for e2e-agentic-ML:

- **Prompt caching** — the Stage 1 frame, Stage 4 feature manifest, and Stage 5 preregistration are all stable across iterations. Put them in the `system` block with `cache_control={"type": "ephemeral", "ttl": "5m"}` (or `"1h"` for longer sessions). Across 50 Optuna trials, this is the difference between paying input tokens once and paying them 50 times.
- **Thinking blocks** — set `thinking={"type": "enabled", "budget_tokens": 8000}` (or `"adaptive"`) for Stage 6 model ranking and Stage 8 evaluation diagnostics. The reasoning step matters there; for boilerplate stages it doesn't.
- **Tool use with `tool_choice`** — force structured JSON for any decision the orchestration loop must consume (hyperparameter ranges, model rankings, gate verdicts). See the Stage 7 code in `lifecycle-stages.md`.
- **Batch API** — when running > 1000 independent LLM calls (e.g. Pattern 5 outer loop scoring 1000 candidate hypotheses), `client.messages.batches.create(...)` cuts cost ~50% and rate-limit pressure to zero. Verify current pricing at deploy time — unverified beyond Jan 2026.
- **Files API** — cache parquet pointers and large preregistration PDFs for the duration of a session. Upload once, reference by file ID. Verify availability for non-beta accounts — currently a beta feature.
- **Code execution sandbox** — `code_execution_20260120` (or later) lets Claude run Python in a sandbox for self-validation (e.g. "verify the feature manifest passes a leakage scan"). Cheaper and faster than spinning up Bash for small checks.

The exact field names above match the current `anthropic-sdk-python` (verified via Context7); structures like `{"type": "ephemeral", "ttl": "..."}` and `thinking={"type": "adaptive", "display": "summarized"}` are pulled from the SDK's type definitions.

## DSPy — prompt-as-program

Use [`prompt-engineering/dspy`](../../prompt-engineering/dspy/SKILL.md) when the LLM is choosing features, hyperparameters, or models often enough that the prompt deserves to be optimized (BootstrapFewShot, MIPRO). The API surface:

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

## LangGraph / LlamaIndex

[`agents/langchain`](../../agents/langchain/SKILL.md) and [`agents/llamaindex`](../../agents/llamaindex/SKILL.md) host the state-machine and RAG-over-research-vault patterns. Use:

- **LangGraph** when the orchestration is a true state machine with cycles (Stage 11 monitor → retrain → promote → monitor). For linear pipelines, plain Claude Code Skill+Agent calls are simpler.
- **LlamaIndex / RAG** when the team has a deep research vault (papers, notes, previous backtest tearsheets) and Stage 1 framing should pull from it. Cross-link [`infranodus`](../../infranodus/SKILL.md), [`ontology-creator`](../../ontology-creator/SKILL.md) for the knowledge-graph layer; cross-link [`deep-tool-wiki`](../../deep-tool-wiki/SKILL.md) for the curated wiki layer.

## MLflow + W&B

- [`mlops/mlflow`](../../mlops/mlflow/SKILL.md) for tracking (`mlflow.start_run`, `mlflow.log_params`, `mlflow.xgboost.log_model`). The default. Self-hosted, no per-call cost.
- [`mlops/weights-and-biases`](../../mlops/weights-and-biases/SKILL.md) when the team wants the hosted UI and richer artifact comparison. Use one or the other, not both; double-tracking is a maintenance liability.

Tag every run with the preregistration hash, the data manifest sha256, and the git commit. Three tags, no exceptions — the agent enforces this on `mlflow.start_run(...)`.

## Hydra

For config. One YAML per experiment, composed from a base config. Cross-link [`infrastructure`](../../infrastructure/SKILL.md) for the broader infra patterns. The agent generates the YAML from the Stage 1 frame so that "rerun the whole pipeline" is `python -m e2e_agentic_ml +experiment=exp_2026_05_20`.

## MCP gateway

For any external tool — Tardis, CCXT, exchange APIs, news feeds — route through the project's MCP gateway when one is configured (the `tardis-data-agent` and `coingecko` skills assume the gateway). Direct API calls work but lose the unified caching, retry, and credential layer.
