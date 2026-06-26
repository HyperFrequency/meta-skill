---
name: neuro-quant-resource-router
description: Use when working in the neuro-quant monorepo on route long neuro-quant tasks to the smallest relevant skill, local resource, kb leaf, or deep-tool-wiki page. Route to local references first, then deep-tool-wiki or 02-KB-main for full documentation.
allowed-tools: Read, Grep, Glob, Bash
---

# Quant Resource Router

## Scope

Route long neuro-quant tasks to the smallest relevant skill, local resource, KB leaf, or deep-tool-wiki page.

Use this skill when the task matches one of these signals:
- which neuro-quant skill should handle this
- find docs for a quant repo
- avoid context rot in a long workflow
- route this strategy or backtest task
- show the resource path before editing

## Required Workflow

1. Restate the goal, target repo/tool, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Open `references/verification-checklist.md` for the smallest relevant proof path.
4. Use `references/handoff-template.md` when a long workflow should move to another family skill.
5. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or `neuro-link/02-KB-main/<tool>/index.md`.
6. Separate verified facts, assumptions, missing resources, and blocked checks in the final answer.

## Progressive Disclosure

This skill keeps local resources in its own folder for immediate operation, but the full documentation belongs in deep-tool-wiki and the navigable leaf docs belong in 02-KB-main. Do not duplicate long API docs here. If a full doc is missing, use the generated stub path from the resource map and mark the lookup incomplete.

## Local Resources

- `references/resource-map.md`: relevant repos, local docs, deep-tool-wiki targets, and missing-doc status.
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
| nautilus_admin | `toolbox/nautilus_admin` | `deep-tool-wiki/nautilus-admin/wiki.md` | `neuro-link/02-KB-main/nautilus-admin/index.md` |
| Nautilus-Web-UI | `toolbox/Nautilus-Web-UI` | `deep-tool-wiki/nautilus-web-ui/wiki.md` | `neuro-link/02-KB-main/nautilus-web-ui/index.md` |
| nautilus_prediction | `toolbox/nautilus_prediction` | `deep-tool-wiki/nautilus-prediction/wiki.md` | `neuro-link/02-KB-main/nautilus-prediction/index.md` |
| pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` |
| Pine Script | `deep-tool-wiki/pine-script` | `deep-tool-wiki/pine-script/wiki.md` | `neuro-link/02-KB-main/pine-script/index.md` |
| openalgo-pinets | `toolbox/openalgo-pinets` | `deep-tool-wiki/openalgo-pinets/wiki.md` | `neuro-link/02-KB-main/openalgo-pinets/index.md` |
| neuro-link | `neuro-link` | `deep-tool-wiki/neuro-link/wiki.md` | `neuro-link/02-KB-main/neuro-link/index.md` |
| QMD | `deep-tool-wiki/qmd` | `deep-tool-wiki/qmd/wiki.md` | `neuro-link/02-KB-main/qmd/index.md` |
| k-dense-byok | `toolbox/k-dense-byok` | `deep-tool-wiki/k-dense-byok/wiki.md` | `neuro-link/02-KB-main/k-dense-byok/index.md` |
| TabPFN | `toolbox/TabPFN` | `deep-tool-wiki/tabpfn/wiki.md` | `neuro-link/02-KB-main/tabpfn/index.md` |
| chronos-forecasting | `toolbox/chronos-forecasting` | `deep-tool-wiki/chronos-forecasting/wiki.md` | `neuro-link/02-KB-main/chronos-forecasting/index.md` |
| Ludwig | `toolbox/ludwig` | `deep-tool-wiki/ludwig/wiki.md` | `neuro-link/02-KB-main/ludwig/index.md` |
| h2o-3 | `toolbox/h2o-3` | `deep-tool-wiki/h2o-3/wiki.md` | `neuro-link/02-KB-main/h2o-3/index.md` |
| hmmlearn | `toolbox/hmmlearn` | `deep-tool-wiki/hmmlearn/wiki.md` | `neuro-link/02-KB-main/hmmlearn/index.md` |
| DeepLOB | `toolbox/DeepLOB` | `deep-tool-wiki/deeplob/wiki.md` | `neuro-link/02-KB-main/deeplob/index.md` |
| TLOB | `toolbox/TLOB` | `deep-tool-wiki/tlob/wiki.md` | `neuro-link/02-KB-main/tlob/index.md` |
| poly_data | `toolbox/poly_data` | `deep-tool-wiki/poly-data/wiki.md` | `neuro-link/02-KB-main/poly-data/index.md` |
| tardis-python | `deep-tool-wiki/tardis-python` | `deep-tool-wiki/tardis-python/wiki.md` | `neuro-link/02-KB-main/tardis-python/index.md` |
| CCXT | `toolbox/docs/tools/ccxt.md` | `deep-tool-wiki/ccxt/wiki.md` | `neuro-link/02-KB-main/ccxt/index.md` |
| OpenBB | `toolbox/docs/tools/openbb.md` | `deep-tool-wiki/openbb/wiki.md` | `neuro-link/02-KB-main/openbb/index.md` |
| Optuna | `deep-tool-wiki/optuna` | `deep-tool-wiki/optuna/wiki.md` | `neuro-link/02-KB-main/optuna/index.md` |
| Ray | `deep-tool-wiki/ray-distributed` | `deep-tool-wiki/ray-distributed/wiki.md` | `neuro-link/02-KB-main/ray-distributed/index.md` |
| Dask Distributed | `deep-tool-wiki/dask-distributed` | `deep-tool-wiki/dask-distributed/wiki.md` | `neuro-link/02-KB-main/dask-distributed/index.md` |
| MLflow | `deep-tool-wiki/mlflow` | `deep-tool-wiki/mlflow/wiki.md` | `neuro-link/02-KB-main/mlflow/index.md` |
| PostgreSQL Optuna | `deep-tool-wiki/postgresql-optuna` | `deep-tool-wiki/postgresql-optuna/wiki.md` | `neuro-link/02-KB-main/postgresql-optuna/index.md` |
| GNU Parallel | `deep-tool-wiki/gnu-parallel` | `deep-tool-wiki/gnu-parallel/wiki.md` | `neuro-link/02-KB-main/gnu-parallel/index.md` |
| QuantLib-SWIG | `toolbox/QuantLib-SWIG` | `deep-tool-wiki/quantlib-swig/wiki.md` | `neuro-link/02-KB-main/quantlib-swig/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
