---
name: lean-setup
version: 0.1.0
description: Set up a freshly cloned leanprover/lean4 source repository so it can be built and tested - run the first-time cmake preset + make bootstrap, run/write the test suite, and (for interactive work) link stage0/stage1 elan toolchains so `lean`/`lake` resolve to the local clone. Use WHEN you have just cloned or are repairing a lean4 source checkout and need it buildable, when `cmake --preset release` has never been run, or when a user needs to work interactively against their own lean4 build. Do NOT use for subsequent incremental builds (the cmake step is one-time; just rerun `make -C build/release`), for installing a released Lean toolchain via elan (use `elan toolchain install` directly), for Mathlib or other downstream lake projects (see mathlib-build), or for proving/PR/MWE/bisect tasks (see lean-proof, lean-pr, lean-mwe, lean-bisect).
---

# Lean 4 Repository Setup

## Prerequisites

A source build needs: a C++14-capable compiler (clang or gcc), CMake, GMP, libuv, and OpenSSL. Install `elan` if you want the interactive toolchain linking below, and `ccache` (optional) — the build uses it automatically to skip redundant recompiles. Platform setup guides live in `doc/make/` of the clone (Ubuntu, msys2, WSL, macOS/homebrew, or `nix develop`).

## First build

The first time you build in a lean4 repository clone, you need to run
```
cmake --preset release
make -j -C build/release
```

The `cmake` command is not needed on subsequent builds — just rerun `make -j -C build/release`. For iterative source work, `cmake --preset dev-release` reuses the same `build/release` directory; `debug` and `sandebug` presets also exist.

## Tests

### Running a Single Test

```bash
cd tests/lean/run
./test_single.sh example_test.lean
```

### Running the Full Test Suite

```bash
make -j -C build/release test ARGS="-j$(nproc)"
```

### Writing Tests

- All new tests should go in `tests/lean/run/`
- These tests don't have expected output files — they run on a success/failure basis
- Use `#guard_msgs` to check for specific messages

## Lean 4 repositories for interactive use

If you are cloning or repairing the leanprover/lean4 repository for a user to work in, you need to do further set up. First, do an initial build according to the instructions above. Then you'll need to pick a toolchain name. If this is the only clone of `lean4` on the machine, just use `lean4`. Otherwise you might use something like `lean4-XYZ`.

Then run the following commands:
```bash
elan toolchain link lean4-XYZ build/release/stage1
elan toolchain link lean4-XYZ-stage0 build/release/stage0
echo lean4-XYZ > lean-toolchain
echo lean4-XYZ > script/lean-toolchain
echo lean4-XYZ > tests/lean-toolchain
echo lean4-XYZ-stage0 > src/lean-toolchain
```

After setting up the toolchains, verify it worked:

```bash
cd tests/lean/run
lean --version  # Should show the commit hash from your clone, not a release version
```

When done with the clone, remove the toolchains:

```bash
elan toolchain uninstall lean4-XYZ
elan toolchain uninstall lean4-XYZ-stage0
```

- The `tests/` directory needs stage1 because tests run against the full Lean system
- The `src/` directory needs stage0 because it's rebuilding the stdlib itself
