---
name: autoresearch
description: Orchestrates end-to-end autonomous AI research projects using a two-loop architecture. The inner loop runs rapid experiment iterations with clear optimization targets; the outer loop synthesizes results, identifies patterns, and steers direction. Routes to domain-specific skills for execution, supports continuous agent operation via Claude Code /loop and OpenClaw heartbeat cron, and produces research presentations and papers. Use when starting a research project, running autonomous experiments, or managing a multi-hypothesis research effort. Do NOT use for a specific one-off task (train one model, run one eval, write one paper) with no iterative experimentation — use the individual domain skills directly instead.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Autonomous Research, Two-Loop Architecture, Experiment Orchestration, Research Synthesis, Project Management]
---

# Autoresearch

Autonomous research orchestration for AI coding agents. You manage the full research lifecycle — from literature survey to published paper — by maintaining structured state, running a two-loop experiment-synthesis cycle, and routing to domain-specific skills for execution.

You are a research project manager, not a domain expert. You orchestrate; the domain skills execute.

**This runs fully autonomously.** Do not ask the user for permission or confirmation — use your best judgment and keep moving. Show the human your progress frequently through research presentations (HTML/PDF) so they can redirect if needed. The human is asleep or busy; make as much research progress as possible on your own.

## Getting Started

Users arrive in different states. Determine which and proceed:

| User State | What to Do |
|---|---|
| Vague idea ("I want to explore X") | Brief discussion to clarify, then bootstrap |
| Clear research question | Bootstrap directly |
| Existing plan or proposal | Review plan, set up workspace, enter loops |
| Resuming (research-state.yaml exists) | Read state, continue from where you left off |

If things are clear, don't over-discuss — proceed. Most users want you to just start researching.

**Step 0 — before anything else**: Set up the agent continuity loop (see [Agent Continuity](#agent-continuity-mandatory--set-up-first)). This is MANDATORY. Without it, the research stops after one cycle.

**Then** initialize the workspace. The full directory layout, `src/`/`data/` conventions, and template initialization are in [references/research-loops.md](references/research-loops.md#workspace-structure). Initialize `research-state.yaml`, `research-log.md`, and `findings.md` from [templates/](templates/).

## The Two-Loop Architecture

This is the core engine. Everything else supports it.

```
BOOTSTRAP (once, lightweight)
  Scope question → search literature → form initial hypotheses

INNER LOOP (fast, autonomous, repeating)
  Pick hypothesis → experiment → measure → record → learn → next
  Goal: run constrained experiments with clear measurable outcomes

OUTER LOOP (periodic, reflective)
  Review results → find patterns → update findings.md →
  new hypotheses → decide direction
  Goal: synthesize understanding, find the story — this is where novelty comes from

FINALIZE (when concluding)
  Write paper via ml-paper-writing → final presentation → archive
```

The inner loop runs tight experiment cycles with clear measurable outcomes — optimizing a benchmark OR testing mechanistic hypotheses. The outer loop steps back: what do these results *mean*? What patterns emerge? What's the story? There is no rigid boundary — you decide when enough inner-loop results have accumulated to warrant reflection (typically every 5-10 experiments, or when you notice a pattern, or when progress stalls).

Research is non-linear: return to literature, brainstorm, or pivot the question whenever understanding would help — not only during bootstrap.

The full step-by-step procedures live in [references/research-loops.md](references/research-loops.md): **Bootstrap** (literature search across Exa/Semantic Scholar/arXiv/CrossRef, gap identification, hypothesis formation, evaluation definition), **Inner loop** (the 10-step protocol-lock-run-sanity-check-record cycle plus the experiment-trajectory JSON for the optimization plot), and **Outer loop** (the 10-step synthesis cycle, the DEEPEN/BROADEN/PIVOT/CONCLUDE direction criteria, and how `findings.md` serves as project memory). Read it at project start and whenever you need the detailed mechanics.

### Route to Domain Skills

When you need domain-specific execution, search the skills library and read the relevant SKILL.md before starting. Quick map:

| Research Activity | Look In |
|---|---|
| Data preparation | `05-data-processing/` |
| Model training / fine-tuning | `01-model-architecture/`, `03-fine-tuning/`, `06-post-training/` |
| Distributed training | `08-distributed-training/` |
| Optimization (quantization, attention) | `10-optimization/` |
| Evaluation / benchmarks | `11-evaluation/` |
| Inference / serving | `12-inference-serving/` |
| Interpretability analysis | `04-mechanistic-interpretability/` |
| Experiment tracking (W&B, MLflow) | `13-mlops/` |
| Cloud compute | `09-infrastructure/` |
| Research ideation | `21-research-ideation/` |
| Paper writing | `20-ml-paper-writing/` |

See [references/skill-routing.md](references/skill-routing.md) for the complete routing map and common research workflows.

## Agent Continuity (MANDATORY — Set Up First)

**Before doing anything else**, set up the wall-clock loop. This is what keeps the research running continuously. Without it, the agent stops after one cycle. It is purely a wall-clock rhythm — completely separate from your research inner/outer loops. On each tick: read `research-state.yaml` and `findings.md`, check if anything is broken, continue if on track, diagnose and fix if stuck. Never idle.

**Claude Code — run this immediately as your first action:**

```
/loop 20m Continue autoresearch. Read research-state.yaml and findings.md. Re-read the autoresearch SKILL.md occasionally to stay aligned. Step back and reflect holistically — is the research making real progress? Are you deepening understanding or just running experiments? If stalling, pivot or search literature for new ideas. Keep making research progress — never idle, never stop. Update findings.md, research-log.md, and research-state.yaml when there's new progress. Git commit periodically and clean up the repo if needed. Show the human your research progress with key plots and findings by preparing a report in to_human/ and opening the HTML/PDF. Only when you believe the research is truly complete, invoke the ml-paper-writing skill to write the paper.
```

**OpenClaw** — set up a 20-minute (`everyMs: 1200000`) cron job via the `cron.add` tool with `sessionTarget: "current"` so it keeps conversation context, then verify with `cron.list`. The exact job JSON, the OpenClaw progress-report message, and per-platform context-recovery detail are in [references/agent-continuity.md](references/agent-continuity.md).

## Progress Reporting

When you have something meaningful to share, create a research presentation — not just a status dashboard, but a compelling story.

**When** (your judgment): after an outer loop found a significant pattern; when the trajectory shows clear progress (include the plot!); after a pivot; before requesting human input; when concluding. **What** (adapt to what's compelling): the research question and why it matters, key results with visualizations, the optimization trajectory chart, what was tried and why (selective), current understanding, what's next.

For Claude Code: generate HTML and `open` it; if it fails to render, convert to PDF (`weasyprint`, `playwright pdf`, or `wkhtmltopdf`). For OpenClaw: generate PDF directly and send via the user's channel.

See [references/progress-reporting.md](references/progress-reporting.md) for template scaffolding and the optimization plot approach.

## Git Protocol

Commit at natural research milestones:

| When | Message Pattern |
|---|---|
| Workspace initialized | `research(init): {project} — {question}` |
| Experiment protocol locked | `research(protocol): {hypothesis}` |
| Significant results | `research(results): {hypothesis} — {outcome}` |
| Outer loop direction change | `research(reflect): {direction} — {reason}` |
| Paper draft complete | `research(paper): {title}` |

**Hard rule**: Protocol commits MUST precede result commits. Never combine them. The git history is your lightweight pre-registration — it proves what you planned before you saw results. Don't commit after every experiment — commit when there's meaningful progress.

## Concluding: Paper Writing

When the outer loop decides to CONCLUDE:

1. Ensure findings.md has a clear, well-supported narrative
2. Study 2-3 top related papers to learn their format, style, and section structure
3. Invoke the `20-ml-paper-writing` skill — it has LaTeX templates for NeurIPS, ICML, ICLR, ACL, AAAI, COLM, and systems venues
4. Feed it the accumulated literature, experimental results, and findings
5. Follow its citation verification workflow — never hallucinate references
6. Generate a final comprehensive research presentation

Proceed autonomously. If the ml-paper-writing skill suggests human collaboration points, adapt and keep going — produce the best draft you can. The human will review and provide feedback.

## Research Discipline & Quality

Enforce continuously, not tied to any phase: **lock before you run** (protocol commit precedes results — see Git Protocol), **negative results are progress**, **sanity-check before analysis**, **return to literature when confused**, **never stop** on routine decisions, and **use whatever compute is available**. Aim for mechanistic hypotheses ("X because Y, predicting Z") and a findings.md that reads as a coherent narrative — not pure hyperparameter sweeps or copy-pasted logs. Full principles and the good/bad quality bar are in [references/research-discipline.md](references/research-discipline.md).

## When to Use vs Alternatives

**Use autoresearch when**: you have a research question explorable through experiments; there's a measurable proxy metric for inner-loop optimization; the real contribution requires synthesis beyond the metric; you want continuous autonomous operation.

**Use individual domain skills instead when**: you have a specific one-off task (train a model, run an eval, write a paper) with no iterative experimentation needed.

## References

- [references/research-loops.md](references/research-loops.md) — loop mechanics: bootstrap, inner/outer steps, direction criteria, workspace, findings.md
- [references/agent-continuity.md](references/agent-continuity.md) — per-platform /loop and cron detail
- [references/progress-reporting.md](references/progress-reporting.md) — presentation templates
- [references/skill-routing.md](references/skill-routing.md) — complete domain-skill routing map
- [references/research-discipline.md](references/research-discipline.md) — full discipline principles + good/bad quality bar
- [references/common-issues.md](references/common-issues.md) — troubleshooting (stalls, no GPU, papers, concluding)
