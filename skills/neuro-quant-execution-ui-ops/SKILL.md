---
name: neuro-quant-execution-ui-ops
description: Use when working in the neuro-quant monorepo on operate nautilus admin, prediction, and web ui repos without mixing ui, strategy, and execution state. Route to local references first, then deep-tool-wiki or 02-KB-main for full documentation.
allowed-tools: Read, Grep, Glob, Bash
---

# Execution UI Ops

## Scope

Operate Nautilus admin, prediction, and web UI repos without mixing UI, strategy, and execution state.

Use this skill when the task matches one of these signals:
- nautilus admin UI
- Nautilus-Web-UI
- nautilus prediction
- execution dashboard
- operator health check

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
| nautilus_admin | `toolbox/nautilus_admin` | `deep-tool-wiki/nautilus-admin/wiki.md` | `neuro-link/02-KB-main/nautilus-admin/index.md` |
| Nautilus-Web-UI | `toolbox/Nautilus-Web-UI` | `deep-tool-wiki/nautilus-web-ui/wiki.md` | `neuro-link/02-KB-main/nautilus-web-ui/index.md` |
| nautilus_prediction | `toolbox/nautilus_prediction` | `deep-tool-wiki/nautilus-prediction/wiki.md` | `neuro-link/02-KB-main/nautilus-prediction/index.md` |
| Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
