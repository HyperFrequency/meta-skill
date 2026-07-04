---
name: temporal-design
description: Review, audit, or score a Temporal workflow design for correctness, production readiness, and best-practice compliance — either as an interactive critique or as an automated, non-interactive gate (replay-history determinism tests, versioning/patch-safety checks, payload-size wire assertions, and a rubric judge scoring against a versioned criteria schema). Use when asked to review a Temporal architecture, judge whether a design is production ready, flag anti-patterns or determinism/history/payload risks, assess Temporal fitness for a use case, give a thumbs up/down, or regression-gate authored workflow code in CI against a pinned baseline. Not for writing or debugging Temporal code (use temporal-developer), running the generic eval chassis / rubric-as-criteria-schema runner (skill-eval-runner), or scoring dynamic state-based graph-workflow state machines (graph-workflow-eval).
version: 0.2.0
---

# Temporal Workflow Design Critic

Use this skill to review a Temporal workflow design, spec, architecture document, implementation plan, pseudocode, workflow code, or code-generation output.

This skill is for critique and review, not implementation.

## Two paths: interactive review and automated gate

This skill has two entry points that share one rubric:

- **Interactive review** (default) — produces a human-facing critique with a
  verdict and severity-ranked findings. Everything below this section describes it.
- **Automated gate** — turns the same rubric into a non-interactive, versioned
  criteria schema and runs it as a pass/fail regression gate (static determinism
  analysis, replay-history tests, versioning/patch-safety checks, payload-size
  wire assertions, an SDK-capability bound, and a rubric judge), comparing a
  candidate against a pinned baseline so CI can block regressions. Take this path
  when asked to "gate this in CI", "score it non-interactively", "run the replay
  corpus", or "block the PR on regression". See
  [automated-gate.md](references/automated-gate.md) — do not re-derive the gate
  mechanics inline; that file owns them.

When unsure which path, run interactive review; the gate is for repeatable,
unattended scoring where a numeric verdict must beat noise.

## What this skill does

This skill helps you:

- determine whether a use case is a good fit for Temporal
- inspect usage of Temporal primitives
- identify determinism, retry, timeout, event-history, signal-volume, and payload-size risks
- detect anti-patterns and missing design decisions
- evaluate production readiness
- give concrete remediation guidance
- produce consistent review output across designs

## When to use this skill

Use this skill when the user asks you to:

- review a Temporal workflow design
- critique a Temporal architecture or implementation plan
- evaluate workflow code or pseudocode against best practices
- assess whether a design is production ready
- identify risks, anti-patterns, or missing decisions in a Temporal-based design
- score or checklist a Temporal design

Do not use this skill for:

- deep debugging of a live production incident
- replacing SDK documentation
- writing the full implementation unless the user explicitly asks for that
- deciding product strategy unrelated to Temporal workflow design

## Primary review goal

Prioritize:

1. correctness
2. operability
3. production readiness

Do not demand perfection. Accept reasonable tradeoffs, but clearly flag risks, anti-patterns, and missing information.

## Expected inputs

This skill works best when the user provides some combination of:

- deployment model (Temporal Cloud or self-hosted)
- use-case description
- workflow diagram
- workflow code or pseudocode
- Temporal UI execution history
- activity definitions
- signal, query, or update usage
- timeout and retry settings
- task queue and worker topology
- expected scale, volume, and duration

If important inputs are missing, explicitly call that out and mark affected checks as `inconclusive`.

## Review method

When reviewing a design, follow this sequence:

1. Decide whether the use case is actually a good fit for Temporal.
2. Inspect workflow-level correctness and determinism.
3. Evaluate use of Temporal primitives.
4. Check event-history growth, payload size, and long-running execution strategy.
5. Inspect retries, timeouts, idempotency, and cancellation behavior.
6. Evaluate worker topology, task queues, and routing choices.
7. Check visibility, versioning, and replay safety.
8. Return a structured critique with severity-ranked findings and actionable fixes.

## Reference materials

For detailed guidance during review, consult these supporting files:

- [rubric.md](references/rubric.md) — Complete review rubric covering Temporal fit, workflows, child workflows, activities, signals, queries, updates, workers, timers, side effects, data converters, visibility, versioning/replay safety, Continue-As-New, sessions, storage optimization, Saga/compensation, Nexus/cross-service, and SDK-specific constraints (sections 1-19).
- [checklist.md](references/checklist.md) — Structured pass/fail/inconclusive checklist for all review categories.
- [decision-guide.md](references/decision-guide.md) — Verdict rubric (approve, approve with changes, needs revision, high risk), open questions template, and optional structured JSON output format.
- [output-schema.json](references/output-schema.json) — JSON Schema for the machine-readable verdict output (verdict enum, severity-ranked findings, checklist, open questions). Validate machine-readable critiques against it for deterministic output.

For the **automated gate** path, consult these instead of (or after) the review files:

- [automated-gate.md](references/automated-gate.md) — the non-interactive gate: when to take it, how the rubric compiles into a versioned criteria schema, the six runners (static determinism analysis, replay-history tests, versioning/patch-safety checks, payload/wire-size assertions, SDK-capability bound, rubric judge), hard-fail invariants, regression-gate mechanics vs a pinned baseline, the score record, the determinism checklist, the meta-loop, the non-interactive invocation contract, and cross-skill handoff.
- [gate-criteria-schema.yaml](references/gate-criteria-schema.yaml) — a concrete, versioned example criteria schema (weighted deterministic + model-graded assertions, hard-fail invariants, threshold, capability inventory, regression settings) compiled from the interactive rubric.
- [gate-output-schema.json](references/gate-output-schema.json) — JSON Schema for the machine-readable gate result (subject, schema/corpus version, weighted score vs threshold, per-assertion and hard-fail results, baseline delta, pass/fail/inconclusive). Validate gate output against it so CI consumes a stable contract.

## Related skills (which adjacent tool wins)

This skill reviews **design fit** and defers deeper operational depth to the sibling skill that owns each area (mirroring the way code writing/debugging is deferred to `temporal-developer`). When a review needs depth in one of these areas, hand off:

- **temporal-cloud** — Temporal Cloud connection, account/namespace limits, retention, and `tcld` operations. This skill flags design-level limit risks; `temporal-cloud` owns the operational detail.
- **temporal-observability** — search attributes, visibility, and operational monitoring depth. This skill checks search attributes are visibility-only and within limits; `temporal-observability` owns observability setup.
- **temporal-workertuning** — worker concurrency, poller counts, rate limits, and task-queue throughput tuning. This skill reviews topology and queue-split intent; `temporal-workertuning` owns the tuning knobs.
- **temporal-developer** — writing and debugging the actual workflow/activity code (this skill does not implement). When the automated gate fails and the fix requires editing the workflow (add a patch marker, move I/O into an activity, shrink a payload), hand the failing assertions to `temporal-developer`, then re-run the gate.

The **automated gate** path additionally defers to two eval-chassis siblings:

- **skill-eval-runner** — owns the generic evaluation chassis (rubric-as-versioned-criteria-schema, deterministic + model-graded assertion runners, trials/variance, baseline regression gating) as a reusable engine. This skill supplies the *Temporal-specific* criteria schema, replay-corpus runner, and capability inventory; defer the general runner mechanics there instead of re-implementing them.
- **graph-workflow-eval** — owns scoring **dynamic state-based graph workflows** (state-transition coverage, checkpoint/resume fidelity, interrupt round-trip, fanout/join determinism, replay *equivalence*). If the subject is a graph state machine rather than a Temporal workflow, route there; the two gates are complementary.

## Output contract

Always return results in this structure:

```md
# Workflow Design Critique

## Verdict
- status: approve | approve_with_changes | needs_revision | high_risk
- summary: <1-3 paragraph summary>

## Top Issues
1. [severity] <issue title>
   - why it matters
   - evidence from design
   - recommended fix

## Category Review
### Temporal fit
### Workflows
### Child Workflows
### Activities
### Signals
### Queries
### Updates
### Workers and Task Queues
### Timers / Schedules / Cron
### Data / Payloads / Converters
### Visibility
### Versioning
### Long-running execution
### Saga / Compensation
### Nexus / Cross-service

## Open Questions
- <question>

## Checklist Result
- pass/fail/inconclusive per item
```

## Severity levels

Use only these severity levels:

- `critical` — likely to fail, become non-deterministic, exceed limits, or cause production incidents
- `high` — serious design problem likely to impair correctness, scale, or operability
- `medium` — suboptimal design likely to cause friction, cost, or maintenance issues
- `low` — improvement opportunity or missing optimization
- `info` — observation or tradeoff explanation

## Default judgments

Apply these defaults unless the design clearly justifies otherwise.

### Local activity vs regular activity

Default to regular activities.

Use local activities only when very short execution and high-throughput fan-out justify them.

### Child workflow vs activity

Default to activity.

Use child workflows only when partitioning, lifecycle isolation, or routing semantics justify them.

### Workflow-to-workflow communication

Acceptable options include:

- signals
- queries
- updates
- **Nexus** — the recommended pattern for cross-namespace / cross-service interaction (GA; Go and Java SDKs). See rubric section 18.
- activity-mediated client calls for cross-namespace interaction only as a fallback when Nexus is not available in the target SDK

### Large payload handling

Prefer:

- passing references
- moving data-heavy work into activities
- compression
- explicit handling over hidden remote payload fetches

### Large workflow history

Prefer:

- Continue-As-New
- partitioning with child workflows where justified
- reducing per-event data size and message volume

### Parallelism

Parallel execution should use async invocation patterns with promise or future collection and later aggregation.

### Worker-specific activity queues

Use when capabilities, locality, security, or rate control justify them.

### Schedule vs timer

Use timers for relative delays inside workflows.

Use schedules for calendar-based or recurring launches.

## Reviewer operating style

When using this skill:

- be specific, practical, and conservative
- do not assume missing details are safe
- distinguish between blocking issues and reasonable tradeoffs
- provide concrete remediation guidance, not vague advice
- clearly separate evidence, risk, and recommendation
- mark missing-information areas as `inconclusive` instead of guessing

## Anti-pattern catalog

Always call out these critical, must-flag anti-patterns when present:

- non-deterministic workflow logic
- workflow logic depending directly on external mutable state
- passing large data blobs through workflow history
- activity side effects without idempotency
- signal floods against a single workflow
- search attributes used as business-state storage
- workflow retry policy used to compensate for transient activity failures

High-risk and medium-risk anti-patterns (child workflows for code organization, misused local activities, schedules-vs-cron misuse, missing Continue-As-New, missing versioning/replay strategy, identical timeouts across activities, over-fragmented activities, assuming strong consistency for memos/visibility, arbitrary task-queue splits, and missing Saga/compensation for multi-step external mutations) are detailed inline in the relevant [rubric.md](references/rubric.md) sections — flag them there during the category walk.

## Maintainer note

Keep this skill:

- stable enough for repeatable agent use
- readable by humans
- extensible as Temporal features evolve
- opinionated toward production safety

When updating, preserve:

- explicit rules
- default recommendations
- anti-pattern detection
- structured output expectations
- practical review questions
