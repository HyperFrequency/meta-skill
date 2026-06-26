---
name: neuro-quant-forecasting-oracle-ml
description: Use when working in the neuro-quant monorepo on run and evaluate forecasting, automl, tabular ml, regime, and order-book learning repos. Route to local references first, then deep-tool-wiki or 02-KB-main for full documentation.
allowed-tools: Read, Grep, Glob, Bash
---

# Forecasting Oracle ML

## Scope

Run and evaluate forecasting, AutoML, tabular ML, regime, and order-book learning repos.

Use this skill when the task matches one of these signals:
- TabPFN baseline
- Chronos forecast
- Ludwig benchmark
- H2O AutoML
- DeepLOB or TLOB
- regime model with hmmlearn

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
| TabPFN | `toolbox/TabPFN` | `deep-tool-wiki/tabpfn/wiki.md` | `neuro-link/02-KB-main/tabpfn/index.md` |
| chronos-forecasting | `toolbox/chronos-forecasting` | `deep-tool-wiki/chronos-forecasting/wiki.md` | `neuro-link/02-KB-main/chronos-forecasting/index.md` |
| Ludwig | `toolbox/ludwig` | `deep-tool-wiki/ludwig/wiki.md` | `neuro-link/02-KB-main/ludwig/index.md` |
| h2o-3 | `toolbox/h2o-3` | `deep-tool-wiki/h2o-3/wiki.md` | `neuro-link/02-KB-main/h2o-3/index.md` |
| hmmlearn | `toolbox/hmmlearn` | `deep-tool-wiki/hmmlearn/wiki.md` | `neuro-link/02-KB-main/hmmlearn/index.md` |
| DeepLOB | `toolbox/DeepLOB` | `deep-tool-wiki/deeplob/wiki.md` | `neuro-link/02-KB-main/deeplob/index.md` |
| TLOB | `toolbox/TLOB` | `deep-tool-wiki/tlob/wiki.md` | `neuro-link/02-KB-main/tlob/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
