# Integration — how orchestrators invoke this skill

`hitl-interview` is a **gate primitive**. Autonomous orchestrators run unsupervised for long stretches, but every one of them has moments where correct progress requires a human input. Instead of each orchestrator re-implementing its own ad-hoc "let me ask the user…" prose, they delegate that moment to this skill and get back a validated answer set plus a durable ledger entry.

## The invocation contract

An orchestrator calls this skill at a gate with:
- the **candidate decisions** it faces at this gate (or lets the skill draft them),
- the **ledger path** (so prior answers are honored — no re-asking),
- the **gate name** (for provenance).

The skill returns:
- a resume summary (settled decisions + recorded assumptions + still-open items),
- an updated ledger,
- control, immediately (it does not execute the orchestrator's work).

If nothing survives the blocking filter, the skill returns "no blocking questions — proceed with recorded assumptions" and the run never actually interrupts the human. That non-interruption is a success, not a no-op.

## Per-orchestrator wiring

### `relentless-inception`
The nuclear long-running orchestrator with triple-gated adversarial review (planning / phase / summarization). Delegate to `hitl-interview` at the **planning gate** (elicit acceptance criteria, scope boundaries, the "definition of green" for the proof tearsheet) and at any **approval gate** before an irreversible ship (deploy, spend, publish). Batch a whole phase's open questions into one interview round at the phase boundary rather than interrupting mid-phase. Write to the run's decisions store if it has one; else `state/interview-ledger.md`.

### `autonomous-orchestrator`
Targets the *harness* itself (recursive self-improvement). Use `hitl-interview` to elicit the **benchmark's success definition**, the **budget/stop condition**, and **approval to overwrite the agent's own skills/config** — high-stakes, un-defaultable approvals that must block per `answer-record.md`.

### `e2e-agentic-ML`
Reserves specific decisions for the human (capital allocation, Stage-10 deploy, Stage-1 frame override). Those reserved decisions ARE this skill's job: at each such checkpoint, invoke `hitl-interview` to elicit and record, then let the pipeline continue autonomously on everything else.

### Background watchdogs / goal-loops
A watchdog that detects "this node needs a human input it doesn't have" routes here. But a watchdog that detects "this node has **stalled, rotted, or is hallucinating**" routes to `background-rescue` instead — see below.

## `hitl-interview` vs `background-rescue`

Both are **lateral passes** that don't finish the underlying work — but they fire on opposite conditions and must not be confused:

| | `hitl-interview` | `background-rescue` |
| --- | --- | --- |
| Fires when | the run is healthy but **missing a human input** | a node has **diverged** — stalled, context-rotted, hallucinating, looping |
| The gap is | outside the agent (in the human's head) | inside the agent (degraded context) |
| Produces | validated human answers + durable ledger | one clean re-grounding prompt |
| Hands back to | the orchestrator, to continue | the original stronger agent, to restart clean |

If a node is looping, do **not** interview the human about it — that just adds a human to a broken loop. Rescue it first; interview only if, once re-grounded, it turns out a genuine human input is missing.

## Placement discipline

- **Batch at boundaries.** Collect a phase/stage's open questions and ask once at its edge, not scattered mid-work. One interruption per gate.
- **Honor the shared ledger.** All orchestrators sharing a project share one ledger so an answer given to one is visible to all — never re-asked.
- **Return fast.** The skill's value is the *decision*, not the *doing*. It records and hands back; the orchestrator owns execution.
