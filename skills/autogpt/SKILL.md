---
name: autogpt
description: Autonomous AI agent platform (Significant-Gravitas/AutoGPT) for building, deploying, and running continuous agents via a visual node/block workflow builder or the Forge dev toolkit. Use when building visual workflow-based agents, deploying persistent agents with webhook/schedule triggers, composing multi-step automation pipelines, or needing a self-hosted no-code/low-code agent builder. Do NOT use for simple one-shot LLM calls (call the model SDK directly), fine-grained programmatic agent control (use LangChain/LlamaIndex), role-based multi-agent crews (use CrewAI), or fully managed agents with no self-hosting (use OpenAI Assistants).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Agents, AutoGPT, Autonomous Agents, Workflow Automation, Visual Builder, AI Platform]
dependencies: [autogpt-platform>=0.4.0]
---

# AutoGPT - Autonomous AI Agent Platform

Platform for building, deploying, and managing continuous AI agents through a
visual interface or a developer toolkit. This file is a router; deep how-to
content lives in `references/`.

## When to use AutoGPT

**Use AutoGPT when:**
- Building autonomous agents that run continuously
- Creating visual workflow-based AI agents
- Deploying agents with external triggers (webhooks, schedules)
- Building complex multi-step automation pipelines
- You need a self-hosted no-code/low-code agent builder

**Use alternatives instead:**
- **LangChain/LlamaIndex**: fine-grained programmatic control over agent logic
- **CrewAI**: role-based multi-agent collaboration
- **OpenAI Assistants**: simple fully-hosted agent deployments
- **Semantic Kernel**: Microsoft ecosystem integration
- A plain **model SDK call**: single-shot generate/summarize/classify tasks

**Key features:** visual drag-and-drop builder, continuous/triggered execution,
marketplace of shareable agents and blocks, modular block system, the Forge
developer toolkit, and a standardized benchmark suite.

## Two systems

- **AutoGPT Platform (production):** React visual builder + FastAPI backend with
  an execution engine, on PostgreSQL + Redis + RabbitMQ.
- **AutoGPT Classic (development):** `Forge` agent toolkit, `agbenchmark`
  performance testing, and a development CLI (under `classic/`).

## Core concepts

### Graphs, nodes, blocks

Agents are **graphs** of **nodes** connected by **links**; each node wraps a
**block**:

```
Graph (Agent)
  ├── Node (Input)    → AgentInputBlock
  ├── Node (Process)  → LLMBlock
  ├── Node (Decision) → SmartDecisionMaker
  └── Node (Output)   → AgentOutputBlock
```

Blocks are reusable functional components, typed by role:

| Block Type | Purpose |
|------------|---------|
| `INPUT` | Agent entry points |
| `OUTPUT` | Agent outputs |
| `AI` | LLM calls, text generation |
| `WEBHOOK` | External triggers |
| `STANDARD` | General operations |
| `AGENT` | Nested agent execution |

### Execution flow

```
User/Trigger → Graph Execution → Node Execution → Block.execute()
     ↓              ↓                 ↓
  Inputs      Queue System      Output Yields
```

## Quick start (local dev)

```bash
git clone https://github.com/Significant-Gravitas/AutoGPT.git
cd AutoGPT/autogpt_platform
cp .env.example .env
docker compose up -d --build   # backend services
```

Then start the frontend and open the UI:
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8006/api
- WebSocket: ws://localhost:8001/ws

Full setup, production compose, environment variables, and the encryption-key
step are in [Advanced Usage](references/advanced-usage.md#production-deployment).

## Best practices

1. **Start simple**: begin with 3-5 node agents.
2. **Test incrementally**: run and test after each change.
3. **Use webhooks**: external triggers for event-driven agents.
4. **Monitor costs**: track LLM API usage via the credits system.
5. **Version agents**: save working versions before changes.
6. **Benchmark**: use agbenchmark to validate agent quality.

## References

- **[API & Execution](references/api-and-execution.md)** — trigger types
  (manual/webhook/scheduled), WebSocket + REST monitoring, building agents in the
  visual builder, and integrations/credentials.
- **[Forge & Benchmark](references/forge-and-benchmark.md)** — Classic dev
  toolkit: custom agents, abilities, and the agbenchmark suite.
- **[Advanced Usage](references/advanced-usage.md)** — custom block development,
  advanced execution/composition patterns, production deployment, scaling.
- **[Troubleshooting](references/troubleshooting.md)** — installation, service,
  execution, and performance issues; debugging tips.

## Resources

- **Documentation**: https://docs.agpt.co
- **Repository**: https://github.com/Significant-Gravitas/AutoGPT
- **Discord**: https://discord.gg/autogpt
- **License**: MIT (Classic) / Polyform Shield (Platform)
