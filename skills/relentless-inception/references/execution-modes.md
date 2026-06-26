# Execution modes

The execution mode controls *how much work the orchestrator does between user check-ins* and *how aggressive the proof loop is*. Modes compose with planning modes (see `planning-modes.md`).

Default: `proof-loops`.

---

## gigaprompt

The simplest mode — prompt the agent to build. Often used inside the other modes as a building block; rarely the right top-level choice on its own.

When to use directly:

- You already have a precise specification and just want the harness to drive one execution pass.
- Quick experiments where the proof loop overhead isn't worth it.

What it does:

- Loads the plan + per-unit prompts.
- Spawns dev-workers in parallel for independent units.
- Does NOT run the simulated-user harness.
- Adversarial-review only at the plan gate and (single) phase gate, not on summarization.

---

## proof-loops (default)

The workhorse mode. Subagents submit "done"; the orchestrator's job is to *verify* by running the code into an HTML tearsheet and judging.

What it does:

- Same dispatch shape as `gigaprompt`.
- After each phase merges, the orchestrator runs the actual code:
  - `uv run pytest` for unit + integration tests
  - `dagger -m ./dagger call test` for containerized tests when the project has a Dagger module
  - The simulated-user harness designed by `test-harness-designer`
- Outputs flow into `assets/tearsheet_template.html` to produce a tearsheet for the cycle.
- If the projected outputs don't match actuals, the orchestrator does NOT trust the dev-worker's self-report. It triggers adversarial-review with 5× gpt-latest + opus-latest xhigh as a consciousness consortium on the *plan* phase (was the plan wrong?), plus gemini-latest xhigh + parallel exa-web + knowledge-base agents on the *review* phase (what did we miss?).
- The `/loop` gate re-evaluates: function works, or rerun the phase. Max 3 reruns per phase before escalating to rescue.

When to pick: most multi-day work. This is the right default for "ship a feature with proof" or "land a refactor that touches a lot."

---

## skynet

Proof-loops + the kitchen sink.

What it adds on top:

- **Code-execution proof tearsheets** with full LLM reasoning traces, full harness logs, full tool-call log, and adversarial-review verdicts at every gate.
- **Temporal.io workflow logs** when the project uses Temporal — every workflow execution attached to the tearsheet.
- **Code adversarial reviews** at the file level: every dev-worker's diff goes through a second pass by a different model before merge.
- **Doesn't stop looping** until the simulated-user harness performs per requirements on a mock image (Docker) and, if `--real-platform` is set, a real machine. Simulated users interact with the software, create PRs against fake remotes, raise feature requests, and other agents merge them.
- **Captures**: skill use, GitHub Actions runs, reasoning output traces, tool calls, background-agent reports on missed tool calls, hook/skill context, prompt engineering tweaks, RAG/MCP/CLI usage, API accessory calls. The tearsheet has tabs.

When to pick: "I need to defend this in front of someone" or "production-bound work that has to be airtight."

Beware: skynet is **expensive**. Routinely 5-20× the token cost of `proof-loops`. Use deliberately.

---

## exaflop-infiniloop

The literal nuclear option. Keeps going until an LLM or a human says stop.

What it does:

- Maxes out reasoning on every call (forces `--effort=xhigh` everywhere; rescue stays at xhigh).
- **3× adversarial loops** on every subagent's output (not just at gates — on every meaningful artifact).
- **3× adversarial loops** on the orchestrator's own decisions.
- **Consciousness council** at every gate: a quorum of independent models from different providers must agree.
- **Miro-fish swarm using OCR agents** for diagrams, figures, screen recordings — the harness can ingest visual artifacts and reason about them.
- Honors the soft / hard budget caps. When `--budget-soft-hours` is hit, the run pauses for user review. When the kill switch (`~/.claude/relentless-inception/KILL`) is set, the run stops within 60 seconds.

When to pick: never casually. The right contexts are research breakthroughs, intractable bugs that have survived multiple `skynet` runs, or projects where the user has explicitly allocated a large budget for "make this as good as it can be."

---

## Choosing the execution mode

| Situation                                                          | Mode                |
|--------------------------------------------------------------------|---------------------|
| Quick build, you'll review by hand                                  | `gigaprompt`        |
| Multi-day feature, ship-with-proof                                  | `proof-loops` (default) |
| Has to be airtight; you'll show this to others                       | `skynet`            |
| Stuck for days; want max effort with the budget you've allocated     | `exaflop-infiniloop` |

In `staff-up` planning, the planner pair recommends a mode based on prompt analysis and asks the user to confirm. In `kitchen-sink-monorepo` and `lawyer-up`, modes are picked deterministically (`proof-loops` and `skynet` respectively).
