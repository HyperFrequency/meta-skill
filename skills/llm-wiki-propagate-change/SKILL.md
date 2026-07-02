---
name: llm-wiki-propagate-change
version: 0.2.0
description: Propagate staleness from ONE changed note outward through the vault's wikilink dependency graph and report which downstream notes are now likely stale and need review — the blast radius of an edit. Use WHEN a single framework/insight note in the user's Obsidian/turbovault vault was substantially rewritten, the user says their thinking on a topic changed, or new source material contradicts an existing note, and they want to know what downstream notes that invalidates. Do NOT use to re-score the WHOLE vault or produce a health/lifecycle report (use llm-wiki-coherence-sweep), to discover NEW related notes from a note or topic (use llm-wiki-find-connections), to triage recently-added or orphaned notes (use llm-wiki-integrate-recent-notes), or to surface contradictions between notes (use llm-wiki-detect-tensions).
argument-hint: <note name>
allowed-tools: [Bash, Read, Grep]
user-invocable: true
automation: gated
---

# Propagate Note Change

When one note is substantially edited, this skill computes which downstream notes may now be stale and worth reviewing. It seeds a staleness signal at the changed note and pushes it outward across the directed dependency edges of the vault (the links pointing *into* the changed note — the notes that lean on it).

This is a targeted, single-seed blast-radius query. For a whole-vault recompute, use `llm-wiki-coherence-sweep`.

## How staleness propagates

The signal weakens as it travels, so only genuinely affected notes surface:

- **Edge-type decay** — dependency edges are not equal. A note that *derives from* or *cites* the changed note inherits far more staleness than one that merely *mentions* it in passing. Structural dependencies pass staleness; loose references barely do.
- **Distance decay** — staleness diminishes with each hop away from the changed note, so notes several links removed are rarely flagged.
- **Hub dampening** — a highly-connected hub (an index/MOC or a note everything links to) absorbs staleness rather than amplifying it across all its neighbours, which prevents one edit from flagging half the vault.

The output is a per-note staleness score; only notes above a review threshold are reported.

## Process

### Step 1 — Locate the changed note and its dependents

`<NOTE_NAME>` is the note title as it appears in the vault, not a file path. Quote it (titles contain spaces).

Find the notes that depend on it — the backlinks (`[[<NOTE_NAME>]]` references) pointing into it:

```bash
grep -rl --include='*.md' -F "[[<NOTE_NAME>]]" "$VAULT_DIR"
```

If the vault is indexed, prefer the richer path: `turbovault` / `obsidian-cli` for backlink queries, or reuse the graph that `llm-wiki-analyze-kb` builds (hubs, bridges, clusters) so hub dampening is accurate. Fall back to the `grep` above when no index exists.

### Step 2 — Propagate the staleness signal

Starting from the changed note (seed staleness = 1.0), walk the dependency graph outward and, for each note reached, combine the three decays into a staleness score:

- Classify each incoming edge (`derives-from` / `cites` > `references` > `mentions`) and apply its attenuation.
- Multiply by a per-hop distance decay.
- Dampen contributions that arrive through hub notes.

Keep only notes whose score clears the review threshold. For a light touch-up rather than a full rewrite, scale the seed down (e.g. 0.5) so fewer downstream notes cross the threshold.

Read the flagged notes to judge whether the specific claim that changed actually feeds them — a link alone is not proof of dependence.

### Step 3 — Present the blast radius

List the flagged notes sorted by staleness score. For each:

- **Why flagged** — which upstream change reached it, through what edge type and how many hops.
- **Suggested action** — review, update, or dismiss as still-valid.

This skill is read-only: it reports the blast radius and never rewrites notes or links.

## When to Use

- After substantially editing a framework or key-insight note.
- When the user says they have changed their thinking on a topic.
- After ingesting source material that contradicts an existing note.

## When NOT to Use

- **Whole-vault health check** — to recompute staleness, lifecycle, and structure across every note and write a report, use `llm-wiki-coherence-sweep`. This skill is single-seed and targeted.
- **Trivial edits** — a typo or formatting fix leaves downstream meaning unchanged; no propagation needed.
- **Discovering connections** — to find which notes *relate* to a note (not which are now stale), use `llm-wiki-find-connections`; to triage newly-added or orphaned notes, use `llm-wiki-integrate-recent-notes`.
- **Finding contradictions** — to surface note pairs that disagree, use `llm-wiki-detect-tensions`.
- **Note not yet linked** — a just-created note with no backlinks has no edges to propagate along; there is no blast radius to compute.
