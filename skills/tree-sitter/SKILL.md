---
name: tree-sitter
description: Parse + query source code (including PineScript v5) via the tree-sitter MCP server at `http://tree-sitter:9003/sse`. Use when the user types `/tree-sitter <tool> [args]`, asks for an AST, wants to extract symbols, run a tree-sitter query against source, or specifically wants PineScript parsing (the Pine grammar is loaded at runtime via a monkey-patch — neuro-harness is the only stack where Pine works through this MCP). Trigger on phrases like "parse this Pine script", "show me the AST of", "what symbols are in", "find all function calls in", "tree-sitter query for", or any request that requires language-aware syntactic analysis.
---

# /tree-sitter

Shortcut to the tree-sitter MCP server. **Pine grammar is loaded at runtime** via `docker/tree-sitter-mcp-with-pine.py` — pass `language=pine` to parse PineScript v5.

## How it works

```bash
docker compose exec -T app uvx mcp2cli --mcp http://tree-sitter:9003/sse <tool> --args '<k=v>...'
```

Tool list:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://tree-sitter:9003/sse --list
```

## Examples

- `/tree-sitter list_languages` — confirms `pine` is available
- `/tree-sitter parse path=strategies/breakout.pine language=pine` — Pine AST
- `/tree-sitter parse path=src/cli.py language=python` — Python AST
- `/tree-sitter symbols path=src/cli.py language=python kind=function` — function defs
- `/tree-sitter query path=strategies/breakout.pine language=pine query="(call_expression function: (identifier) @name)"` — tree-sitter query language

## When NOT to use

- For *executing* code: use Bash. tree-sitter is parse-only.
- For *whole-repo* symbol queries: `/gitnexus` (it builds a richer graph across files).

## Companions

- `/forge`, `/gitnexus`, `gitnexus-exploring`, `gitnexus-impact-analysis` — pair when analysing code at multiple resolutions.
