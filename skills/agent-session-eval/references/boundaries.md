# Boundaries, edge cases, failure modes

## Class 3 vs the other D13 classes (the runner family)

All ten D13 classes share one chassis (`task/solver/scorer` + criteria schema +
`_llm_scores` + variance-aware gate). They differ **only** in the system-under-test
and the criteria. Route by *what you are scoring*:

| You are scoring… | Class | Skill | Why it is not Class 3 |
|---|---|---|---|
| an agent's whole multi-turn **session/thread** | **3** | **agent-session-eval** | — this skill |
| one `SKILL.md` vs the frontier rubric | 1 | `skill-eval-runner` | a static artifact, not a session; with-skill-vs-baseline A/B, not a thread |
| one **prompt/variant** on a dataset | 2 | class-2 prompt eval | a single completion function, not a multi-turn agent; label-flip gate |
| **market/PnL** correctness of a strategy | 4 | class-4 market eval / `strategy-verify` | numeric reward, nautilus runs, deflated-Sharpe/PBO — no judge panel |
| a **graph's** transitions/checkpoint/replay-equivalence | 5 | `graph-workflow-eval` | structural invariants (no-loss/no-dup), not behavioral quality |
| **rescue** quality (recovery/false-rescue rate) | 6 | `rescue-agent-eval` | evaluates a *rescue agent* on stuck fixtures; Class 3 evaluates a *task* agent |
| **compaction** policy downstream effect | 7 | `compaction-eval` | replays one session under condensers vs token budget; a strategy bake-off, not a task benchmark |
| **reproducibility** of a past experiment | 8 | `repro-eval` | re-executes from a config-snapshot hash; audits the other classes |

The tell: Class 3 is the only runner whose unit of evaluation is a **conversation
thread** and whose criteria include **conversational** metrics (coherence,
retention, frustration).

## Not a miner, not a rescuer, not a judge

- **`trajectory-miner`** ingests a *corpus* of past runs read-only and emits a
  versioned anti-pattern registry. agent-session-eval scores *one agent config* on a
  *dataset* and returns a *gate*. They meet at the `.traj` schema (this runner
  produces the artifacts the miner consumes) and at the session-quality gate (shared
  filter). If the goal is "what systematically goes wrong across my runs", that's the
  miner; if it's "does this config pass", that's here.
- **`background-rescue`** re-grounds one live stuck node. This skill does not rescue
  anything — it *scores*. (Scoring rescue quality is class 6.)
- **`judge-panel`** is the verdict primitive this runner *calls*; it is not itself a
  runner. Designing the individual judge is `ce-advanced-evaluation`.

## Edge cases the runner must handle

- **Simulated-user unrealism.** A persona-driven user that is too cooperative or too
  hostile skews every metric. Mitigation: prefer **scripted** SimulatedUsers for
  gate-critical items; keep persona temperature bounded; validate persona threads
  through the representativeness gate before they enter the dataset.
- **Non-deterministic threads.** SimulatedUser (and live-replay) threads vary run to
  run. Never gate on a single thread — N≥3 trials with variance is mandatory
  (see [runner.md](runner.md)). A one-trial "regression" is noise.
- **Lucky-path success.** An agent reaches the right final answer via an absurd
  route. Task completion alone would pass it; `trajectory_accuracy` +
  `step_efficiency` catch it. Never gate on task completion alone.
- **Judge sycophancy / self-enhancement** on task-completion. Mitigated by the
  calibration ledger + Align-Evals (meta-loop) and by anchoring tier-1 on
  deterministic tool/argument correctness the judge cannot flatter.
- **Contamination.** Production traces promoted into the dataset must not leak into
  the tier-1 held-out split, or the ungameable floor quietly becomes gameable.
- **Empty / broken sessions.** A thread with zero valid tool calls or a truncated
  transcript is a *broken candidate*, reported as such — not scored 0 and averaged in
  (which would silently drag a tier mean). The deterministic pre-gate flags it.
- **Cost runaway on a Hard tier.** A candidate that solves Hard by burning tokens
  fails condition 2 of the gate even with a perfect solve-rate. Efficiency is a
  first-class gate condition, not a footnote.
- **Thread/run confusion.** Scoring at *run* (single step) level instead of *thread*
  level double-counts and breaks conversational metrics. The `thread_id` spine keeps
  the level explicit; conversational metrics are always `scope: whole_thread`.

## Scope limits (what this skill deliberately does not do)

- It does not **author** the agent, the personas, or the judges — it runs them.
- It does not **own** the dataset lifecycle beyond consuming a pinned version;
  promotion/versioning lives in `experiment-tracker`.
- It returns a **gate decision + scorecard**, not a fix. Turning failures into
  harness improvements is Loop 1 (prompt/workflow evolution) and Loop 3
  (trajectory-miner → anti-patterns), which consume this runner's outputs.
