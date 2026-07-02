# Concrete workflow (one full overnight run)

Deep reference for `autonomous-orchestrator`. This is the canonical sequence. Step
numbers are checkpoints; the meta-agent can use `TaskCreate` / `TaskUpdate` to
track them.

## Pre-flight (human, one-time)

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

> "Read PROGRAM.md and BOUNDARY.md. Run the autonomous-orchestrator loop. Don't
> stop until budget is hit."

## Step 1 — Baseline

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

## Step 2 — Iteration

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

## Step 3 — Wake-up summary

When the loop exits (budget, plateau, or human interrupt), the meta-agent writes a
final summary:

```text
3.1 Best score across the run + which commit achieved it
3.2 List of kept changes in order, each with the score delta it produced
3.3 Top 3 failure modes that remain unfixed
3.4 Recommended next directive edit (for the human to consider)
3.5 Open questions / things the meta-agent could not decide autonomously
3.6 Write all of the above to log.md and to a final SUMMARY.md
3.7 Commit SUMMARY.md to the harness branch
```

The human wakes up, reads `SUMMARY.md`, decides whether to merge the branch or
kick a new run with an updated directive.
