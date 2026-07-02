---
name: ce-project-development
version: 1.3.0
description: "This skill should be used for project-level decisions about LLM-powered systems: whether an LLM is the right primitive for the task at hand, the shape of a multi-stage batch or agent pipeline, token and cost estimation, choosing between single-agent and multi-agent at the project level, structured output design for downstream parsing, and structuring agent-assisted iteration. Use this when the unit of work is a whole project or a multi-stage pipeline. Route individual tool design to tool-design and individual skill-loading or context-budget tactics to context-optimization. Not for individual tool schemas (tool-design), per-trajectory token optimization (context-optimization), multi-agent topology (multi-agent-patterns), or autonomous control loops (harness-engineering)."
---

# Project Development Methodology

A router for project-level decisions about LLM-powered systems: identifying tasks suited to LLM processing, designing project architectures, and iterating rapidly with agent-assisted development. Applies whether building a batch processing pipeline, a multi-agent research system, or an interactive agent application.

The unit of work is the whole project or a multi-stage pipeline. This skill owns the project-level questions — should you build this with an LLM at all, what shape should the pipeline take, what does it cost, how should it be iterated. Per-tool design, per-trajectory token tactics, agent topology, and the autonomous control loop are owned elsewhere (see Integration).

The detailed methodology lives in `references/methodology.md`. This file is a router: read the section pointers below, then open the reference for the depth you need.

## When to Activate

Activate when the unit of work is a whole project or pipeline:

- Deciding whether an LLM is the right primitive for a task at all (task-model fit before any code).
- Shaping a multi-stage batch or agent pipeline (acquire / prepare / process / parse / render).
- Estimating tokens, dollar cost, and timelines for an LLM-heavy project.
- Choosing between single-agent and multi-agent at the project level.
- Structuring agent-assisted iteration (where the agent helps build the project itself).
- Designing structured output at the pipeline contract level (cross-stage handoff format).

Do not activate for adjacent work owned by other skills:

- Per-tool description, schema, naming, response format, error message → `tool-design`.
- Per-trajectory token-efficiency tactics (masking, partitioning, caching) → `context-optimization`.
- Splitting work across sub-agents at the topology level → `multi-agent-patterns`.
- The autonomous control loop (locked metrics, novelty gates, human approval boundaries) → `harness-engineering`.

## Core Concepts (pointers)

Each concept is expanded in `references/methodology.md`. Use this list to jump to the section you need.

- **Task-model fit recognition** — two proceed/stop tables to decide before writing any code. *(methodology.md → Task-Model Fit Recognition)*
- **The manual prototype step** — run one representative input by hand before automating; a failed prototype predicts a failed system. *(methodology.md → The Manual Prototype Step)*
- **Pipeline architecture** — `acquire -> prepare -> process -> parse -> render`; isolate the non-deterministic, expensive LLM stage (process) from the deterministic stages so you re-run it only when needed. *(methodology.md → Pipeline Architecture; deeper layout/caching in `references/pipeline-patterns.md`)*
- **File system as state machine** — output-file existence gives idempotency and human-readable debugging; re-run a stage by deleting its output. *(methodology.md → File System as State Machine)*
- **Structured output design** — section markers, format examples, parsing-rationale disclosure, constrained values; build parsers that tolerate variation. *(methodology.md → Structured Output Design)*
- **Agent-assisted development** — clear requirements, discrete components, test-before-proceed, one task at a time. *(methodology.md → Agent-Assisted Development)*
- **Cost and scale estimation** — `(items x tokens_per_item x price_per_token) + overhead`, plus a 20-30% buffer. *(methodology.md → Cost and Scale Estimation)*
- **Single vs multi-agent** — default single-agent; escalate only for parallel exploration, context-window overflow, or benchmark-proven specialization. *(methodology.md → Choosing Single vs Multi-Agent Architecture)*
- **Architectural reduction** — start minimal; the Vercel d0 case cut many tools to bash + SQL and improved success. *(methodology.md → Architectural Reduction)*
- **Iteration and refactoring** — plan for repeated refactors; keep architecture simple so model improvements help rather than fight the harness. *(methodology.md → Iteration and Refactoring)*

For the project-planning template, worked examples, full guidelines, and the gotchas list, see `references/methodology.md`.

## Integration

This skill owns project-shape and pipeline decisions. Adjacent decisions are owned elsewhere:

- `tool-design` — the per-tool interface layer (descriptions, schemas, response formats, error messages, MCP namespacing, tool consolidation). If the question is "what should this specific tool look like" rather than "what should the pipeline look like," route there.
- `multi-agent-patterns` — agent topology (supervisor vs swarm vs hierarchical, handoff protocols, context isolation across agents). This skill picks single-vs-multi at the project level; topology details belong there.
- `harness-engineering` — the autonomous control loop (locked metrics, novelty gates, run state machine, human approval boundaries). If the question is "how do we make this run unattended for days," route there.
- `context-fundamentals` — the conceptual frame for context constraints that inform prompt design at every stage.
- `evaluation` — outcome measurement and quality gates for pipeline runs.
- `context-compression` — when long-running pipeline stages produce trajectories that need summarization.

## References

Internal references:
- [Methodology](./references/methodology.md) — full detail behind every Core Concept pointer above: fit tables, manual prototype, pipeline/file-system/structured-output design, single-vs-multi, architectural reduction, iteration, the planning template, worked examples, guidelines, and gotchas.
- [Case Studies](./references/case-studies.md) — read when evaluating architecture tradeoffs or reviewing real-world pipeline implementations (Karpathy HN Capsule, Vercel d0, Manus patterns).
- [Pipeline Patterns](./references/pipeline-patterns.md) — read when designing a new pipeline stage layout, choosing caching strategies, or debugging stage boundaries.

Related skills: `tool-design`, `multi-agent-patterns`, `evaluation` (see Integration for routing).

External resources:
- Karpathy's HN Time Capsule project: https://github.com/karpathy/hn-time-capsule
- Vercel d0 architectural reduction: https://vercel.com/blog/we-removed-80-percent-of-our-agents-tools
- Manus context engineering: Peak Ji's blog on context engineering lessons
- Anthropic multi-agent research: How we built our multi-agent research system

---

## Skill Metadata

**Created**: 2025-12-25
**Last Updated**: 2026-06-29
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.3.0
