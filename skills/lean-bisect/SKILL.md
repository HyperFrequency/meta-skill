---
name: lean-bisect
version: 0.1.0
description: Bisect Lean 4 toolchain versions (nightlies or commits) with the lean4 repo's script/lean-bisect to pinpoint which commit changed a test file's behavior. Use when identifying which Lean 4 commit caused a regression, a fixed bug, or any pass/fail or message change between two toolchain points. Do NOT use for Mathlib-dependent test cases directly (Mathlib is pinned per-toolchain and fails on most versions tested — minimize to a standalone, import-free file first via the lean-mwe skill), for non-minimal or slow test files (each bisection step recompiles the whole test), or when the two endpoints do not already show different behavior.
---

# Bisecting Lean Toolchains

Use the `lean-bisect` script (in the lean4 repo at `script/lean-bisect`) to find which commit introduced a behavior change.

## Test File Requirements

Test files must be self-contained with no `Mathlib` imports (Mathlib is pinned to specific toolchains and will fail on most versions tested). See the minimization skill if you need to reduce a Mathlib test case to a standalone one.

## Usage

```bash
# Auto-find regression
script/lean-bisect /tmp/test.lean

# Bisect up to a given nightly
script/lean-bisect /tmp/test.lean ..nightly-2024-06-01

# Between nightlies
script/lean-bisect /tmp/test.lean nightly-2024-01-01..nightly-2024-06-01

# Between commits
script/lean-bisect /tmp/test.lean abc1234..def5678

# With timeout
script/lean-bisect /tmp/test.lean --timeout 30
```

## Pass/Fail Determination

The script compares a "signature" of exit code + stdout + stderr. It bisects to find where this signature changes. Use `--ignore-messages` to only consider exit code.

## Test File Patterns

### Using exit code

```lean
axiom G : Type
axiom op : G -> G -> G

example : ... := by
  <the failing tactic call>
```

### Using `#guard_msgs`

```lean
/--
error: the specific error that should appear
-/
#guard_msgs in
example : ... := by ...
```

## Options

- `--timeout N`: Timeout in seconds per test
- `--ignore-messages`: Only compare exit codes
- `--nightly-only`: Only test nightly releases when bisecting commits
- `--selftest`: Verify the script works
- `--clear-cache`: Clear `~/.cache/lean_build_artifact/`

## Workflow for Mathlib Issues

When the issue requires Mathlib:

1. Create a minimal test case
2. Use https://github.com/kim-em/mathlib-minimizer to produce a Mathlib-free version (see `lean-mwe` skill)
3. Run lean-bisect on the minimized file

## Tips

Verify endpoints of the range show different behavior before bisecting. Keep tests fast — each bisection step runs the full test.
