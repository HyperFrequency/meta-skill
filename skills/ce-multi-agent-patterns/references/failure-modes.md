# Multi-Agent Failure Modes, Gotchas, and Examples

Read this when hardening a multi-agent system: anticipating how coordination breaks, budgeting realistically, and seeing concrete topology/handoff examples. The SKILL.md router lists the headline risks; this file holds the mitigations and worked examples.

## Failure Modes and Mitigations

**Failure: Supervisor Bottleneck**
The supervisor accumulates context from all workers, becoming susceptible to saturation and degradation.

Mitigate by constraining worker output schemas so workers return only distilled summaries. Use checkpointing to persist supervisor state without carrying full history in context.

**Failure: Coordination Overhead**
Agent communication consumes tokens and introduces latency. Complex coordination can negate parallelization benefits.

Mitigate by minimizing communication through clear handoff protocols. Batch results where possible. Use asynchronous communication patterns. Measure whether multi-agent coordination actually saves time versus a single agent with a longer context.

**Failure: Divergence**
Agents pursuing different goals without central coordination drift from intended objectives.

Mitigate by defining clear objective boundaries for each agent. Implement convergence checks that verify progress toward shared goals. Set time-to-live limits on agent execution to prevent unbounded exploration.

**Failure: Error Propagation**
Errors in one agent's output propagate to downstream agents that consume that output, compounding into increasingly wrong results.

Mitigate by validating agent outputs before passing to consumers. Implement retry logic with circuit breakers. Use idempotent operations where possible. Consider adding a verification agent that cross-checks critical outputs before they enter the pipeline.

## Gotchas

1. **Supervisor bottleneck scaling** — Supervisor context pressure grows non-linearly with worker count. At 5+ workers, the supervisor spends more tokens processing summaries than workers spend on actual tasks. Set a hard cap on workers per supervisor (3-5) and add a second supervisor tier rather than overloading one.
2. **Token cost underestimation** — Multi-agent runs cost approximately 15x baseline. Teams consistently underbudget because they estimate per-agent costs without accounting for coordination overhead, retries, and consensus rounds. Budget for 15x and treat anything less as a bonus.
3. **Sycophantic consensus** — Agents in debate patterns tend to converge on agreeable answers, not correct ones. LLMs have an inherent bias toward agreement. Counter this by assigning explicit adversarial roles and requiring agents to state disagreements before convergence is allowed.
4. **Agent sprawl** — Adding more agents past 3-5 shows diminishing returns and increases coordination overhead. Each additional agent adds communication channels quadratically. Start with the minimum viable number of agents and add only when a clear context isolation benefit exists.
5. **Telephone game in message-passing** — Information degrades through repeated summarization as it passes between agents. Each agent paraphrases and loses nuance. Use filesystem coordination instead of message-passing for state that multiple agents need to access faithfully.
6. **Error propagation cascades** — One agent's hallucination becomes another agent's "fact." Downstream agents have no way to distinguish upstream hallucinations from genuine information. Add validation checkpoints between agents and never trust upstream output without verification.
7. **Over-decomposition** — Splitting tasks too finely creates more coordination overhead than the task itself. A 10-step pipeline with 10 agents spends more tokens on handoffs than on actual work. Decompose only when subtasks genuinely benefit from separate contexts.
8. **Missing shared state** — Agents operating without a shared filesystem or state store duplicate work, produce inconsistent outputs, and lose track of what has already been accomplished. Establish shared persistent storage before building multi-agent workflows.

## Examples

**Example 1: Research Team Architecture**
```text
Supervisor
├── Researcher (web search, document retrieval)
├── Analyzer (data analysis, statistics)
├── Fact-checker (verification, validation)
└── Writer (report generation, formatting)
```

**Example 2: Handoff Protocol**
```python
def handle_customer_request(request):
    if request.type == "billing":
        return transfer_to(billing_agent)
    elif request.type == "technical":
        return transfer_to(technical_agent)
    elif request.type == "sales":
        return transfer_to(sales_agent)
    else:
        return handle_general(request)
```
