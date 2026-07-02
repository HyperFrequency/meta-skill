---
name: relentless-inception
version: 0.1.0
description: Long-running autonomous orchestrator that consolidates /goal, /batch-create-eval, /exaflop, and /gigaprompt into a single team of planning, executor, and review subagents. Use this skill when the user asks for "relentless inception", "ship this end-to-end and don't stop until it works", "/relentless-inception", "stand up a full harness for X", "build until the proof tearsheet is green", or describes a multi-day project that needs the orchestrator + adversarial gates + rescue-mode + HTML proof tearsheets. Also trigger for live containerized testing, uv/Una/Dagger shipping, simulated-user harnesses, or any pipeline where "done" requires functional proof rather than just code compiling. Triple-gated adversarial review on planning, phase, and summarization; rescue mode resurrects stalled runs with a fresh-context consortium. The nuclear option for long autonomous work — does NOT fire casually. NOT for single-file edits, refactors, PR review, research questions, or anything you want to babysit turn-by-turn.
---

# /relentless-inception

The "I'm walking away from the laptop and it needs to actually finish" orchestrator.

This skill replaces four ancestors — `/goal`, `/batch-create-eval`, `/exaflop`,
`/gigaprompt` — with a single team-of-agents harness that plans, builds, reviews, ships,
and resurrects itself when stuck. This SKILL.md is a **router**: it tells you what exists
and points to the reference file for each part. Read the references named below; don't
work from this overview alone for a real run.

The companion Python types live at `packages/orchestrator/src/orchestrator/` in the user's
`neuro-harness` monorepo (Role, ModelBinding, Plan, Phase, Unit, RunManifest); scripts
import from there inside that workspace and fall back to stdlib-only shims elsewhere.

## When to use (and not)

Use when **all three** are true:

1. The work is **multi-hour to multi-day** and would be painful to babysit turn-by-turn.
2. "Done" means a **functional proof** — a real install, a real simulated-user run, an
   HTML tearsheet — not just a green build.
3. The user wants the harness to **survive its own failures** — stalls, hook misfires,
   tool errors, context blowouts — without giving up.

If any are false, prefer a smaller tool. Do NOT use for:

- Single-file edits, refactors that fit in one coding pass, or interactive teaching.
- Work where the user wants to review every step — this skill runs unattended.
- Anything where a stall or wrong decision would damage production. The blast radius
  assumes safe local + branch environments; tear down + retry must be free.

For "look at this PR" use `/review`; for "sketch a plan" use plain conversation (this skill
is *execution*); for one test use the test-harness skill directly.

## The team

A typed cast of subagents (`planner`, `architecture-analyzer`, `dev-worker`,
`adversarial-review`, nexus graph writers/synthesizers, uv/dagger shippers, test designers
+ evaluators, `background-agent`, `rescue-agent`). Full role table with default
model/effort and firing conditions: **`references/team-roster.md`**. Per-role prompt
templates: **`agents/<role>.md`** (loaded per-spawn).

## Modes

Flags on the entrypoint. Planning and execution modes compose orthogonally. Default is
`staff-up` planning + `proof-loops` execution.

- **Planning (`--plan=…`)**: `staff-up` *(default)*, `kitchen-sink-monorepo`, `lawyer-up`.
  Details + when to pick each: **`references/planning-modes.md`**.
- **Execution (`--exec=…`)**: `gigaprompt`, `proof-loops` *(default)*, `skynet`,
  `exaflop-infiniloop`. Details: **`references/execution-modes.md`**.

## The triple gate

The single most important pattern — if it doesn't fire, the orchestrator drifts. An
adversarial review runs at three checkpoints:

1. **Plan gate** — after planner + architecture-analyzer propose a plan, before any
   dev-worker dispatches.
2. **Phase gate** — after each phase merges, before the next begins.
3. **Summarize gate** — every compaction/handoff is re-reviewed 3× in parallel
   (gpt-5.5 + gemini-latest + opus-4.7, all xhigh); **all three must approve** or the
   summary regenerates. Load-bearing protection against context-rot drift.

Implementation (`scripts/adversarial_review.sh` shelling to `codex`) and pass/fail shape:
**`references/adversarial-gates.md`**.

## Rescue mode

Fires automatically (the background-agent watches via the Stop hook + a periodic stall
check) on: N consecutive failures on one unit (N=3), unattended stall (no output/tool calls
for `STALL_MINUTES`, default 12), a dead spawned subprocess, or a hook misfiring three times
in a row. It reads the full session log, spawns a fresh-context 2-model consortium
(gpt-5.5 + opus-latest, both xhigh), triple-gates their fix, then clears + re-pastes via the
tmux relay to restart from the last checkpoint. Each cycle also runs a self-improvement pass.
Full mechanics: **`references/rescue-mode.md`**.

## Settings + flags

Defaults are tuned for "I won't be watching" runs; override per-invocation with explicit
flags. All models route through 1M-context variants with an **xhigh-frontier-only** fallback
chain (no silent degradation — the run pauses on router error rather than using weaker
reasoning). Full table (model/effort defaults, budget caps, retry limits, forced-effort
conditions): **`references/settings-and-flags.md`**.

## Proof tearsheets, hooks, runtime

Every cycle emits a self-contained HTML tearsheet at
`~/.claude/relentless-inception/runs/<run_id>/cycle-<N>/tearsheet.html`. The skill also
installs three hooks (`UserPromptSubmit`, `Stop`, `statusLine`) via
`scripts/install_hooks.sh`, and has a documented runtime relationship to the `neuro-harness`
monorepo. Tearsheet contents, hook details, the end-to-end workflow diagram, the
contract-vs-daemon honest-scope note, and the iterate-forward policy all live in:
**`references/runtime-and-hooks.md`**.

## Shipping

When the plan declares a deliverable, the harness ships it via three ladders: uv package
(`scripts/shipping/uv_package.sh`), uv workspaces monorepo
(`scripts/shipping/uv_workspaces.sh`), and Una + Dagger
(`scripts/shipping/dagger_deploy.sh`). Each is idempotent and emits a `ship-report.json`
consumed by the tearsheet. Full descriptions: **`references/shipping.md`**.

## Prerequisites

The entrypoint refuses to start (with a remediation hint) if any of these is missing:
`codex` CLI authenticated, `OPENROUTER_API_KEY` in env or `~/.claude/.env`, and the
`git-nexus` / `context7` / `mcp2cli` MCPs, plus `infranodus` (optional graph viz), `uv`, and
`dagger` for shipping. Install pointers: **`references/prereqs.md`**.

## Safety + budgets

- **Never run on `main`/`master`** — the entrypoint refuses unless on a feature branch.
- **Per-run agent-hour budget**: 40h soft cap, then pause for review.
- **Per-cycle cost cap**: $50 USD (router estimate), configurable.
- **Hard cap**: any non-empty file at `~/.claude/relentless-inception/KILL` stops all
  orchestrators within 60s.
- **No force-push, ever.** No flag bypasses this. The harness creates and merges only.
- **No `rm -rf` outside the run's namespace** (`.worktrees/relentless-<run_id>/` and
  `~/.claude/relentless-inception/runs/<run_id>/`).

`exaflop-infiniloop` overrides "stop when convergence is reached" but **respects the budget
caps and kill switch**. There is no flag to bypass the cost cap.

## Trigger guide

Reliably triggers: "relentless inception X" / "/relentless-inception X"; "ship X end-to-end
and don't stop until it's green"; "build a full harness for X" + "I'm going afk"; "run until
the tearsheet is green"; "nuclear option for X"; "full proof-loops / skynet mode / exaflop
X"; "I want simulated-user testing to drive this"; "stand up a uv-workspaces + Dagger
monorepo for X"; "self-healing harness on X"; long task descriptions naming multiple
deliverables across days.

Does NOT trigger: "write a test for X", "look at this PR" (`/review`), "refactor X",
"sketch a plan for X".

## Reading order for a first real run

1. `references/planning-modes.md` — pick the mode matching the task shape.
2. `references/execution-modes.md` — pick the execution mode (default `proof-loops`).
3. `references/adversarial-gates.md` — what passes/fails the gates.
4. `references/rescue-mode.md` — when and how rescue fires.
5. `references/settings-and-flags.md` — confirm model + effort defaults match the plan.
6. `references/shipping.md` — only if the plan declares a deliverable.
7. `references/prereqs.md` — only if a prereq check failed.
8. `references/team-roster.md` + `references/runtime-and-hooks.md` — roster, tearsheets,
   hooks, workflow diagram, honest scope.
