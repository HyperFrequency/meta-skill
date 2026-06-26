---
name: web-scrape-ingest
description: >
  End-to-end pipeline that turns a topic, URL list, or search query into a curated
  vault of OFM (Obsidian-flavored Markdown) notes with raw originals preserved,
  metadata frontmatter, wikilinks wiring related items together, an InfraNodus
  ontology over the corpus, and a generated INDEX.md. Use whenever the user says
  "scrape and ingest", "build a vault from these URLs", "research pipeline", "do my
  research on X and put it in my notes", "ingest papers into Obsidian", "build me a
  knowledge base from these papers", "harvest documentation for", "rip these
  sources into the vault", or any phrasing that implies "go fetch this content and
  turn it into structured knowledge in my vault". Routes through the unified
  mcp2cli gateway (parallel-web, exa-mcp, turbovault, infranodus, markitdown).
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, WebFetch, WebSearch
license: HyperFrequency original
---

# /web-scrape-ingest

End-to-end research-ingest pipeline. Given a topic, a list of URLs/DOIs, or a search
query, this skill produces a curated `__raw/<topic>/` tree inside the vault with:

1. Raw originals preserved in `_originals/` (PDF, HTML).
2. Converted full-text Markdown alongside (one `<slug>-fulltext.md` per source).
3. Per-source metadata notes (`<slug>.md`) with YAML frontmatter, verbatim
   abstract, why-it-matters paragraph, and `[[wikilinks]]` to related items.
4. An InfraNodus ontology (`_ontology.md`, `_clusters.md`) generated over the
   converted corpus.
5. A generated `INDEX.md` grouped by cluster.

## When to use

Trigger this skill on any of these scenarios:

1. **Research literature scrape** — "scrape the canonical market microstructure
   papers into my vault". The pipeline produces a tree like
   `__raw/microstructure-papers/` with one note per paper, cross-linked, plus
   ontology + INDEX. The 2026-05-20 microstructure run is the canonical example
   (108 papers, 6 parallel agents, ~97% wikilink resolution).
2. **News ingestion** — "ingest the last 50 articles about <topic> into the vault
   so I can review them". Same pipeline; the metadata notes carry publication
   date and source instead of DOI.
3. **Documentation harvest** — "rip the Nautilus Trader v1.227 docs into my
   notes". Source list is the doc-site sitemap; the converted MD becomes the
   per-page note.
4. **Competitor / market analysis dump** — "harvest 30 product pages from
   competitor X.com and structure them as notes". The ontology pass highlights
   feature clusters and gaps.
5. **Paper + GitHub repo cross-ingest** — "scrape this arXiv paper and its
   companion repo's README, link them together". Multi-source-type variant; the
   wikilink pass treats the paper's slug and the repo's slug as a pair.
6. **DOI / arXiv batch** — "here are 40 DOIs, build me a vault". Bypasses search;
   goes straight to direct download.

If the user wants a single-URL fetch with no vault wiring, use `parallel-web`
extract directly or `WebFetch` — this skill is overkill for one URL.

## The required tooling — unified gateway contract

When operating, **always** route through the unified mcp2cli gateway. See the
`neuro-harness` skill in `neuro-quant-agent-skills/neuro-base/` for the
full endpoint table. Concretely:

| Phase | Use | Why |
| --- | --- | --- |
| Search (default) | `mcp2cli parallel-web search` or the `parallel-web` skill | Synthesized summaries + citations + integrated extract API |
| Search (alt, long-tail technical) | `mcp2cli exa search` if installed | Better at code/docs; needs `EXA_API_KEY` |
| Single-URL fetch | `WebFetch` first, then `curl` for PDFs | Cheapest, no rate limit |
| Convert PDF/HTML → MD | `markitdown <file> -o <out>` (the `markitdown` skill) | Token-efficient, preserves structure |
| Vault writes | `mcp2cli turbovault write_note` (the `turbovault` skill) | Honors vault conventions, updates link graph |
| Ontology over corpus | `mcp2cli infranodus generate_knowledge_graph` (the `infranodus` skill) | Local OSS engine; no per-request fees |

**Do not** scrape directly with `requests` / `httpx` when a gateway route exists.
**Do not** call `infranodus.com` — the local engine is pinned (see
`project_infranodus_local_only.md` in user memory).

If the gateway is unreachable (no compose stack), degrade explicitly: announce
the degradation, then fall back to `WebFetch` + `curl` + local `markitdown` CLI.
Never silently bypass.

## Pipeline overview

```
INPUT
  ├─ topic        (e.g. "market microstructure papers")
  ├─ source-list  (URLs or DOIs)
  └─ search-query (parallel-web or Exa)
       │
       ▼
PHASE 1 — DISPATCH        split work across N parallel agents (default 6)
       │
       ▼
PHASE 2 — FETCH           parallel-web → Exa → WebFetch → curl → arxiv
       │                  save raw to __raw/<topic>/_originals/<slug>.{pdf,html}
       ▼
PHASE 3 — CONVERT         markitdown <file> -o <slug>-fulltext.md
       │                  fallback: pandoc (HTML), pdfplumber (PDF)
       ▼
PHASE 4 — METADATA NOTE   write <slug>.md with YAML frontmatter,
       │                  verbatim abstract, why-it-matters, links
       ▼
PHASE 5 — WIKILINKS       name→slug index, replace bare citations,
       │                  resolution-rate check
       ▼
PHASE 6 — INFRANODUS      generate_knowledge_graph over the corpus,
       │                  save _ontology.md and _clusters.md
       ▼
PHASE 7 — INDEX           INDEX.md grouped by cluster + stats
```

Each phase is idempotent — re-running on an existing tree is a merge, not a
clobber. Slugs are the join key.

## Phase 1 — DISPATCH

Decide how to split the work. Default = 6 parallel sub-agents; the cost/time
tradeoff is roughly linear up to ~8 agents, then diminishing because of
upstream API rate limits.

1. Resolve the source list. Three paths:
   - **explicit URL/DOI list provided** → skip to dispatch
   - **topic only** → run `mcp2cli parallel-web search "<topic> seminal papers"`
     (or equivalent for non-academic topics), curate the result, ask the user
     to confirm before fetching
   - **search-query provided** → run search, treat top N hits as the source list
2. Pre-generate slugs deterministically:
   `<first-author-lastname>-<year>-<short-title>` for papers,
   `<domain>-<path-slug>` for non-paper URLs. The slug is the join key for every
   later phase. Lowercase, kebab-case, no punctuation, ASCII only.
3. Partition the slug list into N disjoint chunks (`chunk_0.txt` ... `chunk_N-1.txt`)
   inside `__raw/<topic>/_dispatch/`. Each agent operates only on its chunk to
   avoid write collisions in phase 4.
4. Spawn N `Agent` sub-tasks, each given:
   - the chunk file path
   - the topic directory path
   - the gateway endpoint table
   - the explicit phase-2 through phase-4 instructions (this file)
   - a hard rule: "you write only to files matching your slug list"

Backend choice for the dispatch search: **parallel-web by default**. Exa only
when the user is searching long-tail technical content (specific lib versions,
niche GitHub repos) and `EXA_API_KEY` is configured. WebFetch when a single
known URL is enough.

## Phase 2 — FETCH

Per agent, per item, try in this order. **Stop at the first success.**

1. **parallel-web search + extract** (default).
   ```bash
   mcp2cli parallel-web search --query "<title> <first-author> <year>" --format json
   # then for the chosen URL:
   mcp2cli parallel-web extract --url "<canonical-url>" --format markdown
   ```
   Save extract output to `_originals/<slug>.html` (preserve as HTML even if the
   API returns markdown — phase 3 will re-convert).
2. **Exa search + contents** (alt).
   ```bash
   mcp2cli exa search --query "..." --num-results 5
   mcp2cli exa contents --ids <result-id>
   ```
3. **WebFetch on the canonical URL.** For known landing pages where the publisher
   reliably serves the PDF behind a redirect.
4. **Direct curl** for PDFs. The publisher URL often returns the abstract page,
   not the PDF — *anti-pattern: this was the failure mode of the 2026-05-20 run*.
   Always prefer the open-access PDF URL.
   ```bash
   curl -L --max-time 30 -o "_originals/<slug>.pdf" \
        -H "User-Agent: Mozilla/5.0" \
        "<pdf-url>"
   file "_originals/<slug>.pdf"  # verify it's actually a PDF, not HTML
   ```
5. **arXiv direct** for arXiv IDs. Normalize the ID first (see common pitfalls).
   ```bash
   curl -L -o "_originals/<slug>.pdf" \
        "https://arxiv.org/pdf/<arxiv-id>.pdf"
   # HTML rendering is also available for newer papers:
   curl -L -o "_originals/<slug>.html" \
        "https://arxiv.org/html/<arxiv-id>"
   ```
6. **SSRN / NBER / BIS / SEC** — most have direct PDF endpoints but rate-limit
   aggressively. Add `sleep 1` between hits per source and respect any 429.
   SSRN abstract pages without preprints are common — record the abstract as
   stub-only and *do not* hallucinate a body.

**Paywall handling:** if every endpoint returns paywalled HTML, do not fabricate
content. Save the metadata only and set `verified: stub` in the frontmatter so
later phases know to skip phase-3 conversion.

**File-name discipline:** `_originals/<slug>.<ext>` exactly. No spaces, no
re-encoded titles. The slug is what links phase 2 to phase 3.

## Phase 3 — CONVERT

For each file in `_originals/`, convert to Markdown.

```bash
markitdown "_originals/<slug>.pdf" -o "<slug>-fulltext.md"
# Or for HTML:
markitdown "_originals/<slug>.html" -o "<slug>-fulltext.md"
```

CLI flag reference (verified via Context7 against `/microsoft/markitdown`,
2026-05-24):

- `-o <path>` — output file (preferred over shell redirect for whitespace safety)
- `-x <.ext>` — force file-type hint when piping
- `-m <mime>` — MIME hint
- `-c <charset>` — charset hint for text files
- `--keep-data-uris` — keep base64 data URIs in HTML output (default: truncate)

**Fallback chain** if `markitdown` produces empty or garbled output:

1. **pandoc** for HTML:
   `pandoc -f html -t gfm "_originals/<slug>.html" -o "<slug>-fulltext.md"`
2. **pdfplumber** for PDF (Python):
   ```python
   import pdfplumber
   with pdfplumber.open("_originals/<slug>.pdf") as pdf:
       text = "\n\n".join(p.extract_text() or "" for p in pdf.pages)
   open("<slug>-fulltext.md", "w").write(text)
   ```
3. **PyMuPDF / fitz** for scanned PDFs that need OCR — only if the PDF is
   image-based; `markitdown` already handles text PDFs well.

**Quality check** before considering phase 3 done:

- byte size > 500 (anything smaller is almost certainly empty or error HTML)
- contains the paper title or some recognizable token from the search hit
- no runs of `\x00` or non-UTF8 garbage
- if PDF: page count from `pdfinfo` matches expected (sanity)

Flag any failures in `_dispatch/conversion-failures.txt` rather than silently
proceeding.

**TurboVault is the destination for the metadata MD (phase 4), not the
converter.** TurboVault has 47 vault-write tools but no PDF/HTML→MD tools.
Don't confuse the layers.

## Phase 4 — METADATA NOTE

For each item, write `<slug>.md` (the metadata note, separate from
`<slug>-fulltext.md`). Use this YAML frontmatter spec — derived from the
microstructure-papers cluster format:

```yaml
---
title: "..."                    # verbatim from source
authors: ["Last, First", "..."]  # one entry per author, "Last, First"
year: 2024
venue: "Journal Name"            # or "arXiv preprint" / "Working paper" / website name
volume: "12(3)"                  # optional
doi: "10.xxxx/..."               # null if none
arxiv: "2401.12345"              # null if none, ID only no version unless versioning matters
ssrn: null
nber: null
url: "<best canonical URL>"
pdf_url: "<direct PDF URL>"      # null if no open-access PDF exists
topics: [topic-1, topic-2, ...]  # kebab-case, 3-8 tags
cluster: "<assigned cluster>"    # set in phase 6 via InfraNodus; placeholder ok at first
verified: 2026-05-24             # ISO date; "stub" if paywalled
---
```

Body sections (in this order):

```markdown
# {Title}

**Authors:** ... &nbsp; **Year:** {year} &nbsp; **Venue:** {venue}, {citation}

## Abstract

{VERBATIM abstract — no paraphrase, no truncation. If the source has none,
write "No abstract available." Do not invent one.}

## Why it matters (one paragraph)

{Free-form, but precise. 3-6 sentences. State what the paper / source
*contributes*, not just what it covers. Tie it to the user's research context
if known.}

## Related (in this collection)

- [[other-slug-1]]
- [[other-slug-2]]
{Filled in phase 5. Initially blank.}

## Links

- [PDF]({pdf_url})
- DOI: {doi}
- [Full text]({slug}-fulltext.md)
```

**The verbatim-abstract rule is non-negotiable.** Hallucinated abstracts poison
the corpus for the phase-6 ontology pass. If parallel-web's extract gave you a
synthesized summary, *do not paste it as the abstract* — re-fetch the source
page or set the abstract to "No abstract available."

**Why-it-matters rule:** the bar is a senior researcher should learn something
they couldn't from the abstract alone. State the contribution, the lineage
(what it descends from), and the practical hook (why a working quant /
researcher would care). 3-6 sentences. No bullet lists.

## Phase 5 — WIKILINKS

After all metadata notes exist, do one pass over the corpus to wire them
together.

1. **Build the name→slug index.** Walk every `<slug>.md`, parse the YAML
   `authors` and `year`, and emit a dict:
   ```
   "Cont, Kukanov, Stoikov 2014" → "cont-kukanov-stoikov-2014-ofi"
   "Almgren & Chriss 2001"        → "almgren-chriss-2001-optimal-execution"
   ```
   Include common alias forms: full-name, last-name-only, et-al, first-author-only.
2. **Alias-fix pass.** Read each note's body. Replace bare citations matching
   the index with `[[slug]]` (or `[[slug|display label]]` if the original text
   should be preserved). Order matters — substitute longest matches first to
   avoid partial overwrites.
3. **Cross-reference fill.** For each note, populate the `## Related (in this
   collection)` section with up to 5 wikilinks chosen by topic-tag overlap
   (Jaccard on the `topics:` frontmatter is a good first cut). For papers, also
   include canonical lineage links (e.g. anything that cites the source as
   foundational).
4. **Resolution-rate check.** Count the wikilinks that resolve to an existing
   `<slug>.md` vs. those that don't. The 2026-05-20 microstructure run hit 97%
   (101/104). Below 90% means too many stub references — either add the missing
   papers in a follow-up batch or convert them to plain-text citations.
5. **Collision audit.** Two papers with the same first-author + year is the
   main hazard. The dispatcher should have caught it in phase 1, but verify:
   `ls __raw/<topic>/*.md | awk -F'-' '{print $1"-"$2"-"$3}' | sort | uniq -c | awk '$1 > 1'`
   If any duplicates emerge, decide a disambiguator (next-author-name or
   short-title) and rename consistently in both the file and every wikilink.

## Phase 6 — InfraNodus ontology

Generate the topical ontology over the corpus. The local OSS engine is fully
offline — no per-request fees, no infranodus.com calls.

```bash
# Concatenate the metadata notes (abstract + why-it-matters carry the signal;
# fulltext is too noisy for the OSS engine's topic-extraction).
cat __raw/<topic>/*.md | grep -v "^---$" > /tmp/corpus.txt

# Generate the graph:
mcp2cli infranodus generate_knowledge_graph --text "$(cat /tmp/corpus.txt)"

# Or topical clusters only (lighter, often enough):
mcp2cli infranodus generate_topical_clusters --text "$(cat /tmp/corpus.txt)"

# Optional: find gaps in the corpus (research-question generator).
mcp2cli infranodus generate_content_gaps --text "$(cat /tmp/corpus.txt)"
```

**Output format.** Save the InfraNodus response (JSON or markdown depending on
mcp2cli's current shape — check `--help`) to two files:

- `__raw/<topic>/_ontology.md` — full graph (nodes + edges + cluster
  assignments), pretty-printed in `[[wikilink]]` syntax so Obsidian's graph
  view renders the topical structure overlaid on the paper graph.
- `__raw/<topic>/_clusters.md` — the cluster summary alone (cluster name +
  member slugs + a one-line description). Use this as the spine for phase 7's
  INDEX.

**Back-fill `cluster:` in frontmatter.** For each slug, look up which cluster
it landed in and update the `cluster:` field of its `<slug>.md`. This is what
lets phase 7 group the INDEX cleanly.

**Tool naming (verified 2026-05-24 against upstream `infranodus/skills/infranodus-cli/SKILL.md`).** The tool names above (`generate_knowledge_graph`, `generate_topical_clusters`, `generate_content_gaps`) are canonical in the upstream skill. The full upstream tool list is:

`analyze_existing_graph_by_name`, `analyze_google_search_results`, `analyze_related_search_queries`, `analyze_text`, `create_knowledge_graph`, `develop_conceptual_bridges`, `develop_latent_topics`, `develop_text_tool`, `generate_content_gaps`, `generate_contextual_hint`, `generate_difference_graph_from_text`, `generate_knowledge_graph`, `generate_overlap_from_texts`, `generate_research_ideas`, `generate_research_questions`, `generate_seo_report`, `generate_topical_clusters`, `list_graphs`, `memory_add_relations`, `memory_get_relations`, `merged_graph_from_texts`.

If the local OSS engine has drifted from upstream (some AI-dependent tools like `generate_research_ideas` degrade gracefully because the OSS engine lags the SaaS), `mcp2cli infranodus --list` is authoritative.

## Phase 7 — INDEX

Generate `__raw/<topic>/INDEX.md` from the (now cluster-tagged) metadata notes.
Template:

```markdown
# {Topic} — Curated Collection

{N} verified items scraped {date} by {N} parallel agents. Each note has YAML
frontmatter (title, authors, year, venue, DOI / arXiv / SSRN, URL, topics,
cluster, verified date) plus a verbatim abstract and `[[wikilinks]]` to related
items in this collection. Wikilink resolution: {resolved}/{total} ({pct}%).

## Stats by cluster

- **{cluster-1}** — {count} items
- **{cluster-2}** — {count} items
- **{cluster-3}** — {count} items
- ...

## By cluster

### {cluster-1}

- [[{slug}]] · {year} · *{venue}* — {title}
- ...

### {cluster-2}

- ...

## All items (alphabetical by slug)

- [[{slug}]] · {year} · *{venue}* — {title}
- ...
```

The "All items" tail is the redundant flat index — keep it; it's what users
hit when they're searching by slug instead of cluster.

## Parallel-agent orchestration

The pipeline assumes N parallel agents in phase 2-4. **Default N=6.**

- **Cost / time tradeoff:** with N=1, 100 papers takes ~25 min of fetch+convert
  on a fast link. With N=6, ~5 min. With N=12, ~4 min — upstream APIs start
  rate-limiting and the wall-clock saving is gone.
- **Disjoint slug assignment:** the dispatcher writes `_dispatch/chunk_<i>.txt`
  files. Each agent is told "you may write only to files whose slug appears in
  your chunk". Enforces no-collision by construction.
- **Reconciliation pass:** after all agents complete, the parent (this skill)
  runs the slug-collision audit from phase 5.5 and the wikilink pass over the
  union. Agents do *not* run phase 5 themselves — that requires the global
  index.
- **Failure isolation:** if one agent fails (network timeout, malformed
  response), the others continue. The parent retries the failed chunk after
  the others finish, with a fresh agent.

## Choosing the search backend

| Use case | Backend | Why |
| --- | --- | --- |
| Academic papers + open web | parallel-web | Default. Good for both, has extract API. |
| Targeted code/docs search | Exa | Better at long-tail technical content. Needs `EXA_API_KEY`. |
| Single known URL | WebFetch | Cheapest, no rate limit. |
| Known DOI / arXiv ID | direct curl + arxiv API | Free, fast, deterministic. |
| Mixed (paper + Github + docs) | parallel-web with multiple queries | One backend keeps citations consistent. |

When in doubt: parallel-web. The 6-agent dispatch hides any per-request latency.

## Anti-patterns

- **DON'T** grab the abstract page when the full PDF is openly available. This
  was the failure mode of the 2026-05-20 microstructure scrape — every note
  initially had publisher landing pages instead of paper content. The fix:
  phase-2 step 4 (direct curl on `pdf_url`) before falling back to the
  publisher URL.
- **DON'T** fabricate citations. Author + year + venue + working link minimum,
  and verify each via parallel-web or perplexity-search. The verbatim-abstract
  rule (phase 4) exists specifically to block this failure mode.
- **DON'T** overwrite a vault note silently. Phase 4 must `read_note` first; if
  the slug exists and the frontmatter differs, merge — never clobber. Flag
  conflicts in `_dispatch/merge-conflicts.txt`.
- **DON'T** let two parallel agents touch the same slug. The dispatcher must
  assign disjoint slug sets up front (phase 1 step 3). If you skip the
  pre-partition, you will get half-merged notes and corrupt YAML.
- **DON'T** skip the InfraNodus ontology pass. Phase 6 is what turns a flat
  document dump into a graph the user can browse. Without `cluster:`, INDEX.md
  is a flat list and the Obsidian graph view shows a hairball.
- **DON'T** expose the vault directly to ngrok or any public tunnel for
  Obsidian sync. Use CouchDB + LiveSync — see the `neuro-harness` skill or
  `docs/obsidian-livesync.md`.
- **DON'T** paraphrase the abstract. Verbatim or "No abstract available." —
  no third option.
- **DON'T** call `infranodus.com`. The local pin (see user memory
  `project_infranodus_local_only.md`) means the user pays per request when the
  pin is broken. Always use the gateway, which routes to the local engine.

## End-to-end example (worked)

Reproduces the 2026-05-20 microstructure-papers run. Approximate timing on a
fast link with N=6 agents: ~7 minutes wall-clock for 108 papers.

```text
User: "Scrape the canonical market microstructure papers into my vault."

# Phase 1 — DISPATCH
- Topic resolved: "market-microstructure-papers"
- Source list: 110 candidate papers from parallel-web search +
  curated extras (Kyle, Almgren-Chriss, VPIN, Hawkes, OFI lineage).
- Slugs pre-generated:
    kyle-1985-continuous-auctions
    almgren-chriss-2001-optimal-execution
    cont-kukanov-stoikov-2014-ofi
    ... (108 total)
- Chunked into 6 files of ~18 slugs each, written to
    __raw/market-microstructure-papers/_dispatch/chunk_{0..5}.txt
- 6 sub-agents spawned, each given its chunk + the gateway endpoint table.

# Phase 2 — FETCH (per agent, parallel)
- Agent 0 handles chunk_0 (kyle-1985 ... cont-stoikov-talreja-2010):
    for slug in chunk_0:
      parallel-web search "<title> <author> <year>"
      curl -L the pdf_url → _originals/<slug>.pdf
      verify with `file` and pdfinfo
- Agents 1-5: same on their chunks.
- 2 paywalled (JSTOR, Elsevier) → marked verified: stub.

# Phase 3 — CONVERT (per agent, parallel)
- markitdown _originals/<slug>.pdf -o <slug>-fulltext.md
- pdfplumber fallback for 3 image-based PDFs.
- Quality check: 106/108 pass byte-size + token-presence checks.

# Phase 4 — METADATA NOTE (per agent, parallel)
- 108 notes written under __raw/market-microstructure-papers/
- YAML frontmatter populated from search + arXiv API + Crossref DOI lookup.
- Verbatim abstract pulled from arXiv abstract page / publisher abstract.

# Phase 5 — WIKILINKS (parent, single pass)
- name→slug index built (158 unique name forms).
- Alias-fix pass: 4,210 substitutions across 108 notes.
- Related-fill: ~4 wikilinks per note on average.
- Resolution rate: 101/104 = 97%. (3 stubs for papers outside this batch.)

# Phase 6 — INFRANODUS (parent)
- generate_topical_clusters over concatenated abstract+why-matters.
- 6 clusters emerged:
    - "OFI + Kyle + price impact" — 10 papers
    - "Spreads + market making" — 15 papers
    - "VPIN + informed trading" — 17 papers
    - "Hawkes processes in finance" — 18 papers
    - "hft-market-quality-regulation" — 17 papers
    - "microstructure-papers" (residual) — 31 papers
- Back-filled cluster: in 108 frontmatters.

# Phase 7 — INDEX
- INDEX.md generated with cluster sections + flat alphabetical tail.
- Total wall-clock: ~7 minutes.
```

The output tree for that run lives at
`$HOME/Vaults/neuro-quant-vault/__raw/microstructure-papers/` —
use it as the canonical layout reference.

## Common pitfalls

1. **arXiv ID format.** New format is `YYMM.NNNNN[vN]`, old format is
   `<archive>/YYMMNNN`. The PDF URL needs the bare ID without `v<N>` unless you
   want a specific version. Normalize before phase 2:
   `python -c "import re; s='2401.12345v3'; print(re.sub(r'v\d+$', '', s))"`
2. **Slug collisions on same-year same-author.** Two Bouchaud 2009 papers, two
   Brogaard et al 2014 papers, etc. The slug template
   `<author>-<year>-<short-title>` mostly handles this — but only if the
   short-title field is set thoughtfully. Use a 3-4 word descriptor of the
   paper's main contribution, not the full title.
3. **SSRN abstract pages without preprints.** Common for Working-Paper-Series
   entries. The SSRN landing page is HTML with abstract but no PDF. Mark
   `verified: stub` and `pdf_url: null`; do not fabricate the body.
4. **JSTOR paywall on classic 1985 / 1995 / 2002 papers.** Most have unofficial
   author-hosted mirrors — search for `"<title>" filetype:pdf` via
   parallel-web. Cite the mirror as `pdf_url` and the JSTOR DOI as canonical.
5. **CouchDB attachment size limits if you store PDFs in the LiveSync.** Default
   limit is ~50 MB per attachment. Store PDFs in `_originals/` (outside the
   vault folder tree synced by LiveSync) or bump the CouchDB limit. See
   `docs/obsidian-livesync.md`.
6. **`markitdown` returns empty on protected PDFs.** Some publisher PDFs have
   copy-protection that defeats markitdown's text extraction. Fall through to
   `pdfplumber` or `pdftotext` (poppler) before giving up.
7. **`infranodus` OSS engine drift.** The OSS release is older than the SaaS,
   so AI-dependent tools (`generate_research_ideas`,
   `generate_research_questions`) degrade gracefully but unevenly. Stick to
   `generate_knowledge_graph` + `generate_topical_clusters` for reliable
   cluster output; mark anything else as "best-effort".

## References

- **Primary tools**
  - `parallel-web` skill — search + extract via Parallel Chat API
  - Exa MCP — alt search backend (long-tail technical)
  - `markitdown` skill / Microsoft markitdown CLI — file → MD conversion
  - `turbovault` skill — vault write/search/backlinks operations
  - `infranodus` skill — local OSS knowledge-graph engine
  - `neuro-harness` skill — gateway endpoint registry (canonical reference)
  - `forge` skill — slash-command router over the gateway
- **Adjacent / fallback**
  - `WebFetch` and `WebSearch` built-in tools
  - `curl` for direct PDF download
  - `pandoc` for HTML → MD fallback (when markitdown empty)
  - `pdfplumber`, `pdftotext` (poppler) for image-based PDFs
  - GNU `wget` with `--mirror` for whole-site harvests (not the default path)
  - `scrapy` for production-scale crawls with structured pipelines
  - MoneyPrinterTurbo's scraper for video/transcript ingest (different domain)
- **Tutorials & references**
  - `$HOME/Vaults/neuro-quant-vault/__raw/microstructure-papers/INDEX.md`
    — canonical worked output (108 papers, 97% wikilink resolution)
  - `$HOME/Vaults/CLAUDE.md` — vault conventions (`neuro-link-recursive`
    layout, YAML frontmatter schema)
  - microsoft/markitdown README — CLI flag reference (verified via Context7)
  - `scrape-ingest-organize` skill — slash-command flavor of this same
    pipeline; new work should call `/web-scrape-ingest` directly
- **Last cross-checked:** 2026-05-24 (markitdown CLI flags verified via
  Context7 `/microsoft/markitdown`; gateway endpoints verified against
  `neuro-harness` skill)
