# DSPy Configuration, Best Practices & Comparison

Relocated from SKILL.md to keep the router lean. Covers LM provider setup
(modern `dspy.LM` API), best practices, evaluation, and framework comparison.

## LM Provider Configuration

DSPy 2.5+ unified all providers behind a single `dspy.LM` class backed by
LiteLLM. The model string is `"<provider>/<model>"`. The old per-provider
classes (`dspy.Claude`, `dspy.OpenAI`, `dspy.OllamaLocal`) are removed — do
not use them.

### Anthropic Claude

```python
import dspy

# Reads ANTHROPIC_API_KEY from env, or pass api_key=...
lm = dspy.LM("anthropic/claude-sonnet-4-6", max_tokens=1000, temperature=0.7)
dspy.configure(lm=lm)
```

### OpenAI

```python
lm = dspy.LM("openai/gpt-4o-mini", max_tokens=1000)  # reads OPENAI_API_KEY
dspy.configure(lm=lm)
```

### Local Models (Ollama)

```python
lm = dspy.LM("ollama_chat/llama3.1", api_base="http://localhost:11434", api_key="")
dspy.configure(lm=lm)
```

### Per-call / scoped models

```python
cheap_lm  = dspy.LM("openai/gpt-4o-mini")
strong_lm = dspy.LM("anthropic/claude-opus-4-8")

# Swap the active LM for a block of code
with dspy.context(lm=cheap_lm):
    context = retriever(question)

with dspy.context(lm=strong_lm):
    answer = generator(context=context, question=question)
```

## Best Practices

### 1. Start simple, iterate

```python
qa = dspy.Predict("question -> answer")            # baseline
qa = dspy.ChainOfThought("question -> answer")     # add reasoning
optimized_qa = optimizer.compile(qa, trainset=data)  # add optimization with data
```

### 2. Use descriptive signatures

```python
# Bad: vague
class Task(dspy.Signature):
    input = dspy.InputField()
    output = dspy.OutputField()

# Good: descriptive docstring + field descriptions
class SummarizeArticle(dspy.Signature):
    """Summarize news articles into 3-5 key points."""
    article = dspy.InputField(desc="full article text")
    summary = dspy.OutputField(desc="bullet points, 3-5 items")
```

### 3. Optimize with representative data

```python
trainset = [
    dspy.Example(question="factual ...",     answer="...").with_inputs("question"),
    dspy.Example(question="reasoning ...",   answer="...").with_inputs("question"),
    dspy.Example(question="calculation ...", answer="...").with_inputs("question"),
]

def metric(example, pred, trace=None):
    return example.answer in pred.answer
```

### 4. Save and load optimized programs

```python
optimized_qa.save("models/qa_v1.json")

loaded_qa = dspy.ChainOfThought("question -> answer")
loaded_qa.load("models/qa_v1.json")
```

### 5. Inspect and debug

```python
dspy.configure(lm=lm)
result = qa(question="...")

# Print the last N prompts/responses the LM actually saw
dspy.inspect_history(n=1)
```

## Evaluation

```python
from dspy.evaluate import Evaluate

def exact_match(example, pred, trace=None):
    return example.answer.lower() == pred.answer.lower()

evaluator = Evaluate(devset=testset, metric=exact_match,
                     num_threads=4, display_progress=True)

score_before = evaluator(qa)
score_after  = evaluator(optimized_qa)
print(f"Improvement: {score_after - score_before:.2%}")
```

See `optimizers.md` for richer metric design (F1, graded, multi-factor) and
train/val/test splitting.

## Comparison to Other Approaches

| Feature            | Manual Prompting | LangChain     | DSPy                |
|--------------------|------------------|---------------|---------------------|
| Prompt engineering | Manual           | Manual        | Automatic           |
| Optimization       | Trial & error    | None          | Data-driven         |
| Modularity         | Low              | Medium        | High                |
| Type safety        | No               | Limited       | Yes (Signatures)    |
| Portability        | Low              | Medium        | High                |
| Learning curve     | Low              | Medium        | Medium-High         |

**Choose DSPy when:** you have (or can generate) training data, you need
systematic prompt improvement, you're building multi-stage systems, or you
want to optimize across different LMs.

**Choose alternatives when:** quick one-off prototypes (manual prompting),
simple chains over existing integrations (LangChain), or you need fully
custom optimization logic.
