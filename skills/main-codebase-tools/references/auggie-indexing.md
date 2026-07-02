# Auggie (Augment Code) indexing — setup, success criteria, known gaps

Auggie is Augment Code's local CLI. It builds a semantic embedding layer over the full
source tree, giving code-aware retrieval that complements Context7's doc-focused snippets.

## Commands used by this skill

`register_repo.sh` and `reindex.sh` call exactly these:

```bash
auggie index --path <local_path> --project <repo-slug>   # build/refresh the index
auggie status <repo-slug>                                # check progress
```

These match what the bundled scripts invoke. Flag names can change between Auggie
versions — if a call errors on flags, confirm the current surface with `auggie --help`
and `auggie index --help` rather than guessing. Do not invent subcommands.

## Setup (what must be true before Step 3 succeeds)

1. **Installed:** `command -v auggie` resolves. If not, Auggie indexing is skipped — not
   fatal (see below).
2. **Authenticated:** Auggie needs an Augment account/token. Without auth the first
   `index` call errors. Auth is per-machine, set up once via Auggie's own login flow;
   this skill does not manage Augment credentials and must never read or echo them.
3. **Repo is a real git checkout** at `local_path` (the script already asserts
   `<local_path>/.git` exists).

## Success criterion

Auggie is **successfully indexed** when `auggie status <slug>` reports `indexed`
(not `pending`, not `error`). Indexing runs in the background (2–20 min by repo size),
so registration backgrounds it and reports the slug to poll rather than blocking.

## Known gaps / failure handling

- **Not installed:** `register_repo.sh` prints "Auggie not installed; skipping" and
  continues. Set `index_auggie: false` in the spec and note the gap in the CLAUDE.md
  addendum so a later reindex can backfill it.
- **Auth missing / first-run error:** treat exactly like not-installed — set
  `index_auggie: false`, do NOT fail the registration, leave a TODO to backfill once
  auth is configured.
- **Large monorepo timeout:** the background index can take well past 20 min. Don't
  re-launch it; poll `auggie status`. Re-launching duplicates work.
- **Backfilling later:** once Auggie is installed/authed, run
  `/main-codebase-tools reindex <slug>` (or `scripts/reindex.sh <slug> <local_path>`)
  to build the embedding and flip `index_auggie` to `true`.

The guiding rule, same as Context7: an absent or unauthenticated Auggie is a degraded —
not failed — registration. Context7 (if available) still feeds the auto-RAG route.
