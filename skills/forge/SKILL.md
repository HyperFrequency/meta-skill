---
name: forge
description: Single entry point to every MCP server federated through the neuro-harness ContextForge gateway. Use when the user types `/forge <server>.<tool> [args]`, asks to invoke a specific MCP tool, wants to chain calls across MCPs, or asks "what tools are available". Wraps mcp2cli so any server's full tool set is reachable as a flat CLI surface without paying per-turn token cost for tool schemas. Use this whenever the user references a federated MCP server (turbovault, gitnexus, infranodus, uv-mcp, tree-sitter, context7) and wants its tools called from a script, workflow, or one-off command — even if they don't explicitly say "mcp" or "forge".
---

# /forge

The unified CLI surface over every MCP server in the `neuro-harness` ContextForge stack.

## Why this exists

We have 6 MCP servers federated through ContextForge: `gitnexus`, `uv-mcp`, `tree-sitter` (with Pine grammar), `turbovault`, `infranodus`, `context7`. Each ships dozens of tools — turbovault alone has 47. Letting an agent see every tool schema on every turn wastes tokens. Instead: use `mcp2cli` to lazily dispatch to any tool, surface only the ones called.

This skill is the "router" — it knows the registry and the SSE endpoints; per-server skills (`/turbovault`, `/gitnexus`, …) delegate to it.

## Server registry

| Server | SSE endpoint (compose network) | SSE endpoint (host)               |
|---|---|---|
| `contextforge` | n/a (this IS the gateway) | `http://localhost:4444/sse` |
| `gitnexus`     | `http://gitnexus:9001/sse` | (not exposed on host)              |
| `uv-mcp`       | `http://uv-mcp:9002/sse`   | (not exposed on host)              |
| `tree-sitter`  | `http://tree-sitter:9003/sse` | (not exposed on host)              |
| `turbovault`   | `http://turbovault:9004/sse` | (not exposed on host)              |
| `infranodus`   | `http://infranodus-mcp:9005/sse` | (not exposed on host)              |
| `context7`     | `https://mcp.context7.com/mcp` | same                               |

Canonical registry source: `$HOME/neuro-harness/config/contextforge/virtual-server.yaml`. If this table drifts from that file, prefer the file.

## How to invoke

**Inside the app container** (recommended — service-name DNS works):
```bash
docker compose exec -T app uvx mcp2cli --mcp http://<server>:<port>/sse <tool> [args]
```

**From the host** (only the gateway is reachable):
```bash
uvx mcp2cli --mcp http://localhost:4444/sse <tool> [args]
```

The gateway routes the tool call to the right backend via the registered catalog (`virtual-server.yaml`). The auth flow is still being shaken down (see `docs/vendor-issues.md#contextforge-live-catalog-import-auth--partial`), so direct-to-bridge URLs from inside the network are the most reliable today.

## Slash-command shape

The user typically invokes this via the per-server slash skills:

- `/turbovault <tool> <args>` → routes here with `server=turbovault`
- `/gitnexus <tool> <args>` → routes here with `server=gitnexus`
- `/infranodus <tool> <args>` → routes here with `server=infranodus`
- `/uv-mcp <tool> <args>` → routes here with `server=uv-mcp`
- `/tree-sitter <tool> <args>` → routes here with `server=tree-sitter`

A direct `/forge <server>.<tool> [args]` form is supported too — useful when chaining across servers in one workflow.

## Operating procedure

When a user invokes this (directly or through a per-server skill):

1. **Resolve the server URL** from the registry table above (the in-network URL if you're going to exec inside the app container; the host URL otherwise).
2. **List tools first if you don't know the name.** `uvx mcp2cli --mcp <url> --list` (or whatever the current mcp2cli list flag is — check `mcp2cli --help`). Cache the listing in your reply so the user sees what's available.
3. **Dispatch the tool.** Pass `--args 'key=value …'` per mcp2cli's docs.
4. **Surface only the result.** Don't echo the tool schema unless asked — the whole point is to keep schemas out of the conversation.
5. **For composite workflows**, the workflow skill (e.g., `/scrape-ingest-organize`) owns the multi-step orchestration — invoke `/forge` once per step.

## Error handling

- **Tool unknown:** print the tool list from `mcp2cli --list` for that server and ask.
- **Server unreachable:** check `docker compose ps`; if the service is down, surface `make up` as the fix.
- **Auth-gated 401 on the gateway:** fall back to the in-network direct-to-bridge URL.
- **Tool returns an error payload:** surface verbatim; don't paraphrase.

## How this composes

Read `references/mcp2cli-patterns.md` for canonical workflow shapes (parallel-scrape → ingest → organize → ontology-build, etc.). Read `references/server-registry.md` for the per-server tool catalog with examples.

## Companion skills

- `/turbovault`, `/gitnexus`, `/infranodus`, `/uv-mcp`, `/tree-sitter` — per-server shortcuts
- `/scrape-ingest-organize` — the canonical multi-MCP workflow (parallel-scrape → vault-ingest → turbovault-organize → infranodus-ontology)
- `mcp2cli` (the upstream skill, already installed) — the underlying CLI; this skill is a thin opinionated layer on top

## When NOT to use this

- One-off bash scripting that doesn't need an LLM at all — just run `uvx mcp2cli` directly.
- The user wants the GitNexus *native* Claude skills (refactoring, debugging, exploring, etc.) that ship in `vendor/gitnexus/.claude/skills/gitnexus/*` — those are richer wrappers and are already symlinked into `~/.claude/skills/gitnexus-*`. Prefer them when the request is GitNexus-specific.
