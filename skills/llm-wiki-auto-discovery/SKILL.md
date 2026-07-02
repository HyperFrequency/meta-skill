---
name: llm-wiki-auto-discovery
version: 0.2.0
description: Autonomously mine the user's Obsidian/turbovault vault for non-obvious CROSS-DOMAIN connections - sample notes across diverse clusters (no seed note needed), then surface pairs with LOW semantic similarity (0.50-0.70) but HIGH conceptual strength and log them to dated changelogs. Use WHEN the user wants an unattended serendipity/consilience pass over the WHOLE vault, to "find surprising connections", "discover cross-domain patterns", "mine hidden links", or on this skill's scheduled run. Needs an up-to-date Local Brain Search index. Do NOT use when starting from ONE known note or topic (use llm-wiki-find-connections), for high-similarity opposing-conclusion pairs (llm-wiki-detect-tensions), for profiling vault structure/graph stats (llm-wiki-analyze-kb), for merging notes into a narrative (llm-wiki-synthesize-insights), for integrating recently-edited notes (llm-wiki-integrate-recent-notes), for plain "find notes about X" search, or for a graph from arbitrary text (use infranodus).
automation: autonomous
schedule: "0 20 * * 0"
allowed-tools: Read, Write, Grep, Glob, Bash
---

# LLM-Wiki Auto-Discovery

Autonomous cross-domain connection hunter for the user's notes vault. Unlike its siblings, it takes **no seed note** — it samples broadly across the vault on its own and surfaces relationships that pure semantic similarity would rank as too weak to matter but that share a deep conceptual pattern.

> **Vault layout.** Paths below assume an Obsidian/turbovault vault with the folders in [State Dependencies](#state-dependencies) and a `resources/local-brain-search/` helper exposing `run_search.sh` / `run_connections.sh`. Adjust the paths to match the target vault before running.

## The core idea

A discovery is valuable when it has **low semantic similarity (0.50-0.70) but high conceptual strength**. Two notes that the vector index thinks are unrelated, yet share a structural pattern, mechanism, or meta-principle — that gap is where the "aha" lives. High-similarity pairs (0.85+) are obvious and belong to plain search; same-domain or already-linked pairs are not discoveries.

## Boundaries vs sibling skills

- Starting from one known note/topic → **llm-wiki-find-connections**.
- High-similarity but *contradictory* pairs → **llm-wiki-detect-tensions**.
- Whole-vault structure, hubs, graph stats → **llm-wiki-analyze-kb**.
- Weaving chosen notes into an article/framework → **llm-wiki-synthesize-insights**.
- Onboarding recently created/edited notes → **llm-wiki-integrate-recent-notes**.
- Graph from arbitrary external text → **infranodus**.

## State Dependencies

| Source | Location | Read | Write | Role |
|--------|----------|------|-------|------|
| Permanent notes | `Brain/02-Permanent/` | ✓ | | Sampling source |
| AI-extracted notes | `Brain/AI Extracted Notes/` | ✓ | | Sampling source |
| Document insights | `Brain/Document Insights/` | ✓ | | Sampling source |
| Local Brain Search | `resources/local-brain-search/` | ✓ | | Similarity scores, connections |
| Session changelogs | `Brain/05-Meta/Changelogs/` | | ✓ | Dated discovery log |
| Master changelog | `Brain/CHANGELOG.md` | ✓ | ✓ | Summary entry |

## Prerequisites

- Local Brain Search index up to date (`/refresh-index`).
- Vault accessible at the paths above.

## Process

### 1. Get the date

```bash
date '+%Y-%m-%d'
```

Used for the changelog filename.

### 2. Strategic sampling

Sample 3-5 **diverse** domains so seeds land in different clusters:

```bash
resources/local-brain-search/run_search.sh "dopamine" --limit 5 --json
resources/local-brain-search/run_search.sh "uncertainty" --limit 5 --json
resources/local-brain-search/run_search.sh "identity" --limit 5 --json
```

Pick one seed note per cluster.

### 3. Get connections for each seed

```bash
resources/local-brain-search/run_connections.sh "Note Name" --json
```

Keep candidates with similarity **0.50-0.70** that sit in a *different* domain from the seed.

### 4. Cross-domain analysis

For each cross-domain pair: read both notes fully, record the **actual** similarity score from the search (never estimate), then look for a shared structural pattern, common mechanism, meta-principle, or paradox. Rate conceptual strength 1-5 stars. Target: low similarity + high conceptual strength.

### 5. Document strong connections

```markdown
## CROSS-DOMAIN CONNECTION

**Node A**: [[Note X]] (Domain: Neuroscience)
**Node B**: [[Note Y]] (Domain: Economics)
**Semantic Similarity**: 0.63 (actual from search)
**Conceptual Strength**: ⭐⭐⭐⭐⭐

**The Link**: [2-3 sentences on WHY they connect]
**Shared Pattern**: [the underlying principle]
**Synthesis Opportunity**: [candidate new note title]
```

### 6. Write the dated changelog

`Brain/05-Meta/Changelogs/CHANGELOG - Auto-Discovery Session YYYY-MM-DD.md`:

```markdown
## Auto-Discovery Session: YYYY-MM-DD

### Session Parameters
- Notes sampled: [N] from [X] clusters
- Domains analyzed: [list]

### Discoveries Made
**Strong Connections**: [N]
1. [[A]] ↔ [[B]] - [pattern]

**Meta-Patterns**: [N]
**Consilience Zones**: [N]

### Session Statistics
- Total notes analyzed: [N]
- Non-obvious connections (similarity < 0.70): [N]
```

### 7. Update the master changelog

Append to `Brain/CHANGELOG.md`:

```markdown
## YYYY-MM-DD - Auto-Discovery Session

See: [[CHANGELOG - Auto-Discovery Session YYYY-MM-DD]]
- [N] connections discovered
- [N] meta-patterns identified
```

## Quality bar

**Keep:** similarity 0.50-0.70, a clear cross-domain conceptual link, genuine "aha" factor, an actionable synthesis opportunity.
**Skip:** similarity 0.85+ (too obvious), same-domain pairs, already-linked notes.

## Error handling

| Error | Recovery |
|-------|----------|
| Search returns empty | Try different seed terms |
| All results high-similarity | Note it in the changelog, sample broader clusters |
| Index outdated | Run `/refresh-index` first |

## Completion checklist

- [ ] Notes sampled from 3+ different clusters
- [ ] Actual similarity scores recorded (not estimated)
- [ ] Cross-domain pairs analyzed for conceptual strength
- [ ] Non-obvious discoveries (similarity < 0.70) documented
- [ ] Dated changelog created in `Brain/05-Meta/Changelogs/`
- [ ] Master changelog updated with a summary
