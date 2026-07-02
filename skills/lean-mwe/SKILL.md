---
name: lean-mwe
version: 0.1.1
description: "Minimize a failing Lean 4 / Mathlib file into a minimal, self-contained working example (MWE) for a bug report, using the delta-debugging minimizer (`lake exe minimize` from kim-em/lean-minimizer or mathlib-minimizer) guarded by `#guard_msgs`/`#guard_panic`. Use when minimizing a Lean error or panic, creating an MWE/repro, or preparing a bug report for leanprover/lean4 or leanprover-community/mathlib4. WHEN-NOT: not for actually proving goals or fixing the underlying error (use lean-proof); not for bisecting which toolchain commit changed behavior (use lean-bisect — but minimize to an import-free file with lean-mwe first); not for filing/formatting the PR itself (lean-pr, mathlib-pr); not for installing a toolchain (lean-setup) or building Mathlib (mathlib-build)."
---

# Minimizing Lean Errors (MWE)

Reduce a failing Lean file to a minimal, self-contained reproduction so a bug report
shows the smallest case that still triggers the error or panic.

## Workflow (at a glance)

1. **Set up the guard** — wrap the failing code in `#guard_msgs` (errors) or
   `#guard_msgs in #guard_panic in` (panics) so the minimizer knows what to preserve.
2. **Verify the guard** — `lake env lean YourFile.lean` should produce no output.
3. **Run the minimizer** — `lake exe minimize YourFile.lean` → `YourFile.out.lean`.
4. **Review** — `lake env lean YourFile.out.lean`; confirm minimal imports and exact message.

**Never pass `--no-import-inlining`** — the goal is a self-contained file.

## Full workflow

See [references/minimizer-workflow.md](references/minimizer-workflow.md) for repository
setup (mathlib-minimizer vs lean-minimizer), guard templates for errors and panics, all
minimizer flags (`--resume`, `--quiet`, `--only-delete`, `--only-import-inlining`),
handling long-running/interrupted runs, and the pre-filing checklist.

## Next steps

- Bisecting which Lean commit changed the behavior → **lean-bisect** (needs an import-free MWE first).
- Filing the bug as a PR → **lean-pr** (core) or **mathlib-pr** (Mathlib).
- Actually fixing the proof/error → **lean-proof**.
