---
title: VectorBT Pro — AI workflows
domain: trading
last_updated: 2026-04-20
---

# VectorBT Pro AI workflows

VBT Pro ships **first-class AI integration** — an MCP server, chat
commands, and a knowledge base module. Wire these into your Claude
Code stack so the translator/author can query VBT Pro's docs + run
code against a live runtime without leaving the session.

Source: https://vectorbt.pro/pvt_16ebf9ef/#ai-workflows
Module: `vectorbtpro.mcp_server`, `vectorbtpro.mcp`,
`vectorbtpro.knowledge`

## The VBT Pro MCP server

### What it exposes

Tools registered in `vectorbtpro.mcp.tool_registry` (verified against
live dump):

| Tool | Purpose |
|---|---|
| `search` | Semantic search over the VBT Pro knowledge base |
| `find` | Find an object (class/function/module) by name |
| `get_page` | Fetch a documentation page by URL or ref |
| `get_source` | Retrieve source code for a named symbol |
| `get_attrs` | List attributes of a class/module |
| `get_message`, `get_message_block`, `get_message_thread` | Pull examples from the docs' code blocks |
| `run_code` | **Execute Python in a VBT Pro context** — returns result or error |
| `register_tool` | Plug your own tool into the registry |
| `auto_cast`, `resolve_refnames` | Utilities |

These are consumed both by the MCP server and by the CLI
(`vectorbtpro.cli`) — so the same tool surface is reachable
programmatically via MCP and interactively via `python -m vectorbtpro.cli`.

### How to start it

```bash
python -m vectorbtpro.mcp_server
```

That's it — a stdio MCP server on the process's stdin/stdout.

### How to wire it into Claude Code

Add to `~/.claude.json` (merge into `mcpServers`):

```json
{
  "mcpServers": {
    "vectorbt-pro": {
      "command": "python",
      "args": ["-m", "vectorbtpro.mcp_server"],
      "type": "stdio",
      "env": {}
    }
  }
}
```

Once registered, Claude Code exposes tools like
`mcp__vectorbt-pro__search`, `mcp__vectorbt-pro__run_code`, etc. —
callable exactly like any other MCP tool.

### Translator integration

When `/vectorbt` or `/strategy-translator` is emitting VBT Pro code,
**prefer live `mcp__vectorbt-pro__search` over static reference files**
for "is this function's signature still X?" questions. The MCP server
queries the installed version's actual API — no version drift.

Typical sequence:
1. `mcp__vectorbt-pro__search(query="Portfolio.from_signals size_type percent")` →
   returns ranked doc snippets matching the query.
2. `mcp__vectorbt-pro__get_source(name="Portfolio.from_signals")` →
   pulls the actual Python signature.
3. Emit code that matches the installed version exactly.
4. Optionally: `mcp__vectorbt-pro__run_code(code=emitted_snippet)` →
   smoke-test the emitted code in-process before returning to user.

## Chat commands (CLI-level)

VBT Pro also exposes direct chat commands — useful for non-Claude
workflows or for ad-hoc exploration:

| Command | Purpose |
|---|---|
| `python -m vectorbtpro.cli chat` | Launch interactive chat with the knowledge base + an LLM of your choice |
| `python -m vectorbtpro.cli quick_chat` | One-shot chat — prompt in, answer out |
| `python -m vectorbtpro.cli run_chat` | Run a pre-scripted chat flow |
| `python -m vectorbtpro.cli build_mcp_app` | Build a deployable MCP server package for another agent |

Source references (from `vectorbtpro/cli.py`):
- `chat_command` — `vectorbtpro/cli.py#L572-L586`
- `quick_chat_command` — `L589-L603`
- `run_chat_command` — `L475-L500`
- `build_mcp_app` — `L503-L542`

## Knowledge base

The `vectorbtpro.knowledge` subpackage holds the indexed corpus the
MCP `search` tool queries:

- `knowledge.base_asset_funcs` — `AssetFunc` class for indexable assets
- Ingested from VBT Pro's own documentation + user-provided additions
- Exposes semantic search via the MCP `search` tool

**Upstream API docs:** `https://vectorbt.pro/pvt_<current>/api/knowledge/`
— authoritative reference for every `AssetFunc` subclass, ingestion
helper, and search entrypoint. Complements `api/mcp_server/` (which
documents the tool surface) — this page documents the *corpus*.
Construct the current URL with:

```bash
printf '%s/api/knowledge/\n' "$(./scripts/get-pvt-url.sh | sed 's|/$||')"
```

Typical assets indexed:
- Every page of the VBT Pro docs (API reference, tutorials, how-tos)
- Discord message threads (curated Q&A)
- Source code (every function, class, docstring)

## When to use which

- **Interactive exploration** by a human → `quick_chat_command`
- **Agent integration** (Claude Code, other LLM clients) → MCP server
- **Batch processing** of many queries → direct `tool_registry` calls
- **Custom tools for your own agent** → `register_tool` + `build_mcp_app`

## Setup checklist (for the `/vectorbt` skill)

Before emitting a VBT Pro translation in an environment that has
`vectorbtpro` installed, verify:

```bash
# 1. Pro is installed
python -c "import vectorbtpro; print(vectorbtpro.__version__)"

# 2. MCP server module is importable
python -c "from vectorbtpro import mcp_server; print('mcp ok')"

# 3. Knowledge base is populated (run once to build local index)
python -m vectorbtpro.cli chat --help   # shows chat flags, confirms CLI works

# 4. ~/.claude.json has the MCP entry
jq '.mcpServers["vectorbt-pro"]' ~/.claude.json
```

If any step fails, document in the translation's Diff vs spec section
that the live MCP wasn't available and you fell back to Context7.

## Getting the current pvt URL (hash rotation)

VBT Pro's `pvt_<hash>` rotates. Polakow maintains a stable pointer
branch `pvt-links` on the private `polakowo/vectorbt.pro` repo whose
`README.md` is a one-line file:

```
:sparkles: https://vectorbt.pro/pvt_<current-hash> :sparkles:
```

The `/vectorbt` skill ships `scripts/get-pvt-url.sh` to fetch the
current URL via GitHub API (GAT-authenticated):

```bash
./scripts/get-pvt-url.sh              # https://vectorbt.pro/pvt_<hash>/
./scripts/get-pvt-url.sh --llms       # https://vectorbt.pro/pvt_<hash>/llms-full.txt
./scripts/get-pvt-url.sh --api        # https://vectorbt.pro/pvt_<hash>/api/
```

Use this when you need to re-fetch the llms-full dump or link to the
live docs. Don't hardcode a hash; read it from the branch every time.

## Source

- Live dump: `~/Dev/neuro-link/01-raw/vectorbt-pro/llms-full.txt`
  (18MB, fetched from `pvt_16ebf9ef` on 2026-04-20, lines 7305-8050
  cover `mcp_server` + `mcp` modules in detail)
- Stable pointer for the current pvt URL:
  `https://github.com/polakowo/vectorbt.pro/blob/pvt-links/README.md`
  (requires GAT with private-repo access — your VBT Pro purchase grants this)
- Upstream API pages (hash-rotating — construct via `get-pvt-url.sh`):
  - `https://vectorbt.pro/pvt_<current>/api/mcp_server/` — MCP tool surface
  - `https://vectorbt.pro/pvt_<current>/api/mcp/` — `tool_registry` internals
  - `https://vectorbt.pro/pvt_<current>/api/knowledge/` — ingested corpus / `AssetFunc` classes
- Source refs: `vectorbtpro/mcp.py`, `vectorbtpro/mcp_server.py`,
  `vectorbtpro/cli.py`, `vectorbtpro/knowledge/`
