---
name: autonomous-orchestrator
version: 1.0.0
description: Turn Claude Code itself into a meta-agent that improves its own harness instead of solving the task. Use when the user says "use claude code as orchestrator", "build me an autonomous harness", "recursive self-improvement loop", "meta-agent that improves the agent", "hill-climb the harness", "autonomous overnight agent engineering", "let it iterate on itself", or describes a benchmark where the goal is to make the AGENT better, not to solve a single task. Do NOT use for one-shot tasks (a single Skill call is faster), for shipping a product to users (use relentless-inception), or for research/paper synthesis (use autoresearch). Distinct from relentless-inception (targets the product) and autoresearch (targets research artifacts) — this one targets the harness itself, autoagent-style.
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, TaskCreate, TaskUpdate
license: HyperFrequency original (derived from kevinrgu/autoagent MIT and muratcankoylan/Agent-Skills-for-Context-Engineering MIT — see NOTICE.md)
---

# Autonomous Orchestrator

This skill turns Claude Code into a meta-agent that hill-climbs on a benchmark by
editing its **own** skills, tools, prompts, and orchestration — not by solving the
benchmark directly. Inspired by `kevinrgu/autoagent`'s "program the meta-agent, not
the harness" framing and grounded in the harness-engineering / multi-agent /
context-optimization / evaluation discipline of the Context-Engineering skill
collection.

One job: **iterate the agent, not the task.** Distinct from `relentless-inception`
(ships a *product* end-to-end), `autoresearch` (improves a *research artifact*),
and `e2e-agentic-ML` (walks a linear ML lifecycle).

## When to use

- **Overnight harness improvement** — walk away while the meta-agent edits skills /
  tool descriptions / orchestration prompts, keeps wins, discards losses, logs all.
- **Agent benchmark iteration** — optimizing a measurable score (Harbor-style
  tasks, internal eval suite, paper-replication, trading-strategy scores).
- **Harness debugging by ablation** — let the loop ablate components; the score
  curve tells you what mattered.
- **Multi-agent orchestration design** — run a tournament across orchestration
  shapes and let the eval arbitrate supervisor vs swarm vs hierarchical.
- **Skill-design-from-eval-results** — read failed trajectories, group by root
  cause, propose skills/edits targeting failure classes, verify by re-running eval.
- **Bootstrapping a new agent stack** — populate the skill set against the eval
  rather than against your guesses.

Do **not** use for:
- One-shot tasks — the loop is overhead; a single `Skill` call is faster.
- Shipping a product to users — that is `relentless-inception`'s job.
- Research synthesis or paper-style writing — that is `autoresearch`'s job.
- Anything where the eval can be Goodharted into a meaningless number — the whole
  loop becomes garbage if the score is wrong.

## The loop in one breath

READ baseline → BENCH (record score) → IDEATE (read failure log) → APPLY (edit ONE
surface) → BENCH again → KEEP-OR-DISCARD (keep if `new > baseline + ε`, or tie +
simpler; else `git revert`) → LOG → REPEAT until budget or plateau.

Three rules the meta-agent must internalize: (1) you don't solve tasks, you change
the harness that solves them; (2) the score is the only feedback that matters
(ties broken by simplicity); (3) the boundary (`BOUNDARY.md`) is sacred — read it
before every edit.

## Router — read the reference for the phase you're in

| You are about to... | Read |
| --- | --- |
| Run/design the loop, define the edit surface, write `PROGRAM.md`, or enforce the recursive-self-improvement guardrails | [references/loop-and-boundaries.md](references/loop-and-boundaries.md) |
| Pick an orchestration shape (single+specialist / hierarchical / pair+critic / tournament) | [references/orchestration-patterns.md](references/orchestration-patterns.md) |
| Wire MCP routing (gateway contract), design the eval/scoring, apply context hygiene, or lay out the run directory + `results.tsv` | [references/state-and-layout.md](references/state-and-layout.md) |
| Execute a full overnight run step-by-step (pre-flight → baseline → iterate → wake-up summary) | [references/workflow.md](references/workflow.md) |
| Recognize the autonomous-loop anti-patterns, or check upstream attribution + tool list | [references/anti-patterns-and-attribution.md](references/anti-patterns-and-attribution.md) |

## Non-negotiables (full detail in loop-and-boundaries.md)

- **Never modify the eval verifier, the benchmark task set, `PROGRAM.md`, or
  `BOUNDARY.md`** without human approval — a meta-agent that controls its grader
  will Goodhart it.
- **Never bypass the pinned model.** Model swaps confound the trace; they are a
  separate run.
- **Never run without git.** Every iteration is a real commit on
  `harness-run-<run_id>`; `keep` advances, `discard` reverts. No git, no run.
- **Stop on plateau (default 3 consecutive non-improving iterations) or budget**
  (wall-clock + cost). Stalling is signal — surface to the human, never relax a
  guardrail to escape it.
- **Blast radius is bounded** — edit only the run directory + the editable skill
  surface declared in `BOUNDARY.md`. Never touch `~/.claude/settings.json` or
  hooks.

## All MCP traffic routes through the gateway

This skill obeys the **neuro-harness gateway contract**: all MCP calls route
through `/forge` → mcp2cli (`docs-dual-lookup`, `gitnexus`, `infranodus`,
`turbovault`, `tree-sitter`). Direct MCP calls bypass the local-only routing pin
and break doc-sync hook discipline. See
[references/state-and-layout.md](references/state-and-layout.md) for the per-route
map.

## Cross-link to siblings

| Skill | Relationship |
| --- | --- |
| `relentless-inception` | Ships the *product* end-to-end. This one improves the *agent*. |
| `autoresearch` | Same loop shape; artifact is a research output, not the harness. |
| `e2e-agentic-ML` | Linear ML lifecycle. Use this skill to improve the agent that runs it. |
| `ce-harness-engineering` | **Conceptual foundation — read before running the loop.** |
| `ce-multi-agent-patterns` | Source for the orchestration shapes (A/B/C/D). |
| `ce-context-*` / `ce-memory-systems` / `ce-filesystem-context` | Context + externalized-state hygiene the loop depends on. |
| `ce-evaluation` / `ce-advanced-evaluation` / `ce-tool-design` | Eval design rigor and tool-design discipline. |
| `model-evaluation` | Purged/embargoed CV when the benchmark involves trading metrics. |
| `neuro-harness` / `mcp2cli` / `forge` | Gateway routing, narrowed tool surface, slash-command router. |
| `gitnexus-*` | Code-graph queries on the skill stack during structural ideation. |
| `doc-sync-embed-verify` | Post-`keep` doc + knowledge-graph resync for large edits. |

Last cross-checked: 2026-05-24.
