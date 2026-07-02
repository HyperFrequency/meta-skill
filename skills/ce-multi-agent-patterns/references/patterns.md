# Multi-Agent Patterns — Detailed Reference

Read this when designing the topology in depth: justifying multi-agent over single-agent, selecting among supervisor/swarm/hierarchical, choosing an isolation mechanism, or wiring consensus and coordination. The SKILL.md router covers the summary; this file holds the rationale and code.

## Why Multi-Agent Architectures

**The Context Bottleneck**
Reach for multi-agent architectures when a single agent's context fills with accumulated history, retrieved documents, and tool outputs to the point where performance degrades. Recognize three degradation signals: the lost-in-middle effect (attention weakens for mid-context content), attention scarcity (too many competing items), and context poisoning (irrelevant content displaces useful content).

Partition work across multiple context windows so each agent operates in a clean context focused on its subtask. Aggregate results at a coordination layer without any single context bearing the full burden.

**The Token Economics Reality**
Budget for substantially higher token costs. Production data shows multi-agent systems can cost far more tokens than single-agent chat (claim-multi-agent-token-multiplier):

| Architecture | Token Multiplier | Use Case |
|--------------|------------------|----------|
| Single agent chat | Baseline | Simple queries |
| Single agent with tools | Higher than baseline | Tool-using tasks |
| Multi-agent system | Much higher than baseline | Complex research/coordination |

Browsing-agent evaluation research suggests token usage, tool calls, and model choice dominate performance variance (claim-evaluation-browsecomp-variance). This supports measuring multi-agent setups against single-agent baselines instead of assuming extra agents help.

Prioritize model selection alongside architecture design — upgrading to better models often provides larger performance gains than doubling token budgets. BrowseComp data shows that model quality improvements frequently outperform raw token increases. Treat model selection and multi-agent architecture as complementary strategies.

**The Parallelization Argument**
Assign parallelizable subtasks to dedicated agents with fresh contexts rather than processing them sequentially in a single agent. A research task requiring searches across multiple independent sources, analysis of different documents, or comparison of competing approaches benefits from parallel execution. Total real-world time approaches the duration of the longest subtask rather than the sum of all subtasks.

**The Specialization Argument**
Configure each agent with only the system prompt, tools, and context it needs for its specific subtask. A general-purpose agent must carry all possible configurations in context, diluting attention. Specialized agents carry only what they need, operating with lean context optimized for their domain. Route from a coordinator to specialized agents to achieve specialization without combinatorial explosion.

## Architectural Patterns

**Pattern 1: Supervisor/Orchestrator**
Deploy a central agent that maintains global state and trajectory, decomposes user objectives into subtasks, and routes to appropriate workers.

```
User Query -> Supervisor -> [Specialist, Specialist, Specialist] -> Aggregation -> Final Output
```

Choose this pattern when: tasks have clear decomposition, coordination across domains is needed, or human oversight is important.

Expect these trade-offs: strict workflow control and easier human-in-the-loop interventions, but the supervisor context becomes a bottleneck, supervisor failures cascade to all workers, and the "telephone game" problem emerges where supervisors paraphrase sub-agent responses incorrectly.

**The Telephone Game Problem and Solution**
Anticipate that supervisor architectures initially perform approximately 50% worse than optimized versions due to the telephone game problem (LangGraph benchmarks). Supervisors paraphrase sub-agent responses, losing fidelity with each pass.

Fix this by implementing a `forward_message` tool that allows sub-agents to pass responses directly to users:

```python
def forward_message(message: str, to_user: bool = True):
    """
    Forward sub-agent response directly to user without supervisor synthesis.

    Use when:
    - Sub-agent response is final and complete
    - Supervisor synthesis would lose important details
    - Response format must be preserved exactly
    """
    if to_user:
        return {"type": "direct_response", "content": message}
    return {"type": "supervisor_input", "content": message}
```

Prefer swarm architectures over supervisors when sub-agents can respond directly to users, as this eliminates translation errors entirely.

**Pattern 2: Peer-to-Peer/Swarm**
Remove central control and allow agents to communicate directly based on predefined protocols. Any agent transfers control to any other through explicit handoff mechanisms.

```python
def transfer_to_agent_b():
    return agent_b  # Handoff via function return

agent_a = Agent(
    name="Agent A",
    functions=[transfer_to_agent_b]
)
```

Choose this pattern when: tasks require flexible exploration, rigid planning is counterproductive, or requirements emerge dynamically and defy upfront decomposition.

Expect these trade-offs: no single point of failure and effective breadth-first scaling, but coordination complexity increases with agent count, divergence risk rises without a central state keeper, and robust convergence constraints become essential.

Define explicit handoff protocols with state passing. Ensure agents communicate their context needs to receiving agents.

**Pattern 3: Hierarchical**
Organize agents into layers of abstraction: strategy (goal definition), planning (task decomposition), and execution (atomic tasks).

```
Strategy Layer (Goal Definition) -> Planning Layer (Task Decomposition) -> Execution Layer (Atomic Tasks)
```

Choose this pattern when: projects have clear hierarchical structure, workflows involve management layers, or tasks require both high-level planning and detailed execution.

Expect these trade-offs: clear separation of concerns and support for different context structures at different levels, but coordination overhead between layers, potential strategy-execution misalignment, and complex error propagation paths.

## Context Isolation as Design Principle

Treat context isolation as the primary purpose of multi-agent architectures. Each sub-agent should operate in a clean context window focused on its subtask without carrying accumulated context from other subtasks.

**Isolation Mechanisms**
Select the right isolation mechanism for each subtask:

- **Full context delegation** — Share the planner's entire context with the sub-agent. Use for complex tasks where the sub-agent needs complete understanding. The sub-agent has its own tools and instructions but receives full context for its decisions. Note: this partially defeats the purpose of context isolation.
- **Instruction passing** — Create instructions via function call; the sub-agent receives only what it needs. Use for simple, well-defined subtasks. Maintains isolation but limits sub-agent flexibility.
- **File system memory** — Agents read and write to persistent storage. Use for complex tasks requiring shared state. The file system serves as the coordination mechanism, avoiding context bloat from shared state passing. Introduces latency and consistency challenges but scales better than message-passing.

Choose based on task complexity, coordination needs, and acceptable latency. Default to instruction passing and escalate to file system memory when shared state is needed. Avoid full context delegation unless the subtask genuinely requires it.

## Consensus and Coordination

**The Voting Problem**
Avoid simple majority voting — it treats hallucinations from weak models as equal to reasoning from strong models. Without intervention, multi-agent discussions devolve into consensus on false premises due to inherent bias toward agreement.

**Weighted Voting**
Weight agent votes by confidence or expertise. Agents with higher confidence or domain expertise should carry more weight in final decisions.

**Debate Protocols**
Structure agents to critique each other's outputs over multiple rounds. Adversarial critique often yields higher accuracy on complex reasoning than collaborative consensus. Guard against sycophantic convergence where agents agree to be agreeable rather than correct.

**Trigger-Based Intervention**
Monitor multi-agent interactions for behavioral markers. Activate stall triggers when discussions make no progress. Detect sycophancy triggers when agents mimic each other's answers without unique reasoning.

## Framework Considerations

Different frameworks implement these patterns with different philosophies. LangGraph uses graph-based state machines with explicit nodes and edges. AutoGen uses conversational/event-driven patterns with GroupChat. CrewAI uses role-based process flows with hierarchical crew structures. For framework-specific code examples, see [frameworks.md](./frameworks.md).
