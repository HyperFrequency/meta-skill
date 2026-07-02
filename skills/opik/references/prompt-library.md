# Prompt Library — detailed examples

Background and rules live in SKILL.md ("Prompt Library"). This file holds the
longer code samples: multi-turn chat templates and the TypeScript path.

Reminders that apply to every snippet here:
- Call `get_prompt` / `get_chat_prompt` **inside** a `@opik.track`-decorated
  function so the fetched version is linked to the trace and shows in the UI.
- Store model/temperature/etc. in the prompt's `metadata` dict so config versions
  together with the template; read it back via `prompt.metadata["model"]`.
- `get_prompt` / `get_chat_prompt` always return the latest published version
  (including metadata). After the first run the prompt is editable/versionable
  from the Opik UI.

## Python — string prompt (full, with create-on-first-run fallback)

```python
import opik

client = opik.Opik()

@opik.track(entrypoint=True, project_name="my-agent")
def run_agent(question: str) -> str:
    # Fetch inside @track so the prompt version is recorded in the trace
    prompt = client.get_prompt(name="agent-system-prompt")
    if prompt is None:
        prompt = client.create_prompt(
            name="agent-system-prompt",
            prompt="You are a helpful assistant for {{product}}.",
            metadata={"model": "gpt-4o", "temperature": 0.7, "max_tokens": 1024},
        )
    system_message = prompt.format(product="Opik")
    return llm_call(
        model=prompt.metadata["model"],
        temperature=prompt.metadata["temperature"],
        max_tokens=prompt.metadata["max_tokens"],
        system_prompt=system_message,
        question=question,
    )
```

## Python — multi-turn chat template

```python
@opik.track(entrypoint=True, project_name="my-agent")
def run_agent(task: str) -> str:
    chat_prompt = client.get_chat_prompt(name="agent-chat-template")
    if chat_prompt is None:
        chat_prompt = client.create_chat_prompt(
            name="agent-chat-template",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Help me with {{task}}"},
            ],
            metadata={"model": "gpt-4o", "temperature": 0.7},
        )
    messages = chat_prompt.format(task=task)
    return llm_call(
        model=chat_prompt.metadata["model"],
        temperature=chat_prompt.metadata["temperature"],
        messages=messages,
    )
```

## TypeScript — string prompt

```typescript
import { Opik, track } from "opik";

const client = new Opik({ projectName: "my-agent" });

const runAgent = track({ entrypoint: true, projectName: "my-agent" }, async (question: string) => {
    // Fetch inside track() so the prompt version is recorded in the trace
    let prompt = await client.getPrompt({ name: "agent-system-prompt" });
    if (prompt === null) {
        prompt = await client.createPrompt({
            name: "agent-system-prompt",
            prompt: "You are a helpful assistant for {{product}}.",
            metadata: { model: "gpt-4o", temperature: 0.7, maxTokens: 1024 },
        });
    }
    const systemMessage = prompt.format({ product: "Opik" });
    const { model, temperature, maxTokens } = prompt.metadata as { model: string; temperature: number; maxTokens: number };
    return llmCall({ model, temperature, maxTokens, systemMessage, question });
});
```
