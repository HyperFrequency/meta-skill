# Context7 indexing — when it helps, how to query, what to do when it's unavailable

Context7 (MCP server `context7`) serves a pre-computed documentation + code-snippet
index for public libraries. Two tools:

- `mcp__context7__resolve-library-id(<name-or-url>)` → returns one or more `/org/project`
  ids ranked by name match, snippet count, and source reputation.
- `mcp__context7__query-docs(<id>, <question>)` → returns doc/code snippets for that id.

## When Context7 helps vs doesn't

| Repo trait | Context7 value |
|---|---|
| Public, popular, has real docs/README | High — rich snippet index, good API surface coverage |
| Public but niche / few stars | Partial — id may resolve but snippets thin; lean on Auggie |
| Private repo | None — Context7 only ingests public repos; will never resolve |
| Brand-new public repo | Delayed — not yet ingested; queue a re-resolve later |

Context7 is doc/API-surface focused. It complements — does not replace — Auggie's
code-semantic layer. For the user's own private monorepos, expect Context7 to add little
and Auggie to carry the registration.

## Success criterion

Registration treats Context7 as **successfully indexed** only when BOTH hold:

1. `resolve-library-id` returns a concrete `/org/project` id (pick the highest-ranked
   exact-name match; if several plausibly match, surface the choice to the user rather
   than guessing).
2. `query-docs` against that id returns non-empty snippets.

## Unavailability decision tree

```
resolve-library-id returns no id?
  └─ yes → private or not-yet-ingested.
            set context7_id: "", index_context7: false in the spec.
            if the repo is PUBLIC: queue a re-resolve (note it in the spec comment);
            if PRIVATE: leave it off permanently — Auggie covers it.
            DO NOT fail the registration.
  └─ no  → id resolved.
            query-docs returns empty?
              └─ yes → thin/no docs. keep the id but set a low weight (0.5) and
                        rely on Auggie for code semantics.
              └─ no  → fully indexed. record context7_id, index_context7: true.
```

The guiding rule: Context7 being absent is **never** a hard failure. The auto-RAG route
can run on Auggie alone; Context7 is additive coverage.

## Re-resolving later

`/main-codebase-tools reindex <slug>` re-runs `resolve-library-id`. Useful for public
repos that were too new at first registration. If it now resolves, it flips
`index_context7` to `true` and records the id.

> Per the user's global rule, prefer Context7 for any library/API question even when you
> think you know the answer — training data may be stale. This skill registers repos INTO
> that flow; it does not replace it.
