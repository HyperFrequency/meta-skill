---
name: cornelius-dialectic
version: 0.2.0
description: An Electric Monk engine — two subagents believe fully committed positions on the user's behalf while the orchestrator performs structural contradiction analysis and synthesis. By outsourcing belief work to agents, the user operates from a belief-free position where they can analyze the structure of the contradiction rather than being inside either side. Use when the user wants to stress-test an idea, resolve a genuine tension, build a deeper mental model, or make a high-stakes decision where the tradeoffs are unclear. Works across any domain — technical architecture, product strategy, philosophy, personal decisions, risk analysis, policy, creative direction. Do NOT use for purely empirical lookups, when one side is obviously correct, or when the user just wants a quick recommendation rather than deep analysis.
---

# The Electric Monks — Dialectic Skill

An **artificial belief system** for building deeper understanding through productive contradiction.

Two subagent sessions — the Electric Monks — *believe* fully committed positions so you don't have to. A third (the orchestrator) performs structural analysis of their contradiction and generates a synthesis (Aufhebung) that transforms the question itself. The user orchestrates from a belief-free position, freed from the cognitive load of holding either position.

**Why this works:** The bottleneck in human reasoning isn't intelligence — it's *belief.* Once you believe a position, you can't simultaneously hold its negation at full strength. You hedge, you steelman weakly, you unconsciously bias the comparison. The Electric Monks carry the belief load at full conviction, which frees you to operate in the space above belief — analyzing the *structure* of the contradiction rather than being inside either side. In Boyd's terms: outsourcing belief work leads to faster transients. Each dialectical cycle is a reorientation that would take weeks of natural thinking, compressed into minutes because you carry zero belief inertia.

## When to Use This Skill

Use when:
- The user wants to **stress-test** an idea against the strongest possible counter-argument
- The user is **torn between two positions** and the tension feels genuine, not just a preference
- A **decision has real stakes** and the tradeoffs are unclear
- The user wants to **build a deeper mental model** of a domain, not just pick an answer
- The problem space is poorly understood and needs exploration from multiple angles
- Requirements genuinely conflict and can't be resolved by simple tradeoff analysis

Do NOT use when:
- The question is purely empirical (just look up the answer)
- One side is obviously correct and doesn't need dialectical treatment
- The user wants a quick recommendation, not deep analysis

**Related skills:** For one-sided assumption-challenging without the full belief-system machinery, see `critical-perspective` / `scientific-critical-thinking`. For generating (rather than stress-testing) hypotheses, see `hypothesis-generation` / `scientific-brainstorming`. Reach for this skill specifically when the value is in a *contradiction held at full conviction on both sides*.

## Core Concepts (Read This First)

Three frameworks drive every phase. Internalize them before proceeding — they determine *how* you execute, not just *why*. Full treatment in **[references/theory.md](references/theory.md)**.

- **Rao — this is an Artificial Belief System, not AI.** The monks aren't thinking for the user; they're *believing* for the user. Belief inertia is the bottleneck: once you hold a position you can't entertain its negation at full strength. A hedging monk has failed its one job — anti-hedging is a functional requirement, not a stylistic preference.
- **Hegel — how contradictions resolve.** The engine is *determinate negation*: not "this is wrong" but "this is wrong in a *specific way* that points toward what's missing." Synthesis (Aufhebung) cancels, preserves, and elevates simultaneously — it is NOT compromise. If either monk could have proposed it while feeling conciliatory, it isn't a real Aufhebung.
- **Boyd — how creativity works.** You can't synthesize something genuinely new by recombining within one domain. First *shatter* the positions into atomic parts (destruction), then find cross-domain connections (creation). This is why Phase 4.5 strips claims from their sources and why recursive rounds often need research from *outside* the original domains.

## How It Works: Overview

You are the **orchestrator**. You conduct the elenctic interview, identify the user's belief burden, generate the monk prompts, spawn the Electric Monks, perform the structural analysis, and produce the synthesis. Use subagent sessions (via `claude -p` or your environment's equivalent) for the monks so each gets a fresh, fully committed belief context.

```
You (Orchestrator)
├── Phase 1: Elenctic Interview + Research (you, with the user)
│   ├── 1a: Explain the process — set expectations, user as co-pilot
│   ├── 1c′: Identify the user's belief burden and calibrate monk roles
│   ├── 1d: Ground the monks (research or deep interview, domain-dependent)
│   ├── 1e: Write context briefing document to file
│   └── 1f: Confirm framing with user — ask about gaps in coverage
├── Phase 2: Generate Electric Monk prompts (you) — reference briefing file
├── Phase 3: Spawn the Electric Monks (subagents, read briefing, BELIEVE fully)
│   ├── Decorrelation check: did monks genuinely diverge in framework?
│   └── User checkpoint: evidence or comparison class both monks missed?
├── Phase 4: Determinate Negation (you — structural analysis, saved to file)
│   ├── 4.0: Internal tensions — where each monk's logic undermines itself
│   └── 4.5: Boydian decomposition — shatter, find cross-domain connections
├── Phase 5: Sublation / Aufhebung (you — synthesis, saved to file)
│   └── Abduction test: does synthesis make the contradiction *predictable*?
├── Phase 6: Validation (Monks A & B + Hostile Auditor, then refine)
└── Phase 7: Recursion — propose 2-4 directions, user chooses (default: ≥ once)
```

The user can intervene at any point — correcting a monk's framing, redirecting research, rejecting a compromise-shaped synthesis. The user never has to *believe* anything — that's the monks' job.

## Detailed References

Load the relevant file when you reach that part of the work. Do not inline these — pull them on demand to keep context lean.

- **[references/phases.md](references/phases.md)** — Full step-by-step playbook for Phases 1–7: elenctic interview, belief-burden catalog, monk prompt structure, determinate negation, sublation criteria, validation + hostile-auditor prompts, and recursion. Re-read the relevant `<phaseN>` section before executing it, especially in recursive rounds.
- **[references/theory.md](references/theory.md)** — Theoretical foundations (Rao, Hegel, Boyd, Socrates, Peirce, Pollock, Galinsky, Klein, Fauconnier & Turner, ensemble diversity, SICP closure, Alexander semi-lattices, and more). Read to understand *why* the process works when you need to improvise.
- **[references/operations.md](references/operations.md)** — Model selection & cost/token budgets, environment mapping (`claude -p` vs Claude Code Task tool), domain adaptation table, and the final output format.
- **[references/examples.md](references/examples.md)** — Three worked examples (technical architecture, personal values, a 7-cycle recursive dialectic) plus what makes good monk prompts work.

**Quick start:** Begin with Phase 1 in `references/phases.md`. The first round is calibration — the real breakthroughs come in the recursive rounds (Phase 7).
