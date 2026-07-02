# Runtime, tearsheets, hooks, and honest scope

## Proof tearsheets

Every cycle of every run produces an HTML tearsheet at
`~/.claude/relentless-inception/runs/<run_id>/cycle-<N>/tearsheet.html`. The tearsheet
shows:

- The plan + acceptance criteria
- Per-phase unit table with pass/fail/retry counts
- Per-subagent reasoning traces (collapsed by default, click to expand)
- Tool-call log (filtered by significance)
- Test harness output (pytest, dagger functions, simulated-user persona reports)
- Adversarial-review verdicts at all three gates
- HTML+screen-recording embeds when `--exec=skynet` recorded them
- A short LLM-as-judge meta-summary at the top

Generator: `scripts/tearsheet.py`. Template: `assets/tearsheet_template.html`. The HTML is
self-contained — no external requests — so a tearsheet attached to an email or shared on a
USB still renders.

## Hooks installed by this skill

This skill expects three hooks to be wired into `~/.claude/settings.json` (the installer in
`scripts/install_hooks.sh` handles this idempotently):

- **`UserPromptSubmit`** → `scripts/relentless_relay.sh`. Watches for `# RELENTLESS-INBOX`
  prompts; when seen, clears the active session and re-pastes the body. Foundation for
  rescue.
- **`Stop`** → `scripts/stall_watchdog.sh`. Records every Stop event with a timestamp; the
  background-agent reads this trail to detect stalls.
- **`statusLine`** → `scripts/status_line.sh`. Lightweight indicator showing run-id, current
  phase, retries remaining, last gate verdict.

Run `bash scripts/install_hooks.sh` once before the first invocation. The script is safe to
re-run and refuses to overwrite hooks it doesn't recognize.

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

## How this skill relates to neuro-harness

The user's `neuro-harness` monorepo at `/Users/DanBot/neuro-harness/` is where the runtime
lives:

- `packages/orchestrator/src/orchestrator/` holds the Python dataclasses (`Role`,
  `ModelBinding`, `Plan`, `Phase`, `Unit`, `RunManifest`) — scripts in this skill import
  them when running inside that workspace, and fall back to stdlib-only shims when they
  don't.
- `vendor/claude-temporal-plugin/`, `vendor/mcp-context-forge/`, `vendor/gitnexus/`,
  `vendor/uv-mcp/`, `vendor/mcp2cli/`, `vendor/mcp-server-tree-sitter/`,
  `vendor/tree-sitter-pine/`, `vendor/pinelsp/` are the MCP and tooling layer the skill
  assumes.
- `docker-compose.yaml` brings up the stack (Temporal + ContextForge + Postgres + Redis +
  3 bridged stdio MCPs + the dev app); this skill's runs typically execute inside
  `neuro-harness-app`.

When this skill runs outside the `neuro-harness` workspace it still functions, but
adversarial-review + nexus-graph features that depend on git-nexus/context7 MCPs are
gracefully reduced.

## Honest scope (what's runtime vs what's contract)

The skill is **a designed contract + state-management harness**, not a standalone
autonomous daemon. The LLM that loads this skill IS the orchestrator. Scripts are the
supporting machinery:

- **What scripts do:** scaffold run directories, write/read state, validate JSON gate
  outputs, claim rescue triggers, run codex CLI invocations with timeouts, drive the tmux
  relay, generate tearsheets, ship via uv/Dagger.
- **What the LLM does:** read SKILL.md + the relevant references on entry, spawn subagents
  (Agent tool) per the role prompts in `agents/`, call `scripts/adversarial_review.sh` at
  gates, write/read manifest + checkpoint state, invoke `scripts/rescue.sh` when a trigger
  fires, follow the documented workflow.

Safety claims (budget caps, kill switch, no force-push) are honored by the LLM following
the documented contract. The kill switch (`~/.claude/relentless-inception/KILL`) IS
additionally checked by every shell script at invocation, so a triggered kill propagates
through state-changing commands within seconds.

A future iteration may add a launchd / cron daemon that periodically runs
`stall_watchdog.sh --sweep` + `rescue.sh` so stall detection + rescue handoff happen
without the LLM needing to remember — see `evals/codex-review-2026-05-19.md` for the patch
backlog.

## Iterate forward, not in place

The skill is intentionally young. When you encounter a real problem — a gate that's too
forgiving, a rescue cycle that drifts, an agent role that lacks a tool it needs — open a new
run with `/skill-creator` against this skill to revise. Don't hand-edit the SKILL.md
mid-run; use the iteration loop. The whole point is to keep getting better.

The initial adversarial review by codex is preserved at `evals/codex-review-2026-05-19.md`
along with per-finding patch status — start from there if you're picking up Slice-2 work.
