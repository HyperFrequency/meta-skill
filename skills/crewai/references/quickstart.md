# CrewAI Quick Start

## Installation

```bash
# Core framework
pip install crewai

# With 50+ built-in tools
pip install 'crewai[tools]'
```

Requires Python 3.10-3.13. Latest stable is the 1.x line (1.15.x as of mid-2026).

## Create a project with the CLI

```bash
# Create new crew project (scaffolds YAML config + crew.py + main.py)
crewai create crew my_project
cd my_project

# Install dependencies
crewai install

# Run the crew
crewai run
```

## Simple crew (code-only)

```python
from crewai import Agent, Task, Crew, Process

# 1. Define agents
researcher = Agent(
    role="Senior Research Analyst",
    goal="Discover cutting-edge developments in AI",
    backstory="You are an expert analyst with a keen eye for emerging trends.",
    verbose=True
)

writer = Agent(
    role="Technical Writer",
    goal="Create clear, engaging content about technical topics",
    backstory="You excel at explaining complex concepts to general audiences.",
    verbose=True
)

# 2. Define tasks
research_task = Task(
    description="Research the latest developments in {topic}. Find 5 key trends.",
    expected_output="A detailed report with 5 bullet points on key trends.",
    agent=researcher
)

write_task = Task(
    description="Write a blog post based on the research findings.",
    expected_output="A 500-word blog post in markdown format.",
    agent=writer,
    context=[research_task]  # Uses research output
)

# 3. Create and run crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,  # Tasks run in order
    verbose=True
)

# 4. Execute
result = crew.kickoff(inputs={"topic": "AI Agents"})
print(result.raw)
```

## YAML configuration (recommended for larger projects)

### Project structure

```
my_project/
├── src/my_project/
│   ├── config/
│   │   ├── agents.yaml    # Agent definitions
│   │   └── tasks.yaml     # Task definitions
│   ├── crew.py            # Crew assembly
│   └── main.py            # Entry point
└── pyproject.toml
```

### agents.yaml

```yaml
researcher:
  role: "{topic} Senior Data Researcher"
  goal: "Uncover cutting-edge developments in {topic}"
  backstory: >
    You're a seasoned researcher with a knack for uncovering
    the latest developments in {topic}. Known for your ability
    to find relevant information and present it clearly.

reporting_analyst:
  role: "Reporting Analyst"
  goal: "Create detailed reports based on research data"
  backstory: >
    You're a meticulous analyst who transforms raw data into
    actionable insights through well-structured reports.
```

### tasks.yaml

```yaml
research_task:
  description: >
    Conduct thorough research about {topic}.
    Find the most relevant information for {year}.
  expected_output: >
    A list with 10 bullet points of the most relevant
    information about {topic}.
  agent: researcher

reporting_task:
  description: >
    Review the research and create a comprehensive report.
    Focus on key findings and recommendations.
  expected_output: >
    A detailed report in markdown format with executive
    summary, findings, and recommendations.
  agent: reporting_analyst
  output_file: report.md
```

### crew.py

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

@CrewBase
class MyProjectCrew:
    """My Project crew"""

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
            tools=[SerperDevTool()],
            verbose=True
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'],
            verbose=True
        )

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])

    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'],
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
```

### main.py

```python
from my_project.crew import MyProjectCrew

def run():
    inputs = {
        'topic': 'AI Agents',
        'year': 2025
    }
    MyProjectCrew().crew().kickoff(inputs=inputs)

if __name__ == "__main__":
    run()
```
