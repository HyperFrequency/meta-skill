---
name: mathlib-build
version: 0.1.0
description: How to build Mathlib4 efficiently from the command line with `lake` — fetch the prebuilt olean cache, build single files vs. the whole library, reduce log verbosity to save tokens, and run the linter. Use WHEN you need to compile Mathlib or specific Mathlib modules locally, verify a proof/edit builds, or resolve a merge conflict by rebuilding affected files. Use WHEN a build is slow because you forgot to fetch the cache. Do NOT use for first-time Lean toolchain/repo setup (see lean-setup), for opening or reviewing Mathlib PRs (see mathlib-pr, mathlib-review), for writing proofs or minimal examples (see lean-proof, lean-mwe), or for bisecting regressions / nightly-testing failures (see lean-bisect, nightly-testing).
---

# Building Mathlib

Router for the `lake` commands that compile Mathlib4. Run every command from the **repo root** (where `lakefile.lean` lives). The golden rule: **fetch the cache first.** A cold full build is hours; a warm one is minutes.

## 1. Always fetch the olean cache before building

```bash
lake exe cache get
```

- `cache` downloads the precompiled `.olean` artifacts that Mathlib CI built for the **current checked-out revision** — it does not store/retrieve artifacts for downstream projects, only Mathlib and its upstreams.
- After `git pull` / `lake update` / checking out a branch, run `cache get` again; the prior oleans no longer match the revision.
- `lake exe cache get!` (with `!`) **overwrites** local files — use it when `tar` errors out or the cache looks corrupt; plain `get` will not re-download files it already has.
- If it is still wedged, run `lake clean` (or `rm -rf .lake`) then `lake exe cache get` again.

## 2. Build only what you touched

Editing a file invalidates the olean cache for that file **and every file that transitively imports it** — those must rebuild from source, the rest stay cached. So scope the build:

```bash
lake build Mathlib.Foo.Bar -q --log-level=info   # one module + its dirty deps
```

Use the dotted module path (e.g. `Mathlib.Algebra.Group.Defs`), not a file path. This is the right command for verifying a single proof/edit or resolving a merge conflict in a few files.

## 3. Keep logs cheap (token budget)

`-q` / `--quiet` suppress progress noise; `--log-level=info` (or `warning`) raises the message threshold so only relevant diagnostics print. Pair them on every build to save tokens.

## 4. Full local build (only when CI is not enough)

Most of the time, leave the complete build to CI. For a thorough local pass:

```bash
lake build Mathlib MathlibTest Archive Counterexamples && lake exe runLinter
```

`runLinter` is the environment/style linter; run it after the build succeeds, not before.

## When NOT to use this skill (sibling routes)

- First-time toolchain / repo setup → **lean-setup**
- Writing proofs or minimal examples → **lean-proof**, **lean-mwe**
- Opening / reviewing PRs → **mathlib-pr**, **mathlib-review**
- Bisecting regressions / nightly-testing failures → **lean-bisect**, **nightly-testing**

