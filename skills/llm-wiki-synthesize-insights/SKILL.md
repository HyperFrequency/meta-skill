---
name: llm-wiki-synthesize-insights
version: 0.2.0
description: 'Combine multiple permanent notes from your Obsidian/turbovault knowledge base into a single coherent narrative, framework, or argument — surfacing non-obvious patterns, cross-domain bridges, tensions, and emergent understanding that no single note holds. Use WHEN the user hands you 5-10+ specific notes or a topic cluster and wants them MERGED into one artifact: "synthesize these notes", "what connects X and Y", "turn my notes on Z into a framework", "what can I write from my notes about W". Do NOT use to merely list related/adjacent notes without merging them (use llm-wiki-find-connections), to surface contradictions between notes (use llm-wiki-detect-tensions), to profile whole-vault structure/hubs/clusters (use llm-wiki-analyze-kb), to retrieve or semantic-search notes (use Local Brain Search directly), or to draft a finished publishable article — this skill produces the synthesis foundation, not the final piece.'
---

# Synthesize Insights

Merge multiple notes or insights from the vault into one coherent narrative, framework, or argument, exposing the emergent understanding that lives *between* the notes rather than in any one of them.

## Usage

```
/synthesize-insights <note names or topic cluster>
```

The argument is either an explicit list of notes or a cluster description:
- Explicit notes: `[[Note A]], [[Note B]], [[Note C]]`
- Topic cluster: `All notes connecting dopamine, social media, and AI`
- Theme: `Buddhism-neuroscience-AI triangle`

## When to reach for this vs. siblings

| You want to… | Use |
|---|---|
| **Merge** several notes into one narrative/framework | this skill |
| Find notes *related* to one note/topic (no merge) | `llm-wiki-find-connections` |
| Surface *contradictions* between notes | `llm-wiki-detect-tensions` |
| Profile whole-vault structure, hubs, clusters | `llm-wiki-analyze-kb` |
| Just retrieve/search notes | Local Brain Search directly |
| Stress-test ONE idea dialectically | `llm-wiki-dialectic` |

## Workflow

1. **Gather the notes.**
   - If specific notes are named, read them directly.
   - If a topic/theme is given, use Local Brain Search (`resources/local-brain-search/`) to pull the cluster, and optionally consult a MOC in `Brain/03-MOCs/` for thematic scope.
   - Aim for 5-10 notes. Fewer than ~4 rarely yields emergent insight — say so and offer to widen the cluster rather than forcing a thin synthesis.

2. **Find the structure.** Identify common threads, non-obvious bridges (independent domains converging on the same truth), and tensions or contradictions. The bridges and tensions are the point; a synthesis that only restates shared themes is a summary, not a synthesis.

3. **Build the narrative.** Structure as Pattern → Evidence → Implications. Show how notes build on each other and name the emergent understanding explicitly.

4. **Output** the synthesis in the format below and cite each source note with its role.

## Output Format

```
Synthesis: [Topic/Theme]

Pattern Identified:
[The overarching pattern or framework emerging from the notes]

Key Connections:
1. [[Note A]] + [[Note B]] — [how they relate, what emerges]
2. [[Note C]] + [[Note D]] + [[Note E]] — [multi-way emergent insight]
3. [[Note F]] ↔ [[Note G]] — [bidirectional tension]

Emergent Understanding:
[The new insight that wasn't obvious in any single note]

Implications:
- [For thinking/practice]
- [For content/frameworks]
- [For future exploration]

Suggested Applications:
- Article topic, framework name, or research direction

Synthesized Notes:
- [[Note 1]] — role in synthesis
- [[Note 2]] — role in synthesis
```

## Quality bar

A strong synthesis identifies non-obvious patterns across 5-10+ notes, produces genuinely emergent understanding, names at least one tension or contradiction, and suggests a concrete application. If the result is only surface-level shared themes with no emergent insight, widen or swap the note cluster and try again.

## Advanced moves

- **Multi-domain** — pull notes from independent domains to reveal consilience (where they converge on the same truth).
- **Temporal** — synthesize how the user's thinking on a topic evolved over time.
- **Contrarian** — gather notes that challenge conventional wisdom into a provocative angle.
- **Problem-solution** — connect problem notes with solution notes from different domains.

## Downstream

This skill produces the *foundation*, not the finished piece. Hand its output to an article-drafting step, feed the emergent theme back into `llm-wiki-find-connections` to widen the network, or extract 3-5 narratives for a content series.

## State Dependencies

| Source | Location | Read | Write |
|--------|----------|------|-------|
| Vault notes | `Brain/**/*.md` | ✓ | |
| Local Brain Search | `resources/local-brain-search/` | ✓ | |
| MOCs | `Brain/03-MOCs/` | ✓ | |

Read-only: this skill maps and merges, it never writes notes or links.

## Completion Checklist

- [ ] 5-10+ notes gathered (or cluster widened / thin synthesis flagged)
- [ ] Common threads, cross-domain bridges, and tensions identified
- [ ] Emergent understanding articulated (not just a summary)
- [ ] Pattern → Evidence → Implications structure
- [ ] Concrete application suggested
- [ ] Every source note cited with its role
