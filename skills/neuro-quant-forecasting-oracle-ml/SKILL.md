---
name: neuro-quant-forecasting-oracle-ml
version: 0.1.0
description: >
  Routes forecasting and ML ORACLE-stack work in the neuro-quant monorepo across
  TabPFN, chronos-forecasting, ludwig, h2o-3, hmmlearn, DeepLOB, and TLOB. Use when
  the user asks to "forecast this series", "run a TabPFN baseline", "chronos forecast",
  "build a Ludwig config", "compare H2O AutoML", "fit HMM regimes" or "regime via HMM",
  or work a "LOB deep model" (DeepLOB/TLOB). Picks the right oracle tool, enforces the
  data-contract and leakage gates, runs a small verified path (import smoke -> tiny-data
  -> baseline -> artifact) before any long training, and routes to local references and
  deep-tool-wiki for current APIs. For model VALIDATION / PBO / walk-forward scoring use
  model-evaluation; for feature pipelines use feature-engineering; route hyperparameter
  search, parallel workers, study storage, and cluster execution to
  oracle-distributed-optimization.
allowed-tools: Read, Grep, Glob, Bash
---

# Forecasting Oracle ML

Use this family when the task is to evaluate, run, package, or document forecasting
and ML tools on the oracle side of the neuro-quant stack. The goal is a small verified
path first, then deeper training or wiki work only when the first gate passes.

## Scope

Run and evaluate forecasting, AutoML, tabular ML, regime, and order-book learning repos.
This family owns these tools:

- `TabPFN`: small tabular classification baselines and zero-shot tabular inference.
- `chronos-forecasting`: foundation time-series forecasting and probabilistic forecast checks.
- `ludwig`: declarative ML experiments from config files.
- `h2o-3`: JVM-backed H2O AutoML and tabular model export checks.
- `hmmlearn`: hidden Markov model regime detection and simple probabilistic state models.
- `DeepLOB`: CNN/LSTM limit-order-book research workflow; research-script style unless packaging exists.
- `TLOB`: transformer limit-order-book research workflow; research-script style unless packaging exists.

### Boundaries

- For model VALIDATION, PBO, deflated metrics, and walk-forward scoring use `model-evaluation`.
- For feature pipelines and feature construction use `feature-engineering`.
- Route hyperparameter search orchestration, parallel workers, study storage, MLflow
  tracking, and cluster execution to `oracle-distributed-optimization`.

## Trigger Phrases

Use this skill for requests like:

- "forecast this series"
- "run a TabPFN baseline"
- "forecast this series with Chronos" / "chronos forecast"
- "build a Ludwig config"
- "compare H2O AutoML against oracle models"
- "fit HMM regimes" / "regime via HMM"
- "DeepLOB or TLOB order book model" / "LOB deep model"
- "zero-shot forecast"
- "tabular oracle smoke"
- "oracle ML family coverage"

Ask one clarifying question if the request does not name the target data shape:
tabular rows, univariate series, multivariate panel, or order book tensor.

## Required Workflow

1. Restate the goal, target repo/tool, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Open `references/verification-checklist.md` for the smallest relevant proof path.
4. Use `references/handoff-template.md` when a long workflow should move to another family skill.
5. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or
   `neuro-link/02-KB-main/<tool>/index.md`.
6. Separate verified facts, assumptions, missing resources, and blocked checks in the final answer.

## Operating Rules

- State the assumed data contract before work: target column, timestamp column, symbol
  key, train/test split, and whether future bars are excluded.
- Do not run long training by default. Start with an import or tiny-data smoke, then a
  bounded eval, then a real run.
- Keep research repos separate from packaged libraries. If DeepLOB or TLOB still has no
  install metadata, treat it as script/notebook work and do not invent an import path.
- Before giving current API signatures or code examples, use the docs-dual-lookup path:
  local qmd/wiki first, then Context7 plus Auggie when external confirmation is needed.
- Prefer local repo evidence over memory: `toolbox/docs/tools/oracle-ml-family.md`,
  `toolbox/docs/tools/h2o.md`, pending DeepLOB/TLOB notes, package manifests, and smoke evidence.

## Progressive Disclosure

This skill keeps local resources in its own folder for immediate operation, but the full
documentation belongs in deep-tool-wiki and the navigable leaf docs belong in 02-KB-main.
Do not duplicate long API docs here. If a full doc is missing, use the generated stub path
from the resource map and mark the lookup incomplete.

| Level | Load only this much | Use when | Stop when |
| --- | --- | --- | --- |
| 0 | User request, `git status --short`, relevant data path names | Every task | Intent, write boundary, and data shape are clear |
| 1 | `toolbox/docs/tools/oracle-ml-family.md`, `toolbox/docs/tools/h2o.md`, `_pending/deeplob.md`, `_pending/tlob.md` | Picking a tool or checking local install status | The requested tool and current packaging state are known |
| 2 | `deep-tool-wiki/<tool>/wiki.md` when present, plus qmd/RAG query | Explaining tool behavior or known pitfalls | Local page answers the question with source paths |
| 3 | Tool README, examples, tests, and package metadata under `toolbox/<tool>/` | Runtime or packaging work | Entry point, dependency surface, and smoke command are known |
| 4 | `.batch-runs/.../evidence` and current venv commands | Verifying a claim | Fresh command output confirms or refutes the claim |
| 5 | Context7 plus Auggie, then official docs or papers | Local coverage is missing or stale | Source gap is captured for deep-tool-wiki |

## Local Resources

- `references/resource-map.md`: relevant repos, local docs, deep-tool-wiki targets, and missing-doc status.
- `references/verification-checklist.md`: proof gates for this family.
- `references/handoff-template.md`: structured handoff for multi-step workflows.
- `evals/evals.json`: trigger, false-positive, and missing-resource cases.
- `agents/openai.yaml`: minimal UI metadata for skill discovery.

## Covered Tools / Tool Routing

| Tool | Source | First use | Verification focus | Avoid |
| --- | --- | --- | --- | --- |
| `TabPFN` | `toolbox/TabPFN` | Fast tabular classification baseline | Import, deterministic split, class labels, probability shape, metric above dummy baseline | Large-table claims without checking current upstream limits |
| `chronos-forecasting` | `toolbox/chronos-forecasting` | Zero-shot univariate or panel forecast | Context length, prediction length, quantile/sample shape, no future leakage | Treating forecast samples as point estimates without documenting aggregation |
| `ludwig` | `toolbox/ludwig` | Declarative model config from structured data | Config validates, train/eval split exists, metrics artifact lands | Silent config generation without naming input and output features |
| `h2o-3` | `toolbox/h2o-3` | JVM-backed tabular AutoML | JDK/JAVA_HOME, cluster init/shutdown, leaderboard produced, cluster cleanup | Leaving an H2O cluster running after a smoke |
| `hmmlearn` | `toolbox/hmmlearn` | Regime detection and probabilistic state labels | Feature scaling, state count rationale, random seed, transition matrix sanity | Claiming regimes are causal market states |
| `DeepLOB` | `toolbox/DeepLOB` | Limit-order-book research reproduction | Dataset tensor schema, script path, paper metric target, hardware fit | Pretending it is an installed package if no packaging exists |
| `TLOB` | `toolbox/TLOB` | Transformer LOB research reproduction | Sequence/window shape, train script path, seed, memory budget | Mixing it with DeepLOB preprocessing unless the file path proves compatibility |

Full docs: `deep-tool-wiki/<tool>/wiki.md`. KB lookup: `neuro-link/02-KB-main/<tool>/index.md`.
See `references/resource-map.md` for per-tool doc status.

## Verification Gates

1. **Data contract gate**: target, time index, symbol key, and split boundaries are
   explicit. For market data, the split must be chronological unless the user says otherwise.
2. **Import or CLI gate**: the selected tool imports or starts locally. For H2O, Java and
   the cluster lifecycle must pass. For research repos, the script path must exist.
3. **Tiny-data gate**: run a minimal sample that finishes in minutes and produces a metric,
   forecast array, state sequence, or leaderboard.
4. **Baseline gate**: compare against a dummy classifier, naive forecast, simple HMM, or
   documented paper baseline as appropriate.
5. **Artifact gate**: save or name the produced model, config, metric file, forecast file,
   plot, or logs. If nothing is saved, say so.
6. **Leakage gate**: verify no future labels, future covariates, or post-event
   normalization entered the training context.

## Local Docker and Eval Personas

- `mac-oracle-smoke`: venv-only import and tiny-data checks on Apple Silicon. Default for
  TabPFN, Chronos, Ludwig, and hmmlearn.
- `h2o-jvm-smoke`: local or containerized JDK plus H2O cluster init/shutdown. Use when H2O
  behavior, Java, ports, or memory are in scope.
- `lob-research-repro`: isolated run for DeepLOB/TLOB scripts with fixed data slices and
  explicit memory limits. Use Docker only if the repo requires CUDA or system packages that
  the local venv cannot provide.
- `forecast-eval-persona`: walk-forward forecast scoring with naive baseline,
  horizon-specific metrics, and artifact capture.
- `tabular-eval-persona`: train/test split, label distribution check, probability
  calibration check, and SHAP/LIME only after model quality is real.

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Done Criteria

A forecasting or ML task is done when the response names:

- The selected tool and why it was selected.
- The data contract and leakage check.
- The exact local source, wiki page, or command used.
- The verification gate reached and any gate that remains blocked.
- Any deep-tool-wiki gap discovered during the work.

For draft-only work, list the proposed Markdown or JSON files and say no runtime model
state was changed.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next
verification step.
