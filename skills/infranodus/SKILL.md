---
name: infranodus
description: Knowledge graph + text network analysis via the LOCAL InfraNodus MCP (`http://infranodus-mcp:9005/sse`). Use when the user types `/infranodus <tool> [args]`, wants to generate a knowledge graph from text, find topical clusters, identify content gaps, propose research questions, or analyze text structure / bias / coherence. Trigger on phrases like "build an ontology from these notes", "what are the topical clusters in X", "find content gaps", "generate research questions from Y", "analyze the bias in this text", or any text-network / knowledge-graph framing. Important: runs against the local OSS engine — no calls to infranodus.com, no per-request fees. AI-dependent tools (research-ideas) degrade gracefully because the OSS engine is older than the SaaS.
---

# /infranodus

Shortcut to the InfraNodus MCP server. **Fully local** — no calls leave the compose network.

## Architecture

```
/infranodus  →  /forge router  →  http://infranodus-mcp:9005/sse  →  Node MCP server
                                                                ↓ HTTP
                                                       http://infranodus:3000  (OSS engine)
                                                                ↓ Bolt
                                                       neo4j:7687  (graph DB)
```

Everything runs in the compose stack. `INFRANODUS_API_BASE=http://infranodus:3000/api/v1` — no calls to `infranodus.com`.

## How it works

```bash
docker compose exec -T app uvx mcp2cli --mcp http://infranodus-mcp:9005/sse <tool> --args '<k=v>...'
```

If unsure of the tool name:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://infranodus-mcp:9005/sse --list
```

## Tools (per the upstream MCP server)

- `generate_knowledge_graph` — text → graph
- `analyze_existing_graph_by_name` — pull a saved graph
- `analyze_text` — text / URL / YouTube → topics + clusters + summary
- `generate_content_gaps` — what's underexplored?
- `generate_topical_clusters` — main themes + sub-themes
- `generate_contextual_hint` — high-level topical overview
- `generate_research_questions` — bridge content gaps  *(may degrade on OSS engine)*
- `generate_research_ideas` — actionable next-step ideas  *(may degrade on OSS engine)*
- `optimize_text_structure` — bias + coherence analysis

## Examples

- `/infranodus analyze_text text="..."` — graph + clusters + summary
- `/infranodus generate_topical_clusters text="..."` — themes only
- `/infranodus generate_content_gaps text="..."` — gaps
- `/infranodus optimize_text_structure text="..."` — bias + coherence

For multi-document analysis (vault-wide), pair with `/turbovault`:

1. `/turbovault list_notes --tag=research` → get note paths
2. For each, `/turbovault read_note` → bodies
3. Concatenate + `/infranodus analyze_text text=...` → vault-wide graph

That chain is exactly what `/scrape-ingest-organize` automates.

## First-time signup (one-off)

The OSS engine needs an account before its API works. On first install:

1. `docker compose up -d` (the stack)
2. Visit `http://localhost:3030/signup?invitation=<secret>` — the secret lives in the engine's `config.json` (`secrets.invitation`). Default for the t1r1rizk image is documented in `vendor/turbovault`'s README — check there or shell into the container to read `/app/config/secrets.json` if you're stuck.
3. Create a user, then update `INFRANODUS_API_KEY` in `.env` if the OSS engine requires it (it doesn't for most local-only flows; the MCP server tolerates an empty key).

## When NOT to use

- For *editing* notes: use `/turbovault` (it owns vault writes).
- For *parsing source code*: use `/tree-sitter` (Pine grammar) or `/gitnexus`.
- For "I want a quick web search": use the parallel-web / perplexity-search skills.

## Companions

- `/forge`, `/turbovault`, `/scrape-ingest-organize`, `ontology-creator`, `critical-perspective`, `infranodus-cli` — the three retained user-named InfraNodus skills.
