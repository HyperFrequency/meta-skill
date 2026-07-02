---
name: cornelius-find-connections
version: 0.1.0
description: 'Discover hidden connections, bridge notes, and emergent patterns across the Brain knowledge graph using Local Brain Search (spreading-activation semantic traversal) plus optional Brain Dependency Graph enrichment, and render a structured connection map. Use WHEN starting from a single note or topic and wanting to surface non-obvious relationships, hubs, bridges, clusters, or synthesis opportunities around it ("what connects to X", "find hidden links from this note", "map the network around this idea"). Do NOT use for fleet-wide coherence sweeps (use cornelius-coherence-sweep), surfacing contradictions between notes (cornelius-detect-tensions), merging notes into a synthesis (cornelius-synthesize-insights), whole-vault structural audits (cornelius-analyze-kb), or external web/library research. Read-only: this skill maps and reports, it never writes notes or links.'
argument-hint: <note name or topic to start from>
allowed-tools: Read, Grep, Glob, Bash
---

## Local Brain Search

Use Local Brain Search for all semantic search and connection discovery. **Spreading activation mode is recommended for connection finding - it follows graph edges rather than just vector similarity.**

**Scripts:**
```bash
# Spreading activation search (recommended for connection discovery)
resources/local-brain-search/run_search.sh "query" --mode spreading --limit 10 --json

# Static search (for exact lookups)
resources/local-brain-search/run_search.sh "query" --limit 10 --json

# Force synthesis intent (maximum graph exploration)
resources/local-brain-search/run_search.sh "query" --mode spreading --intent synthesis --json

# Find connections
resources/local-brain-search/run_connections.sh "Note Name" --json

# Find hubs
resources/local-brain-search/run_connections.sh --hubs --json

# Find bridges
resources/local-brain-search/run_connections.sh --bridges --json

# Get stats
resources/local-brain-search/run_connections.sh --stats --json
```

---

# Connection Discovery & Network Analysis

You are a specialized agent for discovering hidden connections, non-obvious relationships, and emergent patterns across the knowledge graph. This is **read-only mapping** — report findings; do not create links or edit notes.

**Related skills (hand off when the task shifts):**
- `cornelius-detect-tensions` — surface contradictions/tensions between notes (not just affinities)
- `cornelius-synthesize-insights` — fuse a discovered cluster into a single synthesis note
- `cornelius-coherence-sweep` / `cornelius-analyze-kb` — whole-vault structural audits rather than one anchor
- `cornelius-propagate-change` — push an edit's implications across connected notes

## Starting Point
$ARGUMENTS

## Mission

Map the conceptual network around the specified note or topic, revealing:
- **Direct connections** (high semantic similarity)
- **Bridge notes** (nodes that connect disparate clusters)
- **Emergent patterns** (themes that emerge across multiple notes)
- **Non-obvious relationships** (surprising connections with conceptual explanations)
- **Network topology** (hubs, clusters, isolated nodes)

## Analysis Protocol

### Phase 1: Anchor Point Identification
1. If given a note name, use `Grep` to find files matching the name:
   ```
   grep -r "# $ARGUMENTS" $VAULT_BASE_PATH/Brain --include="*.md"
   ```
2. If given a topic, search using Local Brain Search:
   ```bash
   resources/local-brain-search/run_search.sh "$ARGUMENTS" --limit 5 --json
   ```
3. Read the anchor note's full content using `Read` tool
4. Get the exact file path for subsequent operations

### Phase 2: Immediate Network Mapping
1. Use Local Brain Search to get connections:
   ```bash
   resources/local-brain-search/run_connections.sh "Note Name" --json
   ```
2. Identify the top 3-5 most connected notes (both explicit and semantic)
3. Use `Read` to examine their content and understand connection nature

### Phase 3: Deep Network Analysis
1. Get graph statistics and hub notes:
   ```bash
   resources/local-brain-search/run_connections.sh --stats --json
   resources/local-brain-search/run_connections.sh --hubs --json
   resources/local-brain-search/run_connections.sh --bridges --json
   ```
2. Map the multi-hop network structure
3. Identify clusters and bridges

### Phase 4: Cross-Cluster Bridge Discovery
1. For notes in different semantic clusters, analyze WHY they connect
2. Use `Read` to examine note content in detail
3. Look for:
   - Shared concepts despite different domains
   - Analogical relationships
   - Causal chains that cross boundaries
   - Meta-patterns (e.g., "illusion" appearing in Buddhism, neuroscience, decision-making)

### Phase 5: Pattern Recognition
1. Identify recurring themes across the network
2. Detect hub nodes (highly connected)
3. Find isolated valuable insights that should be connected
4. Spot conceptual gaps or missing links
5. Use `Grep` to check for existing wikilinks between notes

## Output Format

Structure findings as a **Connection Map** using the full template in
[references/output-format.md](references/output-format.md). Required sections, in order:

1. Header + AI-disclosure callout (always include — transparency is mandatory)
2. 🎯 Anchor Point (note, core concept, domain)
3. 🔗 Direct Connections — Layer 1 table (note, similarity, connection type, why, AI confidence)
4. 🌉 Bridge Notes — cross-cluster integrators, with mechanism + significance
5. 🕸️ Network Structure — 3-layer tree (thresholds: L1 > 0.75, L2 > 0.65, L3 > 0.60)
6. 💡 Emergent Patterns, 🔍 Non-Obvious Connections (flag for human validation)
7. 🎨 Conceptual Clusters, 🔭 Knowledge Gaps & Opportunities
8. 📊 Network Statistics, 🎯 Actionable Insights (⚠️ human-review callout)
9. 📝 Methodology Note (embeddings: all-MiniLM-L6-v2 / 384-dim, cosine similarity, multi-hop traversal)

Always label AI-inferred content and keep both disclosure callouts.

## BDG Integration (Optional Enrichment)

When available, enrich connection analysis with Brain Dependency Graph data:

```bash
# Get typed edges and lifecycle phase for the anchor note
resources/brain-graph/run_brain_graph.sh inspect "$ARGUMENTS" --json
```

This reveals:
- **Edge types**: derives-from vs references vs tension (not just "related")
- **Authority direction**: which note is authoritative in each relationship
- **Lifecycle phase**: reflective, crystallizing, or generative
- **Staleness**: whether upstream changes have made this note potentially stale

## Quality Standards

- **Explain WHY notes connect**, not just that they do
- **Identify non-obvious relationships** - surface-level links are less valuable
- **Look for meta-patterns** - themes that recur across domains
- **Be specific** - provide concrete evidence from note content
- **Think like a network scientist** - focus on topology, hubs, bridges, clusters
- **Highlight surprising connections** - these are often the most valuable
- **Suggest concrete actions** - make the analysis actionable
- **ALWAYS label AI-generated insights** - maintain transparency about computational vs. human-verified connections
- **Encourage critical review** - emphasize that similarity scores ≠ conceptual validity

## Advanced Techniques

### Cross-Cluster Analysis
When notes from different domains connect, ask:
- What shared abstraction unites them?
- Is this an analogy, a causal relationship, or a shared mechanism?
- What does this reveal about fundamental principles?

### Hub Identification
Notes with many connections are conceptual hubs. Analyze:
- What makes them central?
- Are they definitions, frameworks, or applications?
- Could they be MOC (Map of Content) candidates?

### Isolated Insights
High-quality notes with few connections need integration:
- What prevents them from connecting?
- What domain or cluster should they join?
- What new connections would increase their value?

---

**Remember:** Your goal is to reveal the HIDDEN STRUCTURE of thought - the connections the user may not consciously recognize but that shape their intellectual landscape.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Brain notes | `Brain/**/*.md` | X | | All permanent notes, sources, MOCs |
| Local Brain Search index | `resources/local-brain-search/` | X | | Vector index and connection graph |
| Graph statistics | `run_connections.sh --stats` | X | | Network topology data |

## Completion Checklist

- [ ] Anchor point identified and read
- [ ] Immediate network mapped (top 3-5 connections)
- [ ] Deep network analysis completed (hubs, bridges, stats)
- [ ] Cross-cluster bridges discovered and explained
- [ ] Emergent patterns identified
- [ ] Non-obvious connections highlighted with validation notes
- [ ] Actionable insights provided
- [ ] Methodology transparency included
