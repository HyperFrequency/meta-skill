---
name: infranodus
version: 0.1.0
description: >
  Text network analysis, knowledge graphs, content gap detection, SEO/GEO optimization,
  structured memory, and text comparison via the InfraNodus MCP server driven from the CLI (mcporter).
  Use when asked to: analyze text structure, generate knowledge graphs, find content gaps,
  generate research questions or ideas, compare texts, optimize text/content for SEO,
  analyze Google search results/queries, retrieve from a knowledge base (GraphRAG),
  save/retrieve structured memories, develop latent topics, or bridge conceptual gaps.
  Supports plain text, URLs (including YouTube video transcription), and existing InfraNodus graphs.
  Defaults to the LOCAL OSS engine (no per-request fees); the hosted infranodus.com SaaS is
  opt-in only and bills per request. When not to use: for the MCP-router (/forge or /infranodus
  slash-command) path use the sibling "infranodus" skill instead — this skill is the mcporter CLI variant.
homepage: https://infranodus.com
metadata:
  {
    "openclaw":
      {
        "emoji": "🕸️",
        "requires": { "bins": ["mcporter"] },
        "primaryEnv": "INFRANODUS_API_KEY",
        "install":
          [
            {
              "id": "mcporter",
              "kind": "node",
              "package": "mcporter",
              "bins": ["mcporter"],
              "label": "Install mcporter (node)",
            },
          ],
      },
  }
---

# InfraNodus

Text network analysis and knowledge graph tools via the InfraNodus MCP server.

## Setup & Auth

> **Default to the LOCAL engine. Never default to `infranodus.com`.** The hosted SaaS
> bills the user per request; the local OSS engine is free and is what the rest of the
> neuro-harness stack pins to (`INFRANODUS_API_BASE=http://infranodus:3000/api/v1`). Only
> use the hosted endpoint when the user *explicitly* asks for it.

### Default: local OSS engine (no API key, no fees)

The local MCP server is exposed at `http://infranodus-mcp:9005/sse` inside the compose
stack (or `http://localhost:9005/sse` from the host). Point mcporter at it — no auth header:

```bash
mcporter config add infranodus \
  --url http://localhost:9005/sse \
  --transport sse \
  --scope home
```

No `INFRANODUS_API_KEY` is needed for the local engine. The engine UI lives at
`http://localhost:3030` (sign-up/admin handled by the sibling `infranodus` skill's compose
stack). AI-dependent tools (e.g. `generate_research_ideas`) degrade gracefully because the
OSS engine is older than the SaaS.

### Opt-in only: hosted SaaS (`mcp.infranodus.com`, bills per request)

Use **only** when the user explicitly requests the hosted service. Requires an InfraNodus
account at https://infranodus.com and an API key.

Set `INFRANODUS_API_KEY` (Bearer token) via env var (`export INFRANODUS_API_KEY=...`) or
OpenClaw config (`~/.openclaw/openclaw.json`, which maps `skills.entries.infranodus.apiKey`
→ the env var). Then add the server:

```bash
mcporter config add infranodus \
  --url https://mcp.infranodus.com/ \
  --transport http \
  --header "accept=application/json, text/event-stream" \
  --header "Authorization=Bearer $INFRANODUS_API_KEY" \
  --scope home
```

OAuth alternative (interactive browser login): add with `--auth oauth` (omit the
Authorization header), then `mcporter auth infranodus`; re-auth with
`mcporter auth infranodus --reset`.

### Preflight & verify

1. `mcporter list infranodus` — server must show as healthy
2. For the hosted SaaS only: `test -n "$INFRANODUS_API_KEY"`, or OAuth tokens must be cached
3. If auth fails: re-run `mcporter auth infranodus` or check your API key

## Calling Tools

```bash
mcporter call infranodus.<tool_name> key=value
# or with JSON args:
mcporter call infranodus.<tool_name> --args '{"text": "...", "includeGraph": true}'
```

All analysis tools accept either `text` (plain text) or `url` (web page / YouTube video URL). Many also accept an existing InfraNodus graph via `graphName`.

## Tool Catalog

### Analysis & Knowledge Graph Tools

| Tool | Purpose |
|------|---------|
| `generate_knowledge_graph` | Full graph analysis: clusters, gaps, concepts, relations, diversity stats. Set `includeGraph: true` for full structure. |
| `create_knowledge_graph` | Same as above but **saves** the graph to InfraNodus. Requires `graphName`. |
| `analyze_text` | General text analysis with clusters, gaps, concepts, and statements. Focus on analysis results rather than graph structure. |
| `analyze_existing_graph_by_name` | Analyze an already-saved InfraNodus graph by name. |
| `generate_topical_clusters` | Compact extraction of main topical clusters only. |
| `generate_content_gaps` | Identify underdeveloped areas between topical clusters. |
| `generate_contextual_hint` | Structural summary for LLM context (useful for GraphRAG augmentation). |

### Ideation & Development Tools

| Tool | Purpose |
|------|---------|
| `generate_research_questions` | Generate research questions bridging content gaps. Use `useSeveralGaps: true` for diversity. |
| `generate_research_ideas` | Generate ideas to develop the text. Use `shouldTranscend: true` to connect to wider discourse. |
| `develop_text_tool` | Combined pipeline: content gap ideas + latent topic ideas + conceptual bridges. Use `transcendDiscourse: true` for outside-the-box thinking. |
| `develop_latent_topics` | Find underdeveloped topics and generate ideas to develop them. `requestMode: "transcend"` for wider context. |
| `develop_conceptual_bridges` | Find high-influence bridging concepts and generate ideas linking discourse to other contexts. |
| `optimize_text_structure` | Analyze bias/coherence and suggest improvements. `responseType: "transcend"` for broader perspective. |

### Memory Tools (Knowledge Graph Memory)

| Tool | Purpose |
|------|---------|
| `memory_add_relations` | Save structured memories as knowledge graphs with `[[wikilink]]` entities. Use `modifyAnalyzedText: "extractEntitiesOnly"` for entity-focused graphs. |
| `memory_get_relations` | Retrieve memories by entity from a graph. Pass `memoryContextName` and optional `entity` (e.g. `[[god]]`). |

### Retrieval & Search Tools

| Tool | Purpose |
|------|---------|
| `retrieve_from_knowledge_base` | GraphRAG retrieval from a saved graph. Pass `graphName`, `prompt`, and optionally `includeGraphSummary: true`. |
| `list_graphs` | List graphs in user's account. Filter by `nameContains`, `type`, etc. |
| `search` | Search all graphs for statements containing a term. Returns graph IDs. |
| `fetch` | Fetch specific statements found by `search` using the returned `id`. |

### Text Comparison Tools

| Tool | Purpose |
|------|---------|
| `generate_difference_graph_from_text` | Show what's missing in the **first** context that exists in the others. Pass `contexts` array of `{text}`, `{url}`, or `{graphName}` objects. |
| `generate_overlap_from_texts` | Find common topics across all provided contexts. |
| `merged_graph_from_texts` | Merge multiple sources into one graph for overview analysis. |

### SEO / GEO / LLMO Tools

| Tool | Purpose |
|------|---------|
| `analyze_google_search_results` | Graph of Google search results for queries. Use `includeSearchResults: true` for URLs. |
| `analyze_related_search_queries` | Analyze "people also search for" data with search volume. Set `importLanguage` and `importCountry`. |
| `search_queries_vs_search_results` | Find queries with high volume not covered by current results — content opportunities. Use `includeSearchQueries: true` for volume data. |
| `generate_seo_report` | Full SEO report combining all SEO tools. Use `contentToExtract: "header tags"` for header analysis. **Timeout: 90s+** |

## Key Patterns

**Input flexibility:** Most tools accept `text`, `url` (including YouTube), or reference an existing `graphName`.

**Comparison tools** use a `contexts` array: `[{text: "..."}, {url: "..."}, {graphName: "..."}]`

**Diversity stats** in responses indicate text focus: `biased` → too concentrated, `focused` → somewhat concentrated, `diversified` → balanced, `dispersed` → too scattered.

**Content gaps** show under-connected topic clusters — opportunities for new ideas or content.

**Conceptual gateways** are high-influence bridging nodes linking different topic clusters.

For detailed response schemas and examples, see [references/tool-examples.md](references/tool-examples.md).
