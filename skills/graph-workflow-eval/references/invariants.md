# Class 5 invariants — definitions, fixtures, assertions, edge cases

The six invariant families class 5 verifies. Each entry gives: **what it
measures**, the **fixture shape** that exercises it, the **exact assertion**,
whether it is **hard-fail or graded**, and the **edge cases** that a naive runner
misses. All fixtures are graph specs + *scripted* node behaviors (see
`fixtures.md`) so runs are deterministic and a violation is always a real bug.

Terminology used throughout:
- **spec** — the declarative graph: nodes, edges (static / conditional), fan-out
  points, join/barrier points, entry, terminal. The unit under test.
- **state** — the typed value threaded through the graph. Updated by a node
  emitting a partial update that a reducer merges (LangGraph channel model).
- **barrier / superstep** — one scheduling round: all ready nodes run, then their
  updates merge in a canonical order before the next round (Pregel model).
- **durable vs scratch state** — durable keys must survive checkpoint/resume and
  replay; per-invocation scratch (timestamps, generated IDs, run-local counters)
  must be excluded from equivalence comparison via a normalizer/filter profile.

---

## 1. State-transition coverage %

**Measures.** The fraction of the spec's declared transitions that the fixture
suite actually exercises. A transition is a (node, outgoing-edge) pair; for
conditional edges, each branch is a distinct transition. A spec with 12 edges and
3 conditional branches has 15 transitions; if the suite drives 13 of them,
coverage is 13/15 = 86.7%.

**Fixture shape.** The whole class-5 fixture suite for one spec, aggregated. You
do not author a "coverage fixture"; coverage is computed by walking the union of
event/superstep logs from every fixture that runs against the spec and recording
which transitions fired.

**Assertion.** `coverage(spec) >= pinned_floor(spec)`. The floor is stored per
spec in the criteria schema (baseline coverage at last green run). This is the
one **graded/soft** invariant with a real percentage — **it must not drop** vs
baseline. A drop means a new engine change made a branch unreachable, or a
fixture was silently deleted.

**Edge cases.**
- **Unreachable branches by design.** Some conditional branches are only
  reachable with inputs the suite intentionally excludes (e.g. an error branch
  needing a scripted node failure). Mark these `expected_uncovered` in the schema
  so they are excluded from the denominator, not silently counted as a gap.
- **Cyclic graphs.** Agent-loop specs (metalcraft/graph-flow support cycles, not
  just DAGs) can revisit a transition many times — coverage counts *distinct*
  transitions, not visits. A loop that never takes its exit edge is 0% on that
  exit transition even after 1000 iterations.
- **Dynamic/added edges.** Engines with runtime-added edges (weavegraph
  "conditional routing and dynamic edges") can create transitions not in the
  static spec. Count only transitions the spec *declares*; a fired edge absent
  from the spec is itself a **hard-fail** (spec/engine divergence), reported
  separately from coverage.

---

## 2. Checkpoint/resume correctness

**Measures.** That saving state at a barrier, tearing down, reloading, and
continuing yields the same trajectory as never stopping. Formally: for a run that
would pass through barriers `b0..bn`, checkpointing at `bk` and resuming must
produce `state_final` and the remaining event suffix identical to the
uninterrupted run.

**Fixture shape.** One spec + scripted nodes + a **checkpoint schedule**: the
list of barrier indices at which to save/reload. The harness runs the spec once
uninterrupted (control) and once per checkpoint point (each: run to `bk`, persist
via the `Checkpointer`, drop the executor, reload, continue to terminal).

**Assertion.** For every checkpoint point `bk`:
`normalize(resumed_final) == normalize(control_final)` **and** the resumed event
suffix (events after `bk`) equals the control's suffix under the event
normalizer. **Hard-fail** on: any durable state key lost, any key duplicated or
double-merged, `next_node` pointer wrong on reload, or a resumed run that diverges
into a different branch.

**Edge cases.**
- **`next_node` fidelity.** The checkpoint must persist *which node runs next*,
  not just the state (metalcraft persists `(state, next_node)`; weavegraph
  persists versioned state + `PersistedVersionsSeen` at the barrier). Resuming
  from the wrong node is a classic bug — assert the resumed run's first post-load
  event is the correct node.
- **Mid-superstep checkpoints are illegal.** Checkpoints are only valid at
  barrier boundaries (after all fan-out branches have merged). A fixture that
  requests a mid-superstep save must be rejected by the runner, not silently
  rounded to a boundary — otherwise fan-out branches are lost.
- **State-version monotonicity.** Engines that version state (weavegraph
  `StateVersions` / `PersistedVersionsSeen`) must not regress the version counter
  on reload; an out-of-order import that lowers "latest" is a hard-fail (the
  donor guards this explicitly).
- **Backend parity.** The same fixture must pass on every `Checkpointer` backend
  (in-memory, SQLite, Postgres). A pass on memory but fail on Postgres is a
  serialization bug, not a spec bug — run at least memory + one persistent
  backend per fixture.

---

## 3. HITL interrupt round-trip fidelity

**Measures.** That a node can pause the run for human input, the run parks with
its state intact, an injected value is supplied, and the run resumes applying
that value **exactly once** at the correct node — the durable-agent HITL primitive.

**Fixture shape.** A spec with at least one **interrupt node** (a scripted node
that raises an interrupt with a reason, optionally carrying a partial update) plus
a scripted **injection**: the value a "human" supplies on resume. The control twin
for invariant 5 injects the same value inline without ever parking.

**Assertion.** After resume with injected value `v`:
- the run reaches terminal (does not re-park in a loop),
- `v` is applied **exactly once** — assert the reducer merged it a single time
  (no drop, no double-apply on the re-run of the interrupt node),
- the resume happens at the node the interrupt named as `resume_from`, and
- terminal state reflects `v`.
**Hard-fail** on drop, double-apply, wrong resume node, or a park that cannot be
resumed.

**Edge cases.**
- **The interrupt node re-runs on resume.** Engines resume by *re-executing* the
  node that interrupted (metalcraft `RunOutcome::Interrupted{resume_from}` re-runs
  that node; graph-flow parks with `NextAction::WaitForInput` and re-enters the
  task). The scripted node must be **idempotent across the interrupt** — if it
  has a side effect before the interrupt point, that effect must not fire twice.
  Test both an interrupt-before-effect and interrupt-after-effect node.
- **Injected update vs no update.** Some interrupts carry a partial update
  (`interrupt_with(update, reason)`), some just pause (`interrupt(reason)`).
  Cover both: the pause-only case must still apply the *separately injected*
  value; the update-carrying case must not double-count the carried update plus
  the injection.
- **Nested / multiple interrupts.** A run may park more than once. Assert each
  injection maps to its own park in order; a value injected for park 1 must not
  leak into park 2.
- **Interrupt inside a fan-out branch.** One parallel branch parking while
  siblings continue is the hardest case — the barrier must not join until the
  parked branch resumes. If the engine joins early (dropping the parked branch's
  contribution) that is a no-loss hard-fail (overlaps invariant 4).

---

## 4. Fanout/join determinism

**Measures.** That fan-out (one node schedules N successors) followed by a join
barrier produces a **canonical, completion-order-independent** merged state.
Parallel branches finishing in a different wall-clock order across runs must
still merge identically.

**Fixture shape.** A spec with a fan-out point to N scripted branches that each
emit a partial update, then a join barrier. To provoke nondeterminism, branches
are scripted with *different simulated latencies* (or the runner shuffles
completion order across trials) so a completion-order-dependent merge would
diverge.

**Assertion.** Across trials with shuffled branch-completion order,
`normalize(merged_state)` is **identical every trial**, and the barrier's
canonical ordering (weavegraph `BarrierOutcome` records this) is stable.
**Hard-fail** (no-loss / no-dup, FIX-8 chaos doctrine): every branch's update
appears exactly once in the merge; none dropped, none duplicated; last-writer or
reducer-merge conflicts resolve by the spec's declared reducer, not by arrival
order.

**Edge cases.**
- **Conflicting writes to the same key.** Two branches writing the same state key
  must resolve via the reducer's declared policy (e.g. append/sum/last), and that
  resolution must be order-independent. A `last-write-wins` reducer is inherently
  order-dependent and is a **spec smell** class 5 flags — the fixture asserts the
  merge is canonical regardless, so a `last` reducer over concurrent branches
  fails determinism by construction.
- **Empty / skipped branches.** A conditional fan-out where some branches emit no
  update must still join deterministically; the absent updates must not shift the
  ordering of present ones.
- **Fan-out width > worker parallelism.** If the engine runs N branches over M<N
  workers, batching order must not leak into the merge. Run the same fixture at
  parallelism 1 and parallelism M and assert identical merged state.
- **Nested fan-out.** A branch that itself fans out must join its sub-barrier
  before the outer barrier — assert the superstep structure, not just the final
  state.

---

## 5. Replay equivalence (the headline invariant)

**Measures.** The class's defining property: an **interrupted-then-resumed** run
must end in exactly the same state as an **uninterrupted** run of the same spec
with the same value **injected inline**. This subsumes and cross-checks
invariants 2 and 3 — if checkpoint/resume and interrupt handling are both
correct, replay equivalence holds; if it fails, one of them is subtly broken.

**Fixture shape.** A **ScriptedJudge control pair**: two twins of one spec.
- **Interrupted twin**: runs to an interrupt node, parks, checkpoints, reloads,
  injects value `v`, resumes to terminal.
- **Control twin**: runs uninterrupted; the same value `v` is supplied inline at
  the same node (no park, no checkpoint).
Both use identical scripted node behaviors and identical `v`.

**Assertion.** `compare(interrupted_final, control_final)` reports **no
differences** under the state normalizer, **and** the event streams match under
the event normalizer (which strips per-invocation scratch — timestamps, generated
IDs — via a filter profile that separates durable state from scratch). **Any
surviving difference is a hard-fail.** This is a *byte-identical* control pair, not
a fuzzy judge.

**Edge cases.**
- **Scratch leaking into durable state.** The commonest false failure: a
  timestamp or run-local counter that should be scratch got written to a durable
  key, so the twins differ only by that value. The fix is the *filter profile* —
  register the key as scratch (lifecycle-annotated) so it is normalized out.
  Registering the same key with conflicting lifecycle annotations must panic at
  fixture-build time, not silently normalize wrong.
- **Non-idempotent resume side effects.** If the interrupt node re-runs on resume
  (invariant 3) and performs a durable side effect, the interrupted twin will have
  applied it once before the park and once on resume, diverging from the control.
  This is a real bug the pair is designed to catch — do **not** normalize it away.
- **Ordering-only differences.** If the twins differ only in event *order* but not
  content, that is still a fail for graphs where order is semantic; use a
  content-plus-order comparison, not a set comparison, unless the spec explicitly
  declares an unordered channel.
- **Multiple interrupt points.** For a spec with K interrupt points, generate K
  control pairs (one per park position) plus one all-at-once pair; a spec can be
  equivalent at each single park but diverge when parked at several — cover both.

---

## 6. py-checkpoint fixture round-trip (D8 cross-language boundary)

**Measures.** That a checkpoint serialized by the **Python reference** loads on
the Rust `harness_graph` engine (and vice-versa) and resumes to an identical final
state. Guards the D8 feature where a checkpoint may be produced on one side of the
TS/Rust/Python boundary and consumed on another.

**Fixture shape.** A spec run to a barrier on side A (e.g. Python reference),
its checkpoint blob captured as a fixture artifact, then loaded and resumed on
side B (Rust engine) with a supplied injection; and the mirror (A=Rust, B=Python).

**Assertion.** `normalize(resumed_final_on_B) == normalize(control_final)` where
control is a same-side uninterrupted run. **Hard-fail** on: deserialization
failure, schema-version mismatch not surfaced as a clear error, or a resumed
divergent state. Schema/format version (weavegraph `schema_version` /
`format_version` discipline) must be embedded in the blob and checked — a version
skew must fail loudly, never silently mis-load.

**Edge cases.**
- **Field ordering / map key order** across languages must not affect the resumed
  state (serialize canonically).
- **Numeric precision** (f64 vs Python float) at the durable boundary — assert
  within the durable-comparison tolerance, and flag any lossy field.
- **Absent optional fields** default identically on both sides; a `None` on Rust
  and a missing key on Python must resume the same.

---

## Boundary with class 9 (Temporal workflow authoring)

Class 5 and class 9 both say "replay," and both check determinism, but the
substrate is different — do not run one for the other:

| | Class 5 (this skill) | Class 9 (temporal-design) |
|---|---|---|
| Unit under test | a **graph spec** on `harness_graph` | a **Temporal workflow** on the SDK |
| "Replay" means | interrupted-vs-uninterrupted **state equivalence** | re-running **exported Temporal histories** with no nondeterminism error |
| Determinism source | scripted nodes + canonical barrier merge | `workflow_time` only, no I/O in workflow code, `patched()`/versioning |
| Runner | ScriptedJudge control pairs on the engine | `Worker.runReplayHistories` over a history corpus |
| Gate | no-loss/no-dup, replay-equivalent, coverage floor | zero nondeterminism errors, payload-size ceilings, rubric floor |

A graph spec may *run inside* a Temporal workflow (the harness executes graph runs
as durable workflows), so a single system can be subject to both classes — but
class 5 owns the graph-state-machine invariants and class 9 owns the Temporal
history/determinism invariants. Route accordingly.
