---
name: turbovault
description: Invoke any TurboVault MCP tool against the user's Obsidian vault at ~/Vaults/neuro-quant-vault. Use when the user types `/turbovault <tool> [args]`, asks to read/write/search notes, manage wikilinks, list tags, get backlinks, find daily notes, or any vault-operation phrasing (even when they say "in my notes" or "in obsidian" without saying turbovault). Routes through `/forge` to TurboVault's SSE endpoint at `http://turbovault:9004/sse`. Trigger on phrases like "add a note about", "find notes tagged", "list daily notes", "what's linked from", "vault search for", "create a daily note", or any reference to Obsidian / .md / vault content.
---

# /turbovault

Shortcut to the TurboVault MCP server. TurboVault is a Rust MCP exposing 47 tools over the user's Obsidian vault at `~/Vaults/neuro-quant-vault` (bind-mounted at `/var/obsidian-vault` in its container).

## How it works

This skill is a thin alias over `/forge` with the server preset to `turbovault`. When the user types:

```
/turbovault <tool> [args]
```

…you invoke (from inside the app container, where service-name DNS works):

```bash
docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse <tool> --args '<key=value>...'
```

If the user doesn't name a tool, list them first:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse --list
```

See `~/.claude/skills/forge/references/server-registry.md#turbovault` for the common tool set + `references/mcp2cli-patterns.md` for chaining patterns.

## Examples

- `/turbovault list_notes` — enumerate notes in the vault
- `/turbovault search query="agentic patterns"` — full-text search
- `/turbovault write_note title="Daily 2026-05-20" body="..."` — create a note
- `/turbovault backlinks path="03-ontology-main/some-topic.md"` — find what links here
- `/turbovault tag_filter tag=research` — notes tagged `research`
- `/turbovault vault_stats` — top-level metrics

## When NOT to use

- For *editing* the vault content with deep structural rewrites: use Claude Code's regular Read / Edit / Write on the host filesystem — they're closer to the user's intent. Use `/turbovault` for *MCP-mediated* operations (search, link graph, tagging, frontmatter) that aren't a plain file edit.
- For full-repo / monorepo workflows: prefer `/gitnexus` for code-graph queries; turbovault is the *vault* layer.

## Companions

- `/forge` — the underlying router
- `/infranodus` — pair with this when you want to build a graph/ontology over vault content
- `/scrape-ingest-organize` — the canonical workflow that uses turbovault as the ingest layer
