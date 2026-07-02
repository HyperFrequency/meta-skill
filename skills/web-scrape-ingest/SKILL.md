---
name: web-scrape-ingest
version: 0.1.0
description: >
  End-to-end pipeline that turns a topic, URL/DOI list, or search query into a
  curated vault of OFM (Obsidian-flavored Markdown) notes — raw originals
  preserved, metadata frontmatter, [[wikilinks]] wiring related items, an
  InfraNodus ontology over the corpus, and a generated INDEX.md. Use when the user
  says "scrape and ingest", "build a vault/knowledge base from these URLs/papers",
  "research pipeline", "ingest papers into Obsidian", "harvest documentation for",
  or any phrasing meaning "go fetch this content and turn it into structured
  knowledge in my vault". Routes through the mcp2cli gateway (parallel-web,
  exa-mcp, turbovault, infranodus, markitdown). Do NOT use for a single-URL fetch
  with no vault wiring (use parallel-web extract or WebFetch) — this skill is
  overkill for one URL. For the slash-command flavor of the same pipeline, the
  sibling scrape-ingest-organize skill is equivalent; new work should call this.
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, WebFetch, WebSearch
license: HyperFrequency original
---

# /web-scrape-ingest

End-to-end research-ingest pipeline. Given a topic, a list of URLs/DOIs, or a
search query, produces a curated `__raw/<topic>/` tree inside the vault with:

1. Raw originals preserved in `_originals/` (PDF, HTML).
2. Converted full-text Markdown alongside (one `<slug>-fulltext.md` per source).
3. Per-source metadata notes (`<slug>.md`): YAML frontmatter, verbatim abstract,
   why-it-matters paragraph, and `[[wikilinks]]` to related items.
4. An InfraNodus ontology (`_ontology.md`, `_clusters.md`) over the corpus.
5. A generated `INDEX.md` grouped by cluster.

## When to use

- **Research literature scrape** — "scrape the canonical microstructure papers
  into my vault" → tree with one cross-linked note per paper + ontology + INDEX.
- **News ingestion** — "ingest the last 50 articles about <topic>." Notes carry
  publication date + source instead of DOI.
- **Documentation harvest** — "rip the Nautilus Trader v1.227 docs into my notes."
  Source list = doc-site sitemap; converted MD becomes the per-page note.
- **Competitor / market analysis dump** — "harvest 30 product pages from X.com."
  The ontology pass highlights feature clusters and gaps.
- **Paper + GitHub repo cross-ingest** — "scrape this arXiv paper and its companion
  repo's README, link them." The wikilink pass pairs the paper and repo slugs.
- **DOI / arXiv batch** — "here are 40 DOIs, build me a vault." Bypasses search.

**When NOT to use:** single-URL fetch with no vault wiring → use `parallel-web`
extract or `WebFetch`. This skill is overkill for one URL.

## Required tooling — unified gateway contract

When operating, **always** route through the unified mcp2cli gateway. See the
`neuro-harness` skill (`neuro-quant-agent-skills/neuro-base/`) for the full
endpoint table. Concretely:

| Phase | Use | Why |
| --- | --- | --- |
| Search (default) | `mcp2cli parallel-web search` or `parallel-web` skill | Synthesized summaries + citations + extract API |
| Search (alt, long-tail technical) | `mcp2cli exa search` if installed | Better at code/docs; needs `EXA_API_KEY` |
| Single-URL fetch | `WebFetch` first, then `curl` for PDFs | Cheapest, no rate limit |
| Convert PDF/HTML → MD | `markitdown <file> -o <out>` (`markitdown` skill) | Token-efficient, preserves structure |
| Vault writes | `mcp2cli turbovault write_note` (`turbovault` skill) | Honors vault conventions, updates link graph |
| Ontology over corpus | `mcp2cli infranodus generate_knowledge_graph` (`infranodus` skill) | Local OSS engine; no per-request fees |

- **Do not** scrape directly with `requests` / `httpx` when a gateway route exists.
- **Do not** call `infranodus.com` — the local engine is pinned (user memory
  `project_infranodus_local_only.md`).
- If the gateway is unreachable, degrade **explicitly**: announce the degradation,
  then fall back to `WebFetch` + `curl` + local `markitdown` CLI. Never silently
  bypass.

## Pipeline overview

```
INPUT (topic | source-list | search-query)
  └─ 1 DISPATCH   → split work across N parallel agents (default 6)
  └─ 2 FETCH      → parallel-web → Exa → WebFetch → curl → arxiv; save to _originals/
  └─ 3 CONVERT    → markitdown <file> -o <slug>-fulltext.md (pandoc/pdfplumber fallback)
  └─ 4 METADATA   → <slug>.md: frontmatter + VERBATIM abstract + why-it-matters
  └─ 5 WIKILINKS  → name→slug index, replace bare citations, resolution-rate check
  └─ 6 INFRANODUS → generate_knowledge_graph, save _ontology.md + _clusters.md
  └─ 7 INDEX      → INDEX.md grouped by cluster + stats
```

Each phase is **idempotent** — re-running on an existing tree is a merge, not a
clobber. **Slugs are the join key.** Slug template:
`<first-author-lastname>-<year>-<short-title>` for papers, `<domain>-<path-slug>`
for non-paper URLs — lowercase, kebab-case, ASCII.

**Full step-by-step instructions for every phase** (commands, frontmatter spec,
quality checks, fallback chains): see
[`references/pipeline-phases.md`](references/pipeline-phases.md).

## Non-negotiable rules (read before running)

- **Verbatim abstract or "No abstract available." — never paraphrase or invent.**
  Hallucinated abstracts poison the phase-6 ontology. Don't paste parallel-web's
  synthesized summary as the abstract.
- **Prefer the open-access PDF over the publisher abstract page** (direct curl on
  `pdf_url` before the landing URL). This was the 2026-05-20 run's failure mode.
- **Disjoint slug assignment across agents** — partition into `_dispatch/chunk_<i>.txt`
  up front; each agent writes only to its slugs. No pre-partition → corrupt YAML.
- **Merge, never clobber** — phase 4 must `read_note` first; flag conflicts in
  `_dispatch/merge-conflicts.txt`.
- **Local InfraNodus only** — never `infranodus.com` (the user pays per request).

Backend choice, parallel-agent orchestration details, the full anti-pattern and
common-pitfall lists, and a worked end-to-end example are in
[`references/orchestration-and-pitfalls.md`](references/orchestration-and-pitfalls.md).

## References

- **Primary tools** — `parallel-web` (search + extract), Exa MCP (alt long-tail
  search), `markitdown` skill / Microsoft markitdown CLI (file → MD), `turbovault`
  skill (vault writes/backlinks), `infranodus` skill (local OSS knowledge graph),
  `neuro-harness` skill (gateway endpoint registry — canonical), `forge` skill
  (slash-command router over the gateway).
- **Fallbacks** — `WebFetch`/`WebSearch` built-ins, `curl` (PDF download), `pandoc`
  (HTML→MD when markitdown empty), `pdfplumber`/`pdftotext` (image-based PDFs),
  GNU `wget --mirror` (whole-site harvests, not default), `scrapy` (production crawls).
- **Sibling skills** — `scrape-ingest-organize` (slash-command flavor of this
  pipeline; new work should call `/web-scrape-ingest`), `infranodus` /
  `infranodus-cli` (ontology pass), `markitdown`, `turbovault`, `parallel-web`.
- **Canonical worked output** —
  `$HOME/Vaults/neuro-quant-vault/__raw/microstructure-papers/INDEX.md`
  (108 papers, 97% wikilink resolution). `$HOME/Vaults/CLAUDE.md` — vault
  conventions (layout + YAML frontmatter schema).
- **Last cross-checked:** 2026-05-24 (markitdown CLI flags verified via Context7
  `/microsoft/markitdown`; gateway endpoints verified against `neuro-harness`).
