---
name: llm-wiki-find-connections
version: 0.2.0
description: 'Map hidden connections, bridge notes, hubs, clusters, and emergent cross-domain patterns AROUND ONE anchor (a single note or topic) in the user''s Obsidian/turbovault vault, using the local semantic-search index (spreading-activation graph traversal) plus optional typed-edge enrichment, then render a read-only Connection Map. Use WHEN you start from ONE note/topic and want its non-obvious neighborhood surfaced: "what connects to X", "find hidden links from this note", "map the network around this idea". Do NOT use for: whole-vault structural audits or KB profiling (llm-wiki-analyze-kb); anchorless autonomous serendipity mining on a schedule (llm-wiki-auto-discovery); contradictions / opposing-conclusion pairs (llm-wiki-detect-tensions); fusing a cluster into one note (llm-wiki-synthesize-insights); propagating an edit across neighbors (llm-wiki-propagate-change); or external web/library research. Read-only: it maps and reports, never writing notes or links.'
argument-hint: <note name or topic to start from>
allowed-tools: Read, Grep, Glob, Bash
---

# Connection Discovery & Network Analysis

Discover non-obvious relationships and emergent patterns in the vector-indexed
knowledge vault, starting from **one anchor** note or topic. This is a **read-only
map**: report findings, never create links or edit notes.

## Starting Point
$ARGUMENTS

## Semantic-search helper

All search and connection queries go through the vault's local semantic-search index.
**Spreading-activation mode is the default for connection finding** — it follows graph
edges instead of relying on vector similarity alone.

```bash
# Spreading-activation search (default for connection discovery)
resources/local-brain-search/run_search.sh "query" --mode spreading --limit 10 --json
# Static / exact-match search
resources/local-brain-search/run_search.sh "query" --limit 10 --json
# Force synthesis intent (maximum graph exploration)
resources/local-brain-search/run_search.sh "query" --mode spreading --intent synthesis --json

# Connections of a specific note, plus topology queries
resources/local-brain-search/run_connections.sh "Note Name" --json
resources/local-brain-search/run_connections.sh --hubs --json
resources/local-brain-search/run_connections.sh --bridges --json
resources/local-brain-search/run_connections.sh --stats --json
```

> **Vault layout.** These helpers assume an Obsidian/turbovault vault with a
> `resources/local-brain-search/` index. If paths differ, adjust the commands before running.

## Sibling skills — hand off when the task shifts

- `llm-wiki-detect-tensions` — surface *contradictions* between notes (opposing conclusions), not affinities
- `llm-wiki-synthesize-insights` — fuse a discovered cluster into one synthesis note
- `llm-wiki-analyze-kb` — whole-vault structural profile (all clusters/hubs), not one anchor
- `llm-wiki-auto-discovery` — anchorless, scheduled cross-domain serendipity mining
- `llm-wiki-propagate-change` — push an edit's implications across connected notes

## Analysis protocol

1. **Anchor.** For a note name, `Grep` for the matching file (`grep -r "# $ARGUMENTS" <vault> --include="*.md"`);
   for a topic, run a `--limit 5 --json` search. `Read` the anchor's full content and record its exact path.
2. **Immediate network.** Run `run_connections.sh "Note Name" --json`; pick the top 3-5
   connected notes (explicit + semantic) and `Read` them to understand the nature of each link.
3. **Deep network.** Query `--stats`, `--hubs`, and `--bridges` to map multi-hop structure,
   clusters, and bridge nodes.
4. **Cross-cluster bridges.** For notes in *different* clusters, analyze WHY they connect —
   shared abstraction, analogy, causal chain, or a meta-pattern recurring across domains.
5. **Pattern recognition.** Identify recurring themes, hub nodes, and high-value but isolated
   notes; `Grep` for existing wikilinks to spot gaps and missing links.

## Optional typed-edge enrichment

When a dependency-graph index is present, enrich the analysis with typed edges:

```bash
resources/brain-graph/run_brain_graph.sh inspect "$ARGUMENTS" --json
```

This adds edge *types* (derives-from vs references vs tension), authority direction,
lifecycle phase (reflective / crystallizing / generative), and staleness signals — richer
than a plain "related" edge.

## Output

Render findings as a **Connection Map** using the full template in
[references/output-format.md](references/output-format.md). Required sections, in order:

1. Header + AI-disclosure callout (always — transparency is mandatory)
2. 🎯 Anchor Point (note, core concept, domain)
3. 🔗 Direct Connections — Layer 1 table (note, similarity, type, why, AI confidence)
4. 🌉 Bridge Notes — cross-cluster integrators, with mechanism + significance
5. 🕸️ Network Structure — 3-layer tree (thresholds L1 > 0.75, L2 > 0.65, L3 > 0.60)
6. 💡 Emergent Patterns; 🔍 Non-Obvious Connections (flag for human validation)
7. 🎨 Conceptual Clusters; 🔭 Knowledge Gaps & Opportunities
8. 📊 Network Statistics; 🎯 Actionable Insights (⚠️ human-review callout)
9. 📝 Methodology Note (embedding model, cosine similarity, multi-hop traversal)

Always label AI-inferred content and keep both disclosure callouts.

## Quality bar

- Explain **why** notes connect, not just that they do; prefer non-obvious links to surface-level ones.
- Hunt for **meta-patterns** — themes recurring across domains — and back every claim with concrete note content.
- Think like a network scientist: topology, hubs, bridges, clusters; highlight surprising connections.
- Similarity scores ≠ conceptual validity. Label AI-generated insights and route them for critical human review.

## State dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Vault notes | `<vault>/**/*.md` | X | | Permanent notes, sources, MOCs |
| Semantic-search index | `resources/local-brain-search/` | X | | Vector index and connection graph |
| Graph statistics | `run_connections.sh --stats` | X | | Network topology data |

## Completion checklist

- [ ] Anchor identified and read
- [ ] Immediate network mapped (top 3-5 connections)
- [ ] Deep analysis done (hubs, bridges, stats)
- [ ] Cross-cluster bridges discovered and explained
- [ ] Emergent patterns identified; non-obvious connections flagged for validation
- [ ] Actionable insights + methodology transparency included
