# Pipeline phases — detailed instructions

The pipeline is 7 phases. Each phase is **idempotent** — re-running on an existing
tree is a merge, not a clobber. **Slugs are the join key** for every phase.

```
INPUT (topic | source-list | search-query)
  └─ PHASE 1 DISPATCH   → split work across N parallel agents (default 6)
  └─ PHASE 2 FETCH      → parallel-web → Exa → WebFetch → curl → arxiv
  └─ PHASE 3 CONVERT    → markitdown <file> -o <slug>-fulltext.md
  └─ PHASE 4 METADATA   → <slug>.md: frontmatter + verbatim abstract + why-matters
  └─ PHASE 5 WIKILINKS  → name→slug index, replace bare citations, resolution check
  └─ PHASE 6 INFRANODUS → generate_knowledge_graph, save _ontology.md + _clusters.md
  └─ PHASE 7 INDEX      → INDEX.md grouped by cluster + stats
```

## Phase 1 — DISPATCH

Default = 6 parallel sub-agents. Cost/time is roughly linear up to ~8 agents,
then diminishing because of upstream API rate limits.

1. Resolve the source list. Three paths:
   - **explicit URL/DOI list provided** → skip to dispatch
   - **topic only** → run `mcp2cli parallel-web search "<topic> seminal papers"`,
     curate, ask the user to confirm before fetching
   - **search-query provided** → run search, treat top N hits as the source list
2. Pre-generate slugs deterministically:
   `<first-author-lastname>-<year>-<short-title>` for papers,
   `<domain>-<path-slug>` for non-paper URLs. Lowercase, kebab-case, no
   punctuation, ASCII only. The slug is the join key for every later phase.
3. Partition the slug list into N disjoint chunks (`chunk_0.txt` ... `chunk_N-1.txt`)
   inside `__raw/<topic>/_dispatch/`. Each agent operates only on its chunk to
   avoid write collisions in phase 4.
4. Spawn N `Agent` sub-tasks, each given: the chunk file path, the topic directory
   path, the gateway endpoint table, the explicit phase-2 through phase-4
   instructions, and a hard rule: "you write only to files matching your slug list".

Backend for the dispatch search: **parallel-web by default**. Exa only for
long-tail technical content (specific lib versions, niche GitHub repos) when
`EXA_API_KEY` is configured. WebFetch when a single known URL is enough.

## Phase 2 — FETCH

Per agent, per item, try in this order. **Stop at the first success.**

1. **parallel-web search + extract** (default).
   ```bash
   mcp2cli parallel-web search --query "<title> <first-author> <year>" --format json
   mcp2cli parallel-web extract --url "<canonical-url>" --format markdown
   ```
   Save extract output to `_originals/<slug>.html` (preserve as HTML even if the
   API returns markdown — phase 3 will re-convert).
2. **Exa search + contents** (alt).
   ```bash
   mcp2cli exa search --query "..." --num-results 5
   mcp2cli exa contents --ids <result-id>
   ```
3. **WebFetch on the canonical URL.** For landing pages that reliably serve the
   PDF behind a redirect.
4. **Direct curl** for PDFs. The publisher URL often returns the abstract page,
   not the PDF — *anti-pattern: the failure mode of the 2026-05-20 run.* Always
   prefer the open-access PDF URL.
   ```bash
   curl -L --max-time 30 -o "_originals/<slug>.pdf" \
        -H "User-Agent: Mozilla/5.0" "<pdf-url>"
   file "_originals/<slug>.pdf"  # verify it's actually a PDF, not HTML
   ```
5. **arXiv direct** for arXiv IDs. Normalize the ID first (see pitfalls).
   ```bash
   curl -L -o "_originals/<slug>.pdf" "https://arxiv.org/pdf/<arxiv-id>.pdf"
   curl -L -o "_originals/<slug>.html" "https://arxiv.org/html/<arxiv-id>"  # newer papers
   ```
6. **SSRN / NBER / BIS / SEC** — direct PDF endpoints exist but rate-limit hard.
   Add `sleep 1` between hits per source and respect any 429. SSRN abstract pages
   without preprints are common — record the abstract as stub-only and *do not*
   hallucinate a body.

**Paywall handling:** if every endpoint returns paywalled HTML, do not fabricate
content. Save metadata only and set `verified: stub` in frontmatter so later
phases skip phase-3 conversion.

**File-name discipline:** `_originals/<slug>.<ext>` exactly. No spaces, no
re-encoded titles. The slug links phase 2 to phase 3.

## Phase 3 — CONVERT

For each file in `_originals/`, convert to Markdown.

```bash
markitdown "_originals/<slug>.pdf" -o "<slug>-fulltext.md"
markitdown "_originals/<slug>.html" -o "<slug>-fulltext.md"
```

CLI flag reference (verified via Context7 against `/microsoft/markitdown`, 2026-05-24):

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
3. **PyMuPDF / fitz** for scanned PDFs that need OCR — only if image-based;
   `markitdown` already handles text PDFs well.

**Quality check** before considering phase 3 done:

- byte size > 500 (anything smaller is almost certainly empty or error HTML)
- contains the paper title or a recognizable token from the search hit
- no runs of `\x00` or non-UTF8 garbage
- if PDF: page count from `pdfinfo` matches expected (sanity)

Flag failures in `_dispatch/conversion-failures.txt` rather than silently proceeding.

**TurboVault is the destination for the metadata MD (phase 4), not the converter.**
TurboVault has vault-write tools but no PDF/HTML→MD tools. Don't confuse the layers.

## Phase 4 — METADATA NOTE

For each item, write `<slug>.md` (the metadata note, separate from
`<slug>-fulltext.md`). YAML frontmatter spec — derived from the
microstructure-papers cluster format:

```yaml
---
title: "..."                     # verbatim from source
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

{Free-form, but precise. 3-6 sentences. State what the source *contributes*,
not just what it covers. Tie it to the user's research context if known.}

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
synthesized summary, *do not paste it as the abstract* — re-fetch the source page
or set the abstract to "No abstract available."

**Why-it-matters rule:** the bar is a senior researcher should learn something
they couldn't from the abstract alone. State the contribution, the lineage (what
it descends from), and the practical hook. 3-6 sentences. No bullet lists.

## Phase 5 — WIKILINKS

After all metadata notes exist, do one pass over the corpus to wire them together.

1. **Build the name→slug index.** Walk every `<slug>.md`, parse the YAML `authors`
   and `year`, and emit a dict:
   ```
   "Cont, Kukanov, Stoikov 2014" → "cont-kukanov-stoikov-2014-ofi"
   "Almgren & Chriss 2001"        → "almgren-chriss-2001-optimal-execution"
   ```
   Include alias forms: full-name, last-name-only, et-al, first-author-only.
2. **Alias-fix pass.** Read each note's body. Replace bare citations matching the
   index with `[[slug]]` (or `[[slug|display label]]` to preserve original text).
   Substitute longest matches first to avoid partial overwrites.
3. **Cross-reference fill.** For each note, populate `## Related (in this
   collection)` with up to 5 wikilinks chosen by topic-tag overlap (Jaccard on the
   `topics:` frontmatter is a good first cut). For papers, also include canonical
   lineage links.
4. **Resolution-rate check.** Count wikilinks that resolve to an existing
   `<slug>.md` vs. those that don't. The 2026-05-20 microstructure run hit 97%
   (101/104). Below 90% means too many stub references — add the missing papers in
   a follow-up batch or convert them to plain-text citations.
5. **Collision audit.** Two papers with the same first-author + year is the main
   hazard. The dispatcher should have caught it in phase 1, but verify:
   `ls __raw/<topic>/*.md | awk -F'-' '{print $1"-"$2"-"$3}' | sort | uniq -c | awk '$1 > 1'`
   If duplicates emerge, pick a disambiguator (next-author-name or short-title) and
   rename consistently in both the file and every wikilink.

## Phase 6 — InfraNodus ontology

Generate the topical ontology over the corpus. The local OSS engine is fully
offline — no per-request fees, no infranodus.com calls.

```bash
# Concatenate the metadata notes (abstract + why-it-matters carry the signal;
# fulltext is too noisy for the OSS engine's topic-extraction).
cat __raw/<topic>/*.md | grep -v "^---$" > /tmp/corpus.txt

mcp2cli infranodus generate_knowledge_graph --text "$(cat /tmp/corpus.txt)"
mcp2cli infranodus generate_topical_clusters --text "$(cat /tmp/corpus.txt)"  # lighter
mcp2cli infranodus generate_content_gaps --text "$(cat /tmp/corpus.txt)"      # optional
```

**Output format.** Save the InfraNodus response (JSON or markdown — check
`--help`) to two files:

- `__raw/<topic>/_ontology.md` — full graph (nodes + edges + cluster assignments),
  pretty-printed in `[[wikilink]]` syntax so Obsidian's graph view renders the
  topical structure overlaid on the paper graph.
- `__raw/<topic>/_clusters.md` — the cluster summary alone (cluster name + member
  slugs + a one-line description). Use as the spine for phase 7's INDEX.

**Back-fill `cluster:` in frontmatter.** For each slug, look up which cluster it
landed in and update the `cluster:` field of its `<slug>.md`. This lets phase 7
group the INDEX cleanly.

**Tool naming** (verified 2026-05-24 against upstream
`infranodus/skills/infranodus-cli/SKILL.md`). The tool names above are canonical.
Full upstream tool list:

`analyze_existing_graph_by_name`, `analyze_google_search_results`,
`analyze_related_search_queries`, `analyze_text`, `create_knowledge_graph`,
`develop_conceptual_bridges`, `develop_latent_topics`, `develop_text_tool`,
`generate_content_gaps`, `generate_contextual_hint`,
`generate_difference_graph_from_text`, `generate_knowledge_graph`,
`generate_overlap_from_texts`, `generate_research_ideas`,
`generate_research_questions`, `generate_seo_report`, `generate_topical_clusters`,
`list_graphs`, `memory_add_relations`, `memory_get_relations`,
`merged_graph_from_texts`.

If the local OSS engine has drifted (some AI-dependent tools like
`generate_research_ideas` degrade gracefully because the OSS engine lags the SaaS),
`mcp2cli infranodus --list` is authoritative.

## Phase 7 — INDEX

Generate `__raw/<topic>/INDEX.md` from the (now cluster-tagged) metadata notes.

```markdown
# {Topic} — Curated Collection

{N} verified items scraped {date} by {N} parallel agents. Each note has YAML
frontmatter (title, authors, year, venue, DOI / arXiv / SSRN, URL, topics,
cluster, verified date) plus a verbatim abstract and `[[wikilinks]]` to related
items in this collection. Wikilink resolution: {resolved}/{total} ({pct}%).

## Stats by cluster

- **{cluster-1}** — {count} items
- ...

## By cluster

### {cluster-1}

- [[{slug}]] · {year} · *{venue}* — {title}
- ...

## All items (alphabetical by slug)

- [[{slug}]] · {year} · *{venue}* — {title}
- ...
```

The "All items" tail is the redundant flat index — keep it; it's what users hit
when searching by slug instead of cluster.
