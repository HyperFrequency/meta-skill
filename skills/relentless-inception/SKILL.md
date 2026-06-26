---
name: relentless-inception
description: Long-running autonomous orchestrator that consolidates /goal, /batch-create-eval, /exaflop, and /gigaprompt into a single team of planning, executor, and review subagents. Use this skill when the user asks for "relentless inception", "ship this end-to-end and don't stop until it works", "/relentless-inception", "stand up a full harness for X", "build until the proof tearsheet is green", or describes a multi-day project that needs the orchestrator + adversarial gates + rescue-mode + HTML proof tearsheets. Also trigger when the user wants live containerized testing, uv/Una/Dagger shipping, simulated-user harnesses, or any pipeline where "done" requires functional proof rather than just code compiling. Triple-gated adversarial review on planning, phase completion, and summarization via codex+openrouter (gpt-5.5/gemini/opus-4.7 xhigh). Rescue mode resurrects stalled runs with a fresh-context consortium. Explicit budget — does NOT fire casually; this is the nuclear option for long autonomous work.
---

# /relentless-inception

The "I'm walking away from the laptop and it needs to actually finish" orchestrator.

This skill replaces four ancestors — `/goal`, `/batch-create-eval`, `/exaflop`, `/gigaprompt` — with a single team-of-agents harness that plans, builds, reviews, ships, and resurrects itself when stuck. The companion Python types live at `packages/orchestrator/src/orchestrator/` in the user's `neuro-harness` monorepo (Role enum, ModelBinding, Plan, Phase, Unit, RunManifest); scripts in this skill import from there when they run inside that workspace, and fall back to stdlib-only shims when they don't.

## What this skill is for

Use when **all three** of these are true:

1. The work is **multi-hour to multi-day** and would be painful to babysit turn-by-turn.
2. "Done" means a **functional proof** — a real install, a real simulated-user run, an HTML tearsheet — not just a green build.
3. The user wants the harness to **survive its own failures** — stalls, hook misfires, tool errors, context blowouts — without giving up.

If any of those are false, prefer a smaller tool. A one-file edit doesn't need a team of agents. A research question doesn't need adversarial gates. A demo doesn't need shipping infrastructure.

## What it is NOT for

- Single-file edits, refactors that fit in one coding pass, or interactive teaching.
- Work where the user wants to review every step — this skill is designed to run unattended.
- Anything where a stall or wrong decision would damage production. The blast radius assumes safe local + branch environments. Tear down + retry must be free.

## The team

This skill spawns a typed cast of subagents. Defaults come from `agents/` files; the user's spec in the parent monorepo's `docs/SPEC-original.md` is the source of truth for any role tuning. Models all run at 1M-context variants; effort flags route through codex/openrouter.

| Role                       | Default model            | Default effort   | When fired                                                       |
|----------------------------|--------------------------|------------------|------------------------------------------------------------------|
| `planner`                  | opus-latest              | xhigh            | every plan-mode entry; pairs with architecture-analyzer          |
| `architecture-analyzer`    | gpt-pro-latest (router)  | xhigh            | inverse-engineers similar codebases via git-nexus                |
| `dev-worker`               | opus-latest              | high             | per-unit build inside worktrees                                  |
| `adversarial-review`       | gpt-5.5 (router)         | high (xhigh rescue) | every plan + phase + summarization gate                          |
| `nexus-graph-writer`       | opus-4.7                 | high             | writes graph artifacts inline as work proceeds                   |
| `nexus-graph-synthesizer`  | gpt-latest (router)      | xhigh            | folds parallel graph writes into a coherent view                 |
| `uv-dagger-deploy`         | opus-latest              | high             | builds + ships via Dagger pipelines                              |
| `uv-package`               | opus-latest              | high             | turns workspace members into installable wheels                  |
| `uv-workspaces`            | opus-latest              | high             | workspace-level fixes (members, sources, lockfile)               |
| `test-harness-designer`    | gpt-5.5 (router)         | xhigh            | designs simulated-user personas + scenarios + assertions         |
| `temporal-tester`          | opus-4.7                 | high             | drives Temporal workflows + Temporal-gated integration tests     |
| `test-evaluator`           | opus-4.7                 | xhigh            | reads outputs, decides pass/fail against acceptance criteria      |
| `background-agent`         | codex-latest             | medium           | watches for stalls, drives the rescue path                       |
| `rescue-agent`             | gpt-latest (router)      | xhigh            | fresh context, reads full session log, repairs the harness       |

Read `agents/<role>.md` for the prompt template each role uses. Each file is self-contained so the orchestrator can dispatch without re-deriving instructions.

## Modes

Modes are flags on the entrypoint. They are not exclusive — `planning-mode` and `execution-mode` compose orthogonally. Default is `staff-up` planning + `proof-loops` execution.

### Planning modes (`--plan=…`)

- **`staff-up`** *(default)*. Conversational discovery → goal synthesis → constraint surfacing → gate calibration. The user picks verification intensity [1–3], review style for orchestrator (`code-function-nexus | adversarial-review | simulate-users-harness`), and review style for subagents (`verify-proof | adversarial-pass-fail`). Reference: `references/planning-modes.md#staff-up`.
- **`kitchen-sink-monorepo`**. Git-nexus parses N upstream codebases as if they were one monorepo. ContextForge becomes the MCP layer. `mcp2cli` + this skill's `skill-creator` integration produce a CLI ref for every tool surface. Reference: `references/planning-modes.md#kitchen-sink-monorepo`.
- **`lawyer-up`**. Pick one-or-more codebases with explicit feature lists, performance metrics, API refs. Plan is "advocacy" — the harness defends one shape vs alternatives with quantitative evidence. Reference: `references/planning-modes.md#lawyer-up`.

### Execution modes (`--exec=…`)

- **`gigaprompt`**. Prompt the agent to build. Lightest mode — useful as a building block inside the others.
- **`proof-loops`** *(default)*. Subagents claim "done", proof is the code-into-HTML-tearsheet flow. The orchestrator runs the code; if output doesn't match expectations, adversarial-review fires across the whole process + log summary (5× gpt-latest + opus-latest xhigh consciousness consortium on plan phase; gemini-latest xhigh + parallel/exa web search agents + knowledge-base agents on review). The `/loop` gate succeeds only when the code function checks pass. Reference: `references/execution-modes.md#proof-loops`.
- **`skynet`**. All of proof-loops PLUS: code-execution proof tearsheets with full LLM + harness logs + temporal.io workflow logs + adversarial reviews; doesn't stop looping until tested mock-or-real-platform performs per requirements with simulated users interacting (creating PRs, raising feature requests, other agents merging). Reference: `references/execution-modes.md#skynet`.
- **`exaflop-infiniloop`**. Literally keeps going until an LLM or human says stop. Max reasoning on every call. 3× adversarial loops on each subagent and on the orchestrator. Consciousness council at each gate loop. Miro-fish swarm using OCR agents on artifacts. **Hard budget guards** are still respected — exaflop-infiniloop overrides the *stopping condition*, not the *cost cap*. Reference: `references/execution-modes.md#exaflop-infiniloop`.

## The triple gate

Every transition through "important state" runs an adversarial review at three checkpoints. This is the single most important pattern in the skill — if it doesn't fire, the orchestrator drifts.

1. **Plan gate** — after `planner` + `architecture-analyzer` propose a plan, before any dev-worker is dispatched. Adversarial-review reads the plan, the acceptance criteria, and the user's original prompt; produces a structured pass/fail with surgical fixes.
2. **Phase gate** — after each phase (per the plan's phases) completes its merge but before the next phase begins. Adversarial-review reads the phase's deliverables + per-unit verifications + the cumulative tearsheet. Same pass/fail shape.
3. **Summarize gate** — every time the orchestrator wants to compact context or hand off, the summary is re-reviewed three times in parallel by gpt-5.5 xhigh, gemini-latest xhigh, and opus-4.7 xhigh. **All three must approve** or the summary regenerates. This is the load-bearing protection against context-rot drift.

Implementation: `scripts/adversarial_review.sh` shells out to `codex` with model + effort flags; the OpenRouter key threads through `OPENROUTER_API_KEY`. See `references/adversarial-gates.md`.

## Rescue mode

Fires automatically when any of these is true (the background-agent watches via the Stop hook + a periodic stall check):

- **N consecutive failures** on the same unit (N=3 default).
- **Unattended stall**: no agent output and no tool calls for `STALL_MINUTES` (default 12).
- **Dead process**: a background subprocess this skill spawned exits non-zero without a status report.
- **Hook misfire**: a hook this skill installed returns non-zero on three consecutive invocations.

What rescue does:

1. `background-agent` (codex-latest --effort medium) reads the full session log + tool-call trace + the current run manifest.
2. Spawns **a 2-model consortium** with fresh context windows: `gpt-5.5 --effort xhigh` (rescue lead) + `opus-latest --effort xhigh` (rescue co-pilot). They independently analyze and propose a fix.
3. Triple-gate-adversarial-reviews their proposals.
4. Summarizes the approved repair to a markdown file at `~/.claude/relentless-inception/rescues/<run_id>/<cycle>.md`.
5. Clears the orchestrator's context (via `scripts/relentless_relay.sh` — see below).
6. Pastes the rescue summary into the freshly-cleared session and submits it, which restarts the orchestrator from the last checkpoint with fresh attention.

Each rescue cycle also runs a self-improvement pass: it inspects hooks for misfires, tool-call patterns for errors, and proposes edits to `SKILL.md`, `agents/<role>.md`, `~/.claude/CLAUDE.md`, or `~/.claude/hooks/*.sh` that would prevent the recurrence. Edits are reviewed by adversarial-review before applying.

Full mechanics: `references/rescue-mode.md`. The relay script reuses the proven tmux-driven `/clear` + paste pattern from the archived `inception-clear-relay.sh.original`.

## Settings + flags

Defaults are tuned for "I won't be watching" runs. Override per-invocation with explicit flags.

```
Planner / architecture-analyzer pair  → opus-latest + gpt-pro-latest, both xhigh
Orchestrator                          → opus-latest, xhigh
Subagent executors (default)          → opus-latest, xhigh
Adversarial review                    → gpt-latest, xhigh
Nexus-proof                           → gpt-latest, xhigh
Background agent                      → codex-latest, medium
Rescue agent                          → gpt-latest, xhigh (forced)
```

All models route through 1M-context variants. Fallback chain on router error: **xhigh-frontier-only** (no silent degradation to a smaller model). If the router can't satisfy xhigh, the run pauses with a clear error rather than continuing with weaker reasoning.

See `references/settings-and-flags.md` for the full table including budget caps, retry limits, and the conditions that force `--effort` upward.

## Proof tearsheets

Every cycle of every run produces an HTML tearsheet at `~/.claude/relentless-inception/runs/<run_id>/cycle-<N>/tearsheet.html`. The tearsheet shows:

- The plan + acceptance criteria
- Per-phase unit table with pass/fail/retry counts
- Per-subagent reasoning traces (collapsed by default, click to expand)
- Tool-call log (filtered by significance)
- Test harness output (pytest, dagger functions, simulated-user persona reports)
- Adversarial-review verdicts at all three gates
- HTML+screen-recording embeds when `--exec=skynet` recorded them
- A short LLM-as-judge meta-summary at the top

Generator: `scripts/tearsheet.py`. Template: `assets/tearsheet_template.html`. The HTML is self-contained — no external requests — so a tearsheet attached to an email or shared on a USB still renders.

## Shipping

When the plan declares a deliverable, the harness ships it. Three ladders:

1. **uv install package**: `scripts/shipping/uv_package.sh` — builds one or more wheels, signs them if a key is configured, and either uploads to a configured index or drops them in `dist/`.
2. **uv workspaces monorepo**: `scripts/shipping/uv_workspaces.sh` — coordinates a multi-member workspace release with shared `uv.lock` and per-member versions.
3. **Una + Dagger**: `scripts/shipping/dagger_deploy.sh` — calls the user's Dagger module (`dagger -m ./dagger call …`) to build multi-arch artifacts (mac-arm + linux-arm + linux-x86) and optionally deploy them to Modal / Lambda Labs / GCP Cloud Run.

Each script is idempotent and emits a structured `ship-report.json` consumed by the tearsheet. Full descriptions: `references/shipping.md`.

## Workflow at a glance

```
              ┌──────── ENTRY (user invokes /relentless-inception ARGS) ─────────┐
              │                                                                   │
              ▼                                                                   ▲
       1. capture-intent ──→ 2. planner + architecture-analyzer pair               │ rescue
              │                       │                                           │ relay
              ▼                       ▼                                           │ resurrects
       PLAN GATE (adversarial) ─ fail → revise plan ←─┐                            │ from
              │                                       │                            │ here
              ▼ pass                                  │                            │
       3. dev-worker pool (parallel) ──→ per-unit verify ─ fail (≤3 retries)       │
              │                                                                   │
              ▼ all pass                                                           │
       PHASE GATE (adversarial) ─ fail → retry phase ←─┐                           │
              │                                        │                           │
              ▼ pass                                   │                           │
       4. test-harness-designer + simulated users ──→ tearsheet draft              │
              │                                                                   │
              ▼                                                                   │
       SUMMARIZE GATE (3-model parallel)                                           │
              │                                                                   │
              ▼ all 3 pass                                                         │
       5. ship (uv / workspaces / dagger)                                          │
              │                                                                   │
              ▼                                                                   │
       6. final tearsheet + done                                                   │
              │                                                                   │
              ▲────────── stall? failure burst? hook misfire? ──────── rescue ─────┘
```

## Hooks installed by this skill

This skill expects three hooks to be wired into `~/.claude/settings.json` (the installer in `scripts/install_hooks.sh` handles this idempotently):

- **`UserPromptSubmit`** → `scripts/relentless_relay.sh`. Watches for `# RELENTLESS-INBOX` prompts; when seen, clears the active session and re-pastes the body. Foundation for rescue.
- **`Stop`** → `scripts/stall_watchdog.sh`. Records every Stop event with a timestamp; the background-agent reads this trail to detect stalls.
- **`statusLine`** → `scripts/status_line.sh`. Lightweight indicator showing run-id, current phase, retries remaining, last gate verdict.

Run `bash scripts/install_hooks.sh` once before the first invocation. The script is safe to re-run and refuses to overwrite hooks it doesn't recognize.

## Prerequisites

The skill expects the following to be available — it will surface a clear error if any is missing rather than fail silently:

- `claude-code` (this is a Claude Code skill — it's there by definition)
- `codex` CLI authenticated (used for adversarial review + rescue model routing). `codex:setup` skill installs it.
- `OPENROUTER_API_KEY` in env (or in `~/.claude/.env`). Required for gpt-5.5 / gemini xhigh routes.
- `git-nexus` MCP available (architecture-analyzer needs it for inverse-engineering)
- `context7` MCP available (planner uses it for current-docs lookups)
- `mcp2cli` available (for kitchen-sink-monorepo mode)
- `infranodus` local instance (for the optional Obsidian/graph visualization step)
- `uv` (for shipping)
- `dagger` CLI (for shipping)

See `references/prereqs.md` for install pointers. If any is missing at run time, the entrypoint refuses to start and prints a remediation hint.

## When to invoke this skill (trigger guide)

These phrases reliably indicate /relentless-inception is the right tool:

- "Relentless inception X"  /  "/relentless-inception X"
- "Ship X end-to-end and don't stop until it's green"
- "Build a full harness for X" + "I'm going to bed / out / afk"
- "Run until the tearsheet is green"
- "Nuclear option for X"
- "Full proof-loops on X" / "skynet mode on X" / "exaflop X"
- "I want simulated-user testing to drive this"
- "Stand up a uv-workspaces + Dagger monorepo for X"
- "Self-healing harness on X"
- Long-form task descriptions that name multiple deliverables across days

These phrases do NOT trigger it:

- "Help me write a test for X" (use the test harness skill or just do it)
- "Look at this PR" (use /review)
- "Refactor X" (just do it)
- "Sketch a plan for X" (use the plain conversation; this skill is *execution*)

## Reading order for first invocation

When you first invoke this skill for a real run, read the references in this order:

1. `references/planning-modes.md` — pick the mode that matches the task shape.
2. `references/execution-modes.md` — pick the execution mode (default `proof-loops` is usually right).
3. `references/adversarial-gates.md` — understand what passes/fails the gates.
4. `references/rescue-mode.md` — understand when and how rescue fires.
5. `references/settings-and-flags.md` — confirm the model + effort defaults match the user's plan.
6. `references/shipping.md` — only if the plan declares a deliverable.
7. `references/prereqs.md` — only if a prereq check failed.

`agents/<role>.md` files are loaded per-spawn; the orchestrator doesn't read them all up front.

## Safety + budgets

- **Never run on `main`/`master`**. The entrypoint refuses unless the current branch is a feature branch.
- **Per-run agent-hour budget**: 40 hours soft cap. Beyond that, the harness pauses for the user to review.
- **Per-cycle cost cap**: $50 USD (rough router-cost estimate). Configurable.
- **Hard cap**: a kill switch in `~/.claude/relentless-inception/KILL` (any non-empty file in that path stops all running orchestrators within 60 seconds).
- **No force-push, ever.** Not under any flag. The harness creates and merges; it never overwrites remote history.
- **No `rm -rf` outside the run's namespace**. Cleanup is scoped to `.worktrees/relentless-<run_id>/` and `~/.claude/relentless-inception/runs/<run_id>/`.

The exaflop-infiniloop mode overrides "stop when convergence is reached" but **respects the budget caps and the kill switch**. There is no flag to bypass the cost cap.

## How this skill relates to neuro-harness

The user's `neuro-harness` monorepo at `$HOME/neuro-harness/` is where the runtime lives:

- `packages/orchestrator/src/orchestrator/` holds the Python dataclasses (`Role`, `ModelBinding`, `Plan`, `Phase`, `Unit`, `RunManifest`) — scripts in this skill import them when running inside that workspace.
- `vendor/claude-temporal-plugin/`, `vendor/mcp-context-forge/`, `vendor/gitnexus/`, `vendor/uv-mcp/`, `vendor/mcp2cli/`, `vendor/mcp-server-tree-sitter/`, `vendor/tree-sitter-pine/`, `vendor/pinelsp/` are the MCP and tooling layer the skill assumes.
- `docker-compose.yaml` brings up the stack (Temporal + ContextForge + Postgres + Redis + 3 bridged stdio MCPs + the dev app); this skill's runs typically execute inside `neuro-harness-app`.

When this skill runs outside the `neuro-harness` workspace it still functions, but adversarial-review + nexus-graph features that depend on git-nexus/context7 MCPs are gracefully reduced.

## Honest scope (what's runtime vs what's contract)

The skill is **a designed contract + state-management harness**, not a standalone autonomous daemon. The LLM that loads this skill IS the orchestrator. Scripts are the supporting machinery:

- **What scripts do:** scaffold run directories, write/read state, validate JSON gate outputs, claim rescue triggers, run codex CLI invocations with timeouts, drive the tmux relay, generate tearsheets, ship via uv/Dagger.
- **What the LLM does:** read SKILL.md + the relevant references on entry, spawn subagents (Agent tool) per the role prompts in `agents/`, call `scripts/adversarial_review.sh` at gates, write/read manifest + checkpoint state, invoke `scripts/rescue.sh` when a trigger fires, follow the documented workflow.

Safety claims (budget caps, kill switch, no force-push) are honored by the LLM following the documented contract. The kill switch (`~/.claude/relentless-inception/KILL`) IS additionally checked by every shell script at invocation, so a triggered kill propagates through state-changing commands within seconds.

A future iteration may add a launchd / cron daemon that periodically runs `stall_watchdog.sh --sweep` + `rescue.sh` so stall detection + rescue handoff happen without the LLM needing to remember — see `evals/codex-review-2026-05-19.md` for the patch backlog.

## Iterate forward, not in place

The skill is intentionally young. When you encounter a real problem — a gate that's too forgiving, a rescue cycle that drifts, an agent role that lacks a tool it needs — open a new run with `/skill-creator` against this skill to revise. Don't hand-edit the SKILL.md mid-run; use the iteration loop. The whole point is to keep getting better.

The initial adversarial review by codex is preserved at `evals/codex-review-2026-05-19.md` along with per-finding patch status — start from there if you're picking up Slice-2 work.
