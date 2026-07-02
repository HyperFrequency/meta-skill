# Gateway contract, context hygiene, memory, and run layout

Deep reference for `autonomous-orchestrator`. Read when wiring the run directory,
the MCP routing, or the externalized state.

## The required tooling — unified gateway contract

This skill obeys the **neuro-harness gateway contract** like every other skill in
this repo. All MCP traffic routes through `/forge` → mcp2cli. The meta-agent does
not call upstream services directly when a gateway route exists.

- Documentation lookup → `docs-dual-lookup` (Context7 + Auggie in parallel) when
  researching API surfaces of libraries the meta-agent might want to call.
- Code-graph queries on the current skill stack → `gitnexus` via the gateway.
- Knowledge-graph + content-gap detection on the eval failure log → `infranodus`
  via the gateway.
- Vault read/write for run artifacts → `turbovault` via the gateway, or direct
  filesystem writes under
  `~/Vaults/neuro-quant-vault/orchestrator-runs/<run_id>/` when the agent is
  writing many small files (filesystem is faster for the loop).
- AST queries on skill markdown / agent prompts when the agent wants to refactor
  structure → `tree-sitter` via the gateway.

Direct MCP calls bypass the local-only routing pin
(`project_infranodus_local_only.md`) and break the doc-sync hook discipline.
Always go through the gateway.

## Benchmark + scoring

Defer the rigor of the eval design to the `ce-evaluation` and
`ce-advanced-evaluation` skills. The non-negotiable properties for this loop:

1. **Single scalar score.** The verifier outputs one number. If you need
   multi-dimensional rubric scoring, pre-aggregate into one number per run with
   documented weights. Multi-dimensional scores can be reported alongside, but the
   keep/discard decision uses the scalar.
2. **Reproducible.** Seed everything that can be seeded — random state,
   tie-breaking, model temperature. Two runs of the same harness should produce
   the same score within a small known variance. If they don't, average across N
   runs per harness state.
3. **Cheap to run.** The whole point of the loop is iteration count. If one eval
   pass takes an hour, you get few iterations. Aim for the suite to complete in
   minutes, scale only when individual iterations clearly need higher signal.
4. **Hard to game.** The meta-agent will learn the eval. Defend against this:
   - Lock the verifier code (see `BOUNDARY.md`)
   - Use held-out tasks the meta-agent never sees during ideation
   - Track per-dimension scores even when aggregating to one number, so a
     regression in one dimension is visible
   - Apply the **purged + embargoed CV** discipline from the `model-evaluation`
     skill when the benchmark involves trading metrics or time-series scoring
5. **Anti-overfit rule.** Borrow autoagent's test verbatim: *"If this exact task
   disappeared, would this still be a worthwhile harness improvement?"* If no,
   it's overfitting. Reject the change.

## Context engineering hygiene

The meta-agent will burn its own context faster than the task agent. Apply
`ce-context-fundamentals`, `ce-context-optimization`, and
`ce-context-compression`:

- **Lazy-load skills.** Don't `Read` every skill in the catalog on every turn.
  Use the `Skill` tool only when invoking, and `Read` only the SKILL.md of the
  skill being edited.
- **Compress old context.** When the meta-agent's session exceeds 50% of its
  context window, write a `CHECKPOINT.md` summarizing what's been tried, what was
  kept, what was rejected, and next planned ideation. The next turn (or, in long
  runs, the next session) reads `CHECKPOINT.md` instead of the full chat history.
  This is the autoresearch / `ce-context-compression` pattern.
- **Filter the MCP tool surface.** Don't expose every MCP tool on every turn. The
  meta-agent should explicitly enumerate which gateway routes it needs for the
  current iteration and route through mcp2cli with that narrowed surface. This is
  the consolidation principle from `ce-tool-design`.
- **Track context utilization.** If one subagent eats more than 50% of its
  allotted context budget, that's a red flag — likely it's reading too much.
  Investigate and add a `Read` budget to its prompt template.
- **Don't load the whole results.tsv.** Use `tail` to read recent rows, `grep`
  for specific commits, or write a small `summarize_results.py` script the
  meta-agent calls. The full history is for the human reviewer; the meta-agent
  needs the tail.

Cross-link: `neuro-harness` for the gateway routing, `mcp2cli` for the narrowed
surface invocation pattern, `forge` for the router itself.

## Memory + state

Apply `ce-memory-systems` and `ce-filesystem-context`. The meta-agent
externalizes everything; nothing lives only in chat history because the loop will
outlive any single session.

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

`results.tsv` is a **run ledger, not a unique-commit ledger.** The same commit may
appear multiple times if rerun for variance, exactly as in autoagent.

### Per-iteration experiment notes

Every iteration — kept or discarded — writes `experiments/<iter>-<slug>.md`:

- Hypothesis (one sentence)
- Change (which file, what diff, why)
- Pre/post task-score deltas (which tasks improved, which regressed, which were
  unchanged)
- Failure trajectory references that motivated the change
- Discard or keep reasoning
- Next-action implication

Discarded experiments still produce learning signal (`program.md` Discard Rule).
They feed the rejected log to prevent the meta-agent from re-proposing the same
idea three iterations later.

### `rejected.md`

Append-only. Each entry: hypothesis, what was tried, why it failed, score delta.
Read at the start of every ideation step. The `ce-harness-engineering` skill calls
this "search discipline" — preserve rejected attempts to avoid rediscovery.

### Branching

Each iteration is a commit on a benchmark branch. `keep` advances the branch;
`discard` reverts. The branch name encodes the run: `harness-run-<run_id>`. Never
force-push. Never amend. Each iteration is its own commit so the bisect/audit
trail is intact.

Cross-link: `neuro-harness` for vault layer if the run artifacts mirror into
Obsidian; `llm-wiki` for the experiment-log structure if integrating with the
broader knowledge graph.
