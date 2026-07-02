---
name: llm-wiki-detect-tensions
version: 0.2.0
description: Scan the whole vault for PRODUCTIVE TENSIONS — note pairs that are semantically close (FAISS similarity) yet reach OPPOSING conclusions, marking synthesis opportunities. WHAT — runs the `tensions` CLI over the vault's FAISS index plus note metadata, reports each contradiction (what each note asserts, why they clash, the opportunity), and NEVER auto-resolves. WHEN — surface contradictions across the whole Obsidian/turbovault vault, decide what to write next, or audit tracked tensions; trigger on "find tensions", "where do my notes contradict", "productive contradictions", "synthesis opportunities in my vault". WHEN-NOT — deep-analyzing ONE known tension (use llm-wiki-dialectic); non-contradictory links around a note (llm-wiki-find-connections); merging notes into a narrative (llm-wiki-synthesize-insights); whole-vault structural/staleness audit (llm-wiki-analyze-kb / llm-wiki-coherence-sweep); or contradictions against external documents/web (llm-wiki-extract-document-insights / llm-wiki-deep-research).
allowed-tools: [Bash, Read]
user-invocable: true
automation: gated
---

# Detect Productive Tensions

Scans the vault for productive contradictions: note pairs with high semantic similarity but opposing conclusions. These tension zones are where the most valuable articles and frameworks emerge. This skill only surfaces and reports tensions — it never edits notes or resolves the contradiction.

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

Broader search (more results, lower precision):
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

Check `tension_count` for the total number of tracked tensions.

## Key Principle

Tensions are features, not bugs. This skill NEVER auto-resolves a tension — it surfaces contradictions as the most productive intellectual territory in the vault and leaves resolution to the user (or a hand-off to `llm-wiki-dialectic`).

## Related Skills

- `llm-wiki-dialectic` — hand a single high-stakes tension to the dialectic engine for deep contradiction analysis and synthesis.
- `llm-wiki-find-connections` — for non-contradictory relationships (complementary, hierarchical) around one anchor note, not opposing conclusions.
- `llm-wiki-synthesize-insights` — to fold a resolved tension into a coherent narrative note.
- `llm-wiki-analyze-kb` / `llm-wiki-coherence-sweep` — whole-vault structural health and staleness, not pairwise contradictions.
