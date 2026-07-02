# Orchestration patterns

Deep reference for `autonomous-orchestrator`. Pull directly from
`ce-multi-agent-patterns`. The meta-agent itself runs as the top of one of four
shapes. Pick once at the start of the run; don't switch mid-loop.

## Pattern A — Single meta-agent + N specialist subagents (default)

The canonical autoagent shape. One meta-agent reads the failure log, proposes a
change, dispatches a specialist subagent via the `Agent` tool to actually edit the
skill and run the eval.

Skeleton (Claude Code primitives):

```text
# Meta-agent (this skill's session):
1. Read PROGRAM.md, BOUNDARY.md, results.tsv tail
2. Read latest failure trajectory from logs/
3. Use TaskCreate to track the iteration
4. Spawn a specialist via the Agent tool with subagent_type matching the
   change class (skill-editor / tool-editor / prompt-editor / orchestration-editor)
5. Subagent edits the editable surface, commits, runs the eval, reports score
6. Meta-agent reads the result, keeps or discards via Bash + git
7. Append to results.tsv, write experiment note, mark TaskUpdate complete
```

Use when: the workload decomposes into "diagnose → propose → execute" and you want
context isolation between diagnosis context (full failure log) and execution
context (only the edit + the eval).

## Pattern B — Hierarchical (meta → planning → execution)

Meta proposes the direction. A planning subagent sketches N candidate changes.
Execution subagents run them in parallel, each in their own worktree. Best
candidate wins, others discard.

Use when: a single change-class is exhausted (e.g. prompt tuning has diminishing
returns per `program.md`'s observation) and you want to explore a higher-leverage
axis like tool design, which has more variance and benefits from parallel
exploration.

Reference `ce-multi-agent-patterns` for the supervisor-bottleneck mitigations —
cap candidate count at 3–5, constrain worker output schemas, never overload one
supervisor.

## Pattern C — Pair (meta + critic)

Meta proposes a change. A critic subagent (different `subagent_type`) reviews the
proposal *before* execution. Critic can veto. Then execution runs.

Use when: budget is tight and you can't afford to run the eval on weak ideas. The
critic is a cheap filter.

Mitigation against sycophancy: give the critic an adversarial prompt that
explicitly rewards disagreement. The `ce-multi-agent-patterns` gotcha #3 is real —
without adversarial framing, the critic will rubber-stamp.

## Pattern D — Tournament

N candidate changes are proposed and executed in parallel via `run_in_background`
Bash invocations or parallel `Agent` calls. Winner commits, losers discard.

Use when: you're at a fork — supervisor vs swarm, tool A vs tool B, prompt style 1
vs prompt style 2 — and you want the eval to arbitrate. Token-expensive (15×
baseline per `ce-multi-agent-patterns` gotcha #2) so don't default to this.

## Why not "everything at once"?

Don't. Pattern selection is itself part of the harness. Mixing shapes mid-loop
blows up the trace and makes failure attribution impossible. Pick a shape, run a
budgeted block of iterations under that shape, then if it plateaus consider
switching.

## Quick-reference: which orchestration pattern when

```text
                ┌──────────────────────────────────────────────┐
                │  Is there a single clear hypothesis to test? │
                └──────────────────────────────────────────────┘
                       │ yes                          │ no
                       ▼                              ▼
                ┌──────────────────┐         ┌───────────────────────┐
                │  Budget tight?   │         │ At a structural fork? │
                └──────────────────┘         └───────────────────────┘
                  │ yes      │ no                │ yes        │ no
                  ▼          ▼                   ▼            ▼
              Pattern C   Pattern A          Pattern D    Pattern B
              (pair/      (single meta       (tournament) (hierarchical
              critic)     + specialist)                   meta→plan→exec)
```

Default to Pattern A. Escalate only when the workload clearly warrants the extra
coordination cost.
