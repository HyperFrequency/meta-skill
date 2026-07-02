---
name: cornelius-detect-tensions
version: 0.1.0
description: Scan the knowledge base for productive tensions - note pairs with high semantic similarity (FAISS) but opposing conclusions, which mark synthesis opportunities (article topics, frameworks). WHAT - runs the brain-graph `tensions` CLI over the FAISS index plus metadata, then presents each contradiction (what each note asserts, why they clash, the synthesis opportunity) and never auto-resolves. WHEN - the user wants to surface contradictions across the whole vault, decide what to write next, or audit tracked tensions; trigger on "find tensions", "where do my notes contradict", "productive contradictions", "synthesis opportunities". WHEN-NOT - deep-analyzing a SINGLE known tension or stress-testing one idea (use cornelius-dialectic); discovering non-contradictory links between notes (use cornelius-find-connections); merging insights into a narrative (use cornelius-synthesize-insights); or whole-vault structural health and staleness (use cornelius-coherence-sweep).
allowed-tools: [Bash, Read]
user-invocable: true
automation: gated
---

# Detect Productive Tensions

Scans the knowledge base for productive contradictions: note pairs with high semantic similarity but opposing conclusions. These tension zones are where the most valuable articles and frameworks emerge.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Enrichments | `resources/brain-graph/data/graph_enrichments.json` | ✓ | ✓ | Tension records saved |
| FAISS Index | `resources/local-brain-search/data/brain.faiss` | ✓ | | Similarity search |
| Metadata | `resources/local-brain-search/data/brain_metadata.pkl` | ✓ | | Note content |

## Process

### Step 1: Run tension detection

Default thresholds (similarity > 0.75, divergence > 0.3):
```bash
cd "$(git rev-parse --show-toplevel)"/resources/brain-graph
../local-brain-search/venv/bin/python cli.py tensions
```

Broader search (more results, lower quality):
```bash
../local-brain-search/venv/bin/python cli.py tensions --similarity 0.70 --divergence 0.2
```

### Step 2: Present synthesis opportunities

For each tension, explain:
- What the two notes assert
- Why they contradict
- What synthesis opportunity exists (article topic, framework potential)

### Step 3: Track existing tensions

```bash
../local-brain-search/venv/bin/python cli.py status --json
```

Check `tension_count` for total tracked tensions.

## Key Principle

Tensions are features, not bugs. The system NEVER auto-resolves tensions. It surfaces them as the most productive intellectual territory in the vault.

## Related Skills

- `cornelius-dialectic` — once this skill surfaces a tension, hand a single high-stakes tension to the dialectic engine for deep contradiction analysis and synthesis.
- `cornelius-find-connections` — for non-contradictory relationships (complementary, hierarchical) rather than opposing conclusions.
- `cornelius-synthesize-insights` — to fold a resolved tension into a coherent narrative.
- `cornelius-coherence-sweep` — for whole-vault structural health and staleness, not pairwise contradictions.
