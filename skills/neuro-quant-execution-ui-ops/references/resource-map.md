# Execution UI Ops Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `nautilus-admin` | nautilus_admin | `toolbox/nautilus_admin` | `deep-tool-wiki/nautilus-admin/wiki.md` | `neuro-link/02-KB-main/nautilus-admin/index.md` | existing-deep-missing-kb |
| `nautilus-web-ui` | Nautilus-Web-UI | `toolbox/Nautilus-Web-UI` | `deep-tool-wiki/nautilus-web-ui/wiki.md` | `neuro-link/02-KB-main/nautilus-web-ui/index.md` | missing |
| `nautilus-prediction` | nautilus_prediction | `toolbox/nautilus_prediction` | `deep-tool-wiki/nautilus-prediction/wiki.md` | `neuro-link/02-KB-main/nautilus-prediction/index.md` | missing |
| `nautilus-trader` | Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` | existing-full |

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Tool Coverage Detail

Context7 and Auggie were requested through the `docs-dual-lookup` workflow, but their MCP tools were not available in the drafting session, so exact API examples should be rechecked before relying on them.

| Tool | Role in this family | Primary local source | Public source checked | Notes |
|---|---|---|---|---|
| `nautilus_trader` | Event-driven backtesting, live execution semantics, catalog-backed data replay, Rust/Python engine boundary (ops view) | `deep-tool-wiki/nautilus-trader/wiki.md`, `toolbox/docs/tools/nautilus-trader.md`, `toolbox/nautilus_trader/README.md` | `https://nautilustrader.io/docs/latest/getting_started/`, `.../concepts/data/`, `.../concepts/rust/` | Current docs distinguish high-level node APIs, low-level engines, and active Rust/PyO3 development. |
| `nautilus_admin` | Admin control plane: components, feature flags, databases, RBAC, audit logs, operational controls | `deep-tool-wiki/nautilus-admin/wiki.md`, `toolbox/nautilus_admin/README.md` | No stronger public source found beyond repo-local/admin README | Treat bridge/live-attachment claims as requiring runtime verification. |
| `Nautilus-Web-UI` | Trader-facing FastAPI/React UI: strategies, orders, positions, risk, market data, alerts, backtests, WebSocket updates | `toolbox/Nautilus-Web-UI/README.md`, `toolbox/services/dockerfiles/nautilus-web-ui-frontend.Dockerfile` | Repo-local source only | README states Binance public API fallback, SQLite alerts, optional API key auth, and Cloudflare Pages frontend readiness. Verify at runtime. |
| `nautilus_prediction` | Prediction-market backtesting on Kalshi/Polymarket, PMXT relay/mirror workflows, multi-market plotting and execution modeling | `toolbox/nautilus_prediction/README.md`, `toolbox/nautilus_prediction/AGENTS.md` | Project docs linked from local README: `https://evan-kolberg.github.io/prediction-market-backtesting/` | Active development; treat vendor, relay, and cache status as time-sensitive. |

## Skill Family Edges

- From `market-research-runtime`: consume validated signals and explicit execution assumptions.
- To deployment skills: hand off only after local health, auth mode, and service topology are known.
- To data-feed skills: request catalog, PMXT, relay, or venue data verification before claiming operational readiness.
- To review/eval skills: ask for hostile review before promoting any live-control workflow.

## Promotion / Recheck Checklist

- Re-run Context7 and Auggie for `nautilus_trader` exact API signatures and version-specific Rust/PyO3 notes.
- Add safe command examples only after a local demo stack has been run and all state-changing endpoints are labeled.
- Add browser verification steps for each UI route once the wider skillset defines a standard local-port policy.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.
