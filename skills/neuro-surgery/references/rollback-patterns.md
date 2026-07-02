# Rollback patterns — one undo command per target type

Step 2 of the surgery loop requires a rollback command *before* you apply.
If you can't write one, the change isn't safe enough to apply. This file
gives the canonical rollback shape for each executor in the routing table.

The rule: the rollback must be runnable by someone who only has the
proposal in front of them — no hidden state, no "just re-run the scan."

## `02-KB-main/*.md` body edit (via `nlr_wiki_update`)

The schema-aware writer keeps the prior version. Capture the pre-edit
content hash in the proposal, then roll back by re-writing the captured
prior body:

```
# Before applying, snapshot:
PRIOR=$(tv_read_note "02-KB-main/<page>.md")
# Rollback:
nlr_wiki_update "02-KB-main/<page>.md" --body-from-snapshot "$PRIOR"
```

If the writer integrates with git (vault is a repo), prefer the git form —
it's auditable and atomic:

```
git -C <vault> checkout HEAD -- "02-KB-main/<page>.md"
```

## `02-KB-main/*.md` frontmatter-only edit

Single field changes are the easiest to reverse — record the old value:

```
# Rollback: restore the prior field value
nlr_wiki_update "02-KB-main/<page>.md" --frontmatter-only \
  --set <field>=<OLD_VALUE>
```

## `03-Ontology-main/**/*.md` (via `/reasoning-ontology update`)

Ontology edits touch two tiers plus InfraNodus. A file-level git checkout
is NOT sufficient — it leaves InfraNodus out of sync. Roll back through the
same skill so both tiers and the graph revert together:

```
/reasoning-ontology revert <path> --to <pre-edit-revision-id>
```

Always capture the `<pre-edit-revision-id>` that
`/reasoning-ontology update` prints, and put it in the proposal's Rollback
field. Without it, the rollback can't run.

## Broken wikilink fix (via `tv_edit_note` SEARCH/REPLACE)

The change is a single link-text substitution, so the rollback is the
inverse substitution:

```
# Applied:  [[old-target]] -> [[new-target]]
# Rollback: tv_edit_note "<page>.md" --search "[[new-target]]" --replace "[[old-target]]"
```

## `00-neuro-link/tasks/*.md` and `config/*.md` (direct Edit)

These are git-tracked and schema-light. Plain git checkout is the clean
rollback:

```
git -C <vault> checkout HEAD -- "<path>"
```

## If you genuinely can't write a rollback

Some changes are effectively irreversible (e.g., dispatching a deep-reasoning
task that consumes budget). For these, the rollback field should name the
*containment* action instead of a true undo:

```
Rollback: cannot un-dispatch; cancel via /neuro-link task cancel <id>
          before the worker picks it up (window ~30s)
```

State the irreversibility plainly in the proposal so the user approves with
eyes open. A change you can't reverse is a change that deserves extra
scrutiny, not a hand-waved rollback line.
