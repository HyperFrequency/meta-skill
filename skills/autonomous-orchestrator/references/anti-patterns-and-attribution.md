# Anti-patterns and attribution

Deep reference for `autonomous-orchestrator`.

## Anti-patterns

These are the failure modes that show up over and over in autonomous loops.
Codified so the meta-agent can recognize them in its own behavior.

- **Solving tasks directly.** The meta-agent finds a clever task-specific trick and
  applies it. Score goes up, but only on one task. The Overfitting Rule from
  `program.md` catches this: *"If this exact task disappeared, would this still be
  a worthwhile harness improvement?"* If no, reject.
- **Rewarding proxy metrics.** The score climbs but the agent is worse on the
  actual user-facing task. Defend with per-dimension scoring and held-out tasks
  per `ce-evaluation` / `ce-advanced-evaluation`.
- **Disabling guardrails when stalled.** A stall is signal that the current
  direction is exhausted. Relaxing constraints to escape the stall is how
  meta-agents Goodhart themselves into oblivion. Surface, don't relax.
- **Running without git.** Without git, every discard is destructive. Without a
  real commit per iteration, the audit trail is useless. No git, no run.
- **Forking the model mid-loop.** Model selection is locked in `PROGRAM.md` for a
  reason — model swaps confound the experiment trace. If the human wants to
  evaluate a model swap, that's a separate run.
- **Exposing the verifier to the edit surface.** A meta-agent that can edit its
  grader will. Verifier is LOCKED.
- **Mid-loop pattern-switching.** Picking supervisor at the start and switching to
  swarm halfway through makes the run uninterpretable. Pick once; if a switch is
  needed, end the run and start a new one with the new pattern declared upfront.
- **Multi-file changes per iteration.** One change per iteration. Bigger changes
  are tournaments (Pattern D) — declare them, parallelize them, don't smuggle them
  in as a single commit.
- **Chat-only memory.** All decisions go to disk. The meta-agent's chat history is
  volatile; the run directory is authoritative. `ce-harness-engineering` gotcha #2.
- **Letting the meta-agent edit this SKILL.md.** This skill is part of the harness
  that runs the meta-agent. If the meta-agent edits it, you've broken the boundary.
  List it in `BOUNDARY.md` as LOCKED.
- **Skipping the baseline.** First run is unmodified baseline. Skipping it means
  there's no score to hill-climb against.
- **Ignoring the rejected log.** Without re-reading rejections, the meta-agent will
  re-propose the same idea three iterations later and waste budget. Read
  `rejected.md` at the top of every IDEATE.

## References and attribution

- **Upstream — `kevinrgu/autoagent`** (MIT). The canonical
  autonomous-harness-engineering pattern this skill adapts. Key files quoted:
  `README.md`, `program.md` (Directive / Setup / What You Can Modify / Simplicity
  Criterion / Experiment Loop / Keep-Discard / Overfitting / NEVER STOP sections),
  `agent.py` (FIXED ADAPTER BOUNDARY comment + `create_tools` / `create_agent` /
  `run_task` structure).
- **Upstream — `muratcankoylan/Agent-Skills-for-Context-Engineering`** (MIT). The
  harness/context/eval/multi-agent discipline this skill is built on. Skills
  directly referenced: `harness-engineering`, `multi-agent-patterns`,
  `context-fundamentals`, `context-optimization`, `context-compression`,
  `memory-systems`, `filesystem-context`, `tool-design`, `evaluation`,
  `advanced-evaluation`.
- **Related skills in this repo:**
  - `relentless-inception` — product-shipping orchestrator (different target)
  - `autoresearch` — research-artifact orchestrator (same loop, different artifact)
  - `e2e-agentic-ML` — linear ML lifecycle
  - `neuro-harness` — gateway routing contract
  - `mcp2cli` — narrowed-tool-surface invocation
  - `forge` — slash-command router
  - `ce-harness-engineering`, `ce-multi-agent-patterns`, `ce-context-fundamentals`,
    `ce-context-optimization`, `ce-context-compression`, `ce-memory-systems`,
    `ce-filesystem-context`, `ce-tool-design`, `ce-evaluation`,
    `ce-advanced-evaluation` — the building blocks
  - `model-evaluation` — purged/embargoed CV for trading metrics
  - `gitnexus-*` family — code-graph queries on the skill stack
  - `doc-sync-embed-verify` — post-keep doc resync
- **Tools used (Claude Code primitives):**
  - `Read`, `Write`, `Edit`, `Bash` — file/state manipulation
  - `Skill` — invoking sibling skills lazily
  - `Agent` — dispatching specialist subagents (`subagent_type` field selects the
    role; pair with `run_in_background` for Pattern D)
  - `TaskCreate` / `TaskUpdate` — tracking the iteration as a unit of work
  - `AskUserQuestion` — surfacing budget exhaustion, plateau, or boundary-violation
    requests
- **Operating environment:** git (mandatory), mcp2cli + `/forge` gateway
  (mandatory), Claude Code with the model pinned in `PROGRAM.md`.
- **License attribution:** This skill is HyperFrequency original prose, but adapts
  the autoagent loop structure (MIT, kevinrgu) and the harness/multi-agent/
  context-engineering discipline (MIT, muratcankoylan). See `NOTICE.md` in this
  repo for the full attribution.
- **Last cross-checked:** 2026-05-24
