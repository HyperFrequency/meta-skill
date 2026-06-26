---
name: neuro-harness
description: Reference + invocation guide for the unified mcp2cli gateway that fronts every MCP endpoint in the neuro-quant compose stack. Use this skill when the user types `/forge`, asks "what MCP servers do we have", needs to call a tool through the unified CLI, wants the endpoint URL for InfraNodus/TurboVault/GitNexus/tree-sitter/etc., or asks how docs-lookup / LSPs / language tooling are wired in. All MCP traffic in this environment goes through the gateway — never call upstream services directly when a gateway route exists.
allowed-tools: Read, Bash, Skill
---

# /neuro-harness

Single source of truth for the **unified mcp2cli gateway** that fronts every MCP endpoint in the neuro-quant compose stack. The gateway is reachable via the `/forge` router; mcp2cli wraps each MCP server's tools as CLI subcommands so you can call them from Bash, scripts, or other skills without having to hand-roll JSON-RPC.

## Why a unified gateway

Every MCP server in this stack is reachable two ways:

1. **Direct SSE** — `http://<server>:<port>/sse` (works, but couples each caller to each server's hostname/port and tool schema)
2. **Unified gateway** — `/forge` → mcp2cli (preferred; one auth surface, consistent CLI shape, automatic schema lookup)

When writing a skill or script that touches any MCP server, route through the gateway. Per `project_infranodus_local_only.md` and the `feedback_skill_three_way_mirror.md` discipline, the gateway is the only path that respects the local-only routing pin.

## Endpoints currently behind the gateway

| Endpoint | Purpose | Direct SSE URL | mcp2cli subcommand prefix |
| --- | --- | --- | --- |
| `infranodus-mcp` | Knowledge graph + text-network analysis (LOCAL OSS engine) | `http://infranodus-mcp:9005/sse` | `infranodus` |
| `turbovault` | Obsidian vault read/write/search/backlinks/daily-notes | `http://turbovault:9004/sse` | `turbovault` |
| `gitnexus` | Code-graph indexing + queries over a repo | `http://gitnexus:9001/sse` | `gitnexus` |
| `tree-sitter` | Language-aware AST + query (incl. PineScript v5 via monkey-patch) | `http://tree-sitter:9003/sse` | `tree-sitter` |
| `parallel-web` | Web search + extract via Parallel Chat API | n/a (HTTP) | `parallel-web` |
| `context7` | Up-to-date library docs (Upstash) | n/a (HTTP) | `context7` |
| `augment-code-search` | Repo-scoped semantic code search (Auggie) | n/a (HTTP) | `auggie augment-code-search` |
| `perplexity-search` | Web search via Perplexity Sonar | n/a (HTTP via LiteLLM/OpenRouter) | `perplexity` |
| `neuro-link-recursive` | Vault RAG (qmd + Qdrant) for HyperFrequency-forked tools | local | `nlr_rag_query` / `nlr_rag_query_verified` |

For anything not in the table, check `$HOME/.config/mcp2cli/` and `$HOME/.claude/settings.json` `mcpServers` block before assuming a route doesn't exist.

## How to invoke

### From a slash command

```text
/forge infranodus generate_knowledge_graph "..."
/forge gitnexus what_calls --symbol foo --path src/
/forge tree-sitter parse --file strategy.py --query 'function_definition'
```

### From Bash (inside a skill)

```bash
mcp2cli infranodus generate_knowledge_graph --text "$INPUT"
mcp2cli tree-sitter query --file "$FILE" --query "$QUERY"
auggie augment-code-search --repo-owner nautechsystems --repo-name nautilus_trader \
  --branch develop --query "Strategy trait DataActor on_start"
```

### From another skill (Skill tool)

Some skills (e.g. `docs-dual-lookup`, `tree-sitter`, `infranodus-cli`, `gitnexus*`) already wrap the gateway. Prefer invoking those over hand-rolling Bash when a skill exists for the workflow.

## Discovery

To find tools available on a given endpoint:

```bash
mcp2cli <prefix> --help            # list tools
mcp2cli <prefix> <tool> --help     # tool-specific args
```

If you don't remember the prefix:

```bash
mcp2cli --help                     # lists all configured servers
```

## The contract (for other skills referencing this gateway)

Any skill that needs documentation lookup, language-server features, AST parsing, knowledge-graph queries, vault search, or code-graph queries **must** route through the gateway. Concretely:

- **Documentation lookup** → `docs-dual-lookup` skill (Context7 + Auggie in parallel) or directly `mcp2cli context7 query-docs` / `auggie augment-code-search`
- **LSP / language tooling** → `mcp2cli tree-sitter` for AST queries (the closest LSP-shaped tool in the stack — true LSP integration is via the IDE, not the gateway)
- **Tree-sitter** → `mcp2cli tree-sitter parse|query` or the `tree-sitter` skill
- **Knowledge graph** → `mcp2cli infranodus ...` or the `infranodus` skill
- **Vault** → `mcp2cli turbovault ...` or the `turbovault` skill
- **Code graph** → `mcp2cli gitnexus ...` or one of the `gitnexus-*` workflow skills

If a skill needs one of these and is hard-coding a direct SSE URL, fix it — that's a contract violation. Direct SSE is allowed only as a debug/diagnostic fallback.

## Verifying the gateway is healthy

```bash
# Quick liveness check (any one of these should return data, not 404)
for svc in infranodus-mcp:9005 turbovault:9004 gitnexus:9001 tree-sitter:9003; do
  printf "%-30s " "$svc"
  curl -sS --max-time 2 "http://$svc/sse" | head -1
  echo
done
mcp2cli --help | head -20
```

If any endpoint is unreachable, surface that to the user before falling back to direct calls. Do not silently bypass the gateway.

## Related skills

- `mcp2cli` — the wrapper itself (general invocation guide)
- `forge` — the slash-command router
- `docs-dual-lookup` — Context7 + Auggie in parallel
- `infranodus` / `infranodus-cli` — knowledge-graph workflows
- `gitnexus` and `gitnexus-*` — code-graph workflows
- `tree-sitter` — AST queries
- `turbovault` — Obsidian vault operations (referenced; skill not currently in this repo)
