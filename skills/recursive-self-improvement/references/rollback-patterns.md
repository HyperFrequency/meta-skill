# Rollback patterns — manifests that actually work

Every approved change produces a line in a dated rollback manifest:
`06-Recursive/rollback/YYYY-MM-DD.sh`. The manifest is generated
*concurrently* with execution (see `scripts/generate_rollback.py`), not
reconstructed after the fact — reconstruction loses the pre-change state.

## Core rule: capture the inverse before you apply the change

For each approved proposal, record the inverse operation *before* the
forward change is executed, while the original state is still on disk.

- **File edit** → snapshot the original file (or the exact pre-edit blob)
  and the inverse is a restore of that snapshot, not a reverse-diff
  (reverse-diffs break if the file moved on after the change).
- **File create** → inverse is delete of the created path.
- **Frontmatter knob** → record `key=old_value`; inverse re-sets it.
- **Ontology node/edge add** → inverse removes that node/edge by id.

## Manifest structure

```bash
#!/usr/bin/env bash
# Rollback manifest for YYYY-MM-DD — undoes approved changes in REVERSE order.
set -euo pipefail

# proposal: <slug-N> (applied last) -> undone first
git checkout HEAD -- '03-Ontology-main/agents/by-agent/<name>.md'   # restore snapshot
...
# proposal: <slug-1> (applied first) -> undone last
```

## Why reverse order

Changes can depend on each other (a skill edit that references a new
ontology node). Undoing in the reverse of application order keeps every
intermediate state consistent so the rollback itself never errors halfway.

## Validation before trusting a manifest

- **Dry-run check** — every path referenced in the manifest must exist (or,
  for create-inverses, the delete target must exist).
- **Idempotence** — re-running the manifest after a successful rollback is
  a no-op, never a second destructive pass.
- **Self-contained** — the manifest must not depend on state that the
  forward changes themselves mutated (capture snapshots, not live reads).

A manifest that fails its dry-run check blocks the Phase 4 execution from
being marked complete — no change ships without a verified undo.
