# Orchestration, backend choice, anti-patterns, pitfalls

## Parallel-agent orchestration

The pipeline assumes N parallel agents in phases 2-4. **Default N=6.**

- **Cost / time tradeoff:** N=1, 100 papers ≈ 25 min fetch+convert on a fast link.
  N=6 ≈ 5 min. N=12 ≈ 4 min — upstream APIs start rate-limiting and the
  wall-clock saving is gone.
- **Disjoint slug assignment:** the dispatcher writes `_dispatch/chunk_<i>.txt`.
  Each agent is told "you may write only to files whose slug appears in your
  chunk." Enforces no-collision by construction.
- **Reconciliation pass:** after all agents complete, the parent (this skill) runs
  the slug-collision audit from phase 5 and the wikilink pass over the union.
  Agents do *not* run phase 5 — that requires the global index.
- **Failure isolation:** if one agent fails (timeout, malformed response), the
  others continue. The parent retries the failed chunk after the others finish,
  with a fresh agent.

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

- **DON'T** grab the abstract page when the full PDF is openly available. This was
  the failure mode of the 2026-05-20 microstructure scrape — every note initially
  had publisher landing pages instead of paper content. The fix: phase-2 step 4
  (direct curl on `pdf_url`) before falling back to the publisher URL.
- **DON'T** fabricate citations. Author + year + venue + working link minimum, and
  verify each via parallel-web or perplexity-search. The verbatim-abstract rule
  (phase 4) exists specifically to block this failure mode.
- **DON'T** overwrite a vault note silently. Phase 4 must `read_note` first; if the
  slug exists and frontmatter differs, merge — never clobber. Flag conflicts in
  `_dispatch/merge-conflicts.txt`.
- **DON'T** let two parallel agents touch the same slug. The dispatcher must assign
  disjoint slug sets up front (phase 1 step 3). Skip the pre-partition and you get
  half-merged notes and corrupt YAML.
- **DON'T** skip the InfraNodus ontology pass. Phase 6 turns a flat document dump
  into a browsable graph. Without `cluster:`, INDEX.md is a flat list and the
  Obsidian graph view shows a hairball.
- **DON'T** expose the vault directly to ngrok or any public tunnel for Obsidian
  sync. Use CouchDB + LiveSync — see the `neuro-harness` skill or
  `docs/obsidian-livesync.md`.
- **DON'T** paraphrase the abstract. Verbatim or "No abstract available." — no
  third option.
- **DON'T** call `infranodus.com`. The local pin (user memory
  `project_infranodus_local_only.md`) means the user pays per request when the pin
  is broken. Always use the gateway, which routes to the local engine.

## Common pitfalls

1. **arXiv ID format.** New format `YYMM.NNNNN[vN]`, old format `<archive>/YYMMNNN`.
   The PDF URL needs the bare ID without `v<N>` unless you want a specific version.
   Normalize before phase 2:
   `python -c "import re; s='2401.12345v3'; print(re.sub(r'v\d+$', '', s))"`
2. **Slug collisions on same-year same-author.** Two Bouchaud 2009 papers, etc.
   The template `<author>-<year>-<short-title>` handles this only if short-title is
   set thoughtfully. Use a 3-4 word descriptor of the main contribution, not the
   full title.
3. **SSRN abstract pages without preprints.** Common for Working-Paper-Series
   entries. Mark `verified: stub` and `pdf_url: null`; do not fabricate the body.
4. **JSTOR paywall on classic 1985 / 1995 / 2002 papers.** Most have unofficial
   author-hosted mirrors — search `"<title>" filetype:pdf` via parallel-web. Cite
   the mirror as `pdf_url` and the JSTOR DOI as canonical.
5. **CouchDB attachment size limits if you store PDFs in LiveSync.** Default ~50 MB
   per attachment. Store PDFs in `_originals/` (outside the synced vault folder
   tree) or bump the CouchDB limit. See `docs/obsidian-livesync.md`.
6. **`markitdown` returns empty on protected PDFs.** Some publisher PDFs have
   copy-protection that defeats text extraction. Fall through to `pdfplumber` or
   `pdftotext` (poppler) before giving up.
7. **`infranodus` OSS engine drift.** The OSS release is older than the SaaS, so
   AI-dependent tools (`generate_research_ideas`, `generate_research_questions`)
   degrade gracefully but unevenly. Stick to `generate_knowledge_graph` +
   `generate_topical_clusters` for reliable cluster output; mark anything else as
   "best-effort".

## End-to-end example (worked) — 2026-05-20 microstructure-papers run

Approximate timing on a fast link with N=6 agents: ~7 minutes wall-clock for 108 papers.

```text
User: "Scrape the canonical market microstructure papers into my vault."

# Phase 1 — DISPATCH
- Topic resolved: "market-microstructure-papers"
- Source list: 110 candidate papers from parallel-web search + curated extras
  (Kyle, Almgren-Chriss, VPIN, Hawkes, OFI lineage).
- Slugs pre-generated: kyle-1985-continuous-auctions,
  almgren-chriss-2001-optimal-execution, cont-kukanov-stoikov-2014-ofi, ... (108)
- Chunked into 6 files of ~18 slugs each →
  __raw/market-microstructure-papers/_dispatch/chunk_{0..5}.txt
- 6 sub-agents spawned, each given its chunk + the gateway endpoint table.

# Phase 2 — FETCH (per agent, parallel)
- parallel-web search "<title> <author> <year>"; curl -L pdf_url → _originals/<slug>.pdf
- verify with `file` and pdfinfo. 2 paywalled (JSTOR, Elsevier) → verified: stub.

# Phase 3 — CONVERT (per agent, parallel)
- markitdown _originals/<slug>.pdf -o <slug>-fulltext.md
- pdfplumber fallback for 3 image-based PDFs. Quality check: 106/108 pass.

# Phase 4 — METADATA NOTE (per agent, parallel)
- 108 notes written. Frontmatter from search + arXiv API + Crossref DOI lookup.
- Verbatim abstract from arXiv / publisher abstract page.

# Phase 5 — WIKILINKS (parent, single pass)
- name→slug index (158 unique name forms). 4,210 substitutions across 108 notes.
- ~4 wikilinks per note. Resolution: 101/104 = 97% (3 stubs outside this batch).

# Phase 6 — INFRANODUS (parent)
- generate_topical_clusters over concatenated abstract+why-matters. 6 clusters:
  OFI+Kyle+price impact (10), spreads+market making (15), VPIN+informed (17),
  Hawkes (18), hft-market-quality-regulation (17), residual (31).
- Back-filled cluster: in 108 frontmatters.

# Phase 7 — INDEX
- INDEX.md with cluster sections + flat alphabetical tail. ~7 min wall-clock.
```

Output tree: `$HOME/Vaults/neuro-quant-vault/__raw/microstructure-papers/` — use it
as the canonical layout reference.
