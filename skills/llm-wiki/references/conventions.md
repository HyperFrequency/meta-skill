# Conventions, templates & pitfalls

## Required tooling — the unified gateway contract

When working with any wiki operation, **always** route MCP calls through the unified mcp2cli gateway (see the `neuro-harness` skill for the full endpoint table).

| Task | Use | Why |
| --- | --- | --- |
| Knowledge-graph + gap analysis | `infranodus` skill | Local OSS engine per `project_infranodus_local_only.md` — never default to `infranodus.com`. |
| Vault read / write / search / backlinks | `turbovault` skill | TurboVault is the only sanctioned write path into the vault. |
| Web scrape + ingest of articles, papers, blog posts | `web-scrape-ingest` skill | Composes `parallel-web` + `markitdown` + `turbovault` into one URL → `__raw/` pipeline. |
| PDF / HTML / DOCX → markdown | `markitdown` CLI | `__raw/papers/`, `__raw/patents/`, `__raw/books/` must be markdown before any wiki page references them. |
| Fast in-vault search | `ripgrep` (`rg`) | TurboVault is the API; rg is the unix tool. |
| Ontology generation | `ontology-creator` skill | Owns the relation-code vocabulary + the network-not-tree discipline. Modes: macro, agent, workflow-state, **plus dimension modes** added here (`systems`, `concepts`, `connections`, `differences`, `constraints`, `sources`). |
| Cross-tool / cross-wiki link discovery | `cornelius-find-connections` skill | Augments `infranodus merged_graph_from_texts` with prose-driven connection discovery. |
| KB coherence + tension detection | `cornelius-coherence-sweep`, `cornelius-detect-tensions` | Used in maintenance workflow W10. |
| Change propagation across linked pages | `cornelius-propagate-change` | Used in maintenance workflow W6. |

**Do not** hand-roll direct SSE calls when a gateway route exists — contract violation per `neuro-harness`. Direct SSE is allowed only for debug / liveness checks.

---

## How adjacent skills compose

```
                                  USER goal
                                       │
                                       ▼
                  ┌─────────────────────────────────────┐
                  │       llm-wiki (this skill)         │  ←─── workflow orchestrator
                  │       owns W1-W10                   │       picks W1..W10 by intent
                  └─────────────────────────────────────┘
                            │                  │
                ┌───────────┘                  └──────────────┐
                ▼                                             ▼
   ┌─────────────────────┐                       ┌─────────────────────┐
   │ web-scrape-ingest   │  raw ingestion        │ ontology-creator     │  ontology gen
   │  → parallel-web     │  W1, W5               │  → modes: macro,    │  W1, W7, W8
   │  → markitdown       │                       │    agent, workflow, │
   │  → turbovault writes│                       │    + dimension      │
   └─────────────────────┘                       └─────────────────────┘
            │                                                │
            │ writes to __raw/ + wikis/                      │ writes <tool>/ontology/<dim>.md (×6)
            │                                                │   and ontologies/<dim>.md
            ▼                                                ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │   turbovault   — vault read/write/search/backlinks               │
   │   (the only sanctioned write path into ~/Vaults/neuro-quant-vault) │
   └─────────────────────────────────────────────────────────────────┘
            │
            │ exposes the vault state to:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   infranodus + infranodus-cli  — graph operations                 │
   │     • merged_graph_from_texts        W6 (cross-tool linking)      │
   │     • generate_knowledge_graph       W8 (full-wiki union)         │
   │     • generate_content_gaps          W9 (gap analysis)            │
   │     • generate_topical_clusters      W7 (per-dim refinement)      │
   │     • develop_latent_topics          W6 (novel-entity detection)  │
   └──────────────────────────────────────────────────────────────────┘
            │
            │ structural; prose-driven half is:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   cornelius-*  — prose-level KB operations                        │
   │     • cornelius-find-connections     W6                           │
   │     • cornelius-coherence-sweep      W10                          │
   │     • cornelius-detect-tensions      W10                          │
   │     • cornelius-propagate-change     W5 (downstream after update) │
   │     • cornelius-synthesize-insights  W1 (overview.md generation)  │
   │     • cornelius-extract-document-insights  W1 (concept extraction) │
   └──────────────────────────────────────────────────────────────────┘
            │
            │ for harness-level orchestration of W1-W10 across many tools:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   autonomous-orchestrator — meta-agent loop                       │
   │     • PROGRAM.md directive specifies the wiki to maintain         │
   │     • Hill-climbs on wiki health metric (resolved-wikilink %,     │
   │       gap count, contradiction count)                             │
   │     • Iterates W5 + W7 + W9 overnight                             │
   └──────────────────────────────────────────────────────────────────┘
```

### Skill-by-skill: when to reach for which

| Situation | Reach for | Why |
| --- | --- | --- |
| First-time wiki setup | This skill (W3 bootstrap) | Owns the directory scaffold + AGENTS.md placeholders |
| Adding a new tool | `deep-tool-wiki` skill, then W7 + W8 here | `deep-tool-wiki` is the single-tool populate flow; W7/W8 propagate to ontologies |
| Adding a cross-cutting concept | This skill (W2) | Classifies to dimension + cross-links |
| Re-scraping upstream | This skill (W5) | Owns the diff + propagation chain |
| "Are these two tools related?" | This skill (W6) — uses both InfraNodus and Cornelius | Structural + prose halves |
| "What's missing from the wiki?" | This skill (W9) — uses InfraNodus content-gaps | Gap analysis is the gateway to todos/ |
| "Why are these two pages contradictory?" | `cornelius-detect-tensions` directly, then W10 | Lint folds the result into the report |
| Overnight automated maintenance | `autonomous-orchestrator` with PROGRAM.md set to "maintain the wiki" | Iterates W5/W7/W9 until convergence |
| Querying the wiki | `turbovault` directly or via `/forge turbovault.<tool>` | Vault is the source of truth |

---

## Per-folder `AGENTS.md` — co-located instruction-as-code

Each subdirectory carries its own `AGENTS.md`. When an agent (Claude Code, Codex, any LLM that reads `AGENTS.md` files) opens a directory, the local file tells it exactly how to treat the contents. The top-level `CLAUDE.md` / `AGENTS.md` binds globally; per-folder files specialize.

Every `AGENTS.md` covers five sections:

1. **What lives here** — one-paragraph description of the directory's role
2. **Naming + frontmatter** — file-naming convention + required YAML keys
3. **Write rules** — when and how an agent writes here
4. **Read rules** — context-budget guidance (e.g. for `__raw/papers/`, read abstract first then targeted sections)
5. **Anti-patterns** — directory-specific things NOT to do

Per-folder template:

```markdown
# AGENTS.md — <directory>

## What lives here
<one paragraph>

## Naming
<file naming convention, e.g. kebab-case-slug.md>

## Frontmatter
<required + optional YAML keys with examples>

## Write rules
<when and how an agent writes here>

## Read rules
<context-budget rules — e.g. for __raw/papers/, read abstract first, then sections>

## Cross-links
- relevant skills: [...]
- relevant other directories: [...]

## Anti-patterns
- DON'T: <thing>
- DON'T: <thing>
```

Per-folder cross-links to the relevant skills are non-negotiable. Example for `__raw/papers/AGENTS.md`:

```markdown
## Cross-links
- web-scrape-ingest skill (the ingest path)
- markitdown skill (PDF → MD conversion)
- citation-management skill (BibTeX validation)
- paper-lookup skill (DOI/arXiv lookup)
```

Per-folder cross-links bind the directory to its operating workflows so an agent never has to guess.

---

## `__paywalled/` — stubs for unfetchable content

Web scraping does not always return content. Publisher paywalls, captchas, geo-blocks, and image-only scanned PDFs all leave an ingestion agent holding nothing but a citation. Those cases go to `__raw/__paywalled/` **as a stub note** rather than silently skipped — the wiki has a complete record of what the user asked for AND what was actually retrievable.

Stub format:

```yaml
---
title: "<full title>"
authors: [...]
year: <YYYY>
venue: "<journal or conference>"
doi: "<DOI>"
url: "<canonical-link>"
fulltext_status: paywalled          # paywalled | conversion_failed | not_available | captcha
fulltext_source: none
fetch_attempts:
  - { source: "arxiv", result: "no preprint" }
  - { source: "publisher", result: "403 Cloudflare" }
  - { source: "wayback", result: "no snapshot" }
  - { source: "ssrn", result: "abstract only" }
unblock_path: "Campus VPN; or interlibrary loan via <institution>"
verified: <date>
---

# <Title>

## Why it's here

<one-paragraph why-this-paper-matters>

## Abstract

<verbatim publisher abstract, OR "Abstract not retrievable">

## What to do if you need this

<concrete unblock path>
```

Cross-references from `wikis/` pages still resolve via `[[<slug>]]` wikilinks pointing at the paywalled stub. The graph stays connected.

**Promotion rule**: when a paywalled paper becomes retrievable, the ingestion agent moves the file from `__raw/__paywalled/` to `__raw/papers/`, runs the normal conversion pipeline, updates `fulltext_status: included`, and logs the promotion to `log.md`.

---

## CLAUDE.md / AGENTS.md template (top-level schema)

The top-level files bind globally. Template:

```markdown
# Vault schema — neuro-quant edition

This vault hosts two wikis plus a flat ontology layer. Every LLM that reads this
file must respect the conventions below.

## Layout
- __raw/                       immutable sources, never auto-edited
- wikis/deep-tool-wiki/<tool>/  per-tool docs + per-tool ontology
- wikis/deep-agent-wiki/<dim>/  cross-cutting knowledge by dimension
- ontologies/                  flat global ontology layer (6 dimensions + full union)
- output/                      analyses + reports
- todos/                       gap-driven research priorities

## Gateway contract
Every MCP call routes through neuro-harness (mcp2cli / ContextForge).
InfraNodus is LOCAL OSS — never default to infranodus.com.
Vault writes go through TurboVault (never edit .md files via subprocess + raw fs).

## Naming
kebab-case slugs for files. Page H1 matches the slug. Wikilinks are case-sensitive.

## Page-type taxonomy
- entity:        a thing (tool, system, concept)
- source-summary: a digested upstream source
- comparison:    X vs Y in a single page
- synthesis:     overview / index / log
- ontology:      a relation graph (only in /ontologies/, in <tool>/ontology/<dim>-ontology.md, or
                 in deep-agent-wiki/<dim>/ pages)

## Wikilink discipline
- [[<slug>]]:    canonical entity link
- [[<slug>|alias]]: rare; only when the alias improves readability
- broken [[<slug>]]: agent must either create the target or remove the link
                      within the same edit; no orphan stubs in 02-KB-main per
                      feedback_auto_stub_pages.md.

## Memory pins
- project_infranodus_local_only.md
- feedback_vault_root_clean.md
- feedback_auto_stub_pages.md
- feedback_doc_sync_hook_misfire.md

## Skill router
For any operation, prefer the per-skill router over hand-rolled tool calls:
- llm-wiki: workflows W1-W10 (this file's home)
- deep-tool-wiki: populate one tool's deep-tool-wiki/<tool>/
- web-scrape-ingest: URL → __raw/ pipeline
- ontology-creator: any ontology generation
- infranodus / infranodus-cli: graph operations
- turbovault: vault I/O
- cornelius-*: prose KB operations
```

---

## Common pitfalls

1. **Editing `__raw/` from a wiki workflow.** Raw is immutable. If a source needs fixing, write a correction in `wikis/deep-agent-wiki/sources/` referencing the raw entry — never modify the raw file. Promotion from `__paywalled/` to `papers/` is the one exception (the file moves; its content stays as-fetched).
2. **Hand-editing `ontologies/<dim>-ontology.md`.** Always regenerate via W7. Manual edits get overwritten on the next aggregation. Add the underlying concept page in `deep-agent-wiki/<dim>/` instead — that's the input.
3. **Mixing wiki shapes** — putting per-tool docs in `deep-agent-wiki/` or putting cross-cutting concepts in `deep-tool-wiki/<tool>/`. Use the right shape: if it's specific to one tool, it goes in `deep-tool-wiki/`; if it spans tools, it goes in `deep-agent-wiki/`.
4. **Auto-creating stub pages without content** in `deep-agent-wiki/` to satisfy a wikilink. Per `feedback_auto_stub_pages.md`, no empty placeholders. Either write the page now or remove the wikilink.
5. **Multiple Obsidian Sync writers.** Per `neuro-harness/docs/obsidian-livesync.md`, only desktop Obsidian participates in CouchDB sync. TurboVault + agent writers go through the filesystem; do not enable Obsidian Sync plugin on a second device pointing at the same vault.
6. **Forgetting to run W7/W8 after W5.** Tool updates that don't propagate to the global ontologies create drift — the per-tool ontology says one thing, the global says another. Always cascade.
7. **Naming a custom wiki `deep-research-wiki` etc.** without picking a shape. Pick shape A (`deep-tool-wiki`-like, per-entity nesting) or shape B (`deep-agent-wiki`-like, by-dimension subfolders). Don't invent shape C.

---

## Verification checklist (end-of-session)

After any workflow run, confirm:

- [ ] `log.md` has an entry for this session
- [ ] No new wikilinks in the touched pages are broken (`rg -o '\[\[[a-z0-9-]+\]\]' <page> | sort -u` then check each target exists)
- [ ] `verified:` date in frontmatter is today's date for any page touched
- [ ] The relevant ontology was regenerated (W7) if wiki content changed
- [ ] `full-wiki-ontology.md` was rebuilt (W8) if multiple dimensions changed
- [ ] Gap-driven todos in `todos/<date>-gaps.md` are linked back to the wiki pages that prompted them
