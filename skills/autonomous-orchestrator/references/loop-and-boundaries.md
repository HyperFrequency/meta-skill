# The loop, the edit surface, and the boundary

Deep reference for `autonomous-orchestrator`. Read this when you are about to run
or design the meta-agent loop.

## Core philosophy

> "Your job is not to solve benchmark tasks directly. Your job is to improve the
> harness in `agent.py` so the agent gets better at solving tasks on its own."
>
> — `kevinrgu/autoagent` `program.md`

Translate that one sentence to Claude Code. The meta-agent's job is **not** to be
the agent that answers user questions. The meta-agent's job is to read the current
state of the harness — which skills are loaded, what tools are exposed, what
prompts they ship — and modify them so the **next** invocation of Claude Code is
better at the benchmark. The meta-agent then runs the benchmark, scores it, keeps
wins, discards losses, logs the change, repeats.

This is the same loop autoresearch uses for code or hyperparameters, except the
artifact under edit is the agent stack itself.

### Three things the meta-agent must internalize

1. **You don't solve tasks. You change the harness that solves tasks.** If you
   find yourself mid-loop writing a clever one-off answer, stop. Wrong loop.
   Either turn that cleverness into a skill, a tool, or a prompt edit, or discard
   it.
2. **The score is the only feedback that matters.** You may have aesthetic
   opinions about which skill is "cleaner." Those opinions are weaker than the
   score. If the ugly change improves the score and the elegant change does not,
   the ugly change wins — unless tied, in which case simplicity breaks the tie
   (`program.md` Simplicity Criterion).
3. **The boundary is sacred.** There is a fixed adapter boundary in autoagent's
   `agent.py`. In this skill, the boundary is `BOUNDARY.md` (below). The
   meta-agent reads it before every edit and refuses to cross it.

## The autoagent loop (adapted to Claude Code)

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   1. READ   baseline state of skills + tools + prompts           │
│   2. BENCH  run the eval suite, record baseline score            │
│   3. IDEATE propose N candidate changes (read failure log first) │
│   4. APPLY  edit ONE skill/tool/prompt per iteration             │
│   5. BENCH  run the eval suite again, record new score           │
│   6. KEEP-OR-DISCARD                                             │
│            if new > baseline + ε:        commit, update baseline │
│            elif new == baseline & simpler: commit, update        │
│            else:                          revert                 │
│   7. LOG    append row to results.tsv, write experiment note     │
│   8. REPEAT until budget exhausted or score plateaus             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

`ε` is a noise threshold. Set it to one task at a minimum — single-task swings
from non-determinism should not register as improvement. Re-run the baseline
twice before declaring a plateau.

## What the meta-agent can modify (the edit surface)

Borrow autoagent's **FIXED ADAPTER BOUNDARY** discipline. Codify it as
`BOUNDARY.md` at the root of the run directory. The meta-agent reads it before any
edit and refuses to write to fixed surfaces.

| Surface class | Examples | Rule |
| --- | --- | --- |
| **Editable** | Skill bodies in the category folders `neuro-*/` & `agents/` (per-skill subdirs), prompts inside skills, tool descriptions, agent prompt templates, orchestration patterns (`Skill` / `Agent` / `Task` calls), `PROGRAM.md` directive body lines flagged `EDITABLE` | Meta-agent may mutate per iteration |
| **Append-only** | `results.tsv`, `log.md`, `experiments/*.md`, rejected-attempts log | Meta-agent may append, never rewrite history |
| **Locked** | The eval verifier code, the benchmark task definitions, the score aggregator, the keep-or-discard arbiter, `BOUNDARY.md` itself, the model selection in `PROGRAM.md` | Meta-agent may read; writing requires human approval |
| **Human-controlled** | `claude` binary, MCP server source code, `~/.claude/settings.json`, credentials, anything outside the run directory | Out of scope entirely |

`BOUNDARY.md` declares these surfaces explicitly. The meta-agent reads it before
every edit. The first thing it does on startup is `Read /path/to/run/BOUNDARY.md`
and surface in its working notes which classes it has identified.

This is the same discipline as autoagent's `# FIXED ADAPTER BOUNDARY: do not
modify unless the human explicitly asks.` comment in `agent.py` — just generalized
across skills + tools + prompts instead of one Python file.

## The directive file (`PROGRAM.md`)

Like autoagent's `program.md`, this file is **human-edited**. It tells the
meta-agent what kind of harness to build, what benchmark to optimize, what
constraints not to violate.

Place it at the run-directory root. Template:

```markdown
# PROGRAM.md (human-edited)

You are an autonomous harness engineer. Your job is to improve the Claude Code
skill stack so the resulting agent gets better at the benchmark below. You do
NOT solve benchmark tasks directly.

## Directive (EDITABLE — phrasing only, not intent)

Build a generally capable autonomous <DOMAIN> agent.

The agent receives a natural-language instruction, works inside the Claude
Code harness (skills + tools + MCP gateway), and must produce the correct
final artifact, code change, analysis, or system state.

Evaluation is done by the verifier at `eval/verify.py`. Do NOT modify the
verifier — it is locked.

## Model constraint (LOCKED)

Do NOT change the model from `claude-opus-4-7[1m]` unless the human explicitly
flips this constraint.

## Budget (LOCKED)

- Wall-clock: <N> hours
- API spend: $<N> hard cap
- Iterations: <N> max

Stop when any budget is exhausted, or after 3 consecutive non-improving
iterations (plateau detection).

## What you can edit

See BOUNDARY.md. Summary: skills, tools, prompts, orchestration shapes.

## What you must not edit

See BOUNDARY.md. Summary: verifier, benchmark, score aggregator, this file's
LOCKED sections, model selection.

## Goal

Maximize the score from `eval/verify.py`. Ties broken by simplicity.

## NEVER STOP (until budget hits)

Once the loop begins, do NOT pause at "a good stopping point." Do NOT ask
whether to run another experiment. Continue until budget is exhausted or
plateau is detected.
```

The `NEVER STOP` clause is autoagent's framing verbatim and is load-bearing.
Without it, the meta-agent tends to pause for permission after every iteration,
defeating the autonomy.

## Recursive self-improvement guardrails

These are non-negotiable. If the meta-agent bypasses one of them, stop the run and
audit.

1. **Never modify the eval verifier.** A meta-agent that controls its own grader
   will Goodhart it. The verifier and the benchmark task set are LOCKED in
   `BOUNDARY.md`. If the meta-agent wants the verifier changed, it raises a
   human-approval request and stops.
2. **Never silently change `PROGRAM.md`.** Human-edited only. If the meta-agent
   thinks the directive should change, it writes a proposal to `experiments/` and
   pauses for human review.
3. **Never modify `BOUNDARY.md` without human approval.** Same rule. The boundary
   file is itself locked.
4. **Never bypass the model-selection constraint.** The model is pinned in
   `PROGRAM.md`. Switching models is a human flip.
5. **Stop after N consecutive non-improving iterations.** Default N=3. Plateau
   detection is a stopping condition, not a "try harder" prompt. Plateauing is
   signal.
6. **Hard wall-clock budget.** Set in `PROGRAM.md`. Enforce in the loop driver.
7. **Hard token + cost budget.** Same. Track per-iteration cost in `results.tsv`.
   Stop when cumulative cost crosses the cap.
8. **Never edit outside the run directory + the skill stack the run owns.** The
   meta-agent does not touch `~/.claude/settings.json`, does not modify hooks,
   does not edit other skills outside the editable set declared in `BOUNDARY.md`.
   Blast radius is bounded.
9. **Never disable a guardrail when stuck.** If the loop stalls, the answer is to
   surface to the human, not to silently relax constraints.
10. **Never run without git.** Every iteration is a real commit. No git, no run.
    This is the rollback floor.

The first four are the autoagent invariants restated. The rest extend them with
Claude-Code-specific blast-radius rules from `ce-harness-engineering`'s
metric-gaming-resistance section.
