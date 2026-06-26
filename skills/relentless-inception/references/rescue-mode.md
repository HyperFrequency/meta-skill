# Rescue mode

Rescue is what makes this skill survive its own failures. It's not a fallback — it's a designed escape hatch that fires automatically when the orchestrator gets stuck.

The premise: the orchestrator can get stuck in ways the orchestrator can't see, because it's the one stuck. Recovery requires *fresh context* and *fresh attention* from a different model. Rescue provides both.

---

## Triggers (any one fires rescue)

1. **N consecutive failures on the same unit** (default N=3). Per-unit retry budget exhausted with no progress.
2. **Unattended stall**: `STALL_MINUTES` (default 12) of no agent output AND no tool calls. Watched by the background-agent via the Stop hook trail.
3. **Dead process**: a background subprocess spawned by this skill exits non-zero without writing a status report.
4. **Hook misfire**: a hook installed by this skill (`relentless_relay.sh`, `stall_watchdog.sh`, `status_line.sh`) returns non-zero on three consecutive invocations.
5. **Adversarial-review escalation**: any of the three gates fails its max-iteration budget (3 retries).
6. **Manual**: the user types `# RELENTLESS-RESCUE` into the chat, which the relay hook intercepts and converts into a rescue trigger.

---

## What rescue does (the 7 steps)

### 1. Background-agent reads the situation

`background-agent` (default `codex-latest --effort medium`) gets passed:

- The full session log so far
- The tool-call trace
- The current run manifest
- The last successful checkpoint marker
- The trigger reason (which of the six above fired)

Its job is *diagnosis only* — surface *what* is stuck and *why*. It doesn't propose a fix; that's the consortium's job.

Output: `~/.claude/relentless-inception/runs/<run_id>/rescues/<cycle>/diagnosis.md`

### 2. Consortium proposes a fix

Two fresh contexts spawn in parallel:

| Slot | Model               | Effort |
|------|---------------------|--------|
| Lead | gpt-5.5 (router)    | xhigh  |
| Co-pilot | opus-latest        | xhigh  |

Each reads the diagnosis + a curated subset of the session log (just enough to be informed, not enough to inherit the stuck thinking). They independently propose:

- What state to restore the orchestrator to
- What changes to make to plan/manifest before re-entering
- Whether any skill / hook / agent definition needs editing

Output: `~/.claude/relentless-inception/runs/<run_id>/rescues/<cycle>/{lead,copilot}-proposal.md`

### 3. Triple-gate review of the proposals

Both proposals run through the standard summarize-gate (3 reviewers in parallel). The gate produces:

- A unified rescue plan (lead + copilot, reconciled, with reviewer notes incorporated)
- Or a `regenerate` verdict, in which case the consortium gets the reviewers' notes and tries again

Max 3 attempts to produce an approved rescue plan. If still failing after 3, the run pauses for human intervention.

### 4. Approved plan → markdown summary

The approved rescue plan is written to:

```
~/.claude/relentless-inception/runs/<run_id>/rescues/<cycle>/approved.md
```

Format (rigid — the relay step depends on it):

```markdown
# RELENTLESS-INBOX

Run ID: <run_id>
Resumes from: <last-good-checkpoint>
Reason for rescue: <trigger>
Cycle: <N>

## What to do next
<numbered list of next actions, each one a complete instruction>

## Constraints that still apply
<list of things that must NOT change>

## Open questions for the user (or null)
<if any — these are surfaced at next user interaction>

## Self-improvement edits applied
<list of edits to skill/hook/agent files, with sha and rationale>
```

### 5. Self-improvement pass

Before clearing context, the background-agent inspects:

- Recent **hook misfires** — should the hook be patched? Renamed? Removed?
- Recent **tool-call errors** — does a guard need adding to a script? Is a deferred tool not being loaded?
- Recent **drift moments** — was the orchestrator following an outdated note in `SKILL.md`? Should an `agents/<role>.md` be more explicit?

Any proposed edits get adversarial-reviewed before applying. Applied edits are listed in the rescue summary's "Self-improvement edits applied" section so the user can audit them.

### 6. Clear context via the relay

`scripts/relentless_relay.sh` runs the proven tmux-driven `/clear` + paste sequence:

1. Save `approved.md` to `~/.claude/lateral-pass/pending-relentless.md`.
2. Send `/clear` to the active Claude Code session.
3. Wait 5 seconds.
4. Paste the body of `approved.md` (sentinel line stripped) + Enter.
5. Move the pending file to `archive/`.

The result: a fresh-context orchestrator session with the rescue plan as its first user prompt.

### 7. Continue from checkpoint

The fresh orchestrator reads the rescue plan, picks up the run manifest, spawns subagents from the last good checkpoint, and proceeds. The previous rescue cycle is logged in the manifest under `rescue_cycles`; the next phase's adversarial-review reads it as additional context.

---

## What rescue does NOT do

- **Does not retry the same approach.** If the lead+copilot consortium proposes "just retry," the gate rejects it. Rescue must change *something* about the approach.
- **Does not modify production code without the gate.** All self-improvement edits go through adversarial-review.
- **Does not run forever.** Three failed rescue cycles in a row pauses the run for human intervention.
- **Does not bypass the kill switch.** `~/.claude/relentless-inception/KILL` still wins.

---

## Implementation

`scripts/rescue.sh` is the entrypoint. It orchestrates steps 1-7 above. Each step writes intermediate artifacts so the rescue itself is recoverable.

`scripts/stall_watchdog.sh` is the trigger detector — it runs as the Stop hook and as a periodic check. When it detects a stall, it writes a trigger file at `~/.claude/relentless-inception/triggers/rescue-<run_id>-<timestamp>.json` which the orchestrator polls.

`scripts/relentless_relay.sh` is the tmux relay. It is the only piece of the skill that touches an interactive session — every other component runs from background processes.

---

## Designing your run to be rescue-friendly

Two practices reduce the chance of needing rescue, and make it cheaper when it happens:

1. **Write checkpoints often.** After every phase, the orchestrator writes a checkpoint to the manifest. Make phases small enough that losing one phase's worth of work is acceptable.
2. **Keep dev-worker prompts self-contained.** When a dev-worker prompt requires "context from earlier in the conversation," it can't be re-run cleanly after rescue. Bake the context into the prompt.

These are also good practices for non-rescue runs.
