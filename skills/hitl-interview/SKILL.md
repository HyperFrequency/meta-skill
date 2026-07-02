---
name: hitl-interview
version: 0.1.0
description: "Human-in-the-loop interview / elicitation for autonomous harnesses. Use when a long-running agent run must PAUSE and ask the human only for inputs it genuinely cannot get otherwise — blocking requirements, preferences, approvals/sign-off, disambiguation, or acceptance criteria — then resume with the answers threaded in as durable context. Focused protocol: batch open questions into one round, offer a safe default per question, never re-ask what was answered or is inferable, record answers to a durable ledger. Trigger on \"interview me\", \"ask me what you need\", \"elicit requirements\", \"pause and get my input\", \"HITL checkpoint\", or when an orchestrator (relentless-inception, autonomous-orchestrator) hits a gate needing human judgment. Do NOT use to re-ground a stalled/hallucinating node (use background-rescue), to interrogate a codebase (gitnexus), for research answerable from sources (deep-research), or for back-and-forth on a task you can just do — fires only when a missing human input is genuinely blocking."
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion, Skill, Agent
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    upstream: none — original HITL elicitation layer
    note: "Authored from the neuro-centrifuge harness gap-list summary; the vault HITL spec was not accessible at authoring time. Interview-ledger paths and gate names below are DEFAULTS — reconcile with the harness config if it defines its own."
---

# HITL Interview

An autonomous harness is only as good as its willingness to stop at the right moments. Stop too rarely and it confidently builds the wrong thing on a silent wrong assumption. Stop too often and it becomes a chat toy that can never run unsupervised. This skill is the discipline in between: it converts "I'm not sure what the human wants here" into **the minimum set of questions that are genuinely blocking**, asks them in one batched round with safe defaults, records the answers durably, and hands control back so the run continues.

You are the elicitation pass, not the executor. You do **not** solve the task. You produce (a) a validated set of human answers and (b) a durable record of them, so the calling agent resumes with real inputs instead of guesses.

## When to use this skill

Fire when an autonomous or long-running run reaches a point where progress requires a **human input it cannot obtain any other way**, in one of six categories:

1. **Blocking requirement** — a fact only the human has (target market, budget cap, which of two data sources is canonical, the deploy target).
2. **Preference** — multiple correct answers; the human's taste decides (naming, stack choice, tone, aggressiveness of a risk parameter).
3. **Approval / sign-off** — an irreversible or costly action needs a human yes (deploy, spend, delete, send, publish, allocate capital).
4. **Disambiguation** — the instruction genuinely supports >1 reading and they diverge materially.
5. **Acceptance criteria** — "done" is undefined and the human owns the definition.
6. **Missing precondition** — a credential name, an access grant, a file the human must provide.

Also fire when an orchestrator explicitly delegates a gate to you (see [`references/integration.md`](references/integration.md)).

## When NOT to use it

- The input is **inferable** from context, files, defaults, or prior answers — infer it and note the assumption; do not ask.
- The question is answerable from **sources / the web / a codebase** — use `deep-research`, `perplexity-search`, or `gitnexus` instead.
- A node has **stalled, rotted, or is hallucinating** — that is re-grounding, use `background-rescue`, not an interview.
- You are tempted to ask just to **confirm work you can verify yourself** — verify it (`verify`), don't ask.
- The task is small enough to **just do** — a single tool call beats a question.

The test: *if the human could reasonably answer "why are you asking me this, just decide" — you should not be asking.*

## The protocol (five steps)

Run these in order. Depth for each is in the references.

1. **Draft the candidate question list.** Every open decision the run faces right now. Do not filter yet.
2. **Filter to blocking-only.** Apply the [`references/blocking-criteria.md`](references/blocking-criteria.md) rubric to each candidate: is it blocking, inferable, or deferrable? Drop inferable (record the inferred value as an assumption) and deferrable (queue for a later gate). Keep only what blocks *now*.
3. **Check the ledger — never re-ask.** Load the interview ledger (default `state/interview-ledger.md`). Drop any question already answered, or answerable by combining prior answers. Re-asking is the cardinal sin of this skill.
4. **Batch and ask.** Pose all surviving questions in a **single** `AskUserQuestion` call (multiple questions per call), each with 2–4 concrete options **and a marked safe default**. Structured, not an essay. Schema, batching limits, and good/bad examples are in [`references/question-protocol.md`](references/question-protocol.md).
5. **Record and resume.** Write each answer (and each inferred assumption from step 2) to the ledger as durable context, then hand a clean resume summary back to the calling agent. Format and threading rules: [`references/answer-record.md`](references/answer-record.md).

## Core principles

- **Ask only what is truly blocking.** Every question must trace to a decision that cannot proceed without it. If you can name a defensible default and the cost of being wrong is low/recoverable, use the default and note it — don't ask.
- **Batch.** One round of N questions, not N rounds of one. Round-trips are the expensive resource, not tokens. Never trickle questions.
- **Always offer a safe default.** Each question ships with a recommended option the human can accept with one click. A good interview is answerable by pressing "default" five times.
- **Never re-ask.** Answered, inferable, or derivable-from-prior-answers ⇒ do not ask. The ledger is authoritative.
- **Record durably.** Answers outlive the session. Write them where the next agent (and the next run) will find them, with timestamp and provenance.
- **Stay lateral.** You elicit and record; you do not execute the underlying task. Return control immediately once answers are captured.

## Failure modes to guard against

- **No response / timeout** — the human walks away mid-run. Fall back to the marked safe defaults, record them as `answer: <default> (source: default-on-timeout)`, and continue only if every unanswered question had a safe default. If any un-defaulted question is still open, checkpoint the run and stop cleanly — do not guess a high-stakes answer. See [`references/answer-record.md`](references/answer-record.md).
- **Question flood** — you drafted 15 questions. Almost all are inferable or deferrable. Re-run step 2 harder; a well-run gate is usually 1–4 questions.
- **Approval smuggled as preference** — never present an irreversible action as a low-stakes multiple choice with the dangerous option as default. Approvals default to the *safe/no-op* option and say what is irreversible.
- **Ledger drift** — two runs, two ledgers, contradictory answers. Keep one ledger per project/goal; on conflict, most-recent-wins and flag the contradiction to the human as its own question.
- **Leading the witness** — options that are all one answer dressed up. Offer genuinely distinct choices plus a free-form escape hatch (`AskUserQuestion` allows the human to type their own).

## References

- **[`references/question-protocol.md`](references/question-protocol.md)** — `AskUserQuestion` schema and limits, batching rules, how to build safe defaults, worked good/bad question examples.
- **[`references/blocking-criteria.md`](references/blocking-criteria.md)** — the blocking-vs-inferable-vs-deferrable decision rubric, the six ask-categories, the no-re-ask check.
- **[`references/answer-record.md`](references/answer-record.md)** — the interview-ledger schema, threading answers back into a paused run, the resume summary, timeout/no-response handling.
- **[`references/integration.md`](references/integration.md)** — how `relentless-inception`, `autonomous-orchestrator`, `e2e-agentic-ML`, and background watchdogs invoke this skill at their gates, and how it differs from `background-rescue`.

## Cross-links

- `relentless-inception`, `autonomous-orchestrator`, `e2e-agentic-ML` — orchestrators that call this skill at a human-judgment gate.
- `background-rescue` — sibling lateral pass; use it when a node has **diverged**, use this when a run needs a **missing human input**. They do not overlap.
