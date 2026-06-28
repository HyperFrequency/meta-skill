---
name: neuro-quant-quant-finance-bindings
description: >
  Routes quantitative finance pricing, curve-building, and risk/reporting work
  through QuantLib-SWIG bindings (plus quantstats/pyfolio for risk reports) in
  the neuro-quant monorepo. Use when the request says "price this instrument",
  "value this bond/swap/option", "build a discount curve", "bootstrap a yield
  curve", "compute greeks", "calculate VaR", "QuantLib", or "produce a risk
  report". It opens local references first (resource-map, verification-checklist,
  handoff-template), then escalates to deep-tool-wiki or 02-KB-main for full
  API documentation. For performance tearsheets use
  neuro-quant-tearsheet-generator; for running backtests use the vectorbt or
  nautilus-trader skills.
allowed-tools: Read, Grep, Glob, Bash
---

# Quant Finance Bindings

## Scope

Pricing, curve construction, greeks, and VaR/risk reporting via QuantLib-SWIG
bindings, with quantstats/pyfolio for risk and reporting output.

Use this skill when the task matches one of these signals:
- "price this instrument", "value this bond / swap / option"
- "build a discount curve", "bootstrap a yield curve"
- "compute greeks", "calculate VaR", "risk report"
- "QuantLib", "QuantLib-SWIG"
- curve construction, pricing model, risk calculation, finance bindings

Boundary: for performance tearsheets use `neuro-quant-tearsheet-generator`; for
backtests use the `vectorbt` or `nautilus-trader` skills. Do not run backtests
or build tearsheets here.

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
| QuantLib-SWIG | `toolbox/QuantLib-SWIG` | `deep-tool-wiki/quantlib-swig/wiki.md` | `neuro-link/02-KB-main/quantlib-swig/index.md` |
| quantstats / pyfolio | `toolbox/docs/tools/quantstats-pyfolio.md` | `deep-tool-wiki/quantstats-pyfolio/wiki.md` | `neuro-link/02-KB-main/quantstats-pyfolio/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.
