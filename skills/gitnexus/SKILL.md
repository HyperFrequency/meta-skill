---
name: gitnexus
description: Invoke GitNexus MCP tools — code-graph indexing, dependency analysis, impact queries, callers/callees, community detection. Use when the user types `/gitnexus <tool> [args]`, asks about a codebase's structure ("what calls X", "what does X depend on", "where is Y used", "impact of changing Z"), wants to index a repo into a graph, or queries the symbol graph. Routes through `/forge` to `http://gitnexus:9001/sse`. For deeper GitNexus-specific workflows (debugging, refactoring, PR review, exploring), the native Claude skills at `~/.claude/skills/gitnexus-{cli,debugging,exploring,impact-analysis,pr-review,refactoring,guide}/` are richer — use those when the request matches their domain.
---

# /gitnexus

Shortcut to the GitNexus MCP server (`http://gitnexus:9001/sse`). GitNexus indexes a codebase into a knowledge graph and exposes graph queries.

## How it works

```bash
docker compose exec -T app uvx mcp2cli --mcp http://gitnexus:9001/sse <tool> --args '<k=v>...'
```

If unsure of the tool name:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://gitnexus:9001/sse --list
```

## Examples

- `/gitnexus index_repo path=/workspace` — index a checkout
- `/gitnexus impact path=src/foo.py:do_thing` — what does this reach?
- `/gitnexus callers symbol="process_request"` — backward edges
- `/gitnexus clusters` — community detection across the symbol graph
- `/gitnexus query cypher="MATCH (n:Function)-[:CALLS]->(m) RETURN n, m LIMIT 50"` — raw Cypher

## When to use richer GitNexus skills instead

The vendored upstream skills are *richer* wrappers — use them when the request matches their domain:

| Request shape                                | Use this skill              |
|----------------------------------------------|-----------------------------|
| "What's the call graph for X?"               | `gitnexus-exploring`        |
| "Debug why this test fails"                  | `gitnexus-debugging`        |
| "Find every caller of X before I rename it"  | `gitnexus-impact-analysis`  |
| "Review this PR"                              | `gitnexus-pr-review`        |
| "Refactor this module"                        | `gitnexus-refactoring`      |
| "Help me understand GitNexus itself"          | `gitnexus-guide`            |
| "Run a GitNexus CLI command"                  | `gitnexus-cli`              |
| Anything else (one-off MCP tool call)         | `/gitnexus` (this skill)    |

The richer skills DO go through this MCP under the hood — `/gitnexus` is the bare-CLI escape hatch.

## Companions

- `/forge` — the underlying router
- `/turbovault` — pair when correlating code structure with vault notes
- `gitnexus-*` skills (vendored from `vendor/gitnexus`) — task-specific wrappers
