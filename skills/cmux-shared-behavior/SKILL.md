---
name: cmux-shared-behavior
version: 0.1.0
description: "Shared behavior and mutation-path rules for cmux. Use when a behavior is exposed through multiple entrypoints such as keyboard shortcuts, command palette, context menu, CLI, settings, debug menu, optimistic UI, or tests that previously missed a bug. Do NOT use when the behavior is genuinely independent per entrypoint (no shared state or action), for one-off surface-specific UI with no duplicated logic, or for pure refactors that don't change mutation paths — and prefer cmux-keyboard-shortcuts, cmux-socket-policy, or cmux-testing for surface-specific concerns."
---

# cmux Shared Behavior

Use one shared action/model path when behavior is exposed through multiple entrypoints.

## Shared entrypoints

When a behavior is exposed through multiple surfaces, implement one shared action/model path and verify every entrypoint that should invoke it.

Common entrypoints include:

- keyboard shortcut
- command palette
- context menu
- CLI/socket command
- settings UI
- debug menu

Do not patch one surface while leaving the others with duplicated logic.

## Optimistic updates

For optimistic UI or CLI updates:

- keep one mutation path
- record pending state with a request id or previous snapshot
- reconcile from the authoritative result
- handle failure with an explicit rollback or error state

Do not let each entrypoint maintain its own optimistic copy.

## Missed-bug coverage

When a user says tests missed a bug, add or adjust behavior-level coverage around the exact repro path before claiming the fix is complete. Concretely:

1. Write a failing test that reproduces the reported bug first, and confirm it fails against the unfixed code (red). Only then apply the fix and confirm it passes (green). A test that passes before the fix proves nothing.
2. Exercise the shared action/model path directly — not just one surface. If the bug surfaced via the command palette but the logic is shared, also assert the keyboard-shortcut and CLI entrypoints reach the same state.
3. For optimistic updates, add cases for both reconcile-success and failure-rollback: assert pending state is recorded (request id / snapshot), the authoritative result overwrites it, and a rejected mutation restores the prior state.
4. Cover the boundary the bug lived at — empty/missing input, stale request id, out-of-order responses, or a second mutation arriving before the first reconciles.

See cmux-testing for the project's test harness conventions.
