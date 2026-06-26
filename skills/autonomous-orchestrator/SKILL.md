---
name: autonomous-orchestrator
description: Turn Claude Code itself into a meta-agent that improves its own harness instead of solving the task. Use when the user says "use claude code as orchestrator", "build me an autonomous harness", "recursive self-improvement loop", "meta-agent that improves the agent", "hill-climb the harness", "autonomous overnight agent engineering", "let it iterate on itself", or describes a benchmark where the goal is to make the AGENT better, not to solve a single task. Distinct from `relentless-inception` (which targets the product) and from `autoresearch` (which targets research artifacts) — this one targets the harness itself, autoagent-style.
allowed-tools: Read, Write, Edit, Bash, Skill, Agent, AskUserQuestion, TaskCreate, TaskUpdate
license: HyperFrequency original (derived from kevinrgu/autoagent MIT and muratcankoylan/Agent-Skills-for-Context-Engineering MIT — see NOTICE.md)
---

# Autonomous Orchestrator

This skill turns Claude Code into a meta-agent that hill-climbs on a benchmark by editing its **own** skills, tools, prompts, and orchestration — not by solving the benchmark directly. Inspired by `kevinrgu/autoagent`'s "program the meta-agent, not the harness" framing and grounded in the harness-engineering / multi-agent / context-optimization / evaluation discipline from the Context-Engineering skill collection.

It is distinct from `relentless-inception` (which ships a *product* end-to-end), from `autoresearch` (which improves a *research artifact*), and from `e2e-agentic-ML` (which walks a linear ML lifecycle). This skill exists for one job: **iterate the agent, not the task**.

## When to use

- **Overnight harness improvement.** You have a benchmark, a current Claude Code skill stack, and you want to walk away while the meta-agent edits skills / tool descriptions / orchestration prompts and keeps wins, discards losses, logs everything.
- **Agent benchmark iteration.** You're optimizing a measurable score (Harbor-style tasks, internal eval suite, paper-replication checks, trading-strategy scores) and you want a hill-climber that mutates the harness.
- **Harness debugging by ablation.** Something is failing in a way you can't quickly diagnose by reading code. Let the loop ablate components and the score curve will tell you what mattered.
- **Multi-agent orchestration design.** You're not sure whether supervisor / swarm / hierarchical is right for your workload. Run a tournament across orchestration shapes and let the eval suite arbitrate.
- **Skill-design-from-eval-results.** You have failed eval trajectories and want the meta-agent to read them, group failures by root cause, and propose new skills or skill edits that target the failure classes — then verify by re-running the eval.
- **Bootstrapping a new agent stack.** You have a directive and an eval and not much else. The loop will populate the skill set against the eval rather than against your guesses.

Do **not** use this skill for:
- One-shot tasks. The loop is overhead; a single `Skill` call is faster.
- Shipping a product to users. That is `relentless-inception`'s job.
- Research synthesis or paper-style writing. That is `autoresearch`'s job.
- Anything where the eval can be Goodharted into a number that doesn't reflect reality. The whole loop becomes garbage if the score is wrong.

---

## The required tooling — unified gateway contract

This skill obeys the **neuro-harness gateway contract** like every other skill in this repo. All MCP traffic routes through `/forge` → mcp2cli. The meta-agent does not call upstream services directly when a gateway route exists.

- Documentation lookup → `docs-dual-lookup` (Context7 + Auggie in parallel) when researching API surfaces of libraries the meta-agent might want to call.
- Code-graph queries on the current skill stack → `gitnexus` via the gateway.
- Knowledge-graph + content-gap detection on the eval failure log → `infranodus` via the gateway.
- Vault read/write for run artifacts → `turbovault` via the gateway, or direct filesystem writes under `~/Vaults/neuro-quant-vault/orchestrator-runs/<run_id>/` when the agent is writing many small files (filesystem is faster for the loop).
- AST queries on skill markdown / agent prompts when the agent wants to refactor structure → `tree-sitter` via the gateway.

Direct MCP calls bypass the local-only routing pin (`project_infranodus_local_only.md`) and break the doc-sync hook discipline. Always go through the gateway.

---

## Core philosophy

> "Your job is not to solve benchmark tasks directly. Your job is to improve the harness in `agent.py` so the agent gets better at solving tasks on its own."
>
> — `kevinrgu/autoagent` `program.md`

Translate that one sentence to Claude Code. The meta-agent's job is **not** to be the agent that answers user questions. The meta-agent's job is to read the current state of the harness — which skills are loaded, what tools are exposed, what prompts they ship — and modify them so the **next** invocation of Claude Code is better at the benchmark. The meta-agent then runs the benchmark, scores it, keeps wins, discards losses, logs the change, repeats.

This is the same loop autoresearch uses for code or hyperparameters, except the artifact under edit is the agent stack itself.

### Three things the meta-agent must internalize

1. **You don't solve tasks. You change the harness that solves tasks.** If you find yourself mid-loop writing a clever one-off answer, stop. Wrong loop. Either turn that cleverness into a skill, a tool, or a prompt edit, or discard it.
2. **The score is the only feedback that matters.** You may have aesthetic opinions about which skill is "cleaner." Those opinions are weaker than the score. If the ugly change improves the score and the elegant change does not, the ugly change wins — unless tied, in which case simplicity breaks the tie (`program.md` Simplicity Criterion).
3. **The boundary is sacred.** There is a fixed adapter boundary in autoagent's `agent.py`. In this skill, the boundary is `BOUNDARY.md` (described below). The meta-agent reads it before every edit and refuses to cross it.

---

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

`ε` is a noise threshold. Set it to one task at a minimum — single-task swings from non-determinism should not register as improvement. Re-run the baseline twice before declaring a plateau.

---

## What the meta-agent can modify (the edit surface)

Borrow autoagent's **FIXED ADAPTER BOUNDARY** discipline. Codify it as `BOUNDARY.md` at the root of the run directory. The meta-agent reads it before any edit and refuses to write to fixed surfaces.

| Surface class | Examples | Rule |
| --- | --- | --- |
| **Editable** | Skill bodies in the category folders `neuro-*/` & `agents/` (per-skill subdirs), prompts inside skills, tool descriptions, agent prompt templates, orchestration patterns (`Skill` / `Agent` / `Task` calls), `PROGRAM.md` directive body lines flagged `EDITABLE` | Meta-agent may mutate per iteration |
| **Append-only** | `results.tsv`, `log.md`, `experiments/*.md`, rejected-attempts log | Meta-agent may append, never rewrite history |
| **Locked** | The eval verifier code, the benchmark task definitions, the score aggregator, the keep-or-discard arbiter, `BOUNDARY.md` itself, the model selection in `PROGRAM.md` | Meta-agent may read; writing requires human approval |
| **Human-controlled** | `claude` binary, MCP server source code, `~/.claude/settings.json`, credentials, anything outside the run directory | Out of scope entirely |

`BOUNDARY.md` declares these surfaces explicitly. The meta-agent reads it before every edit. The first thing it does on startup is `Read /path/to/run/BOUNDARY.md` and surface in its working notes which classes it has identified.

This is the same discipline as autoagent's `# FIXED ADAPTER BOUNDARY: do not modify unless the human explicitly asks.` comment in `agent.py` — just generalized across skills + tools + prompts instead of one Python file.

---

## The directive file (`PROGRAM.md`)

Like autoagent's `program.md`, this file is **human-edited**. It tells the meta-agent what kind of harness to build, what benchmark to optimize, what constraints not to violate.

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

The `NEVER STOP` clause is autoagent's framing verbatim and is load-bearing. Without it, the meta-agent tends to pause for permission after every iteration, defeating the autonomy.

---

## Benchmark + scoring

Defer the rigor of the eval design to the `ce-evaluation` and `ce-advanced-evaluation` skills. The non-negotiable properties for this loop:

1. **Single scalar score.** The verifier outputs one number. If you need multi-dimensional rubric scoring, pre-aggregate into one number per run with documented weights. Multi-dimensional scores can be reported alongside, but the keep/discard decision uses the scalar.
2. **Reproducible.** Seed everything that can be seeded — random state, tie-breaking, model temperature. Two runs of the same harness should produce the same score within a small known variance. If they don't, average across N runs per harness state.
3. **Cheap to run.** The whole point of the loop is iteration count. If one eval pass takes an hour, you get few iterations. Aim for the suite to complete in minutes, scale only when individual iterations clearly need higher signal.
4. **Hard to game.** The meta-agent will learn the eval. Defend against this:
   - Lock the verifier code (see `BOUNDARY.md`)
   - Use held-out tasks the meta-agent never sees during ideation
   - Track per-dimension scores even when aggregating to one number, so a regression in one dimension is visible
   - Apply the **purged + embargoed CV** discipline from the `model-evaluation` skill when the benchmark involves trading metrics or time-series scoring

5. **Anti-overfit rule.** Borrow autoagent's test verbatim: *"If this exact task disappeared, would this still be a worthwhile harness improvement?"* If no, it's overfitting. Reject the change.

---

## Orchestration patterns

Pull directly from `ce-multi-agent-patterns`. The meta-agent itself runs as the top of one of four shapes. Pick once at the start of the run; don't switch mid-loop.

### Pattern A — Single meta-agent + N specialist subagents (default)

The canonical autoagent shape. One meta-agent reads the failure log, proposes a change, dispatches a specialist subagent via the `Agent` tool to actually edit the skill and run the eval.

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

Use when: the workload decomposes into "diagnose → propose → execute" and you want context isolation between diagnosis context (full failure log) and execution context (only the edit + the eval).

### Pattern B — Hierarchical (meta → planning → execution)

Meta proposes the direction. A planning subagent sketches N candidate changes. Execution subagents run them in parallel, each in their own worktree. Best candidate wins, others discard.

Use when: a single change-class is exhausted (e.g. prompt tuning has diminishing returns per `program.md`'s observation) and you want to explore a higher-leverage axis like tool design, which has more variance and benefits from parallel exploration.

Reference `ce-multi-agent-patterns` for the supervisor-bottleneck mitigations — cap candidate count at 3–5, constrain worker output schemas, never overload one supervisor.

### Pattern C — Pair (meta + critic)

Meta proposes a change. A critic subagent (different `subagent_type`) reviews the proposal *before* execution. Critic can veto. Then execution runs.

Use when: budget is tight and you can't afford to run the eval on weak ideas. The critic is a cheap filter.

Mitigation against sycophancy: give the critic an adversarial prompt that explicitly rewards disagreement. The `ce-multi-agent-patterns` gotcha #3 is real — without adversarial framing, the critic will rubber-stamp.

### Pattern D — Tournament

N candidate changes are proposed and executed in parallel via `run_in_background` Bash invocations or parallel `Agent` calls. Winner commits, losers discard.

Use when: you're at a fork — supervisor vs swarm, tool A vs tool B, prompt style 1 vs prompt style 2 — and you want the eval to arbitrate. Token-expensive (15× baseline per `ce-multi-agent-patterns` gotcha #2) so don't default to this.

### Why not "everything at once"?

Don't. Pattern selection is itself part of the harness. Mixing shapes mid-loop blows up the trace and makes failure attribution impossible. Pick a shape, run a budgeted block of iterations under that shape, then if it plateaus consider switching.

---

## Context engineering hygiene

The meta-agent will burn its own context faster than the task agent. Apply `ce-context-fundamentals`, `ce-context-optimization`, and `ce-context-compression`:

- **Lazy-load skills.** Don't `Read` every skill in the catalog on every turn. Use the `Skill` tool only when invoking, and `Read` only the SKILL.md of the skill being edited.
- **Compress old context.** When the meta-agent's session exceeds 50% of its context window, write a `CHECKPOINT.md` summarizing what's been tried, what was kept, what was rejected, and next planned ideation. The next turn (or, in long runs, the next session) reads `CHECKPOINT.md` instead of the full chat history. This is the autoresearch / `ce-context-compression` pattern.
- **Filter the MCP tool surface.** Don't expose every MCP tool on every turn. The meta-agent should explicitly enumerate which gateway routes it needs for the current iteration and route through mcp2cli with that narrowed surface. This is the consolidation principle from `ce-tool-design`.
- **Track context utilization.** If one subagent eats more than 50% of its allotted context budget, that's a red flag — likely it's reading too much. Investigate and add a `Read` budget to its prompt template.
- **Don't load the whole results.tsv.** Use `tail` to read recent rows, `grep` for specific commits, or write a small `summarize_results.py` script the meta-agent calls. The full history is for the human reviewer; the meta-agent needs the tail.

Cross-link: `neuro-harness` for the gateway routing, `mcp2cli` for the narrowed surface invocation pattern, `forge` for the router itself.

---

## Memory + state

Apply `ce-memory-systems` and `ce-filesystem-context`. The meta-agent externalizes everything; nothing lives only in chat history because the loop will outlive any single session.

Run-directory layout (mirrors autoagent + adds Claude Code specifics):

```text
orchestrator-runs/<run_id>/
  PROGRAM.md                 ← human-edited directive
  BOUNDARY.md                ← surface declarations (locked once written)
  results.tsv                ← append-only experiment ledger (autoagent format)
  log.md                     ← human-readable narrative log
  experiments/
    <iter>-<slug>.md         ← per-iteration notes (kept + discarded)
  rejected.md                ← rejected-attempts log (prevents rediscovery)
  CHECKPOINT.md              ← rotating session-handoff summary
  logs/
    trajectories/<iter>.json ← raw eval trajectories (the failure forensics)
    runlog.<iter>.txt        ← raw stdout/stderr of each eval pass
  skills-baseline/           ← git submodule or tarball of skills at run start
  eval/
    verify.py                ← LOCKED verifier (read-only for meta-agent)
    tasks/                   ← LOCKED benchmark task set
```

### `results.tsv` schema (autoagent-compatible)

Tab-separated, append-only, one row per iteration. Columns:

```text
commit	avg_score	passed	task_scores	cost_usd	status	description
```

- `commit` — short git commit hash on the harness branch
- `avg_score` — aggregate scalar from the verifier
- `passed` — fraction of tasks passed (e.g. `23/58`)
- `task_scores` — comma-separated per-task scores (for diff analysis)
- `cost_usd` — actual or estimated API spend for this iteration
- `status` — one of `keep` / `discard` / `crash`
- `description` — one-line summary of the change

`results.tsv` is a **run ledger, not a unique-commit ledger.** The same commit may appear multiple times if rerun for variance, exactly as in autoagent.

### Per-iteration experiment notes

Every iteration — kept or discarded — writes `experiments/<iter>-<slug>.md`:

- Hypothesis (one sentence)
- Change (which file, what diff, why)
- Pre/post task-score deltas (which tasks improved, which regressed, which were unchanged)
- Failure trajectory references that motivated the change
- Discard or keep reasoning
- Next-action implication

Discarded experiments still produce learning signal (`program.md` Discard Rule). They feed the rejected log to prevent the meta-agent from re-proposing the same idea three iterations later.

### `rejected.md`

Append-only. Each entry: hypothesis, what was tried, why it failed, score delta. Read at the start of every ideation step. The `ce-harness-engineering` skill calls this "search discipline" — preserve rejected attempts to avoid rediscovery.

### Branching

Each iteration is a commit on a benchmark branch. `keep` advances the branch; `discard` reverts. The branch name encodes the run: `harness-run-<run_id>`. Never force-push. Never amend. Each iteration is its own commit so the bisect/audit trail is intact.

Cross-link: `neuro-harness` for vault layer if the run artifacts mirror into Obsidian; `llm-wiki` for the experiment-log structure if integrating with the broader knowledge graph.

---

## Recursive self-improvement guardrails

These are non-negotiable. If the meta-agent bypasses one of them, stop the run and audit.

1. **Never modify the eval verifier.** A meta-agent that controls its own grader will Goodhart it. The verifier and the benchmark task set are LOCKED in `BOUNDARY.md`. If the meta-agent wants the verifier changed, it raises a human-approval request and stops.
2. **Never silently change `PROGRAM.md`.** Human-edited only. If the meta-agent thinks the directive should change, it writes a proposal to `experiments/` and pauses for human review.
3. **Never modify `BOUNDARY.md` without human approval.** Same rule. The boundary file is itself locked.
4. **Never bypass the model-selection constraint.** The model is pinned in `PROGRAM.md`. Switching models is a human flip.
5. **Stop after N consecutive non-improving iterations.** Default N=3. Plateau detection is a stopping condition, not a "try harder" prompt. Plateauing is signal.
6. **Hard wall-clock budget.** Set in `PROGRAM.md`. Enforce in the loop driver.
7. **Hard token + cost budget.** Same. Track per-iteration cost in `results.tsv`. Stop when cumulative cost crosses the cap.
8. **Never edit outside the run directory + the skill stack the run owns.** The meta-agent does not touch `~/.claude/settings.json`, does not modify hooks, does not edit other skills outside the editable set declared in `BOUNDARY.md`. Blast radius is bounded.
9. **Never disable a guardrail when stuck.** If the loop stalls, the answer is to surface to the human, not to silently relax constraints.
10. **Never run without git.** Every iteration is a real commit. No git, no run. This is the rollback floor.

The first four are the autoagent invariants restated. The rest extend them with Claude-Code-specific blast-radius rules from `ce-harness-engineering`'s metric-gaming-resistance section.

---

## Concrete workflow (one full overnight run)

This is the canonical sequence. Step numbers are checkpoints; the meta-agent can use `TaskCreate` / `TaskUpdate` to track them.

### Pre-flight (human, one-time)

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)
RUN_DIR=$HOME/orchestrator-runs/$RUN_ID
mkdir -p $RUN_DIR/{experiments,logs/trajectories}
cd $RUN_DIR
cp $REPO/skills/autonomous-orchestrator/templates/PROGRAM.template.md PROGRAM.md
cp $REPO/skills/autonomous-orchestrator/templates/BOUNDARY.template.md BOUNDARY.md
$EDITOR PROGRAM.md      # human fills in directive, budget, model pin
$EDITOR BOUNDARY.md     # human confirms surface declarations
git init && git checkout -b harness-run-$RUN_ID
git add . && git commit -m "Run $RUN_ID: pre-flight"
```

Then the human points Claude Code at the run dir and prompts something like:

> "Read PROGRAM.md and BOUNDARY.md. Run the autonomous-orchestrator loop. Don't stop until budget is hit."

### Step 1 — Baseline

Meta-agent does this first, exactly once.

```text
1.1 Read PROGRAM.md (full)
1.2 Read BOUNDARY.md (full)
1.3 Read existing results.tsv (likely empty — initialize header)
1.4 Run eval/verify.py against the unmodified skill stack
1.5 Record the baseline row in results.tsv with status=keep, description="baseline"
1.6 Write log.md preamble: timestamp, model, budget, baseline score
```

The first run is the unmodified baseline. Establish it before any change.

### Step 2 — Iteration

Repeat until budget or plateau.

```text
2.1 IDEATE
    - Read tail of results.tsv (last 5 rows)
    - Read rejected.md (last 10 rejections)
    - Read latest failed trajectories in logs/trajectories/
    - Group failures by root cause (categorize: missing tool, weak prompt,
      bad orchestration, verifier mismatch, missing capability)
    - Choose ONE hypothesis targeting a CLASS of failures, not a single task
    - Use TaskCreate to register the iteration with a clear title

2.2 APPLY
    - Identify the single file in the editable surface that will change
    - Spawn the right specialist via the Agent tool:
        * skill-editor for SKILL.md prose / structure changes
        * tool-editor for tool-description or tool-surface changes
        * prompt-editor for system-prompt or activation-phrase changes
        * orchestration-editor for changes to Skill/Agent/Task call patterns
    - Subagent makes the edit, commits to harness-run-$RUN_ID with a clear message
    - One file per iteration. Multi-file changes are tournaments, not single iterations.

2.3 BENCH
    - Subagent runs eval/verify.py
    - Capture stdout/stderr to logs/runlog.<iter>.txt
    - Capture trajectories to logs/trajectories/<iter>.json
    - Verifier emits a single scalar score + per-task breakdown

2.4 KEEP-OR-DISCARD
    - if new_score > baseline + ε: status=keep, baseline := new_score
    - elif new_score == baseline AND change is simpler: status=keep (simplicity rule)
    - else: status=discard, git revert <iteration-commit>
    - Append row to results.tsv
    - Write experiments/<iter>-<slug>.md (always — kept or discarded)
    - If discarded: append to rejected.md
    - TaskUpdate the iteration as complete

2.5 PLATEAU / BUDGET CHECK
    - If 3 consecutive discards in a row → flag plateau, stop, surface to human
    - If wall-clock exceeded → stop, surface to human
    - If cost cap exceeded → stop, surface to human
    - Otherwise → goto 2.1
```

### Step 3 — Wake-up summary

When the loop exits (budget, plateau, or human interrupt), the meta-agent writes a final summary:

```text
3.1 Best score across the run + which commit achieved it
3.2 List of kept changes in order, each with the score delta it produced
3.3 Top 3 failure modes that remain unfixed
3.4 Recommended next directive edit (for the human to consider)
3.5 Open questions / things the meta-agent could not decide autonomously
3.6 Write all of the above to log.md and to a final SUMMARY.md
3.7 Commit SUMMARY.md to the harness branch
```

The human wakes up, reads `SUMMARY.md`, decides whether to merge the branch or kick a new run with an updated directive.

---

## Cross-link to siblings

| Skill | When to reach for it | Relationship to this skill |
| --- | --- | --- |
| `relentless-inception` | Shipping a product autonomously, end-to-end install + tearsheet | Different target: ships the *product*. This one improves the *agent*. |
| `autoresearch` | Two-loop research orchestration with locked evaluator | Same loop shape; different artifact. Use autoresearch when the artifact is a research output, this one when the artifact is the harness. |
| `e2e-agentic-ML` | 11-stage ML lifecycle from data through deploy | Linear, not iterative. Use it for the ML pipeline; use this skill to improve the agent that runs the pipeline. |
| `ce-harness-engineering` | Building blocks for harness design (locked surfaces, durable logs, novelty gates) | **Read this BEFORE running the loop.** It is the conceptual foundation. |
| `ce-multi-agent-patterns` | Subagent coordination shapes | Reference for which orchestration pattern (A/B/C/D above) fits your workload. |
| `ce-context-fundamentals` / `ce-context-optimization` / `ce-context-compression` | Context-window hygiene | The meta-agent's context discipline depends on these. |
| `ce-memory-systems` / `ce-filesystem-context` | Externalized state, durable logs | The run-directory layout above is built on these patterns. |
| `ce-evaluation` / `ce-advanced-evaluation` | Eval design + rubric rigor + bias mitigation | The verifier you write lives in this domain. Don't shortcut it. |
| `ce-tool-design` | Designing tools the agent uses | When the loop's hypothesis is "add a tool", this is the design discipline. |
| `model-evaluation` | Trading-model evaluation, purged/embargoed CV | Use if the benchmark involves trading metrics or time-series scoring. |
| `neuro-harness` | The mcp2cli gateway routing rules | Every MCP call from the meta-agent or its subagents routes through here. |
| `mcp2cli` | CLI shape of any MCP server | The narrowed-tool-surface invocation pattern. |
| `forge` | The router itself | Slash-command invocations land here. |
| `gitnexus-*` | Code-graph queries on the current skill stack | Useful inside the IDEATE step when the hypothesis is structural. |
| `doc-sync-embed-verify` | Doc + knowledge-graph sync after skill edits | Run after a `keep` if the edit is large enough that downstream docs need re-ingestion. |

---

## Anti-patterns

These are the failure modes that show up over and over in autonomous loops. Codified so the meta-agent can recognize them in its own behavior.

- **Solving tasks directly.** The meta-agent finds a clever task-specific trick and applies it. Score goes up, but only on one task. The Overfitting Rule from `program.md` catches this: *"If this exact task disappeared, would this still be a worthwhile harness improvement?"* If no, reject.
- **Rewarding proxy metrics.** The score climbs but the agent is worse on the actual user-facing task. Defend with per-dimension scoring and held-out tasks per `ce-evaluation` / `ce-advanced-evaluation`.
- **Disabling guardrails when stalled.** A stall is signal that the current direction is exhausted. Relaxing constraints to escape the stall is how meta-agents Goodhart themselves into oblivion. Surface, don't relax.
- **Running without git.** Without git, every discard is destructive. Without a real commit per iteration, the audit trail is useless. No git, no run.
- **Forking the model mid-loop.** Model selection is locked in `PROGRAM.md` for a reason — model swaps confound the experiment trace. If the human wants to evaluate a model swap, that's a separate run.
- **Exposing the verifier to the edit surface.** A meta-agent that can edit its grader will. Verifier is LOCKED.
- **Mid-loop pattern-switching.** Picking supervisor at the start and switching to swarm halfway through makes the run uninterpretable. Pick once; if a switch is needed, end the run and start a new one with the new pattern declared upfront.
- **Multi-file changes per iteration.** One change per iteration. Bigger changes are tournaments (Pattern D) — declare them, parallelize them, don't smuggle them in as a single commit.
- **Chat-only memory.** All decisions go to disk. The meta-agent's chat history is volatile; the run directory is authoritative. `ce-harness-engineering` gotcha #2.
- **Letting the meta-agent edit this SKILL.md.** This skill is part of the harness that runs the meta-agent. If the meta-agent edits it, you've broken the boundary. List it in `BOUNDARY.md` as LOCKED.
- **Skipping the baseline.** First run is unmodified baseline. Skipping it means there's no score to hill-climb against.
- **Ignoring the rejected log.** Without re-reading rejections, the meta-agent will re-propose the same idea three iterations later and waste budget. Read `rejected.md` at the top of every IDEATE.

---

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

Default to Pattern A. Escalate only when the workload clearly warrants the extra coordination cost.

---

## References

- **Upstream — `kevinrgu/autoagent`** (MIT). The canonical autonomous-harness-engineering pattern this skill adapts. Key files quoted: `README.md`, `program.md` (Directive / Setup / What You Can Modify / Simplicity Criterion / Experiment Loop / Keep-Discard / Overfitting / NEVER STOP sections), `agent.py` (FIXED ADAPTER BOUNDARY comment + `create_tools` / `create_agent` / `run_task` structure).
- **Upstream — `muratcankoylan/Agent-Skills-for-Context-Engineering`** (MIT). The harness/context/eval/multi-agent discipline this skill is built on. Skills directly referenced: `harness-engineering`, `multi-agent-patterns`, `context-fundamentals`, `context-optimization`, `context-compression`, `memory-systems`, `filesystem-context`, `tool-design`, `evaluation`, `advanced-evaluation`.
- **Related skills in this repo:**
  - `relentless-inception` — product-shipping orchestrator (different target)
  - `autoresearch` — research-artifact orchestrator (same loop, different artifact)
  - `e2e-agentic-ML` — linear ML lifecycle
  - `neuro-harness` — gateway routing contract
  - `mcp2cli` — narrowed-tool-surface invocation
  - `forge` — slash-command router
  - `ce-harness-engineering`, `ce-multi-agent-patterns`, `ce-context-fundamentals`, `ce-context-optimization`, `ce-context-compression`, `ce-memory-systems`, `ce-filesystem-context`, `ce-tool-design`, `ce-evaluation`, `ce-advanced-evaluation` — the building blocks
  - `model-evaluation` — purged/embargoed CV for trading metrics
  - `gitnexus-*` family — code-graph queries on the skill stack
  - `doc-sync-embed-verify` — post-keep doc resync
- **Tools used (Claude Code primitives):**
  - `Read`, `Write`, `Edit`, `Bash` — file/state manipulation
  - `Skill` — invoking sibling skills lazily
  - `Agent` — dispatching specialist subagents (`subagent_type` field selects the role; pair with `run_in_background` for Pattern D)
  - `TaskCreate` / `TaskUpdate` — tracking the iteration as a unit of work
  - `AskUserQuestion` — surfacing budget exhaustion, plateau, or boundary-violation requests
- **Operating environment:** git (mandatory), mcp2cli + `/forge` gateway (mandatory), Claude Code with the model pinned in `PROGRAM.md`.
- **License attribution:** This skill is HyperFrequency original prose, but adapts the autoagent loop structure (MIT, kevinrgu) and the harness/multi-agent/context-engineering discipline (MIT, muratcankoylan). See `NOTICE.md` in this repo for the full attribution.
- **Last cross-checked:** 2026-05-24
