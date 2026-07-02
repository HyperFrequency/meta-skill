# LLM-based semantic diff

Why not `git diff`: a raw diff between fork and upstream is dominated by renames,
import reordering, and formatting churn. The user wants the *functional* delta —
new capabilities, changed behavior, removed surface — not line noise.

## The prompt

This is the exact prompt `scripts/compute_fork_diff.py` sends per modified file
(via the `claude` CLI, `--no-tools`, 60s timeout). Both file versions are
truncated to 30k chars each to stay within context.

```
You are diffing a fork against its upstream. Read both versions of the file `<rel>`.

Upstream:
```
<upstream content, first 30000 chars>
```

Fork:
```
<fork content, first 30000 chars>
```

Summarize in 2-3 sentences what the fork changes *functionally*. Ignore
formatting, imports, renames, or cosmetic diffs. Focus on:
- What new capability is added?
- What existing behavior is changed?
- What surface is removed?

If the diff is purely cosmetic, respond with "COSMETIC" and nothing else.
Output ONLY the summary — no preamble.
```

Any file whose response is exactly `COSMETIC` is reclassified to the `cosmetic`
category and dropped from the functional-diff output.

## Cheap cosmetic pre-filter (before spending an LLM call)

`categorize_change()` in `compute_fork_diff.py` classifies each changed path as
`new` / `modified` / `deleted` / `cosmetic` from git metadata alone:

- `A` → `new`, `D` → `deleted`.
- `M` → compute `git diff --numstat`. If `(added + deleted) / full_file_lines <
  COSMETIC_RATIO` (0.02, i.e. under 2% of lines touched), pre-tag `cosmetic` and
  skip the LLM. Otherwise `modified` and send to the LLM.

This keeps the LLM pass focused on files that plausibly carry functional change.

## Example outputs

Modified file, real functional change:

> Adds funding-rate awareness to the perps execution path: the fill simulator now
> debits/credits accrued funding every 8h boundary and exposes `funding_pnl` on the
> position object. Order-sizing is unchanged.

Modified file, cosmetic only:

> COSMETIC

New file:

> Introduces a `HyperliquidFundingClient` that polls the predicted-funding endpoint
> and caches per-market rates; no upstream equivalent exists.

## Aggregation

After per-file summaries are collected, a second LLM pass groups the non-cosmetic
summaries into per-feature buckets, which become the sections of
`functional-diff.md` in the generated wiki.
