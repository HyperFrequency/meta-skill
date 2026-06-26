# Planning modes

`/relentless-inception` picks one planning mode at the start of every run. The mode controls how the `planner` + `architecture-analyzer` pair derive a concrete plan from the user's prompt.

Default: `staff-up`.

---

## staff-up

The "talk it out" mode. Conversational discovery between the planner pair and the user (or, if the user is afk, the planner pair simulates the user's preferences from prior memory + the original prompt). Five things have to come out the other end before any dev-worker fires:

1. **Goal synthesis.** Rewrite the user's prompt in unambiguous, testable language. If two interpretations exist, list them and pick the one most consistent with prior conversation; surface the alternative as a flag.
2. **Constraint surfacing.** What's NOT in scope. What's locked (e.g., "must use uv-workspaces"). What's elastic (e.g., "Pine grammar wiring is best-effort"). Constraints become explicit "do not do" lines in dev-worker prompts.
3. **Feature roster.** Concrete deliverables, in a numbered list, each with one-sentence success criteria. This is the source for the per-phase unit table.
4. **Performance gates.** Where applicable: latency targets, memory caps, error-rate ceilings. If none apply, write "none" explicitly so the test-harness-designer knows not to invent any.
5. **Logic check.** The planner pair adversarially debates the plan with each other (opus-latest + gpt-pro-latest, both xhigh) for 1-3 rounds. Any unresolved disagreement is surfaced to the user at the plan gate.

Outputs:

- `~/.claude/relentless-inception/runs/<run_id>/plan.md` — the human-readable plan
- `~/.claude/relentless-inception/runs/<run_id>/manifest.json` — the machine-readable RunManifest (loadable into `orchestrator.manifest.RunManifest` if the orchestrator package is available)

### Interactive controls

If the user is present, they can configure:

- `--intensity=[1-3]` (default 3) — verification loop intensity. 1 = run once, 2 = run twice, 3 = run + adversarial-review + rerun until green.
- `--orchestrator-review-style=[code-function-nexus | adversarial-review | simulate-users-harness]` — what the phase gate runs.
- `--subagent-review-style=[verify-proof | adversarial-pass-fail]` — what individual dev-workers run before claiming done.
- `--budget-soft-hours=N` (default 40) — when to pause for re-engagement.

When the user is afk, the planner pair picks the most conservative option from prior memory.

---

## kitchen-sink-monorepo

For "I want a single repo that pulls these N codebases into a coherent harness." The planner pair:

1. Uses `git-nexus` MCP to parse each candidate codebase as if it were a workspace member.
2. Maps shared types, functions, definitions, and dependency graphs across the set; produces a cross-repo symbol table.
3. Adds `ibm-context-forge` (i.e., the vendored ContextForge gateway) as the MCP fan-out layer so AI agents see one URL behind which the entire monorepo's tool surface federates.
4. Uses `mcp2cli` to flatten the federation into a CLI ref — every tool surface becomes a CLI subcommand.
5. Invokes `/skill-creator` recursively to spin up per-tool helper skills if useful.

Outputs:

- A workspace skeleton (`apps/`, `packages/`, `vendor/<members>/`, `pyproject.toml`, `uv.lock`)
- A ContextForge virtual-server YAML registering each member's MCP surface
- A generated CLI reference at `docs/cli-reference.md`

Best for "I have 5 to 20 repos with overlapping concerns and want one consistent dev experience."

---

## lawyer-up

For "build the case for X versus Y" — when the user wants the harness to make and defend a quantitative claim about one or more codebases. The planner pair:

1. Reads each candidate codebase's stated features, performance metrics, API surfaces, and function inventories.
2. Drafts a falsifiable claim ("X has lower p99 latency than Y on benchmark Z under condition C") OR an advocacy claim ("for use-case A, X dominates Y because of properties P1, P2, P3").
3. Produces a per-claim test design: data, fixtures, harnesses, statistical analysis. The `test-harness-designer` agent owns the implementation.
4. Plans evidence collection in `proofs/` — graphs, logs, raw data, tearsheets.

Best for "I'm trying to decide between vectorbt-pro and nautilus for live trading" or "I need to write a defensible benchmark comparing X to Y for a paper / pitch / OKR review."

---

## Choosing the mode

- One concrete deliverable, "build this thing" → **staff-up**.
- "Bring all these codebases under one roof" → **kitchen-sink-monorepo**.
- "Prove X is better than Y" → **lawyer-up**.

When the user's intent is ambiguous, the planner picks `staff-up` and surfaces the alternatives at the plan gate.
