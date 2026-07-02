# Resynthesis guide — patch vs re-synthesize vs commission

When a `/neuro-scan` finding lands on a `02-KB-main/` page or an ontology
contradiction, you have three escalating responses. Picking the right one
is the core judgment call of surgery. Over-patching leaves stale knowledge;
over-commissioning burns research budget on trivia.

## The three tiers

### Tier 1 — Surface patch

A localized, mechanical fix that doesn't change the page's claims.

Use when the finding is:

- A broken wikilink, dead reference, or moved path
- A stale frontmatter field (date, source count, confidence that drifted
  from a recomputed value)
- A formatting/schema violation (missing required section, malformed table)
- A typo or factual transcription error contradicted by a cited source

Tool: `tv_edit_note` (links) or `nlr_wiki_update --frontmatter-only`
(fields). Risk is almost always low. These are the `agent`-mode
auto-approvable class (see `hitl-protocol.md`).

### Tier 2 — Re-synthesize

The page's underlying sources changed enough that the synthesized claims
are now wrong or incomplete, but the topic is still settled consensus.

Use when:

- An upstream source was re-ingested with materially different content
- New sources were added to a hub and the synthesis predates them
- The page asserts something 1-2 sources now contradict, but the
  resolution is clear (newer/higher-quality source wins)

Process:

1. Re-read every source the page cites, plus any new ones the scan flagged
2. Re-draft the body via `nlr_wiki_update` (NOT `--frontmatter-only`) so
   the schema validator re-runs on the new content
3. Bump the `last_synthesized` frontmatter date and `source_count`
4. Risk is medium — show the full before/after diff; the user is approving
   a change to canonical knowledge, not a typo fix

Re-synthesis is still consensus knowledge. If you find yourself writing
"on one hand... on the other hand," you're in Tier 3, not Tier 2.

### Tier 3 — Commission deep reasoning

The topic isn't settled: 3+ sources genuinely disagree and the resolution
requires judgment, not just recency or source-quality ranking.

Do NOT resolve these in-place. A `02-KB-main/` page is for consensus; a
live contradiction is a reasoning artifact. Instead:

1. Present the contradiction with each source cited verbatim
2. Ask the user whether to commission a research task
3. If yes, draft a task spec in `00-neuro-link/tasks/` with
   `type: deep-reasoning`, then dispatch:
   - `/scientific-critical-thinking` when the dispute is about **evidence
     quality** (which study to trust, methodology flaws)
   - `/hypothesis-generation` when the dispute is about **mechanism** (why
     the sources observe different things)
4. The output lands in `05-insights-HITL/`, never `02-KB-main/`

## Framing a contradiction report

When you present a Tier 3 contradiction to the user, structure it so the
decision is easy:

```
Contradiction on <topic> (N sources, M in conflict)

Claim A: <statement>
  - Source: <citation>, confidence <x>, ingested <date>
Claim B: <statement>
  - Source: <citation>, confidence <y>, ingested <date>

Why this isn't auto-resolvable: <recency/quality don't decide it because…>
Commission? [y/N]
```

## When to escalate Tier 2 → Tier 3

If during a re-synthesis you discover the sources don't actually converge,
stop. Don't force a consensus that isn't there. Abort the
`nlr_wiki_update`, leave the page as-is, and re-present the finding as a
Tier 3 commission. Forcing consensus is exactly the silent-drift failure
the HITL protocol exists to prevent.
