# Class 5 runner on the shared harness_eval chassis

How the class-5 graph-workflow runner plugs into the single `harness_eval`
chassis that all ten D13 classes share, the versioned **criteria schema** for
class 5, the `_llm_scores` record it emits, the **gate mechanics** (why structural
invariants are hard-fail), the artifacts, and the class's **meta-loop** and **D2
conformance** role. Nothing here re-implements the chassis — it specializes it.

## The shared chassis (recap, minimal)

Built once in `harness_eval`; every class consumes it:

- **Runner contract** — `task / solver / scorer` traits + registry (Inspect AI
  shape). The **system under test hides behind the `solver` trait** (a
  completion-function-style boundary) so the same runner drives a prompt, a graph
  agent, or a full Temporal workflow. Dual API: a declarative batch runner for
  gates + incremental score emission from long activities.
- **Criteria schema** — declarative YAML registered per class: a weighted list of
  deterministic assertions + model-graded assertions, combined by weight with a
  test-level **threshold = the regression gate**.
- **Score record** — the `_llm_scores` shape (one table, all ten classes):
  `level` (span|trace|session|episode|experiment), value (numeric|categorical|
  boolean), `scorer_id`+version, `score_config_id`+version, `source_type`,
  `reasoning`.
- **Gate mechanics** — Test-Suite assertions with rollups, candidate-vs-baseline
  on the **same pinned dataset version**, trials `n>=3` + variance stats so
  regressions beat noise.
- **Artifacts** — every runner emits a `.traj`-equivalent trajectory (proto,
  contract plane) + one OTel trace; judge runs self-trace.

**Class 5's specialization**: its scorer is almost entirely **deterministic
structural assertions**, not judges. Because fixtures use scripted nodes, run
variance is ~0, so the `n>=3` trials are used to *shuffle branch-completion order*
(invariant 4) rather than to average model noise — any nonzero delta across trials
is itself a determinism failure.

## The runner loop

```
run_class5(fixture_suite, engine_under_test /* = solver */, criteria_schema, baseline):
  for spec in fixture_suite.specs:
    control = run_scripted(engine, spec, inline_injections)      # uninterrupted twin
    for point in spec.checkpoint_points:                          # invariant 2
        resumed = run_with_checkpoint(engine, spec, point)
        assert_checkpoint_resume(resumed, control)                # hard-fail
    for park in spec.interrupt_points:                            # invariant 3
        rt = run_with_interrupt(engine, spec, park, inject=v)
        assert_interrupt_roundtrip(rt, expected_v_applications=1) # hard-fail
    for pair in spec.scripted_judge_pairs:                        # invariant 5
        cmp = compare_runs(pair.interrupted, pair.control, normalizer)
        assert cmp.is_match()                                     # hard-fail
    for trial in 0..n:                                            # invariant 4
        merged = run_fanout(engine, spec, shuffle_seed=trial)
        record(merged)
    assert all_merged_identical(records)                          # hard-fail
    for blob in spec.py_checkpoint_fixtures:                      # invariant 6
        assert_cross_lang_roundtrip(engine, blob)                 # hard-fail
    coverage = union_transitions(all_event_logs) / declared_transitions(spec)
    emit_score(spec, coverage, invariant_results)                # -> _llm_scores
  gate(scores, baseline)                                          # coverage floor + hard-fails
```

Each fixture run also frames as an **episode-level run with a variant pin**
(tensorzero workflow-evaluation model): the engine build/config is the pinned
variant, so a coverage or determinism delta is attributable to a specific
engine change.

## The class-5 criteria schema (versioned)

Registered in the scorer registry as `graph-workflow-eval/vN`. Sketch (serde-YAML,
promptfoo-style assertion list — but nearly all deterministic):

```yaml
scorer_id: graph-workflow-eval
scorer_version: 1
spec_id: <graph-spec-id>            # schema is pinned per spec
expected_uncovered: []             # transitions intentionally not exercised
coverage_floor: 0.867              # invariant 1 — must not drop vs baseline
durable_scratch_filter:            # normalizer profile for invariants 2/5/6
  scratch_keys: [ts, run_id, node_started_at]   # lifecycle-annotated
assertions:
  - id: coverage
    kind: transition_coverage
    weight: 1.0
    gate: soft            # graded: >= coverage_floor
  - id: checkpoint_resume
    kind: structural
    invariant: checkpoint_resume_equivalence
    backends: [memory, postgres]
    gate: hard            # any failure fails the run
  - id: interrupt_roundtrip
    kind: structural
    invariant: exactly_once_injection
    gate: hard
  - id: fanout_determinism
    kind: structural
    invariant: no_loss_no_dup_canonical_merge
    trials: 5             # shuffle completion order
    gate: hard
  - id: replay_equivalence
    kind: structural
    invariant: scripted_pair_byte_identical
    gate: hard
  - id: py_checkpoint_roundtrip
    kind: structural
    invariant: cross_lang_resume_identical
    gate: hard
threshold:                # test-level regression gate
  hard_fail_invariants: 0 # zero tolerated
  coverage_delta_min: 0.0 # coverage must not drop
```

Version the schema, don't fork it: tightening an assertion or adding an invariant
is a schema **version bump** (its own SemVer, independent of the skill's
`version`); every `_llm_scores` row records the `scorer_version` it was graded
under so old results stay interpretable.

## Gate mechanics — why structural = hard-fail

Class 5 does **not** average its invariants into a 0–5 score. Structural
invariants are **binary pass/fail** because a graph engine that loses one state
key or double-applies one injection is simply wrong — there is no "mostly
correct" state machine. The only graded axis is **coverage %**, which is soft but
**monotone**: it may not drop below the pinned floor.

Gate decision for a candidate engine build:

1. **Any hard-fail invariant fails → gate FAIL.** Block the merge. No override.
2. **Coverage dropped vs baseline → gate FAIL.** A change made a transition
   unreachable or a fixture vanished. Investigate before accepting.
3. **All structural pass + coverage held/rose → gate PASS.** Record the new
   coverage as the candidate baseline (only promote the floor on a green run).

Candidate-vs-baseline runs on the **same pinned fixture set**. Because scripted
runs are deterministic, this is a near-exact comparison — the `n>=3` trials exist
to surface *ordering* nondeterminism (invariant 4), not statistical noise.

## Artifacts

- **`.traj` per run** — the proto trajectory in the contract plane: ordered
  superstep/event log, per-node in/out state deltas, barrier outcomes, checkpoint
  save/load points, interrupt/resume markers. This *is* the evidence the
  structural assertions consume, and the D11 TUI inspector renders it.
- **One OTel trace per run** — `gen_ai`/graph-span kinds (node spans, superstep
  spans, checkpoint spans), so a failed invariant links straight to the offending
  span in `trace-store`. The runner (a judge-equivalent here) self-traces.

## Meta-loop and D2 conformance (dual role)

Per the shared D13 meta-loop, class 5 is improved without letting the loop under
test edit its own gate:

- **Adversarial fixture generation.** Loop 1 (prompt/workflow evolution) treats
  the graph spec as a **config-kind mutation target** and generates adversarial
  graph mutants — malformed edges, racy fan-outs, deeper interrupt nesting,
  conflicting-reducer joins — expanding the fixture suite with cases designed to
  break the engine. New mutants enter the held-out set, not the training set.
- **Schema version bumps are gated.** A change to the class-5 criteria schema
  must go green on the class's **own held-out fixture set** before it lands
  (disjoint-write-scope, swe-loop pattern): the engine change and the gate change
  can never be authored in the same write scope.
- **D2 conformance proof.** This class **doubles as the D2 parity proof for the
  graph crates.** Every change to the first-party `harness_graph` engine must keep
  the **donor parity suite green** — the behaviors of weavegraph, metalcraft,
  graph-flow, and rust-langgraph (checkpoint/resume, interrupt round-trip,
  canonical barrier merge, replay comparison) are encoded as fixtures, so a
  regression against a shipping engine's semantics is caught here. See
  `donor-apis.md` for the exact behaviors mapped to each invariant.

## Where this sits among the classes

- **class 1 — skill-eval-runner**: scores a `SKILL.md`. Shares only the chassis.
- **class 3 — agent-session-eval**: judges session/trajectory *quality*. A graph
  run that IS an agent session is scored for correctness here (class 5) and for
  quality there (class 3) — different questions, same run.
- **class 9 — temporal-design**: Temporal history determinism. See
  `invariants.md` § Boundary with class 9.
