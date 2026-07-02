# A-Evolve Workflows

The three canonical evolution workflows. Read the one matching your task; each is self-contained.

## Workflow 1: Evolve an Existing Agent

**Use when**: You have a working agent and want to optimize it against a benchmark.

**Critical Requirements:**
- [ ] Agent implements `BaseAgent.solve()` returning `Trajectory`
- [ ] Benchmark implements `BenchmarkAdapter` with `get_tasks()` and `evaluate()`
- [ ] Seed workspace has `manifest.yaml` with entrypoint and evolvable layers
- [ ] System prompt exists at `prompts/system.md`
- [ ] Workspace is a git repo (run `git init && git add -A && git commit -m "init"`)

### Steps

```python
import agent_evolve as ae

# Configure evolution parameters
config = ae.EvolveConfig(
    batch_size=10,           # Tasks per solve round
    max_cycles=20,           # Maximum evolution iterations
    evolve_prompts=True,     # Mutate system prompt
    evolve_skills=True,      # Discover and refine skills
    evolve_memory=True,      # Build episodic memory
    evolver_model="us.anthropic.claude-opus-4-6-v1",
)

# Point to your agent workspace and benchmark
evolver = ae.Evolver(
    agent="./my-agent-workspace",
    benchmark="swe-verified",     # Or custom BenchmarkAdapter instance
    config=config,
)

# Run evolution
results = evolver.run(cycles=10)

# Inspect results
print(f"Cycles completed: {results.cycles_completed}")
print(f"Final score: {results.final_score}")
print(f"Converged: {results.converged}")
for cycle_num, score in enumerate(results.score_history):
    print(f"  Cycle {cycle_num + 1}: {score:.3f}")
```

### Post-Evolution

The workspace is now optimized. Inspect what changed:

```bash
cd my-agent-workspace
git log --oneline              # See evo-1, evo-2, ... tags
git diff evo-1 evo-10          # Compare first and last evolution
cat prompts/system.md          # Read evolved prompt
ls skills/                     # See discovered skills
```

## Workflow 2: Add a Custom Benchmark

**Use when**: You want to evolve agents on your own domain-specific tasks.

**Critical Requirements:**
- [ ] Define task format (inputs, expected outputs)
- [ ] Implement scoring logic (0.0–1.0 scale)
- [ ] Prepare task dataset (train + holdout split)

### Steps

```python
import agent_evolve as ae

class CodeReviewBenchmark(ae.BenchmarkAdapter):
    """Evaluate agents on code review quality."""

    def get_tasks(self, split="train", limit=None):
        tasks = load_review_dataset(split)
        if limit:
            tasks = tasks[:limit]
        return [
            ae.Task(id=t["id"], input=t["diff"], metadata={"expected": t["comments"]})
            for t in tasks
        ]

    def evaluate(self, task, trajectory):
        expected = task.metadata["expected"]
        actual = trajectory.output
        precision, recall = compute_review_metrics(expected, actual)
        f1 = 2 * precision * recall / (precision + recall + 1e-9)
        return ae.Feedback(
            success=f1 > 0.7,
            score=f1,
            detail=f"P={precision:.2f} R={recall:.2f} F1={f1:.2f}",
        )

# Use with any agent
evolver = ae.Evolver(agent="./my-agent", benchmark=CodeReviewBenchmark())
results = evolver.run(cycles=5)
```

## Workflow 3: Create a Custom Evolution Engine

**Use when**: The default LLM-driven mutation doesn't suit your domain.

### Steps

```python
import agent_evolve as ae

class RuleBasedEngine(ae.EvolutionEngine):
    def step(self, workspace, observations, history, trial):
        failures = [o for o in observations if not o.feedback.success]
        if not failures:
            return ae.StepResult(mutated=False, summary="No failures to address")

        # Analyze failure patterns
        error_types = categorize_errors(failures)
        prompt = workspace.read_prompt()

        # Append learned rules to prompt
        new_rules = generate_rules(error_types)
        workspace.write_prompt(prompt + "\n" + new_rules)

        return ae.StepResult(
            mutated=True,
            summary=f"Added {len(new_rules)} rules from {len(failures)} failures",
        )

evolver = ae.Evolver(
    agent="./my-agent",
    benchmark="my-benchmark",
    engine=RuleBasedEngine(),
)
```
