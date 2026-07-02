# Whitelisted folder-delegated actions

Detailed reference for the "Folder-delegated improvements" step. hyper-sleep
only executes a todo's `action` if it matches one of the patterns below **and**
the todo's frontmatter has `risk: low` (unset risk → skip). Anything not on
this list is deferred to `/neuro-surgery`.

Each todo lives in some `NN-*/` directory with frontmatter like:

```yaml
---
status: todo
risk: low
action: regenerate-index
target: 02-KB-main/optuna/
---
```

## Allowed action patterns

| `action` value            | What it does                                                                 | Why it is safe                                              |
|---------------------------|------------------------------------------------------------------------------|------------------------------------------------------------|
| `regenerate-index`        | Rebuild `index.md` in `target` dir from the current file listing + frontmatter titles. | Pure derived artifact; fully reproducible, no source loss. |
| `fix-broken-links`        | Repair links matching **known** broken patterns (renamed-dir, `.md` → no-ext, moved `references/`). Only rewrites the link target, never deletes the line. | Bounded transform; original link text preserved.           |
| `normalize-frontmatter-date` | Coerce `date:`/`created:`/`updated:` fields to ISO-8601 (`YYYY-MM-DD`). | Format-only; value semantics unchanged.                    |
| `compact-log`             | Run the log compaction described in `references/compaction.md` on `target`.   | Append-only consolidation; no entries removed.             |

## Hard rules for every action

- **No deletions.** If executing the action would remove a file, a line of
  source content, a Qdrant entry, or a Neo4j node, halt that todo and convert
  it to a `/neuro-surgery` task spec. (See `references/safety-bounds.md`.)
- **Stay inside allowed paths.** Writes are confined to `01-raw/`,
  `01-sorted/`, `02-KB-main/`, `04-Agent-Memory/`, `06-Recursive/`, `state/`.
- **Confidence ceiling 0.6** still applies to any `02-KB-main/` page touched.
- **Unknown actions are not hyper-sleep territory.** If `action` is absent or
  not in the table above, skip and leave `status: todo` untouched so the
  morning report and `/neuro-surgery` can pick it up.

## After executing

- Flip the todo's frontmatter `status: todo` → `status: done` (or
  `status: deferred` if skipped).
- Record the result in the morning report under "Folder improvements
  executed" as `<action> on <target> — ok|deferred`.
