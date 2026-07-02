---
name: neuro-quant-research-proof
version: 0.1.0
description: >
  Cross-cutting VERIFY-before-claiming gate for the neuro-quant monorepo:
  validate repo-local research, Modal, data, release, strategy, and evidence
  artifacts before any result is claimed. Routes to local references first
  (resource-map, verification-checklist, handoff-template), then deep-tool-wiki
  or 02-KB-main for full documentation. Use when the user says "prove this
  result", "verify before claiming", "release-local proof", "modal volume
  roundtrip", or "is this evidence sound", or asks to confirm a research run,
  Optuna tearsheet, or strategy proof before reporting it. For distributed
  sweep and parallel optimization infrastructure use
  neuro-quant-distributed-optimization; for model PBO and deflated-Sharpe
  statistics use model-evaluation.
allowed-tools: Read, Grep, Glob, Bash
---

# Neuro Quant Research Proof

## Scope

Validate repo-local research, Modal, data, release, strategy, and evidence artifacts before claims are made.

This is the cross-cutting proof gate: nothing about a research result, run, or
artifact should be claimed until it has been validated against a repo-local
source. Use this skill when the task matches one of these signals:
- "prove this result"
- "verify before claiming"
- "release-local proof" / "release-local-proof"
- "modal volume roundtrip"
- "is this evidence sound"
- "verify this research run"
- "Optuna tearsheet proof"
- "strategy proof"
- any request to confirm run evidence before it is reported

## Boundary

This skill owns the *verification* surface only. Hand off when the task is not
about proving an existing artifact:
- Distributed sweeps, parallel trial fan-out, or optimization infrastructure
  (running many studies, scaling Optuna/Ray) → `neuro-quant-distributed-optimization`.
- Model selection statistics — Probability of Backtest Overfitting (PBO),
  deflated/probabilistic Sharpe, multiple-testing corrections → `model-evaluation`.
Stay here when the question is "is this result real, reproducible, and backed by
a repo-local artifact?" rather than "how do I run the sweep?" or "what is the
overfit-adjusted statistic?".

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
| neuro-link | `neuro-link` | `deep-tool-wiki/neuro-link/wiki.md` | `neuro-link/02-KB-main/neuro-link/index.md` |
| Optuna | `deep-tool-wiki/optuna` | `deep-tool-wiki/optuna/wiki.md` | `neuro-link/02-KB-main/optuna/index.md` |
| MLflow | `deep-tool-wiki/mlflow` | `deep-tool-wiki/mlflow/wiki.md` | `neuro-link/02-KB-main/mlflow/index.md` |
| poly_data | `toolbox/poly_data` | `deep-tool-wiki/poly-data/wiki.md` | `neuro-link/02-KB-main/poly-data/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
