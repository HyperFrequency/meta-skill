# Auto-RAG integration

Toolbox wiki pages are indexed by `/auto-rag` so that a library-specific
question pulls the relevant `08-code-docs/toolbox/<tool>/` pages into the prompt
alongside Context7 / Auggie results. The mechanics are inherited from
`/main-codebase-tools` Step 4; this file records only what differs.

## What is inherited

- The same chunker, embedder, and index store as main-codebase docs.
- The same frontmatter-aware ranking: `confidence` and `last_synced` bias
  retrieval toward fresh, high-confidence pages.
- The same `[[wikilink]]` expansion — when a tool page is retrieved, its linked
  `[[../my-repos/<repo>]]` neighbors are eligible for co-injection.

## What differs — retrieval weight

Third-party toolbox pages register at a **lower default weight (0.6)** than the
user's own code (1.0). When both a toolbox page and a user-code page match a
query, the user's own code should win the context budget and the toolbox page
should inject alongside but yield. Rationale: when the user asks about how
*their* code uses a tool, their code is the source of truth; the wiki is
supporting context.

## Registration

On `Step 6 — Auto-RAG integration`, register the tool's wiki dir with the lower
weight:

```yaml
# whatever the auto-rag source registry is, mirror main-codebase-tools shape
sources:
  - path: 08-code-docs/toolbox/qmd/
    weight: 0.6
    kind: third-party-tool
```

## Querying

`/adjacent-tools-code-docs query <tool> <question>` routes to
`/auto-rag preview` scoped to `08-code-docs/toolbox/<tool>/`, so you can inspect
exactly which wiki pages a question would retrieve before relying on them.

## Interaction with sync

Retrieval ranking uses `last_synced` / `version_indexed`, so a page that the
sync flow (see `sync-patterns.md`) has marked stale naturally sinks in ranking
until it is regenerated. Keep the sync cadence current or stale pages will keep
surfacing with falling confidence.
