---
name: ce-multi-agent-patterns
version: 2.1.0
description: This skill should be used when designing multi-agent systems that need context isolation, supervisor or swarm coordination, explicit handoffs, parallel execution, or a decision on whether multiple agents are justified. Not for project-level multi-vs-single decisions, runtime infrastructure, or tool specialization — see project-development, hosted-agents, and tool-design.
---

# Multi-Agent Architecture Patterns

Multi-agent architectures distribute work across multiple language model instances, each with its own context window. When designed well, this distribution enables capabilities beyond single-agent limits. When designed poorly, it introduces coordination overhead that negates benefits. The critical insight is that sub-agents exist primarily to isolate context, not to anthropomorphize role division.

This file is a router. Read the linked reference files for depth.

## When to Activate

Activate this skill when:
- Single-agent context limits constrain task complexity
- Tasks decompose naturally into parallel subtasks
- Different subtasks require different tool sets or system prompts
- Building systems that must handle multiple domains simultaneously
- Scaling agent capabilities beyond single-context limits
- Designing production agent systems with multiple specialized components

Do not activate this skill for adjacent work owned by other skills:
- Deciding task-model fit, pipeline shape, or project-level cost before topology is known: `project-development`.
- Designing hosted sandboxes, warm pools, remote sessions, or background runtime infrastructure: `hosted-agents`.
- Sharing orchestrator state through KV-cache compaction in controlled runtimes: `latent-briefing`.
- Designing the tools each agent exposes: `tool-design`.

## Core Concepts

Use multi-agent patterns when a single agent's context window cannot hold all task-relevant information. Context isolation is the primary benefit — each agent operates in a clean context without accumulated noise from other subtasks, preventing the telephone game problem where information degrades through repeated summarization.

Choose among three dominant patterns based on coordination needs, not organizational metaphor:

- **Supervisor/orchestrator** — Centralized control when tasks have clear decomposition and human oversight matters. A single coordinator delegates to specialists and synthesizes results.
- **Peer-to-peer/swarm** — Flexible exploration when rigid planning is counterproductive. Any agent can transfer control to any other through explicit handoff mechanisms.
- **Hierarchical** — Large-scale projects with layered abstraction (strategy, planning, execution). Each layer operates at a different level of detail with its own context structure.

Design every multi-agent system around explicit coordination protocols, consensus mechanisms that resist sycophancy, and failure handling that prevents error propagation cascades.

## Where to Go Next

- **Designing the topology** (why multi-agent, the three patterns with code, the telephone-game fix, isolation mechanisms, consensus/coordination, framework philosophies) → [references/patterns.md](./references/patterns.md)
- **Framework-specific implementation** (LangGraph, AutoGen, CrewAI code) → [references/frameworks.md](./references/frameworks.md)
- **Hardening a running system** (failure modes + mitigations, gotchas, worked examples) → [references/failure-modes.md](./references/failure-modes.md)

The headline failure modes you must design against: supervisor bottleneck, coordination overhead, divergence, and error propagation. The most common practical traps: ~15x token-cost underestimation, agent sprawl past 3-5 agents, sycophantic consensus, telephone-game degradation in message-passing, and over-decomposition. Each is detailed with mitigations in references/failure-modes.md.

## Guidelines

1. Design for context isolation as the primary benefit of multi-agent systems.
2. Choose architecture pattern based on coordination needs, not organizational metaphor.
3. Implement explicit handoff protocols with state passing.
4. Use weighted voting or debate protocols for consensus; avoid simple majority voting.
5. Monitor for supervisor bottlenecks and implement checkpointing.
6. Validate outputs before passing between agents.
7. Set time-to-live limits to prevent infinite loops.
8. Test failure scenarios explicitly and measure multi-agent setups against a single-agent baseline.

## Integration

This skill owns agent topology and coordination protocols. Adjacent skills own project shape, hosted runtime, and latent-state transfer:

- `project-development`: project-level single-vs-multi choice before topology details.
- `hosted-agents`: remote sandbox, session, warm-pool, and multiplayer infrastructure.
- `memory-systems`: shared persistent state across agents.
- `tool-design`: tool specialization and spawn/status tool contracts.
- `context-optimization`: partitioning as one token-efficiency tactic.
- `latent-briefing`: KV-cache trajectory handoff between orchestrator and worker when models align.
- `evaluation`: measuring whether multiple agents improve outcomes after coordination cost.

## References

Internal references:
- [references/patterns.md](./references/patterns.md) — Read when: justifying multi-agent, selecting a pattern, choosing an isolation mechanism, or wiring consensus/coordination.
- [references/frameworks.md](./references/frameworks.md) — Read when: implementing a pattern in LangGraph, AutoGen, or CrewAI and needing framework-specific code.
- [references/failure-modes.md](./references/failure-modes.md) — Read when: hardening a system against bottlenecks, divergence, cost overruns, and error propagation.

Related skills in this collection:
- context-fundamentals — Read when: needing context window mechanics before designing agent partitioning.
- memory-systems — Read when: agents need to share state across context boundaries or persist between runs.
- context-optimization — Read when: individual agent contexts are too large and need partitioning or compression.

External resources:
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) — Read when: building graph-based multi-agent workflows with explicit state machines.
- [AutoGen Framework](https://microsoft.github.io/autogen/) — Read when: implementing conversational GroupChat or event-driven agent coordination.
- [CrewAI Documentation](https://docs.crewai.com/) — Read when: designing role-based hierarchical agent processes.
- [Research on Multi-Agent Coordination](https://arxiv.org/abs/2308.00352) — Read when: needing academic grounding on multi-agent system theory and evaluation.

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2026-05-15
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 2.1.0
