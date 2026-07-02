---
name: web-scrape-ingest
version: 0.1.0
description: >
  Turns a topic, URL/DOI/arXiv list, or search query into a DEEP curated corpus under
  `__raw/<topic>/` in the Obsidian vault: raw originals preserved, one metadata note
  per source (frontmatter + VERBATIM abstract + why-it-matters), [[wikilinks]] between
  related items, an InfraNodus ontology, and a cluster-grouped INDEX.md. Scrapes via
  the parallel-web and exa-search skills (their Python CLIs — NOT an mcp2cli/exa-mcp
  route), then formats, lints, and organizes into the vault via turbovault MCP tools.
  Use for "scrape and ingest these papers/URLs", "build a knowledge base from these
  DOIs", "harvest documentation for X", "ingest papers into Obsidian", or any ask for
  a slug-keyed, cross-linked, ontology-backed corpus. Do NOT use
  for a single-URL fetch with no vault wiring (use parallel-web extract or WebFetch),
  nor for the lighter /forge flavor that dumps N search hits into the 00-raw inbox
  with auto-tagging (use the sibling scrape-ingest-organize, not equivalent — this
  builds the deep per-source corpus).
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

**When NOT to use:**
- Single-URL fetch with no vault wiring → use `parallel-web` extract or `WebFetch`.
  This skill is overkill for one URL.
- The lighter flavor that just fans out N searches and dumps hits into the `00-raw/`
  inbox with turbovault auto-tagging (no per-source metadata notes, no verbatim
  abstracts, no slug-keyed corpus) → use the sibling `scrape-ingest-organize`. The
  two are **not** equivalent: this skill builds the deep, cross-linked, per-source
  corpus under `__raw/<topic>/`.

## Required tooling — verified interfaces

Two distinct layers. **Scraping** goes through the `parallel-web` / `exa-search`
skills, which are **Python-CLI skills** (they call their vendor SDKs directly — there
is NO `mcp2cli parallel-web` / `mcp2cli exa` route; do not invent one). **Vault
writes/format/lint/organize + ontology** go through the mcp2cli gateway to the
`turbovault` and `infranodus` MCP servers. See the `neuro-harness` skill for the full
endpoint table. Real invocations (verified 2026-07-02 against each skill's scripts):

| Job | Tool (skill) | Real invocation |
| --- | --- | --- |
| Scrape — general web / news / market (default) | `parallel-web` | `python scripts/parallel_web.py search "<query>" --model base --json -o out.json` (deep: `research`; verify one URL: `extract "<url>" --full-content`). Needs `PARALLEL_API_KEY`. |
| Scrape — technical / academic / long-tail | `exa-search` | `uv run --with exa-py python scripts/exa_search.py "<query>" --num-results N --category "research paper" --text -o out.json`; batch URL pull: `exa_extract.py <url…> --text`. Needs `EXA_API_KEY`. |
| Single known URL / PDF | `WebFetch`, then `curl` for PDFs | Cheapest, no key, no rate limit. |
| Convert local PDF/HTML → MD | `markitdown` | `markitdown <file> -o <slug>-fulltext.md` — only when the scrape API did NOT already return clean text. |
| Ingest + format into vault | `turbovault` MCP | `mcp2cli --mcp http://turbovault:9004/sse write_note --args 'path=…' --args 'body=…'`; frontmatter via `frontmatter_set`. |
| Lint / organize corpus | `turbovault` MCP | `frontmatter_get`/`frontmatter_set`, `tag_list`/`tag_filter`, `link_graph`, `backlinks`. Full 47-tool list: `mcp2cli --mcp http://turbovault:9004/sse --list`. |
| Ontology over corpus | `infranodus` MCP | `mcp2cli --mcp http://infranodus-mcp:9005/sse generate_knowledge_graph …`. Local OSS engine; no per-request fees. |

- **Do not** scrape directly with `requests` / `httpx` — route through `parallel-web`
  or `exa-search` so results stay saved + citable.
- **Do not** call `infranodus.com` — the local engine is pinned (user memory
  `project_infranodus_local_only.md`).
- If a scrape key is missing or a gateway is unreachable, degrade **explicitly**:
  announce it, then fall back to `WebFetch` + `curl` + local `markitdown` CLI, and
  write notes with plain `Write` if turbovault is down. Never silently bypass.

## Pipeline overview

```
INPUT (topic | source-list | search-query)
  └─ 1 DISPATCH   → split work across N parallel agents (default 6)
  └─ 2 SCRAPE     → parallel_web.py / exa_search.py → WebFetch → curl → arxiv; save to _originals/
  └─ 3 CONVERT    → markitdown <file> -o <slug>-fulltext.md (only if scrape API gave no clean text)
  └─ 4 INGEST     → turbovault write_note: <slug>.md frontmatter + VERBATIM abstract + why-it-matters
  └─ 5 WIKILINKS  → name→slug index, replace bare citations, resolution-rate check (turbovault link_graph)
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

- **Primary tools** — `parallel-web` skill (`parallel_web.py search|research|extract`,
  needs `PARALLEL_API_KEY`), `exa-search` skill (`exa_search.py` / `exa_extract.py` via
  `uv run --with exa-py`, needs `EXA_API_KEY`; best for technical/academic long-tail),
  `markitdown` skill / Microsoft markitdown CLI (file → MD), `turbovault` skill (vault
  write/format/lint/organize + backlinks), `infranodus` skill (local OSS knowledge
  graph), `neuro-harness` skill (gateway endpoint registry — canonical), `forge` skill
  (slash-command router over the gateway).
- **Fallbacks** — `WebFetch`/`WebSearch` built-ins, `curl` (PDF download), `pandoc`
  (HTML→MD when markitdown empty), `pdfplumber`/`pdftotext` (image-based PDFs),
  GNU `wget --mirror` (whole-site harvests, not default), `scrapy` (production crawls).
- **Sibling skills** — `scrape-ingest-organize` (the lighter `/forge`-composition
  flavor: fan-out search → `00-raw/` inbox → turbovault auto-tag → infranodus; use it
  for quick dumps, this skill for the deep per-source corpus), `infranodus` /
  `infranodus-cli` (ontology pass), `markitdown`, `turbovault`, `parallel-web`,
  `exa-search`.
- **Canonical worked output** —
  `$HOME/Vaults/neuro-quant-vault/__raw/microstructure-papers/INDEX.md`
  (108 papers, 97% wikilink resolution). `$HOME/Vaults/CLAUDE.md` — vault
  conventions (layout + YAML frontmatter schema).
- **Last cross-checked:** 2026-07-02 (parallel-web `parallel_web.py` and exa-search
  `exa_search.py`/`exa_extract.py` CLIs verified against their skill scripts;
  turbovault tool set verified against `forge/references/server-registry.md`;
  markitdown flags via Context7 `/microsoft/markitdown`).
