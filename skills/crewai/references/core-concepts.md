# CrewAI Core Concepts

## Agents - Autonomous workers

```python
from crewai import Agent

agent = Agent(
    role="Data Scientist",                    # Job title/role
    goal="Analyze data to find insights",     # What they aim to achieve
    backstory="PhD in statistics...",         # Background context
    llm="gpt-4o",                             # LLM to use
    tools=[],                                 # Tools available
    memory=True,                              # Enable memory
    verbose=True,                             # Show reasoning
    allow_delegation=True,                    # Can delegate to others
    max_iter=15,                              # Max reasoning iterations
    max_rpm=10                                # Rate limit
)
```

## Tasks - Units of work

```python
from crewai import Task

task = Task(
    description="Analyze the sales data for Q4 2024. {context}",
    expected_output="A summary report with key metrics and trends.",
    agent=analyst,                            # Assigned agent
    context=[previous_task],                  # Input from other tasks
    output_file="report.md",                  # Save to file
    async_execution=False,                    # Run synchronously
    human_input=False                         # No human approval needed
)
```

## Crews - Teams of agents

```python
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, writer, editor],      # Team members
    tasks=[research, write, edit],            # Tasks to complete
    process=Process.sequential,               # Or Process.hierarchical
    verbose=True,
    memory=True,                              # Enable crew memory
    cache=True,                               # Cache tool results
    max_rpm=10,                               # Rate limit
    share_crew=False                          # Opt-in telemetry
)

# Execute with inputs
result = crew.kickoff(inputs={"topic": "AI trends"})

# Access results
print(result.raw)                             # Final output
print(result.tasks_output)                    # All task outputs
print(result.token_usage)                     # Token consumption
```

## Process types

### Sequential (default)

Tasks execute in order, each agent completing their task before the next:

```python
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential  # Task 1 → Task 2 → Task 3
)
```

### Hierarchical

Auto-creates a manager agent that delegates and coordinates:

```python
crew = Crew(
    agents=[researcher, writer, analyst],
    tasks=[research_task, write_task, analyze_task],
    process=Process.hierarchical,  # Manager delegates tasks
    manager_llm="gpt-4o"           # LLM for manager
)
```

## Memory system

```python
# Enable all memory types
crew = Crew(
    agents=[researcher],
    tasks=[research_task],
    memory=True,           # Enable memory
    embedder={             # Custom embeddings
        "provider": "openai",
        "config": {"model": "text-embedding-3-small"}
    }
)
```

**Memory types:** Short-term (ChromaDB), Long-term (SQLite), Entity (ChromaDB).

Set a custom storage location with the `CREWAI_STORAGE_DIR` environment variable.

## LLM providers

```python
from crewai import LLM

llm = LLM(model="gpt-4o")                                              # OpenAI (default)
llm = LLM(model="claude-sonnet-4-5-20250929")                         # Anthropic
llm = LLM(model="ollama/llama3.1", base_url="http://localhost:11434") # Local
llm = LLM(model="azure/gpt-4o", base_url="https://...")               # Azure

agent = Agent(role="Analyst", goal="Analyze data", llm=llm)
```

## Best practices

1. **Clear roles** - Each agent should have a distinct specialty.
2. **YAML config** - Better organization for larger projects.
3. **Enable memory** - Improves context across tasks.
4. **Set max_iter** - Prevent infinite loops (default 15).
5. **Limit tools** - 3-5 tools per agent max.
6. **Rate limiting** - Set max_rpm to avoid API limits.
