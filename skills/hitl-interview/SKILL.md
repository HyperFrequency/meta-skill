---
name: hitl-interview
version: 0.2.0
description: "Human-review stage of trajectory-miner (Loop 3): the anti-pattern review surface. Its scan workflow parks on an ApprovalRequest{kind:\"antipattern-review\"} gate (shared hitl.proto envelope) carrying trajectory-miner's AntiPattern/Issue clusters; this skill adjudicates them. Use it when a scan has emitted anti-patterns needing human review, when a finding's confidence is below threshold and needs a CONFIRM/REJECT/LABEL/BOUNDARY verdict, or when mined findings must become an Align-Evals few-shot store plus _llm_scores annotations. Per finding it presents EVIDENCE (traces, excerpts, diffs) and asks 3-7 questions ONLY when confidence < threshold, recording each verdict as a confidence-shifting evidence event. Auto-apply exists ONLY under hyper-sleep bounds (confidence cap, timeout, no deletions); else MANUAL. Do NOT use to MINE transcripts (trajectory-miner), rescue one live stuck node (background-rescue), run the fix loop (recursive-self-improvement / neuro-surgery), or as a generic blocking-input interviewer."
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion, Skill, Agent
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    upstream: none — original review surface for the neuro-centrifuge trajectory-miner loop
---

# HITL Interview — trajectory-miner review surface

`trajectory-miner` (Loop 3) mines a corpus of agent transcripts and emits **candidate anti-patterns** — clustered failure modes, each with evidence and a machine-assigned confidence. Most are unattended-safe to file. Some sit in the murky middle: the miner is not sure the cluster is real, or not sure how to label it, or not sure how wide its blast radius is. **This skill is the human-review stage for exactly those uncertain findings.**

You are the adjudication surface, not the miner and not the fixer. The scan workflow **parks** on an `ApprovalRequest{kind:"antipattern-review", payload:<issue batch>}` — the shared `hitl.proto` gate envelope — and hands you the batch. For each finding you present its clustered evidence, ask a small number of targeted questions **only when confidence is below the review threshold**, and record every decision as a durable **evidence event** that raises or lowers the finding's confidence and feeds an Align-Evals few-shot store. Every decision is logged to `_llm_scores` with `source_type: "annotation"` so the review itself is regression-gateable. Then you hand control back — you do not apply the fix.

## When to use

- A `trajectory-miner` scan has produced `trajectory-report.json` and parked on an `antipattern-review` gate with an issue batch awaiting human adjudication.
- One or more findings have `confidence < review_threshold` and need a human CONFIRM / REJECT / LABEL / BOUNDARY call before they can drive any downstream fix.
- You want mined findings converted into supervised signal: an Align-Evals few-shot store plus `_llm_scores` annotation rows.
- A `hyper-sleep` pass reached the review gate and wants to know which findings (if any) fall inside its auto-apply bounds vs. which must wait for a human.

## When NOT to use

- **Mining** transcripts for anti-patterns in the first place — that is `trajectory-miner`. This skill starts *after* the report exists.
- **Rescuing one live stuck node** — a single diverged/looping/rotted run is `background-rescue`, not a corpus review.
- **Running the fix loop** that consumes approved findings — proposal grading is `recursive-self-improvement`; per-item KB/skill repair is `neuro-surgery`. This skill grades the *finding*, not the *fix*.
- **Generic requirement/preference elicitation** — this is not a blocking-input interviewer. It reviews mined anti-patterns against evidence. If there is no `trajectory-miner` batch, this skill is the wrong tool.

Trigger test: *is there a batch of miner-produced anti-pattern findings that need a human verdict?* If yes, use this. If no, stop.

## The review loop

Work the parked batch one finding at a time. Depth for each step is in the references.

1. **Accept the gate envelope.** Read the `ApprovalRequest{kind:"antipattern-review"}` and its payload (the issue batch = a slice of `trajectory-miner`'s clusters). Validate the envelope shape and resolve every referenced trace/transcript before touching a single question. Contract: [`references/gate-envelope.md`](references/gate-envelope.md).
2. **Triage by confidence.** For each finding compare its confidence to `review_threshold`. **At or above threshold** ⇒ no question needed; record an auto-confirm evidence event and move on. **Below threshold** ⇒ it needs human input — proceed to step 3. Never ask about a finding the miner is already confident in; that trains the human to distrust the gate.
3. **Present clustered evidence.** For each below-threshold finding, assemble its evidence bundle: trace links, minimal transcript excerpts (goal + diverging turns), and before/after diffs where the miner proposed a fix. Scrub secrets first. Assembly rules: [`references/review-protocol.md`](references/review-protocol.md).
4. **Ask 3-7 targeted questions.** Pose CONFIRM / REJECT / LABEL / BOUNDARY questions — the four verdict types — in one batched `AskUserQuestion` round per finding (or per tight finding-group). Each carries the evidence-backed default. Question taxonomy, batching, and worked examples: [`references/review-protocol.md`](references/review-protocol.md).
5. **Record each decision as an evidence event.** Every verdict becomes an append-only evidence event that raises or lowers the finding's confidence, is written into the Align-Evals few-shot store, and is logged to `_llm_scores` with `source_type: "annotation"`. Schemas and the confidence-update rule: [`references/evidence-events.md`](references/evidence-events.md).
6. **Risk-tier the outcome and hand back.** Decide which confirmed findings may be auto-applied (only inside `hyper-sleep` bounds) and which default to MANUAL. Emit a resume summary and return control to the scan workflow — do not execute the fix. Tiering rules: [`references/risk-tiering.md`](references/risk-tiering.md).

## Core principles

- **Evidence before verdict.** No question is posed without the finding's trace links and excerpts resolved and shown. A verdict on unseen evidence is worthless as an annotation.
- **Ask only under the threshold.** Confidence gates every question. If the miner is already confident, the human is not consulted — the gate exists for the uncertain middle, not for rubber-stamping.
- **Every decision is signal.** Each verdict is an evidence event *and* an Align-Evals few-shot *and* an `_llm_scores` annotation. The review is itself a graded, regression-gateable artifact — a reviewer who drifts is caught by replaying old annotations.
- **Manual by default; auto-apply is the exception.** Only findings that clear `hyper-sleep`'s bounds (confidence cap, timeout, no deletions) may auto-apply. Everything else waits for a human. Mirror `neuro-surgery`: per-item, never batch-silent.
- **Grade the finding, not the fix.** You decide *is this a real anti-pattern, and what is it*. Whether/how to repair it belongs to `recursive-self-improvement` and `neuro-surgery` downstream.
- **Stay lateral.** You adjudicate and record, then return control. You never edit the agent, its prompts, its skills, or the transcripts.

## Failure modes to guard against

- **Batch-silent approval.** Approving a whole batch with one click is the cardinal sin — it is exactly what `neuro-surgery`'s per-item rule forbids. One verdict per finding, always. See [`references/risk-tiering.md`](references/risk-tiering.md).
- **Over-asking.** Questioning findings already above threshold floods the human and poisons the annotation store with trivial CONFIRMs. Re-check the triage in step 2.
- **Evidence-free verdict.** A CONFIRM with no resolvable trace is not a usable annotation — reject the finding back to the miner as `insufficient-evidence` rather than guess.
- **Auto-apply creep.** A finding that proposes a deletion, or exceeds the confidence cap, or arrives after the timeout window, is **never** auto-apply — it defaults MANUAL no matter how clean it looks. See the bounds in [`references/risk-tiering.md`](references/risk-tiering.md).
- **Annotation drift.** If the reviewer's verdicts stop matching replayed gold annotations in `_llm_scores`, the gate is regressing — surface it, do not keep annotating. See [`references/evidence-events.md`](references/evidence-events.md).
- **No-response / timeout.** The human never answers. Findings with a safe evidence-backed default are recorded `source: default-on-timeout`; below-threshold findings with no safe default are parked `verdict: UNRESOLVED` and the gate stays open. Never let a timeout auto-confirm an anti-pattern that would drive a deletion.

## References

- **[`references/gate-envelope.md`](references/gate-envelope.md)** — the shared `hitl.proto` `ApprovalRequest{kind:"antipattern-review"}` envelope, the issue-batch payload shape (how it maps to `trajectory-miner`'s clusters), and the park/resume handshake.
- **[`references/review-protocol.md`](references/review-protocol.md)** — assembling the evidence bundle (trace links, transcript excerpts, before/after diffs), the CONFIRM/REJECT/LABEL/BOUNDARY question taxonomy, confidence-threshold gating, batching, worked good/bad examples.
- **[`references/evidence-events.md`](references/evidence-events.md)** — the evidence-event schema, the confidence-raise/lower rule, the Align-Evals few-shot store, and `_llm_scores` annotation logging (`source_type: "annotation"`) for regression-gating the review.
- **[`references/risk-tiering.md`](references/risk-tiering.md)** — the MANUAL-by-default rule, the `hyper-sleep`-bounded auto-apply lane, and the three enforcement patterns (neuro-surgery per-item, recursive-self-improvement consortium pre-vote, meta_skill UncertaintyQueue).

## Cross-links

- `trajectory-miner` — **produces** the findings this skill reviews; the scan workflow parks on the `antipattern-review` gate. Tightly coupled: this skill's input schema is that skill's output.
- `neuro-surgery` — the per-item, never-batch-silent approval discipline this skill mirrors; also a downstream consumer that repairs confirmed findings.
- `recursive-self-improvement` — the consortium-graded fix loop that consumes confirmed anti-patterns as improvement targets; can pre-vote proposals before a human sees them.
- `hyper-sleep` — the only context in which auto-apply is permitted, and only inside its hard bounds (confidence cap, no deletions, timeout).
- `background-rescue` — sibling that rescues ONE live diverged node; this skill reviews mined failures in BATCH, after the fact. They do not overlap.
