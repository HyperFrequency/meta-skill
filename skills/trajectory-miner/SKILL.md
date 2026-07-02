---
name: trajectory-miner
version: 0.2.0
description: "Loop-3 corpus miner over PAST agent runs. Ingests OTel spans, first-party .traj artifacts, Claude Code *.jsonl, and lightspeed/forgecode logs; scrubs secrets/injection/PII before storage; segments sessions into phases (Recon/Change/Validation/WrapUp) and gates junk; runs VERSIONED Scanners (doom loops, stuck patterns, context-degradation, rollback/correction, recursion + cost anomalies); clusters incidents into versioned AntiPatterns ('NEVER X when Y') and Issues, then publishes a VERSIONED anti-pattern registry consumed by skill heals, prompt mutations, judge criteria, and rescue triggers, routing uncertain ones to hitl-interview. Use when you have many past sessions/traces and want SYSTEMIC failures mined for harness improvement, or to triage a benchmark run after the fact. NOT for rescuing ONE live stuck node (background-rescue), running the improvement loop that consumes the registry (recursive-self-improvement), or debugging one known bug in a transcript — corpus-level, read-only, ends at the registry."
license: HyperFrequency original. StuckDetector heuristics re-implemented from the OpenHands algorithm (described, not copied). Optional reflective-mutation handoff targets the MIT gepa/gepars crate's public API.
---

# Trajectory Miner

Read a **corpus** of past agent runs and surface the failure modes that recur
across it. You are a read-only miner: you ingest and scrub many sessions, detect
failure *incidents* deterministically, cluster them into named **AntiPatterns**
and **Issues**, and publish a **versioned anti-pattern registry** with
representative failing trajectories. You never edit the agent, never rescue a
live run, and never fabricate an incident the traces don't support.

The registry feeds *other* systems — skill-heal loops, reflective prompt
optimizers, LLM-judge panels, rescue watchdogs, and human reviewers. **Your job
ends at the registry.** You produce the failure signal; someone else applies the
fix.

## When to use vs. when not

Use this skill when:
- You point at a directory/store of past runs (OTel traces, `.traj`, Claude Code
  `*.jsonl`, lightspeed/forgecode logs) and ask "what keeps going wrong", "find
  recurring failures", "mine my sessions", "build me an anti-pattern registry".
- You want a durable, queryable signal to **drive** harness improvement.
- You are triaging a benchmark or overnight autonomous run *after the fact*.

Do NOT use this skill for:
- **One live stuck node** — re-grounding a single diverged run is `background-rescue`.
- **Running the fix loop** that consumes the registry — `recursive-self-improvement`
  (graded, HITL) or `autonomous-orchestrator` (harness hill-climbing).
- **Debugging one known bug in one transcript** — just read it; this is
  corpus-level statistics, not single-case debugging.

## The Loop-3 pipeline

Five stages, strictly ordered. Do not skip ahead — scanners on an unsegmented,
unscrubbed stream cluster on the wrong fields and leak secrets. Each stage routes
to a reference for the concrete field maps, schemas, thresholds, and formulas.

1. **INGEST + SCRUB** → `references/ingest-and-scrub.md`
   Adapt all four sources — OTel GenAI spans, first-party `.traj` proto, Claude
   Code `*.jsonl`, lightspeed/forgecode logs — into ONE normalized `TurnEvent[]`
   contract. **Scrub before storage:** secret scanner, prompt-injection
   quarantine, PII anonymizer. Nothing raw is persisted. Capture `goal_text`
   (first user turn) and a stable `input_sig` per tool call.

2. **SEGMENT + GATE** → `references/segment-and-gate.md`
   Label every event with a phase — **Recon / Change / Validation / WrapUp** —
   and coalesce phase spans. Then score `session_quality ∈ [0,1]` and **gate out
   junk** below `min_score` (default 0.3) before expensive scanning — but never
   gate a short *failure* (refusal / cascade / quarantine still get scanned).

3. **SCAN** → `references/scanners.md`
   Run each deterministic **Scanner** (a versioned criteria schema) over each
   gated, segmented session: **doom loops** (`[A,A,A]` and `[A,B,C][A,B,C]`
   signature cycles), **stuck patterns** (3+ monologue, 6+ ping-pong, context-
   window-error loops — OpenHands StuckDetector), **context degradation**
   (lost-in-middle / poisoning / distraction / confusion / clash), **rollback /
   correction / failure signals**, and **infinite-recursion + cost anomalies**.
   Every incident cites a real `turn_range` and its `criteria_version`.

4. **CLUSTER** → `references/cluster-and-act.md`
   Group incidents by `(source_type, mode, failed-action similarity)` —
   deterministic bucket first, embedding merge for fuzzy modes. Each cluster →
   an **AntiPattern** `{rule:"NEVER X when Y", instead, severity,
   confidence=n/(n+2)}` and an **Issue** `{cause, suggestedFix, tracesQuery,
   severity, occurrences, firstSeen/lastSeen}`. Drop sub-`min_support` clusters
   to an appendix.

5. **ACT + REVIEW** → `references/cluster-and-act.md`
   Publish confirmed patterns to the **versioned anti-pattern registry**
   (append/supersede, provenance-tagged, re-derivable) consumed by **skill
   heals, prompt mutations, judge criteria, and rescue triggers**. Uncertain or
   high-constraint patterns start as `candidate` and hand off to **`hitl-interview`**
   for human confirmation before promotion. This skill never applies a fix.

## Versioning discipline (cross-cutting invariant)

Everything downstream is only trustworthy because everything upstream is
versioned. Record in the run header: `segmenter_version`, `gate_version`
(+ `min_score`, `min_events`), each scanner's `criteria_version`, `min_support`,
and the registry `schema_version`. Bumping a scanner's criteria does NOT
retroactively rewrite incidents — old ones keep their version; the corpus is
re-scanned deliberately and the registry records the transition. This is what
makes "did fixing X actually reduce mode Y" answerable.

## Boundaries & the miner's own failure modes

- **Read-only.** Never modify traces, agent config, prompts, or skills. You emit
  a registry; consumers decide what lands.
- **Evidence-bound.** No incident without a real, citable `turn_range`; no
  AntiPattern below `min_support`. A cluster you cannot point at is not published.
- **Corpus, not case.** A single failure is an appendix one-off, never a headline
  pattern. `confidence=n/(n+2)` keeps small-n patterns humble.
- **Scrub is non-negotiable and upstream.** If it can't run, ingest stops —
  never persist or judge unscrubbed text. Quarantined injection content stays out
  of every LLM-judged step.
- **Schema drift.** Source formats evolve. If a large fraction of lines/spans fail
  to normalize, stop and report the parse rate rather than mine a corrupt stream.
- **False-positive-prone modes** (context-degradation, hallucination-flavored):
  keep the excerpt, downgrade to `low` when unsure, and route to `hitl-interview`
  rather than auto-confirm — over-eager promotion poisons every consumer at once.

## References

- `references/ingest-and-scrub.md` — the four source adapters (OTel, `.traj`
  proto, Claude `*.jsonl`, lightspeed/forgecode), the `TurnEvent` contract,
  `input_sig`, and the three-stage scrub pipeline.
- `references/segment-and-gate.md` — phase segmentation and the session-quality gate.
- `references/scanners.md` — the versioned `Scanner` trait, the `Incident`
  schema, and the full detector catalog with thresholds.
- `references/cluster-and-act.md` — clustering, `AntiPattern`/`Issue` shapes,
  `confidence=n/(n+2)`, the versioned registry, its four consumers, and the
  `hitl-interview` review handoff.

## Related skills

- **hitl-interview** — the REVIEW handoff: human confirmation of candidate
  anti-patterns before they are promoted in the registry.
- **background-rescue** — a live consumer (rescue triggers) and the inverse of
  this skill: it re-grounds ONE stuck node in real time; this finds those nodes
  in BATCH, after the fact.
- **recursive-self-improvement** — graded, HITL loop that consumes the registry
  (skill heals + prompt mutations) and decides what lands.
- **meta-skill / skill-creator** — skill-heal consumers of the `NEVER X when Y`
  rules. **judge-panel** — consumes anti-patterns as judge criteria.
- **autonomous-orchestrator** — hill-climbs the harness itself; feed it the
  registry as its improvement targets.
