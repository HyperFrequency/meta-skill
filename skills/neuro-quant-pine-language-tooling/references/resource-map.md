# Pine Language Tooling Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `pinelsp` | pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` | missing |
| `pine-script` | Pine Script | `deep-tool-wiki/pine-script` | `deep-tool-wiki/pine-script/wiki.md` | `neuro-link/02-KB-main/pine-script/index.md` | existing-full |
| `openalgo-pinets` | openalgo-pinets | `toolbox/openalgo-pinets` | `deep-tool-wiki/openalgo-pinets/wiki.md` | `neuro-link/02-KB-main/openalgo-pinets/index.md` | missing |
| `vectorbtpro` | vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` | existing-full |
| `nautilus-trader` | Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` | existing-full |

## Family Entry Points

| Component | Role | Primary local paths | Verification |
| --- | --- | --- | --- |
| `pinelsp` | Pine Script v6 LSP, CLI validator, parser, language service, MCP, VSCode extension | `pinelsp/package.json`, `pinelsp/packages/` | `pnpm run build:tsc`, `pnpm test`, CLI/LSP smoke |
| `pine-script` wiki | Canonical Pine v6 docs and pitfall corpus | `deep-tool-wiki/pine-script/wiki.md`, `deep-tool-wiki/pine-script/assets/` | coverage matrix, generated reference diff |
| `openalgo-pinets` | OpenAlgo + PineTS chart app and indicator conversion example | `toolbox/openalgo-pinets/README.md`, `app.py`, `data_fetcher.py`, `static/js/` | Flask route smoke, indicator JS test, OpenAlgo API mock/host smoke |

## pinelsp Package Map

| Path | Purpose | Skill notes |
| --- | --- | --- |
| `pinelsp/packages/core/` | Core validation and semantic tests | First stop for diagnostics and Pine semantic behavior. |
| `pinelsp/packages/parser-ts/` | TypeScript parser surface | Use for syntax recovery and AST-specific bugs. |
| `pinelsp/packages/language-service/` | Completion/hover/validation API | Bridge between core and host adapters. |
| `pinelsp/packages/lsp/` | LSP server, document handlers, converters, capabilities | Use for editor protocol bugs and range/URI conversion issues. |
| `pinelsp/packages/cli/` | `pine-validate` command | Use for local validation workflows and regression smoke tests. |
| `pinelsp/packages/mcp/` | Pine MCP server | Use for agent-facing Pine tooling. |
| `pinelsp/packages/pipeline/` | TradingView reference scrape/generate scripts | Treat as generated-data pipeline; ask before crawling. |
| `pinelsp/packages/tree-sitter-pine/` | Tree-sitter grammar | Use for syntax-highlighting or external parser integration. |
| `pinelsp/packages/vscode/` | VSCode extension host | Use for activation and command wiring. |

## Command Surface

From `pinelsp/package.json`:

- `pnpm run build`: full extension build.
- `pnpm run build:tsc`: TypeScript compile plus data copy.
- `pnpm test`: TypeScript build plus Vitest.
- `pnpm run lint` / `pnpm run check`: Biome checks.
- `pnpm run crawl`, `scrape`, `generate`, `generate:markdown`, `generate:tests`, `generate:syntax`: generated reference-data workflows.
- `pnpm run lsp:start`: starts `pine-lsp` over stdio.
- `pnpm run mcp:start`: starts Pine MCP server.

## PineTS / OpenAlgo Map

| Path | Purpose |
| --- | --- |
| `toolbox/openalgo-pinets/app.py` | Flask application and API route host. |
| `toolbox/openalgo-pinets/data_fetcher.py` | OpenAlgo market-data adapter. |
| `toolbox/openalgo-pinets/static/js/openalgo-provider.js` | Browser-side data provider. |
| `toolbox/openalgo-pinets/static/js/williams-vix-fix-indicator.js` | Example converted indicator module. |
| `toolbox/openalgo-pinets/static/lib/lightweight-charts-5.0.8.js` | Local charting dependency. |
| `toolbox/openalgo-pinets/.env.sample` | Required OpenAlgo/Flask configuration keys. |

## Pine v6 Reference Anchors

- `deep-tool-wiki/pine-script/wiki.md`: conceptual model, v6 differences, types, execution lifecycle.
- `deep-tool-wiki/pine-script/assets/refgraph-builtins.mmd`: built-in function relationship graph.
- `deep-tool-wiki/pine-script/assets/refgraph-strategy.mmd`: strategy API relationship graph.
- `neuro-link/02-KB-main/pine-script/`: vault-side navigable Pine wiki slices and pitfalls.

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.
