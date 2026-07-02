# A-Evolve Configuration, Built-in Components & Skill Format

## Built-in Components

### Seed Agents

| Agent | Domain | Model | Key Feature |
|-------|--------|-------|-------------|
| `swe` | SWE-bench | Claude Opus 4.6 | Verify-fix loop, skill proposals |
| `terminal` | Terminal-Bench | Claude Sonnet 4 | Concurrent timeout, env discovery |
| `mcp` | MCP-Atlas | Claude Opus 4.6 | MCP server integration |

### Benchmarks

| Name | Domain | Metric |
|------|--------|--------|
| `swe-verified` | Code patching | Pass rate |
| `mcp-atlas` | Tool calling | Accuracy |
| `terminal2` | Shell tasks | Pass rate |
| `skill-bench` | Multi-step procedures | Accuracy |
| `arc-agi-3` | Interactive games | RHAE score |

### Evolution Algorithms

| Algorithm | Strategy | Best For |
|-----------|----------|----------|
| A-Evolve/SkillForge | LLM-driven workspace mutation | General-purpose |
| Guided Synthesis | Memory-first, curated skills | Skill discovery |
| Adaptive Evolution | Reward tracking, filtered observations | Fine-grained control |
| Adaptive Skill | Skill-centric refinement | Skill-heavy domains |

## Configuration Reference

```python
ae.EvolveConfig(
    batch_size=10,              # Tasks per solve round
    max_cycles=20,              # Max evolution iterations
    holdout_ratio=0.2,          # Test set split for gating
    evolve_prompts=True,        # Mutate system prompts
    evolve_skills=True,         # Discover/refine skills
    evolve_memory=True,         # Build episodic memory
    evolve_tools=False,         # Mutate tool implementations
    trajectory_only=False,      # Hide scores from evolver
    evolver_model="us.anthropic.claude-opus-4-6-v1",
    evolver_max_tokens=16384,
    egl_threshold=0.05,         # Convergence epsilon
    egl_window=3,               # Cycles for plateau detection
)
```

**Convergence**: Evolution stops early when score improvement is less than `egl_threshold` over the last `egl_window` cycles.

## Skill Format

Skills are reusable procedures discovered and refined during evolution:

```markdown
---
name: verify-edge-cases
description: "TRIGGER when: checking boundary conditions. DO NOT TRIGGER: for happy-path tests."
---

## Pattern
Test all falsy-but-valid values: 0, False, "", [], {}

## Process
1. List all input boundaries
2. Run each against the implementation
3. Check both output AND side effects
```

Skills accumulate in the workspace `skills/` directory. The evolver curates them: ACCEPT new skills, MERGE overlapping ones, SKIP redundant proposals. Target: 5–10 broad skills, not 30 narrow ones.
