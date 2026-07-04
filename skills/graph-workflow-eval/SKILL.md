---
name: graph-workflow-eval
version: 0.1.0
description: >-
  Deterministic eval runner for dynamic state-based graph / state-machine
  workflows — D13 CLASS 5 of the neuro-centrifuge harness. Scores five
  structural invariants of a graph engine and its declarative specs:
  state-transition coverage %, checkpoint/resume correctness, HITL interrupt
  round-trip fidelity, fanout/join determinism, and replay equivalence
  (interrupted-then-resumed final state must equal an uninterrupted run with
  the same value injected). Use to PROVE a graph engine or spec is
  state-machine-correct, or to gate a graph-engine change against a donor
  parity suite (weavegraph / metalcraft / graph-flow / rust-langgraph). Do NOT
  use to judge agent trajectory or session quality (agent-session-eval, class
  3), score a SKILL.md (skill-eval-runner, class 1), check Temporal SDK
  workflow determinism or authoring (class 9 / temporal-design), evaluate
  backtest/market rewards (class 4), or AUTHOR the graph engine itself. It
  scores structural graph invariants, not answer quality.
---

# graph-workflow-eval

The **D13 class 5** runner. Class 5 asks one question: *does the graph engine and
a given graph spec behave correctly as a state machine?* — not "was the answer
good" (that is class 3). It scores **structural invariants** that must hold
byte-for-byte, run on the first-party `harness_graph` engine (Pregel-style
supersteps, channels, interrupt, fanout + a `Store` trait) against fixtures that
are **graph specs plus scripted node behaviors**. Scripted nodes make every run
deterministic, so a violation is a real engine or spec bug, never model noise.

This class is deliberately narrow and deterministic. Everything model-graded
routes to a sibling class:

- **agent-session-eval** (class 3) — trajectory/session *quality*: task
  completion, tool correctness, plan adherence, conversation judges. If your
  graph run IS an agent session and you want to rate how well it did, go there.
  Class 5 only proves the machine underneath it is sound.
- **skill-eval-runner** (class 1) — scores one `SKILL.md` against the frontier
  rubric. Unrelated substrate; shares only the `harness_eval` chassis.
- **temporal-design** / class 9 — Temporal SDK workflow authoring and
  `Worker.runReplayHistories` nondeterminism checks. Both involve "replay," but
  class 9 is about *Temporal history* determinism (workflow_time, no I/O in
  workflow code); class 5 is about a *graph spec's* state-machine equivalence.
  Do not conflate them. See `references/invariants.md` § Boundary with class 9.

All ten classes share one chassis (`harness_eval`: `task/solver/scorer` traits,
a versioned criteria schema, the `_llm_scores` record, trials + variance gates,
`.traj` + OTel artifacts). Class 5's specialization is that its scorer is almost
entirely **deterministic structural assertions**, not judges.

## The five invariants (+ one fixture round-trip)

Each is defined in depth — fixture shape, exact assertion, hard-fail vs soft,
edge cases — in **`references/invariants.md`**. In one line each:

1. **State-transition coverage %** — every declared edge/node in the spec is
   exercised at least once across the fixture suite. Soft gate: **must not drop**
   vs baseline.
2. **Checkpoint/resume correctness** — save at a barrier, reload, continue;
   `resume(state) ≡ uninterrupted continuation` from the same point. Hard-fail on
   state loss or duplication.
3. **HITL interrupt round-trip fidelity** — a node raises an interrupt, the run
   parks, a value is injected, the run resumes and applies it exactly once at the
   right node. Hard-fail on drop, double-apply, or wrong resume node.
4. **Fanout/join determinism** — parallel fan-out then barrier-join produces a
   **canonical ordering** independent of task completion order. Hard-fail on
   non-deterministic merge (no-loss / no-dup, FIX-8 chaos doctrine).
5. **Replay equivalence** — the headline invariant: an interrupted-then-resumed
   run's final state MUST equal an uninterrupted run with the same value
   injected inline. Compared under a normalizer that strips per-invocation
   scratch (timestamps, generated IDs). Hard-fail on any surviving difference.
6. **py-checkpoint fixture round-trip** (D8 feature) — a checkpoint serialized by
   the Python reference loads on the Rust engine and vice-versa with an identical
   resumed final state. Guards the cross-language D8 boundary.

## Run it

Class 5 runs on the shared chassis. The full runner contract — how a fixture
becomes a `task`, how the engine-under-test hides behind the `solver` trait, the
**versioned criteria schema (YAML)** for class 5, the `_llm_scores` record shape,
and gate mechanics — is in **`references/runner-and-chassis.md`**. The shape:

```
1. Load a graph-spec fixture + its scripted node behaviors.
2. Run it on the engine-under-test (solver), producing a ReplayRun-style
   artifact: (final_state, ordered event/superstep log).
3. Apply the class-5 criteria schema:
     - deterministic structural assertions (the six invariants above),
       each weighted; structural invariants are HARD-FAIL.
     - coverage % computed from the event log; compared to the pinned floor.
4. Emit scores to _llm_scores (level=trace/episode, scorer_id=class5/vN),
   one .traj + one OTel trace per run.
5. Gate: hard-fail invariants block; coverage floor blocks; candidate-vs-
   baseline compared on the SAME pinned fixture set (n>=3 trials — scripted
   runs make variance ~0, so any delta is a real regression).
```

**Structural invariants are hard-fail, not scored 0–5.** A single lost state key
fails the run outright. Only coverage % and the (optional) engine-health rollup
are graded on a scale. See `references/runner-and-chassis.md` § Gate mechanics.

## Fixtures

Fixtures are the substrate. **`references/fixtures.md`** covers authoring a
graph-spec fixture, writing scripted node behaviors, building **ScriptedJudge
control pairs** (the interrupted and uninterrupted twins that invariant 5
compares byte-identically), KG-based hard-case generation (Ragas pipeline over
the vault + neo4j plane for multi-hop graphs), and the adversarial-mutant lane
(Loop 1 graph-spec evolution generates malformed/racy graphs to break the
engine). Start from the templates there — do not hand-roll ad-hoc fixtures.

## Grounded in real graph engines

Every invariant is grounded in a behavior that shipping Rust graph engines
already implement, so the assertions are concrete, not invented.
**`references/donor-apis.md`** maps each invariant to the verified
crate/version/type that demonstrates it — weavegraph 0.7.0 `compare_replay_runs`
/ `Checkpointer` / superstep `BarrierOutcome`, metalcraft 0.8.1
`Executor::resume` / `RunOutcome::Interrupted{resume_from}`, graph-flow `Session`
/ `NextAction::WaitForInput` / `FanOutTask`, rust-langgraph conditional edges —
plus the parity-suite role (class 5 doubles as the **D2 conformance proof** for
the first-party graph crates: every engine change must keep these donor
behaviors green).

## Meta-loop (how this class is itself improved)

Per the shared D13 meta-loop: the criteria schema is a versioned registry entity;
**graph-spec evolution** (Loop 1, config component) generates adversarial graph
mutants that expand the fixture suite; a schema version bump is gated on the
class's own held-out fixture set so the loop under evaluation can never edit its
own gate (disjoint-write-scope). Details in
`references/runner-and-chassis.md` § Meta-loop.

## Boundaries

- **Structural, not qualitative.** Class 5 proves the machine is sound. Whether
  the workflow produced a *good* result is class 3 (agent-session-eval).
- **Scripted, deterministic fixtures only.** Live LLM nodes make invariants
  unfalsifiable. Nodes are scripted; the engine is the system under test.
- **Hard-fail invariants are not negotiable.** No-loss / no-dup / replay
  equivalence are pass/fail. Never "score around" a structural violation.
- **Not the Temporal class.** Temporal history determinism is class 9. If you are
  checking `patched()` / `workflow_time` / `Worker.runReplayHistories`, stop —
  wrong skill.
- **Original content only.** This skill is original work. It reads MIT/Apache
  graph donors (weavegraph, metalcraft, graph-flow, rust-langgraph) for
  behavioral accuracy and copies no code; it references no PolyForm-NC, BUSL,
  AGPL, or proprietary source.
