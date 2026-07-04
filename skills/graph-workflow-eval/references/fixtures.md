# Authoring class-5 fixtures

Fixtures are the substrate of class 5. A fixture is a **graph spec + scripted node
behaviors + a scenario** (checkpoint schedule / interrupt points / injections).
Because nodes are scripted, every run is deterministic, so a failing assertion is
always a real engine or spec bug. This file covers the fixture format, the
ScriptedJudge control-pair pattern that invariant 5 depends on, KG-based hard-case
generation, and the adversarial-mutant lane.

## Anatomy of a fixture

```
fixture/
  spec.yaml            # the graph: nodes, edges, fan-out/join, entry, terminal
  nodes.rs|nodes.yaml  # scripted node behaviors (deterministic outputs)
  scenario.yaml        # checkpoint_points, interrupt_points, injections, trials
  expected/            # optional pinned control artifacts (final state, event log)
```

### spec.yaml — the graph under test

Declares only structure; no logic. Enough to compute `declared_transitions` for
coverage and to know where barriers are:

```yaml
id: refund-approval-v1
entry: intake
terminal: [done, rejected]
nodes: [intake, risk_score, human_review, approve, reject, done, rejected]
edges:
  - {from: intake, to: risk_score}
  - {from: risk_score, to: human_review, when: "score > 0.7"}   # conditional branch
  - {from: risk_score, to: approve,       when: "score <= 0.7"}  # conditional branch
  - {from: human_review, to: approve, when: "decision == accept"}
  - {from: human_review, to: reject, when: "decision == reject"}
fanout:
  - {from: enrich, to: [kyc, sanctions, credit], join: merge_checks}  # if present
reducers:
  checks: append          # how concurrent branch writes to `checks` merge
interrupt_nodes: [human_review]     # nodes that may park for HITL
```

### Scripted node behaviors

Each node maps its input state to a deterministic partial update (and, for
interrupt nodes, whether it parks). **No live LLM calls** — a live node makes the
invariants unfalsifiable. Model any "LLM decision" as a fixed scripted output
keyed on input:

```yaml
risk_score:
  emit: {score: 0.82}            # deterministic; drives the >0.7 branch
human_review:
  interrupt: {reason: "needs human decision"}   # parks; value injected on resume
sanctions:
  emit: {checks: ["sanctions:clear"]}
  latency_ms: 30                 # simulated — used to shuffle fan-out completion order
```

For side-effect idempotence tests (invariant 3), a node may declare a durable
side effect and whether it fires before or after the interrupt point, so the
runner can assert it fires exactly once across a resume.

### scenario.yaml — what to exercise

```yaml
checkpoint_points: [after:risk_score, after:merge_checks]   # invariant 2
interrupt_points:
  - {node: human_review, inject: {decision: accept}}         # invariants 3 & 5
fanout_trials: 5                                             # invariant 4 (shuffle order)
py_checkpoint_fixtures: [blobs/refund_at_review.pycheckpoint]# invariant 6
```

## ScriptedJudge control pairs (invariant 5)

The heart of replay equivalence. A control pair is **two twins of one spec** the
runner compares byte-identically:

- **Interrupted twin** — run to the interrupt node, park, checkpoint, reload,
  inject `v`, resume to terminal.
- **Control twin** — run uninterrupted; supply the *same* `v` inline at the same
  node, no park, no checkpoint.

Rules that make the pair valid:

1. **Identical scripted behaviors and identical `v`** in both twins. The only
   difference is the interrupt+checkpoint machinery.
2. **A declared scratch filter.** Any per-invocation value (timestamp, generated
   id, run-local counter) MUST be registered as scratch so the normalizer strips
   it. Registering a key with conflicting lifecycle annotations must fail
   fixture-build (surfaces the mistake at authoring time, not as a flaky pass).
3. **Content-plus-order comparison.** Compare event streams by content *and*
   order unless the spec declares an unordered channel; a set comparison hides
   ordering bugs.
4. **One pair per park position** for multi-interrupt specs, plus one all-parks
   pair — a spec can be equivalent at each single park yet diverge when parked at
   several.

A pair that legitimately *should* differ (e.g. a node with a non-idempotent
durable side effect that re-runs on resume) is a **positive** test: the pair is
expected to fail equivalence, catching the real bug. Mark it `expect: diverge` so
the runner asserts the divergence rather than treating it as a regression.

## KG-based hard-case generation (Ragas pipeline)

Hand-authored fixtures cover the obvious paths; the hard, multi-hop graphs come
from a **KG-based testset generator** (Ragas pattern) run over the D8 vault +
neo4j plane:

1. **Extract** entities/relationships from the knowledge graph (domains,
   decision points, state shapes).
2. **Build relationships** into candidate multi-hop paths (long conditional
   chains, deep fan-out trees, nested interrupts).
3. **Synthesize** each path into a `spec.yaml` + scripted nodes with a persona/
   scenario, targeting graph shapes that stress a specific invariant (e.g. a
   fan-out feeding an interrupt feeding a join).

Generated specs are deduplicated by structural signature (node/edge/fanout shape)
so the suite gains coverage, not near-duplicates.

## Adversarial-mutant lane (Loop 1 graph-spec evolution)

Loop 1 treats a graph spec as a **config-kind mutation target** and evolves
adversarial mutants designed to break the engine, scored by whether the engine
still upholds the invariants. Mutation operators:

- **Racy fan-outs** — widen fan-out beyond worker parallelism; add same-key writes
  under a non-commutative reducer to probe merge determinism.
- **Malformed / dynamic edges** — add a runtime edge absent from the declared
  spec (must be caught as spec/engine divergence, a hard-fail).
- **Deeper interrupt nesting** — parks inside fan-out branches, nested parks,
  interrupt-then-fan-out-then-interrupt.
- **Checkpoint stress** — request a mid-superstep checkpoint (must be rejected),
  or many rapid checkpoints, or a reload from an older checkpoint (version
  monotonicity).
- **Cross-language skew** — a py-checkpoint blob with a bumped `schema_version`
  (must fail loudly, not mis-load).

Mutants enter the **held-out** fixture set, never the training set — the class's
own gate is disjoint from the loop that generates its cases (see
`runner-and-chassis.md` § Meta-loop).

## Fixture hygiene

- **Determinism first.** If a fixture is flaky across identical runs, the fixture
  is wrong (a live node, an unstripped scratch key, or a real determinism bug) —
  fix the cause; never add retries to make it pass.
- **Pin control artifacts.** Store `expected/` control state + event log so a
  regression shows a concrete diff, not just a boolean.
- **Backend matrix.** Run checkpoint/resume fixtures on at least memory + one
  persistent backend (SQLite or Postgres) — serialization bugs only appear on the
  persistent path.
- **Small and single-purpose.** One fixture stresses one invariant primarily.
  Giant "does everything" graphs make failures hard to localize.
