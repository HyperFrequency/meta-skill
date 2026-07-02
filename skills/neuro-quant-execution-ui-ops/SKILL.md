---
name: neuro-quant-execution-ui-ops
version: 0.1.0
description: >
  Operate, inspect, and document the Nautilus EXECUTION / UI / OPS surfaces in the
  neuro-quant monorepo: nautilus_admin (control plane), Nautilus-Web-UI (trader
  dashboard), nautilus_prediction (Kalshi/Polymarket backtest + PMXT relay), and
  nautilus_trader from the operations/runtime view. Routes each request to the right
  surface, runs read-only inspection before any state change, and keeps UI, strategy,
  and execution state separated. Use when the task says "nautilus admin", "web ui",
  "prediction service", "execution dashboard", "operator health check", or
  "do not mix ui/strategy/execution state". For the backtest ENGINE itself and
  strategy authoring use nautilus-trader. Not for strategy research, signal generation,
  or algorithm optimization — route those to nautilus-trader or market-research-runtime.
allowed-tools: Read, Grep, Glob, Bash
---

# Execution UI Ops

## Scope

Operate Nautilus admin, prediction, and web UI repos without mixing UI, strategy, and execution state. This is an execution and operations skill: it protects live-state boundaries, prefers read-only inspection first, and distinguishes demo/synthetic UI state from attached trading-engine state.

Use this skill when the task matches one of these signals:
- nautilus admin UI
- Nautilus-Web-UI
- nautilus prediction
- execution dashboard
- operator health check
- "do not mix ui/strategy/execution state"

## Tool Boundary

- Use `nautilus_trader` (ops view) for event-driven backtesting, catalog-backed data replay, live-trading semantics, and execution-model parity between research and live systems. For the backtest ENGINE and strategy authoring itself, route to the `nautilus-trader` sibling skill.
- Use `nautilus_admin` for control-plane/admin coverage: component health, feature flags, database backends, audit logs, access control, and operational actions.
- Use `Nautilus-Web-UI` for trader-facing workflows: strategies, orders, positions, risk, live market data, alerts, performance, and backtesting pages.
- Use `nautilus_prediction` for Kalshi/Polymarket prediction-market backtesting, PMXT relay/mirror workflows, multi-market charting, and prediction-market execution modeling.
- Send signal research, indicator sweeps, and return tear sheets back to the market-research-runtime family unless the task is explicitly about execution handoff.

## Safety Rules (live-state)

- Start read-only: inspect status, config, routes, docs, and logs before invoking any state-changing endpoint.
- Never assume a UI is attached to a real trading engine. Verify whether it is demo mode, offline fallback, mock data, or live bridge state.
- Treat order placement, strategy start/stop, risk-limit mutation, database cleanup, key rotation, and engine shutdown as high-risk actions.
- Require explicit user confirmation before any live or potentially live state-changing action.
- Preserve auditability: record what endpoint, page, command, or service was inspected or changed.

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

## Operating Steps

1. Classify the surface.
   - `nautilus_trader`: library/runtime engine (ops view).
   - `nautilus_admin`: admin control plane.
   - `Nautilus-Web-UI`: trader dashboard and FastAPI/React interface.
   - `nautilus_prediction`: prediction-market backtest and PMXT relay workflow.

2. Confirm runtime mode.
   - Local dev server, Docker Compose, Modal, cloud VM, or static docs only.
   - Demo/offline fallback versus attached engine.
   - API key, CORS, database, and broker-adapter configuration.

3. Inspect before operating.
   - Health endpoints and process status.
   - Frontend routes and backend route maps.
   - Database availability: Redis, PostgreSQL, TiDB, Parquet, SQLite, or catalog paths as applicable.
   - Nautilus catalog availability and version alignment.

4. Execute only the requested operation.
   - Keep changes scoped to the named service or workflow.
   - Prefer dry-run, demo, testnet, or backtest mode when the goal can be proven without live risk.
   - For UI work, verify the page renders and the backing endpoint returns plausible data.

5. Report with operational evidence.
   - State which mode was verified.
   - State which endpoints/pages/commands were checked.
   - State whether results came from live engine state, demo data, fallback market data, or cached data.
   - List blockers separately from successful checks.

## Per-Tool Verification

For `nautilus_trader` (ops view):
- Confirm the installed/imported version and whether the code path is v1 legacy, v2 Rust, or v2 PyO3 when that distinction matters.
- Prefer high-level `BacktestNode`/`TradingNode` semantics for production handoff unless the task specifically needs low-level engine access.
- Confirm catalog paths and avoid assuming multiple nodes can safely run inside one process.

For `nautilus_admin`:
- Check the Node/Python bridge state before trusting component controls.
- Distinguish component health, feature management, database operations, and audit logs.
- Confirm whether database pages are connected to TiDB, Redis, PostgreSQL, and Parquet or showing placeholder/demo state.

For `Nautilus-Web-UI`:
- Check backend health, frontend route, WebSocket behavior, auth mode, and CORS config.
- Confirm Binance public-market fallback versus engine-sourced market data.
- Verify alerts persistence before claiming restart-safe behavior.

For `nautilus_prediction`:
- Identify the market source: Kalshi, Polymarket, PMXT mirror, local files, or relay.
- Confirm runner contract, output paths, chart/report mode, and execution-model limitations.
- Separate prediction-market charting metrics from Nautilus engine execution evidence.

## Failure Modes To Surface

- UI pages reporting synthetic demo data as if they were live engine state.
- Admin control actions available without a verified bridge or access-control boundary.
- Live-trading assumptions copied from research backtests without checking adapter semantics.
- Prediction-market data fetched from stale mirrors or relay cache without timestamp evidence.
- Multiple Nautilus nodes started in one process when the active version warns against that pattern.
- Database cleanup or optimization endpoints invoked during a shared-worker batch run.

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step. Use this template:

```markdown
## Execution UI Ops Result

Surface: nautilus_trader | nautilus_admin | Nautilus-Web-UI | nautilus_prediction
Runtime mode: <local/docker/cloud/demo/live/testnet>
Evidence checked: <paths, endpoints, logs, screenshots, commands>
State classification: <live engine | demo | fallback | cached | unknown>
Result: <concise conclusion>
Risks/blockers: <anything that prevents operational confidence>
Next handoff: <research, service deployment, UI fix, or live confirmation>
```
