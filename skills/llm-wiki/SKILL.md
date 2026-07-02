---
name: llm-wiki
version: 0.1.0
description: >
  Scaffold and maintain compounding LLM-curated knowledge bases on the neuro-quant stack.
  Triggers: "set up an LLM wiki", "build a research wiki", "deep-tool-wiki / deep-agent-wiki",
  "compounding second-brain over Obsidian", "wiki + ontologies", "wikilinked tool docs",
  "build a knowledge base from these sources", "maintain my wiki". Two canonical wikis
  coexist (`deep-tool-wiki` = per-tool docs, `deep-agent-wiki` = cross-cutting knowledge
  organized by ontology dimension) plus a flat top-level `ontologies/` aggregation layer.
  Every MCP call routes through the unified `neuro-harness` gateway. NOT for vault queries
  (use turbovault), single-tool population (use deep-tool-wiki), or raw ingestion (use
  web-scrape-ingest).
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, Bash, Skill, Agent, TaskCreate, TaskUpdate
license: HyperFrequency original (derived from infranodus/skills `skill-llm-wiki`, MIT — see NOTICE.md)
---

# LLM Wiki — neuro-quant edition

Scaffold and maintain **LLM-curated, compounding knowledge bases** on top of the Obsidian vault at `~/Vaults/neuro-quant-vault`. Instead of re-deriving knowledge from raw documents on every query (RAG-style), the LLM builds a persistent wiki once and keeps it current as new sources arrive.

This is a **router**. It points to detailed references; load the one relevant to the task instead of reading everything inline.

## How this edition differs from upstream `skill-llm-wiki`

1. **Two canonical wiki shapes** — `deep-tool-wiki/` (per-tool, deeply nested) and `deep-agent-wiki/` (cross-cutting, by the 6 ontology dimensions).
2. **Flat top-level `ontologies/`** — six dimension ontologies + a full-wiki union, aggregated from BOTH wikis.
3. **Per-folder `AGENTS.md` discipline** — every subdirectory carries its own instruction-as-code file.
4. **Gateway contract** — every MCP call routes through `neuro-harness` (mcp2cli / ContextForge). InfraNodus is local OSS; vault writes go through TurboVault; ingestion goes through `web-scrape-ingest`.

## Four layers

```
__raw/        immutable source documents (never auto-edited)
  → wikis/    LLM-owned content: deep-tool-wiki/<tool>/ + deep-agent-wiki/<dimension>/
    → ontologies/   flat global aggregation (6 dimensions + full-wiki union)
      → output/ + todos/   analyses, reports, gap-driven research priorities
```

Raw flows up; wiki never edits raw. Ontologies regenerate from wiki content. Output/todos are downstream of gap analysis.

## Routing — load the reference you need

| If the task is… | Read |
| --- | --- |
| Understanding the vault structure, the two wikis, directory trees, the 6 dimensions, multi-wiki slug coordination | `references/architecture.md` |
| Running a workflow — setup, build (W1 new-tool-wiki, W2 new-agent-knowledge, W3 bootstrap) or maintain (W4–W10) | `references/workflows.md` |
| Gateway contract table, per-folder + top-level `AGENTS.md`/`CLAUDE.md` templates, `__paywalled/` stubs, how adjacent skills compose, pitfalls, end-of-session checklist | `references/conventions.md` |

## Workflow index

- **W1** `new-tool-wiki` — add a tool to `deep-tool-wiki/`
- **W2** `new-agent-knowledge` — add a cross-cutting page to `deep-agent-wiki/`
- **W3** `bootstrap` — instantiate the whole structure from zero (idempotent script)
- **W4** `schema-write` — populate every `AGENTS.md` + top-level `CLAUDE.md`
- **W5** `tool-update` — refresh a tool wiki when upstream changes
- **W6** `cross-tool-link` — discover connections between tools (InfraNodus + Cornelius)
- **W7** `ontology-aggregate` — rebuild a global dimension ontology (W7b per-tool refresh, W7c per-tool `full-ontology.md` union)
- **W8** `full-wiki-rebuild` — combine 6 dimensions into the union ontology
- **W9** `gap-analysis` — find what's missing → `todos/`
- **W10** `lint` — vault hygiene (orphans, broken links, stale dates, contradictions)

Full step lists in `references/workflows.md`.

## Hard rules (never violate)

- Route every MCP call through the `neuro-harness` gateway (mcp2cli / ContextForge). Direct SSE only for debug/liveness.
- InfraNodus is **local OSS** — never default to `infranodus.com` (`project_infranodus_local_only.md`).
- Vault writes go through **TurboVault** only — never edit `.md` via raw fs subprocess.
- `__raw/` is immutable. Never auto-edit it (the `__paywalled/ → papers/` promotion is the one exception).
- `ontologies/<dim>-ontology.md` is regenerated via W7 — never hand-edit.
- No empty stub pages to satisfy a wikilink (`feedback_auto_stub_pages.md`). Write the page or remove the link.
- After W5, always cascade W7/W8 so per-tool and global ontologies don't drift.

## Boundaries — when NOT to use this skill

- Querying the vault → `turbovault` (or `/forge turbovault.<tool>`).
- Populating a single tool's docs → `deep-tool-wiki` skill (this skill owns the scaffold + propagation W7/W8 around it).
- URL → `__raw/` ingestion → `web-scrape-ingest`.
- Any ontology generation → `ontology-creator` (owns the relation-code vocabulary + dimension modes).
- Prose-level KB ops (find connections, coherence, tension, propagate) → `cornelius-*`.
- Overnight automated maintenance loop → `autonomous-orchestrator` with PROGRAM.md set to maintain the wiki.

## References

### Upstream
- [infranodus/skills/skill-llm-wiki](https://github.com/infranodus/skills/blob/master/skill-llm-wiki/SKILL.md) — MIT, the phase-structure baseline
- [infranodus/skills/skill-ontology-creator](https://github.com/infranodus/skills/blob/master/skill-ontology-creator/SKILL.md) — MIT, the relation-code vocabulary
- [infranodus/skills/infranodus-cli](https://github.com/infranodus/skills/blob/master/infranodus-cli/SKILL.md) — MIT, full InfraNodus tool surface

### Local references
- `references/architecture.md` — layers, two wikis, directory trees, 6 dimensions, multi-wiki coordination
- `references/workflows.md` — setup + W1–W10 step lists + bootstrap script
- `references/conventions.md` — gateway contract, AGENTS.md/CLAUDE.md templates, `__paywalled/`, skill composition, pitfalls, checklist

### Adjacent skills
`deep-tool-wiki`, `web-scrape-ingest`, `ontology-creator`, `infranodus` / `infranodus-cli`, `turbovault`, `cornelius-*`, `autonomous-orchestrator`, `neuro-harness`.

### Memory pins driving the design
`project_infranodus_local_only.md`, `feedback_vault_root_clean.md`, `feedback_auto_stub_pages.md`, `feedback_doc_sync_hook_misfire.md`. Obsidian Self-hosted LiveSync (CouchDB): `neuro-harness/docs/obsidian-livesync.md`.

### Last cross-checked
2026-05-24 — InfraNodus tool surface verified against upstream; gateway endpoints verified against `neuro-harness/docker-compose.yaml` HEAD.
