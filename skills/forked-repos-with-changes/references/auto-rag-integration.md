# Auto-RAG integration (inherited from adjacent-tools-code-docs)

This skill does not implement its own retrieval layer. The supplementary fork
docs it writes to `08-code-docs/forked-up/<repo>/` are picked up by the same
auto-RAG indexing that the sibling skill `/adjacent-tools-code-docs` configures
for `08-code-docs/`.

## What this means in practice

- Generated fork docs (`functional-diff.md`, `code-examples.md`, etc.) are
  chunked and embedded by the existing `08-code-docs` indexer — no separate
  ingestion step is needed here.
- The frontmatter fields this skill pins (`fork_url`, `upstream_url`,
  `fork_point`, `last_merge_base`, `fork_theme`, `confidence`, `last_diffed`)
  are carried into the index as metadata, so retrieval can filter "fork-only"
  deltas from general upstream docs.
- When the fork resyncs (Step 3–6 re-run on fork commits or stale
  `last_merge_base`), the regenerated files replace the old ones and the indexer
  re-embeds them on its normal cadence.

## Boundary

For the upstream's own documentation, do not duplicate it here — that belongs to
`/deep-tool-wiki` (HyperFrequency forks) or `/adjacent-tools-code-docs` (general
tools). This skill's index footprint is strictly the fork delta layer.
