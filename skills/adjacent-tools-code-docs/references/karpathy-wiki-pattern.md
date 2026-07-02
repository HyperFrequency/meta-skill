# Karpathy LLM-Wiki pattern — full template + examples

The toolbox wiki follows the "LLM-Wiki" convention: a tool is documented as a
*directory of focused pages*, not one monolithic file. Each page is sized so an
LLM can hold it (and its neighbors) in context without truncation — roughly
1500 lines of logical content per page. Pages carry structured frontmatter so a
RAG indexer can rank, filter, and freshness-check them, and so contradictions
and open questions are first-class instead of buried.

## Directory layout

```
08-code-docs/toolbox/<tool>/
├── README.md                 # top-level index, links to every page
├── 01-architecture.md        # core concepts, design, data flow
├── 02-api-reference.md       # public API surface
├── 03-configuration.md       # env vars, config files, flags
├── 04-integration.md         # how the tool is wired into our codebases
└── 05-changelog-watch.md     # version history + breaking changes to track
```

A large tool may need 10+ pages; a small one 3. Split by *logical surface*
(architecture / API / config / integration / changelog), not by line count
alone — never cut a coherent topic in half just to hit 1500 lines.

## Page frontmatter (required)

```yaml
---
tool: qmd
page_slug: architecture          # unique within the tool dir
upstream: https://github.com/tobi/qmd
version_indexed: 0.4.2           # upstream version this page describes
last_synced: 2026-04-18          # ISO date of last regeneration
confidence: 0.9                  # 0–1, how sure we are this is current/correct
primary_sources:                 # upstream files this page was derived from
  - README
  - src/llm.ts
  - CHANGELOG.md
open_questions:                  # unresolved, drives follow-up
  - Does the reranker cache survive restart?
contradictions: []               # see "Contradictions" below
---
```

`primary_sources` is load-bearing: the sync flow matches CHANGELOG keywords
against it to decide which pages a release invalidates (see
`sync-patterns.md`).

## Required sections (in order)

1. **Overview** — one paragraph: what this page covers and why it matters.
2. **Conceptual Model** — the mental model. Analogies, diagrams, the "why".
3. **Details** — the substance: API signatures, config keys, flow specifics.
4. **Contradictions** — places where sources disagree (README vs code vs docs),
   each with the conflicting claims and which one we currently trust.
5. **Open Questions** — things we could not confirm from sources; mirrors the
   `open_questions` frontmatter so it surfaces in both prose and metadata.
6. **Sources** — every upstream file/URL consulted, with the indexed version.

## Cross-linking

- `[[wikilinks]]` between pages in the same tool dir (e.g. API page links the
  Architecture page for a concept it assumes).
- `[[../my-repos/<repo>]]` to the user's own codebases that use the tool, so
  `/auto-rag` injects the tool page and the consuming code together.

## Worked example — `02-api-reference.md` skeleton

```markdown
---
tool: qmd
page_slug: api-reference
upstream: https://github.com/tobi/qmd
version_indexed: 0.4.2
last_synced: 2026-04-18
confidence: 0.85
primary_sources: [src/llm.ts, src/index.ts]
open_questions:
  - Is `stream: true` supported on the batch endpoint?
contradictions:
  - claim_a: "README says `query()` returns a string"
    claim_b: "src/llm.ts types it as `Promise<QueryResult>`"
    trusted: claim_b   # code over prose
---

## Overview
Public functions exported from the package entrypoint.

## Conceptual Model
`qmd` exposes a thin client over a local model server; every call is async ...

## Details
### `query(prompt, opts)`
Returns `Promise<QueryResult>`. See contradiction note re: README.
...

## Contradictions
- `query()` return type — trusting the TypeScript source over the README.

## Open Questions
- Is `stream: true` supported on the batch endpoint?

## Sources
- src/llm.ts @ 0.4.2
- src/index.ts @ 0.4.2
```
