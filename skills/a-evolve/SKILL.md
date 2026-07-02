---
name: a-evolve
description: Guidance for automatically evolving and optimizing AI agents across any domain using LLM-driven evolution algorithms (A-Evolve). Use when building self-improving agents, optimizing agent prompts/skills/memory against a measurable benchmark, or running automated solve-observe-evolve evaluation loops with git-versioned rollback. Do NOT use for building multi-agent orchestration from scratch (use CrewAI/LangGraph), one-shot agent tasks with no iteration (LangChain/LlamaIndex), RAG pipeline tuning (LlamaIndex/Chroma), or prompt-only optimization without skill/memory evolution (DSPy).
version: 1.0.0
author: A-EVO Lab
license: MIT
tags: [Agent Evolution, Self-Improving Agents, Prompt Optimization, LLM, Benchmark Evaluation, Skill Discovery, Agentic AI]
dependencies: [a-evolve>=0.1.0, pyyaml>=6.0]
---

# Evolving AI Agents with A-Evolve

## Overview

A-Evolve is universal infrastructure for evolving any AI agent across any domain using any evolution algorithm with zero manual engineering. It represents all evolvable agent state as files (prompts, skills, memory, tools), runs iterative solve-observe-evolve cycles against benchmarks, and uses LLM-driven mutation to improve agent performance automatically.

**Key differentiator**: Other frameworks _build_ agents; A-Evolve _optimizes_ them. It sits on top of any agent framework and makes it better through automated evolution.

**Benchmark results** (Claude Opus 4.6): MCP-Atlas 79.4% (#1) · SWE-bench Verified 76.8% · Terminal-Bench 2.0 76.5% · SkillsBench 34.9% (#2).

## When to Use

**Use A-Evolve when:**
- Optimizing agent prompts, skills, or memory against a measurable benchmark
- Building self-improving agents with automated gating and rollback
- Evolving domain-specific tool usage through LLM-driven mutation
- Running iterative solve-observe-evolve loops with git-versioned history

**Do NOT use A-Evolve for:**
- Multi-agent orchestration from scratch → CrewAI, LangGraph
- One-shot agent tasks with no iteration → LangChain, LlamaIndex
- RAG pipeline optimization → LlamaIndex, Chroma
- Prompt-only optimization without skill/memory evolution → DSPy

## Quick Start

```bash
pip install a-evolve            # Core (add [anthropic] for Claude, [all] for every provider)
```

```python
import agent_evolve as ae

evolver = ae.Evolver(agent="swe", benchmark="swe-verified")
results = evolver.run(cycles=10)
print(f"Final score: {results.final_score}")
```

This copies the built-in SWE seed workspace, runs 10 evolution cycles against SWE-bench Verified, and returns the optimized agent.

## Core Concepts

### The Agent Workspace

All evolvable state lives as files in a workspace directory:

```
my-agent/
├── manifest.yaml          # Metadata + entrypoint
├── prompts/system.md      # Main system prompt (evolved) + fragments/
├── skills/<name>/SKILL.md # Reusable procedures with frontmatter
├── memory/                # episodic.jsonl (failures) + semantic.jsonl
├── tools/                 # registry.yaml + tool implementations
└── evolution/             # Managed by engine (metrics, history)
```

### The Evolution Loop

Each cycle runs five phases: **Solve** (agent processes a task batch) → **Observe** (benchmark evaluates trajectories into feedback triples) → **Evolve** (engine mutates workspace files) → **Gate** (git snapshot before/after for rollback) → **Reload** (agent reinitializes from evolved filesystem state).

### Three Pluggable Interfaces

```python
class MyAgent(ae.BaseAgent):          # 1. Agent — implements solve()
    def solve(self, task: ae.Task) -> ae.Trajectory: ...

class MyBenchmark(ae.BenchmarkAdapter):  # 2. Benchmark — get_tasks() + evaluate()
    def get_tasks(self, split="train", limit=None) -> list[ae.Task]: ...
    def evaluate(self, task, trajectory) -> ae.Feedback: ...

class MyEngine(ae.EvolutionEngine):   # 3. Engine — implements step()
    def step(self, workspace, observations, history, trial) -> ae.StepResult: ...
```

Full signatures and field-level details: [references/api.md](references/api.md).

## Workflows

Pick the workflow matching your task — each is a self-contained recipe in [references/workflows.md](references/workflows.md):

1. **Evolve an existing agent** — optimize a working agent against a benchmark.
2. **Add a custom benchmark** — evolve agents on your own domain tasks.
3. **Create a custom evolution engine** — replace default LLM-driven mutation.

## Configuration & Built-in Components

Seed agents (`swe`, `terminal`, `mcp`), benchmarks (`swe-verified`, `mcp-atlas`, `terminal2`, `skill-bench`, `arc-agi-3`), evolution algorithms, the full `EvolveConfig` reference, and the discovered-skill file format are documented in [references/configuration.md](references/configuration.md).

## Troubleshooting & Operating Guidance

Common issues (plateaus, workspace bloat, git conflicts, provider errors, reload problems), plus pro tips and warning signs, are in [references/troubleshooting.md](references/troubleshooting.md).

## References

- **Workflows (recipes)**: [references/workflows.md](references/workflows.md)
- **Configuration & components**: [references/configuration.md](references/configuration.md)
- **Troubleshooting & operating guidance**: [references/troubleshooting.md](references/troubleshooting.md)
- **API reference**: [references/api.md](references/api.md)
- **Architecture deep dive**: [references/architecture.md](references/architecture.md)
- **Step-by-step tutorials**: [references/tutorials.md](references/tutorials.md)
- **Real-world examples**: [references/examples.md](references/examples.md)
- **GitHub issues & solutions**: [references/issues.md](references/issues.md)
- **Design patterns**: [references/design-patterns.md](references/design-patterns.md)
- **Release history**: [references/releases.md](references/releases.md)
