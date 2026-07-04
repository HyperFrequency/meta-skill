# Donor graph-engine behaviors that ground each invariant

Class 5's assertions are not invented — each maps to a behavior that a shipping
Rust graph engine already implements. This file records the **verified**
crate / version / type for each, so the first-party `harness_graph` engine has a
concrete parity target and the class doubles as the **D2 conformance proof** for
the graph crates.

**Licensing.** All four donors are permissively licensed and safe to *reference*
for behavioral accuracy. This skill (and any first-party crate it informs) is
**clean-room**: no code is copied; only observed behaviors, public type names, and
API shapes are cited. Confirmed on the local mirrors under
`/Users/DanBot/neuro-centrifuge-repos/`:

| Donor | Crate / version | License |
|---|---|---|
| weavegraph | `weavegraph` 0.7.0 | Apache-2.0 |
| metalcraft | `metalcraft` 0.8.1 | MIT |
| graph-flow (state-graph-rs / rs-graph-llm) | `graph-flow` | MIT |
| rust-langgraph | `rust-langgraph` | MIT |

None of the forbidden sources (PolyForm-NC / gitnexus\*, BUSL-1.1 /
copula-dependency, Anthropic-proprietary pdf·pptx·docx, AGPL / openobserve) are
referenced here.

---

## Invariant 5 — replay equivalence → weavegraph replay-conformance helpers

weavegraph 0.7.0 ships a purpose-built replay-conformance module
(`src/runtimes/replay.rs`) that is the closest existing analogue to what invariant
5 asserts. Verified public surface:

- `ReplayRun { final_state, events }` and `ReplayRun::new(final_state, events)` —
  the captured-run artifact (final state + ordered event log).
- `compare_replay_runs(left, right) -> ReplayComparison` and
  `compare_replay_runs_with(left, right, normalizer)` /
  `compare_replay_runs_with_profile(...)` — compare two captured runs with default
  or caller-supplied event normalization. **This is the interrupted-vs-control
  comparison of invariant 5.**
- `ReplayComparison` with `matched()`, `with_differences(Vec<String>)`,
  `is_match()`, `differences()`, and `assert_matches() -> Result<(),
  ReplayConformanceError>` — the pass/fail with a concrete diff list.
- `ReplayConformanceError` (variant carrying human-readable differences) — the
  hard-fail surfaced when twins diverge.
- `normalize_event(event) -> Value` — strips nondeterministic fields (documented:
  top-level `timestamp`) before comparison.
- `normalize_state(state) -> Value` and `compare_final_state(left, right)` —
  stable state comparison.
- A **filter profile** for `normalize_state_with` / `compare_final_state_with`
  that lists extra-map keys to exclude, annotated with a `StateLifecycle`, to
  **separate durable state from per-invocation scratch** — the exact mechanism
  invariant 5's "strip scratch" step needs. Registering the same key with a
  *different* lifecycle annotation **panics with a clear message**, surfacing
  config mistakes at test time — the behavior the fixture-build validation
  mirrors.

Takeaway for `harness_graph`: expose a `ReplayRun`-equivalent artifact and a
`compare_replay_runs` with a lifecycle-annotated scratch filter; the parity test
asserts twin equivalence and asserts the panic-on-conflicting-lifecycle guard.

## Invariant 2 — checkpoint/resume → weavegraph + metalcraft checkpointers

**weavegraph** (`src/runtimes/checkpointer.rs`, `_postgres`, `_sqlite`):
- `Checkpointer` trait + `InMemoryCheckpointer` / `SQLiteCheckpointer` /
  `PostgresCheckpointer` — the backend matrix invariant 2 runs across.
- `Checkpoint`, `PersistedCheckpoint`, `StateSnapshot`, `CheckpointSaveMeta`,
  `CheckpointLoadMeta` — a checkpoint is "a snapshot of session execution state
  captured at a **barrier boundary**" (confirms: checkpoints are only valid at
  barriers, not mid-superstep).
- `VersionedState`, `StateVersions`, `PersistedVersionsSeen` — state is versioned;
  the Postgres/SQLite backends guard that "out-of-order replays or imports cannot
  regress the cached latest snapshot" (grounds the version-monotonicity edge
  case). Checkpoints are ordered by step descending.

**metalcraft** (`src/checkpoint.rs`, `src/executor.rs`):
- `Checkpointer<S: Reducer>` trait with `save(thread_id, state, next_node)` /
  `load(thread_id) -> Option<(S, String)>` and `MemoryCheckpointer` — confirms a
  checkpoint persists **`(state, next_node)`**, grounding the "`next_node`
  fidelity" assertion (resume from the right node, not just the right state).
- `Executor::with_checkpointer(Arc<dyn Checkpointer<S>>)` wires it in.

## Invariant 3 — HITL interrupt round-trip → metalcraft + graph-flow

**metalcraft** interrupt/resume (`src/graph.rs`, `src/executor.rs`):
- `NodeOutcome::interrupt(reason)` and `interrupt_with(update, reason)` — a node
  parks, optionally carrying a partial update (grounds the "update-carrying vs
  pause-only" edge case).
- `RunOutcome::Interrupted { state, reason, resume_from }` — carries the node that
  **re-runs on resume** (`resume_from`), grounding the "interrupt node re-executes,
  must be idempotent" edge case. Also `RunOutcome::Completed(S)` and
  `RunOutcome::Failed { state, .. }` (failure preserves accumulated partial state
  — relevant to no-loss checks).
- `Executor::resume(thread_id, inject: Option<S::Update>) -> RunOutcome<S>` —
  loads the checkpoint, **applies the injected update once** (`state.apply(update)`
  before continuing), and drives to terminal. This is the exact
  inject-exactly-once semantics invariant 3 asserts.

**graph-flow** (state-graph-rs, `graph-flow/src`):
- `NextAction` (Continue / WaitForInput / End) — `WaitForInput` is the HITL park;
  the `Session` holds state while waiting for injected input.
- `Session`, `SessionStorage` trait + `InMemorySessionStorage` /
  `PostgresSessionStorage`, `ExecutionStatus`, `TaskResult`, `Context`,
  per-task timeouts — the session-level park/resume surface (a second, independent
  implementation of the same round-trip, useful as a parity cross-check).

## Invariant 4 — fanout/join determinism → weavegraph superstep + graph-flow fan-out

**weavegraph** superstep/barrier (`src/runtimes/execution.rs`, `runner.rs`):
- A superstep result embeds a `BarrierOutcome` that "carries the **canonical
  ordering**" of the barrier's merged updates — precisely the deterministic,
  completion-order-independent merge invariant 4 requires.
- The runner applies updates through "the same **deterministic barrier path**"
  (`apply_barrier_and_update`, `run_one_superstep`); scheduler output is
  "normalized … ready for barrier application." Grounds "merge is canonical
  regardless of arrival order."
- Superstep/step types derive ordering so "step numbers can be compared and sorted
  directly" — the stable ordering the parity test asserts.

**graph-flow**: `FanOutTask` + reducers over the shared `Context` — a second
fan-out/merge model to parity-check.

## Invariant 1 — transition coverage → all engines' edge models

Coverage counts declared transitions, including each conditional branch:

- weavegraph: "conditional routing and dynamic edges" — dynamic edges create the
  "fired edge absent from the declared spec = hard-fail" case.
- metalcraft: "static edges, conditional branching, parallel fan-out/merge" and
  **cyclic graphs** ("agent loops that run until a condition is met, not just
  DAGs") — grounds distinct-transition-not-visit-count for loops. `StepGuard` /
  `GuardAction` (loop detection) inform the loop-exit-transition edge case.
- graph-flow / rust-langgraph: conditional edges and routing — each branch is a
  distinct transition in the denominator.

## Invariant 6 — cross-language checkpoint round-trip → versioned schemas

weavegraph exposes `schema_version()` and `weavegraph_version()`, and the
checkpoint backends embed version metadata (`PersistedVersionsSeen`), so a
serialized checkpoint carries the version needed to detect skew on load. Grounds
"schema/format version must be embedded and checked; version skew fails loudly."
Combine with the meta_skill `format_version` discipline for the Rust↔Python D8
boundary.

## Iterative checkpointed sessions (cross-cutting)

weavegraph also ships iterative-session helpers relevant to multi-invocation
graph runs: `SessionState`, `SessionId`, `SessionInit`, `generate_session_id`,
`get_session` / `list_sessions`, `restore_session_state`,
`finish_iterative_session`, `from_session`, plus `snapshot()` and a
`PetgraphConversion` for structural analysis. These frame how a spec is run
repeatedly with checkpoints between invocations — the substrate for coverage
aggregation across a fixture suite.
