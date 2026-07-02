# AutoGPT Classic: Forge & Benchmark

The AutoGPT **Classic** tree (`classic/` in the repo) is the developer-facing
toolkit for building and evaluating agents in code, separate from the visual
Platform. It ships two main tools: **Forge** (agent dev toolkit) and
**agbenchmark** (standardized performance testing).

## Using Forge (Development)

### Create a custom agent

```bash
# Setup forge environment
cd classic
./run setup

# Create new agent from template
./run forge create my-agent

# Start agent server
./run forge start my-agent
```

### Agent structure

```
my-agent/
├── agent.py          # Main agent logic
├── abilities/        # Custom abilities
│   ├── __init__.py
│   └── custom.py
├── prompts/          # Prompt templates
└── config.yaml       # Agent configuration
```

### Implement a custom ability

```python
from forge import Ability, ability

@ability(
    name="custom_search",
    description="Search for information",
    parameters={
        "query": {"type": "string", "description": "Search query"}
    }
)
def custom_search(query: str) -> str:
    """Custom search ability."""
    # Implement search logic
    result = perform_search(query)
    return result
```

## Benchmarking agents (agbenchmark)

### Run benchmarks

```bash
# Run all benchmarks
./run benchmark

# Run specific category
./run benchmark --category coding

# Run with specific agent
./run benchmark --agent my-agent
```

### Benchmark categories

- **Coding**: Code generation and debugging
- **Retrieval**: Information finding
- **Web**: Web browsing and interaction
- **Writing**: Text generation tasks

### VCR cassettes

Benchmarks use recorded HTTP responses for reproducibility:

```bash
# Record new cassettes
./run benchmark --record

# Run with existing cassettes
./run benchmark --playback
```
