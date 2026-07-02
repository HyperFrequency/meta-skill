---
name: llm-wiki-analyze-kb
version: 0.2.0
description: "Profile the WHOLE-VAULT structure of the user's Obsidian/turbovault knowledge base — graph statistics, thematic clusters, hub notes, bridge notes, layer/lifecycle distribution — via Local Brain Search, then (re)generate a single condensed knowledge-base-analysis.md report. Use WHEN the user asks to analyze, profile, map, audit, or summarize the vault as a whole, refresh the KB analysis report, or surface which notes are hubs/bridges and what the major clusters are. Do NOT use for connection discovery from ONE note/topic (use llm-wiki-find-connections), triaging recently added notes (use llm-wiki-integrate-recent-notes), mining hidden cross-domain links (use llm-wiki-auto-discovery), finding contradictions (use llm-wiki-detect-tensions), merging notes into a narrative (use llm-wiki-synthesize-insights), semantic search of a single topic (use Local Brain Search directly), ingesting new sources (use scrape-ingest-organize), or analyzing codebases (use the gitnexus skills)."
automation: gated
allowed-tools: Read, Bash, Glob, Edit, Write
---

# Analyze Knowledge Base

Profile the user's Obsidian/turbovault knowledge base **as a whole** and (re)generate a
condensed, high-signal `knowledge-base-analysis.md`. This is the vault-wide structural map:
what the major clusters are, which notes are hubs and bridges, how connected the graph is,
and where the growth opportunities lie. It reads broadly and writes exactly one report.

**Scope boundary:** whole-vault structure only. Single-note or single-topic work belongs to
the sibling skills named in the frontmatter `description`.

## Tooling

All semantic search, graph statistics, and connection queries route through **Local Brain
Search** and the **brain-graph** CLI (the shared neuro-base vault toolchain). Resolve the
vault root from `$VAULT_BASE_PATH`; do not hardcode a path.

```bash
resources/local-brain-search/run_connections.sh --stats   --json   # graph statistics
resources/local-brain-search/run_connections.sh --hubs    --json   # hub notes
resources/local-brain-search/run_connections.sh --bridges --json   # bridge notes
resources/brain-graph/run_brain_graph.sh status           --json   # layer/lifecycle mix
```

If Local Brain Search reports a stale or missing index, run `/refresh-index` first, then retry.

## Procedure

1. **Graph statistics** — `run_connections.sh --stats --json` for node/edge counts, density,
   component structure.
2. **Directory topology** — `Glob` the vault to map its organizational layers, e.g.
   `**/*.md`, plus whatever folder convention the vault uses (permanent notes, MOCs/maps of
   content, sources, meta). Do not assume specific folder names — discover them.
3. **Hubs & bridges** — `run_connections.sh --hubs --json` and `--bridges --json`. Read the
   top handful of hub notes (whichever the data surfaces — never a hardcoded list) to
   characterize each major cluster.
4. **Layer/lifecycle mix** — `run_brain_graph.sh status --json` for note maturity phases.
5. **Cluster analysis** — identify the dominant thematic clusters and how they interconnect.
6. **Write the report** — `Edit`/`Write` `knowledge-base-analysis.md`. See
   [references/output-format.md](references/output-format.md) for the required sections and
   the hard length/style budget.

## State Dependencies

| Source | Location | Read | Write |
|--------|----------|:----:|:-----:|
| All vault notes | `$VAULT_BASE_PATH/**/*.md` | X | |
| Local Brain Search | `resources/local-brain-search/` | X | |
| brain-graph CLI | `resources/brain-graph/` | X | |
| Analysis report | `knowledge-base-analysis.md` | X | X |

## Completion Checklist

- [ ] Graph statistics retrieved (nodes, edges, density, components)
- [ ] Directory topology mapped via Glob (folder names discovered, not assumed)
- [ ] Hub notes and bridge notes identified from data; top hubs read
- [ ] Layer/lifecycle distribution pulled from brain-graph
- [ ] Dominant thematic clusters and their interconnections characterized
- [ ] `knowledge-base-analysis.md` written per references/output-format.md
- [ ] Report is condensed (600–800 lines max), scannable, non-duplicative
