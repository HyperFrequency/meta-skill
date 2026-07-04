# The eval gate

What makes workflow-evolution a disciplined loop and not unconstrained topology search is the gate: a
proposed spec must **survive hard structural invariants** before it earns a soft task-success score.
This maps directly onto D13 **class 5 — dynamic state-based graph workflows** (spec §c row 5), which
this skill's mutants also feed as adversarial test cases.

## Two-tier scoring inside `GEPAAdapter::evaluate`

Your `GEPAAdapter::evaluate(candidate, batch)` runs, per instance:

```
spec = parse(candidate["topology"])
1. HARD GATE (structural invariants — pass/fail, no partial credit)
     if !compiles(spec)             -> score 0.0, feedback "did not compile: <err>"
     if !structural_invariants(spec)-> score 0.0, feedback "<which invariant failed>"
2. SOFT SCORE (only if the hard gate passed)
     graph = compile(spec)
     run graph on the instance (bounded: max_steps, timeout, cost cap)
     score = w_task * task_success        (the graph's actual job — judge or exact-match)
           + w_lat  * latency_term        (normalized, lower better)
           + w_cost * cost_term           (tokens/$ from llm-router, lower better)
     capture the trajectory (nodes visited, routing taken, failures) for the reflective dataset
```

Return `EvaluationBatch { outputs, scores, trajectories }`. For multi-objective Pareto (task vs.
latency vs. cost as separate axes) set `FrontierType::Objective` (or `Hybrid`) and populate
`EvaluationBatch::objective_scores` — otherwise the engine errors at startup (same contract as
gepa-evolve). A single blended scalar keeps `FrontierType::Instance` (the default).

**Never let a malformed spec `Err`.** In `gepa`, returning `Err` per example aborts the whole run;
reserve `Err` for systemic failure (compiler binary missing, network down). A bad *topology* is a
legitimate `0.0` example, and its feedback string is exactly what the config reflection prompt needs to
avoid re-proposing it.

## Hard structural invariants (the class-5 checklist)

These are pass/fail and run **before** any model call, so a broken shape is cheap to reject:

- **Reachability** — every non-orphan node is reachable from `entry`; at least one output node is
  reachable; no dangling edge references a missing node id.
- **No orphans** — no node with zero in-edges (except `entry`) and no node with zero out-edges (except
  output). Orphan = wasted stage or dead branch.
- **Acyclicity** unless loops are explicitly allowed — if the spec permits `conditional_edges` that
  revisit, each must carry a finite `max_revisits`; an unbounded cycle fails the gate.
- **No-loss / no-dup fanout-join** — a `fanout` of width N must join exactly N results with a declared
  `join` strategy; a join that drops or duplicates branch outputs fails (FIX-8 chaos doctrine; class-5
  "fanout/join determinism").
- **Checkpoint/resume correctness** — compile with a checkpointer; interrupt after a node, resume, and
  assert the resumed run reaches the same terminal state as an uninterrupted run with the injected
  value ("replay equivalence" — class 5). A topology that can't survive its own interrupt is unsafe to
  deploy.
- **Interrupt round-trip fidelity** — HITL-interrupt nodes must pause and resume without losing state.

These are the same invariants a standalone `graph-workflow-eval` (class-5 runner) would assert — this
skill *reuses* that runner as its hard gate rather than reimplementing it. Structural invariants are
**hard-fail**; coverage % (state-transition coverage) must **not drop** relative to the seed.

## Building the reflective dataset from traces

The soft-score path captures a trajectory per instance; `make_reflective_dataset` distills the failures
into the `{Inputs, Generated Outputs, Feedback}` records that become `<side_info>` in the config prompt.
For topology, the most useful feedback is *structural attribution*, e.g.:

- "the `review` debate ran 4 rounds but score plateaued after round 2 — rounds are burning cost"
- "the `score<0.7 -> plan` revisit fired twice and still failed — the loop-back doesn't help here"
- "fanout width 5 gave the same synthesis as width 3 — the extra probes were redundant"

Pull these from the trace (`trace-store` spans) or the in-run trajectory; cluster with the opik
hierarchical-reflective root-cause pattern (spec §b Loop 1 step 4). Good structural feedback is what
lets the config prompt make the *right* topology edit instead of a random one.

## Disjoint-write-scope and reward-hack defenses

The spec's anti-metric-gaming rule (§c meta-loop) applies with force here because a topology loop can
"win" by removing work:

- **The loop under evaluation can never edit its own gate.** The eval criteria schema, the dataset
  version, and the hard-invariant set live in the scorer registry and are **out of the candidate's
  write scope**. Evolving the criteria requires a separate, human-gated `contract-rfc`-style version
  bump on a held-out calibration set — not a spec mutation.
- **Deleting the work is a hard fail, not a high score.** A mutant that drops the validator/review
  node, empties a branch, or shortcuts to output must be caught by the reachability + "required stage"
  invariants (declare mandatory node kinds in the spec constraints), so it scores `0.0` rather than
  winning on latency/cost.
- **Cost/latency terms are bounded, not dominant.** Weight them so a shape can't win purely by doing
  less; task-success is the primary axis (or a hard floor below which cost/latency don't count).
- **Pin dataset + seed.** Trials n≥3 per instance with variance-aware compare vs. the baseline
  experiment (spec §b Loop 1 step 8) so a topology "win" beats LLM noise before it flips a label.

## Feeding class 5 (adversarial mutants)

Run in reverse to *harden the graph engine*: let the loop propose topology mutants against a fixed task
and harvest the ones that (a) pass structural validation but (b) expose a determinism/replay/fanout bug
in the engine. Those become adversarial fixtures in the class-5 conformance suite — every engine change
must then keep them green (spec §c row 5: "graph-spec evolution generates adversarial graph mutants …
the class doubles as the D2 conformance proof for the graph crates").
