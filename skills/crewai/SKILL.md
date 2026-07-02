---
name: crewai
description: Multi-agent orchestration framework (standalone, no LangChain) for building teams of role-based AI agents that collaborate on complex tasks. Use when you need specialized agents (researcher/writer/analyst) with roles, goals, memory, and sequential or hierarchical execution, or event-driven Flows mixing crews with conditional branching. Use when you want a lower learning curve than LangChain/LangGraph for production multi-agent workflows. Do NOT use for single-agent apps, general LLM/RAG pipelines (LangChain), graph workflows with cycles/fine-grained state (LangGraph), or document Q&A retrieval (LlamaIndex).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Agents, CrewAI, Multi-Agent, Orchestration, Collaboration, Role-Based, Autonomous, Workflows, Memory, Production]
dependencies: [crewai>=1.2.0, crewai-tools>=1.2.0]
---

# CrewAI - Multi-Agent Orchestration Framework

Build teams of autonomous, role-based AI agents that collaborate to solve complex
tasks. Standalone (no LangChain dependency), with two paradigms: **Crews**
(autonomous role-based collaboration) and **Flows** (event-driven orchestration).

## When to use CrewAI

**Use CrewAI when:**
- Building multi-agent systems with specialized, role-based agents
- You want sequential or hierarchical task delegation (researcher → writer → editor)
- You need built-in memory (short/long-term, entity) and 50+ ready tools
- You want a simpler setup than LangChain/LangGraph for production workflows

**Use alternatives instead:**
- **LangChain** — general-purpose LLM apps, RAG pipelines
- **LangGraph** — complex stateful workflows with cycles / fine-grained state
- **AutoGen** — Microsoft ecosystem, multi-agent conversations
- **LlamaIndex** — document Q&A, knowledge retrieval

## Routing — read the reference for your task

| Your task | Reference |
|-----------|-----------|
| Install, scaffold a project, first crew, YAML config | [references/quickstart.md](references/quickstart.md) |
| Agent / Task / Crew params, process types, memory, LLM providers, best practices | [references/core-concepts.md](references/core-concepts.md) |
| Event-driven workflows, `@start`/`@listen`/`@router`, state management | [references/flows.md](references/flows.md) |
| Built-in tools, custom tools, MCP integration | [references/tools.md](references/tools.md) |
| Errors, loops, memory/storage issues, debugging | [references/troubleshooting.md](references/troubleshooting.md) |

## 30-second orientation

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(role="Research Analyst", goal="Find AI trends",
                   backstory="Expert analyst.", verbose=True)
research = Task(description="Research {topic}. Find 5 trends.",
                expected_output="5 bullet points.", agent=researcher)

crew = Crew(agents=[researcher], tasks=[research], process=Process.sequential)
result = crew.kickoff(inputs={"topic": "AI Agents"})
print(result.raw)
```

Full walkthroughs (CLI scaffolding, YAML projects, hierarchical crews, Flows) live
in the references above — keep this file as the entry point, not a tutorial.

## Resources

- **GitHub**: https://github.com/crewAIInc/crewAI
- **Docs**: https://docs.crewai.com
- **Tools**: https://github.com/crewAIInc/crewAI-tools
- **Examples**: https://github.com/crewAIInc/crewAI-examples
- **Version**: 1.x stable (1.15.x as of mid-2026) · **License**: MIT
