# Server registry (neuro-harness MCP federation)

The canonical source is `config/contextforge/virtual-server.yaml` in the
neuro-harness repo. This file mirrors it with per-tool notes useful when an
agent is calling tools without seeing the full schema.

## gitnexus  (`http://gitnexus:9001/sse`)

Code-graph MCP. Indexes a repo into a knowledge graph and exposes graph
queries (call-graph, dependency-graph, impact analysis).

Common tools:
- `index_repo` — index a checkout into the graph
- `query` — run a Cypher-style query against the indexed graph
- `impact` — what does this file/function reach?
- `callers`, `callees` — backward / forward edges
- `clusters` — community detection across the symbol graph

Note: native Claude skills shipped by GitNexus are at
`~/.claude/skills/gitnexus-{cli,debugging,exploring,guide,impact-analysis,pr-review,refactoring}/`
— prefer them for GitNexus-specific workflows. This SSE bridge exists for
cross-MCP chaining via `/forge`.

## uv-mcp  (`http://uv-mcp:9002/sse`)

uv workspace + venv inspection. Useful when an agent needs to query the
current workspace state without shelling out.

Common tools:
- `list_workspace_members`
- `list_dependencies`
- `lockfile_status`
- `env_state`

## tree-sitter  (`http://tree-sitter:9003/sse`)

AST + symbol-table MCP. **Pine grammar is loaded at runtime** (monkey-patch
in `docker/tree-sitter-mcp-with-pine.py`); pass `language=pine` to parse
PineScript v5.

Common tools:
- `parse` — file path + language → AST sexp
- `symbols` — extract function/class/var defs
- `query` — tree-sitter query language against the AST
- `list_languages` — available grammars

## turbovault  (`http://turbovault:9004/sse`)

Rust MCP server (47 tools) over the user's Obsidian vault. The vault is
bind-mounted at `/var/obsidian-vault` inside the container, which is
`~/Vaults/neuro-quant-vault` on the host.

Common tools (subset — full list via `mcp2cli --list`):
- `list_notes`, `read_note`, `write_note`, `delete_note`
- `search` — full-text + frontmatter search
- `link_graph` — wikilink graph
- `tag_list`, `tag_filter`
- `frontmatter_get`, `frontmatter_set`
- `backlinks` — what links here
- `daily_note_create`, `daily_note_today`
- `vault_stats`

## infranodus  (`http://infranodus-mcp:9005/sse`)

Knowledge graph + text network analysis. **Local OSS engine** — no calls
hit `infranodus.com`. Some AI-dependent tools (research-ideas, ai-summary)
degrade gracefully because the OSS engine is older than the SaaS API.

Tools per `https://github.com/infranodus/mcp-server-infranodus`:
- `generate_knowledge_graph`
- `analyze_existing_graph_by_name`
- `analyze_text`
- `generate_content_gaps`
- `generate_topical_clusters`
- `generate_contextual_hint`
- `generate_research_questions`  (may degrade on OSS engine)
- `generate_research_ideas`      (may degrade on OSS engine)
- `optimize_text_structure`

## context7  (`https://mcp.context7.com/mcp`)

Remote MCP for current library docs. Streamable-HTTP transport. Not local —
this one DOES call out. Used for "what's the current API for X?" lookups.

Common tools:
- `resolve-library-id`
- `query-docs`

## contextforge gateway  (`http://localhost:4444/sse`)

The federation layer itself. Future: a single SSE endpoint that routes any
tool call to the right backend based on the registered catalog. Today the
gateway requires auth on `/servers/`, so direct-to-bridge URLs are more
reliable; the gateway IS exposed on host:4444 for browsers + observability.
