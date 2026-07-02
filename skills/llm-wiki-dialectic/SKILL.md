---
name: llm-wiki-dialectic
version: 0.3.0
description: >
  WHAT: A dialectic reasoning engine over the user's knowledge vault. Two committed-belief
  subagents each argue ONE side of a single tension at full conviction while the orchestrator
  runs determinate-negation analysis and produces a synthesis (Aufhebung) that transforms the
  question — so the user reasons from a belief-free position. WHEN: deep-analyze ONE known
  tension (often surfaced by llm-wiki-detect-tensions), stress-test a note/idea against its
  strongest counter-argument, resolve a genuine either/or with unclear tradeoffs, or build a
  mental model before writing. Triggers: "stress-test this idea", "steelman both sides",
  "resolve this tension", "run a dialectic on X". WHEN-NOT: surfacing MANY contradictions across
  the vault (use llm-wiki-detect-tensions); merging notes into a framework (use
  llm-wiki-synthesize-insights); finding non-contradictory links (llm-wiki-find-connections);
  one-sided assumption-challenging (critical-perspective); generating hypotheses; or when one
  side is plainly correct.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, Agent
automation: gated
---

# LLM Wiki Dialectic — Belief-Outsourcing Engine

An **artificial belief system** for building deeper understanding out of the tensions in your knowledge vault.

Two subagent sessions each *believe* one fully committed position so the user does not have to. A third session (the orchestrator) performs structural analysis of their contradiction and generates a synthesis (Aufhebung) that transforms the question itself. The user orchestrates from a belief-free position, freed from the cognitive load of holding either side.

**Why this works:** the bottleneck in human reasoning is not intelligence — it is *belief*. Once you believe a position you cannot simultaneously hold its negation at full strength; you hedge, you steelman weakly, you unconsciously bias the comparison. The advocate subagents carry the belief load at full conviction, which frees the user to operate in the space *above* belief — analyzing the *structure* of the contradiction rather than being inside it. Each dialectical cycle is a reorientation that would take weeks of natural thinking, compressed into minutes because the user carries zero belief inertia. (The framing owes an obvious debt to the Electric Monk — a device built to believe things for you.)

## Where This Fits in the Vault Workflow

This is the **single-tension deep-dive** of the `llm-wiki-*` family. It is usually invoked *downstream* of a scan:

- `llm-wiki-detect-tensions` surfaces MANY contradictory note pairs across the whole vault. Pick one → bring it here.
- **This skill** takes ONE tension (or one idea/note the user wants pressure-tested) and drives it to a synthesis, saving the interview brief, structural analysis, and synthesis as artifacts the user can promote into a permanent note.
- `llm-wiki-synthesize-insights` then merges the resulting synthesis with other notes into an article-length narrative or framework.

The input can be a tension between two notes, a single note the user wants stress-tested, or a raw idea. If the vault has semantic search available (Local Brain Search / turbovault), use it in Phase 1 to pull the notes on each side into the briefing; otherwise interview the user directly.

## When to Use This Skill

Use when:
- The user wants to **stress-test** an idea or note against the strongest possible counter-argument.
- The user is **torn between two positions** and the tension feels genuine, not just a preference.
- A **decision has real stakes** and the tradeoffs are unclear.
- The user wants to **build a deeper mental model** of a domain, not just pick an answer.
- The problem space is poorly understood and needs exploration from multiple angles.
- Two notes or requirements genuinely conflict and cannot be resolved by simple tradeoff analysis.

Do NOT use when:
- The question is purely empirical (just look up the answer).
- One side is obviously correct and does not need dialectical treatment.
- The user wants a quick recommendation, not deep analysis.

**Sibling boundaries.** Surfacing many contradictions across the vault → `llm-wiki-detect-tensions`. Merging notes into a narrative/framework → `llm-wiki-synthesize-insights`. Finding non-contradictory links → `llm-wiki-find-connections`. Whole-vault structural health → `llm-wiki-coherence-sweep`. One-sided assumption-challenging without the belief machinery → `critical-perspective` / `scientific-critical-thinking`. Generating (rather than stress-testing) hypotheses → `hypothesis-generation` / `scientific-brainstorming`. Reach for *this* skill specifically when the value is in a **contradiction held at full conviction on both sides**.

## Core Concepts (Read This First)

Three frameworks drive every phase. Internalize them before proceeding — they determine *how* you execute, not just *why*. Full treatment in **[references/theory.md](references/theory.md)**.

- **Artificial Belief System, not AI.** The advocates are not thinking *for* the user; they are *believing* for the user. Belief inertia is the bottleneck: once you hold a position you cannot entertain its negation at full strength. A hedging advocate has failed its one job — anti-hedging is a functional requirement, not a stylistic preference.
- **Hegel — how contradictions resolve.** The engine is *determinate negation*: not "this is wrong" but "this is wrong in a *specific way* that points toward what is missing." Synthesis (Aufhebung) cancels, preserves, and elevates simultaneously — it is NOT compromise. If either advocate could have proposed it while feeling conciliatory, it is not a real Aufhebung.
- **Boyd — how creativity works.** You cannot synthesize something genuinely new by recombining within one domain. First *shatter* the positions into atomic parts (destruction), then find cross-domain connections (creation). This is why Phase 4.5 strips claims from their sources and why recursive rounds often need research from *outside* the original domains.

## How It Works: Overview

You are the **orchestrator**. You conduct the elenctic interview, identify the user's belief burden, generate the advocate prompts, spawn the advocate subagents, perform the structural analysis, and produce the synthesis. Use subagent sessions (via the `Agent` tool / `claude -p` / your environment's equivalent) for the advocates so each gets a fresh, fully committed belief context.

```
You (Orchestrator)
├── Phase 1: Elenctic Interview + Research (you, with the user + vault)
│   ├── 1a: Explain the process — set expectations, user as co-pilot
│   ├── 1c′: Identify the user's belief burden and calibrate advocate roles
│   ├── 1d: Ground the advocates (vault search or deep interview, domain-dependent)
│   ├── 1e: Write context briefing document to file
│   └── 1f: Confirm framing with user — ask about gaps in coverage
├── Phase 2: Generate advocate prompts (you) — reference briefing file
├── Phase 3: Spawn the advocates (subagents, read briefing, BELIEVE fully)
│   ├── Decorrelation check: did advocates genuinely diverge in framework?
│   └── User checkpoint: evidence or comparison class both advocates missed?
├── Phase 4: Determinate Negation (you — structural analysis, saved to file)
│   ├── 4.0: Internal tensions — where each advocate's logic undermines itself
│   └── 4.5: Boydian decomposition — shatter, find cross-domain connections
├── Phase 5: Sublation / Aufhebung (you — synthesis, saved to file)
│   └── Abduction test: does synthesis make the contradiction *predictable*?
├── Phase 6: Validation (Advocates A & B + Hostile Auditor, then refine)
└── Phase 7: Recursion — propose 2-4 directions, user chooses (default: ≥ once)
```

The user can intervene at any point — correcting an advocate's framing, redirecting research, rejecting a compromise-shaped synthesis. The user never has to *believe* anything — that is the advocates' job.

## Detailed References

Load the relevant file when you reach that part of the work. Do not inline these — pull them on demand to keep context lean.

- **[references/phases.md](references/phases.md)** — Full step-by-step playbook for Phases 1–7: elenctic interview, belief-burden catalog, advocate prompt structure, determinate negation, sublation criteria, validation + hostile-auditor prompts, and recursion. Re-read the relevant `<phaseN>` section before executing it, especially in recursive rounds.
- **[references/theory.md](references/theory.md)** — Theoretical foundations (Rao, Hegel, Boyd, Socrates, Peirce, Pollock, Galinsky, Klein, Fauconnier & Turner, ensemble diversity, SICP closure, Alexander semi-lattices, and more). Read to understand *why* the process works when you need to improvise.
- **[references/operations.md](references/operations.md)** — Model selection & cost/token budgets, environment mapping (`claude -p` vs the Claude Code `Agent`/Task tool), domain adaptation table, and the final output format.
- **[references/examples.md](references/examples.md)** — Three worked examples (technical architecture, personal values, a 7-cycle recursive dialectic) plus what makes good advocate prompts work.

**Quick start:** Begin with Phase 1 in `references/phases.md`. The first round is calibration — the real breakthroughs come in the recursive rounds (Phase 7).
