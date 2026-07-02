---
name: brainstorming-research-ideas
description: Guides researchers through ten structured ideation frameworks to discover high-impact research directions. Use when exploring a new problem space, pivoting between projects, feeling stuck and seeking fresh angles, evaluating whether a half-formed idea has potential, or preparing a brainstorming session. Do NOT use when you already have a well-defined question and need execution help, when you need experimental design or methodology (use domain-specific skills), or when you want a literature review (use literature-review). For automated LLM-driven hypothesis testing on data use hypogenic; for structured hypothesis formulation from observations use hypothesis-generation; for free-form creative ideation use scientific-brainstorming.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Research Ideation, Brainstorming, Problem Discovery, Creative Thinking, Research Strategy]
dependencies: []
---

# Research Idea Brainstorming

Structured frameworks for discovering the next research idea — moving from vague curiosity to a concrete, defensible proposal. Ten complementary lenses, each targeting a different cognitive mode. Use individually or combine.

## When to Use This Skill

- Starting a new research direction and need structured exploration
- Stuck on a current project and want fresh angles
- Evaluating whether a half-formed idea has real potential
- Preparing for a brainstorming session with collaborators
- Transitioning between research areas and seeking high-leverage entry points
- Reviewing a field and looking for underexplored gaps

**Do NOT use this skill when**:
- You already have a well-defined research question and need execution guidance
- You need experimental design or methodology help (use domain-specific skills)
- You want a literature review (use `literature-review`)

**Sibling skills** (pick the closer match): `scientific-brainstorming` for free-form creative ideation; `hypothesis-generation` for formulating testable hypotheses from observations; `hypogenic` for automated LLM-driven hypothesis testing on tabular data.

---

## The Ten Frameworks (at a glance)

Each row is a lens. Full workflows, tables, examples, and self-checks live in **[references/frameworks.md](references/frameworks.md)** — read that file when applying a framework in depth.

| # | Framework | Use it to… |
|---|-----------|-----------|
| 1 | Problem-First vs. Solution-First | Classify an idea's origin and check it has both a real problem and a feasible approach |
| 2 | Abstraction Ladder | Generate variants by moving up (generalize), down (instantiate), or sideways (analogize) |
| 3 | Tension & Contradiction Hunting | Find research opportunities in trade-offs everyone treats as fixed |
| 4 | Cross-Pollination | Borrow structural mechanisms from adjacent fields (neuroscience, physics, economics…) |
| 5 | The "What Changed?" Principle | Revive abandoned ideas whose blocking assumptions no longer hold |
| 6 | Failure Analysis & Boundary Probing | Find where accepted methods break and why |
| 7 | The Simplicity Test | Check whether a simpler baseline matches complex SOTA |
| 8 | Stakeholder Rotation | Surface distinct questions from user/dev/theorist/adversary/ethicist/regulator/operator views |
| 9 | Composition & Decomposition | Create novelty by combining or isolating existing techniques |
| 10 | The "Explain It to Someone" Test | Sharpen the value proposition into a two-sentence pitch |

---

## Framework Selection Guide

| Your Situation | Start With |
|---------------|------------|
| "I don't know what area to work in" | Tension Hunting (F3) → What Changed (F5) |
| "I have a vague area but no specific idea" | Abstraction Ladder (F2) → Failure Analysis (F6) |
| "I have an idea but I'm not sure it's good" | Explain-It Test (F10) → Simplicity Test (F7) |
| "I have a good idea but need a fresh angle" | Cross-Pollination (F4) → Stakeholder Rotation (F8) |
| "I want to combine existing work into something new" | Composition/Decomposition (F9) |
| "I found a cool technique and want to apply it" | Problem-First Check (F1) → Stakeholder Rotation (F8) |
| "I want to challenge conventional wisdom" | Failure Analysis (F6) → Simplicity Test (F7) |

---

## Integrated Brainstorming Workflow

Go from blank page to ranked ideas in three phases.

**Phase 1 — Diverge (generate 10-20 candidates, no filtering):**
1. Scan for tensions (F3): list 5 trade-offs in your field
2. Check what changed (F5): list 3 recent shifts (compute, data, regulation)
3. Probe boundaries (F6): pick 2 popular methods, find where they break
4. Cross-pollinate (F4): pull 1 idea from an adjacent field
5. Compose/decompose (F9): combine 2 techniques or split 1 apart
6. Climb the ladder (F2): generate up/down/sideways variants of each candidate

**Phase 2 — Converge (narrow to 3-5):** apply each filter; the kill criterion drops the idea.

| Filter | Question | Kill Criterion |
|--------|----------|----------------|
| Explain-It (F10) | Can I state this in two sentences? | If no → not yet clear |
| Problem-First (F1) | Is the problem genuine and important? | If no one suffers → drop |
| Simplicity (F7) | Is the complexity justified? | If a simpler approach works → simplify or drop |
| Stakeholder (F8) | Who benefits? Who objects? | If no clear beneficiary → drop |
| Feasibility | Can I execute with available resources? | If clearly infeasible → park for later |

**Phase 3 — Refine (sharpen the winner):**
1. Write the two-sentence pitch (F10)
2. Identify the core tension being resolved (F3)
3. Specify the abstraction level (F2)
4. List 3 concrete validating experiments
5. Anticipate the strongest objection and prepare a response
6. Define a 2-week pilot that gives a feasibility signal

**Completion checklist:** pitch clear · problem genuine · approach justified · a stakeholder benefits · core experiments specified · feasibility pilot defined · strongest objection answered.

---

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Novelty without impact | "No one has done X" but no one needs X | Problem-First Check (F1) |
| Incremental by default | Idea is +2% on a benchmark | Abstraction Ladder (F2) |
| Complexity worship | 8 components, each helping marginally | Simplicity Test (F7) |
| Echo chamber | All ideas from the same 10 papers | Cross-Pollination (F4) |
| Stale assumptions | "This was tried and didn't work" (5 years ago) | What Changed (F5) |
| Single-perspective bias | Only the ML engineer's view | Stakeholder Rotation (F8) |
| Premature convergence | Committed to first idea | Run the full Diverge phase |

---

## Usage Instructions for Agents

When a researcher asks for brainstorming help:
1. **Identify the starting point** — exploring a new area, stuck, or evaluating an idea?
2. **Select frameworks** — use the Selection Guide to pick 2-3 lenses; open `references/frameworks.md` for their full workflows.
3. **Walk through interactively** — apply each framework step-by-step, asking for domain-specific inputs.
4. **Generate candidates** — aim for 10-20 raw ideas (Diverge phase).
5. **Filter and rank** — apply the Converge filters down to the top 3-5.
6. **Refine the winner** — articulate the two-sentence pitch and concrete next steps.

**Key principles:** push for specificity (vague "improve efficiency" is not actionable); challenge assumptions (ask "why?" three times); keep a written list of every candidate, even rejected ones (they may recombine later); the researcher makes the final call — the agent facilitates structured thinking.
