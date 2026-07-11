# Integration & troubleshooting

## OpenAI SDK compatibility

Together implements the OpenAI REST surface, so the stock `openai` SDK works
after changing two things: `api_key` and `base_url`.

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["TOGETHER_API_KEY"],
    base_url="https://api.together.xyz/v1",
)

response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    max_tokens=256,
)
print(response.choices[0].message.content)
```

### What the OpenAI SDK supports against Together

| Feature | Works |
|---------|-------|
| `chat.completions.create` | Yes |
| Streaming responses | Yes |
| Function calling / tools | Yes |
| JSON mode / structured outputs | Yes |
| Vision (multimodal) | Yes |
| `embeddings.create` | Yes |
| `images.generate` | Yes |
| `models.list` | Yes |
| Async client | Yes |
| `.with_raw_response` / `.with_streaming_response` | Yes |

Caveat: Together-only sampling params (`top_k`, `repetition_penalty`) are not in
the OpenAI schema. Use the first-party `together` SDK when you need them.

### LangChain

Point `ChatOpenAI` at the Together base URL:

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="meta-llama/Llama-3.3-70B-Instruct-Reference",
    openai_api_key=os.environ["TOGETHER_API_KEY"],
    openai_api_base="https://api.together.xyz/v1",
)
print(llm.invoke("What is the meaning of life?").content)
```

The same base-URL swap works for any OpenAI-compatible client (LlamaIndex,
Instructor, the Vercel AI SDK, etc.).

## CLI reference

```bash
pip install --upgrade together
export TOGETHER_API_KEY="your-api-key"

# Chat
together chat.completions \
    --message "system" "You are helpful." \
    --message "user" "What is PyTorch?" \
    --model meta-llama/Llama-3.3-70B-Instruct-Reference

# Models
together models list

# Images
together images generate "A futuristic city at sunset" \
    --model black-forest-labs/FLUX.1-schnell --n 1

# Files
together files upload training_data.jsonl
together files list
together files retrieve file-abc123
together files delete file-abc123

# Fine-tuning (see fine-tuning.md)
together fine-tuning create --training-file file-abc123 \
    -m meta-llama/Meta-Llama-3.1-8B-Instruct-Reference
together fine-tuning list
together fine-tuning status ft-abc123
```

CLI subcommand names track SDK versions; run `together --help` and
`together <group> --help` to confirm on your install.

## Common issues

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | `TOGETHER_API_KEY` unset or invalid — re-check the export and the key in the dashboard |
| `429 Rate Limited` | Add exponential backoff, cap concurrency, or raise plan limits |
| `Model not found` | Verify the exact ID at https://docs.together.ai/docs/serverless-models (IDs change) |
| JSON mode returns invalid JSON | Restate the schema in the system prompt alongside `response_format`; retry once on parse failure |
| Function calling never fires | Use a tool-capable model (Llama 3.x, DeepSeek, Qwen3, Mistral) |
| Fine-tuning job stuck/failed | Validate JSONL — every line parses and has a `messages` array |
| Batch job failed | Ensure each JSONL line has unique `custom_id` and a valid `body` |
| Slow responses | Try a Turbo/Lite variant, reduce `max_tokens`, or a smaller model |
| Embedding dim mismatch | One index = one embedding model; re-embed if you switch (768 vs 1024) |
| Image generation timeout | Lower `steps`/`n`, or use `FLUX.1-schnell` |
| Together-only params rejected | `top_k`/`repetition_penalty` need the `together` SDK, not the `openai` SDK |

## Resources

- Docs: https://docs.together.ai
- API reference: https://docs.together.ai/reference
- Pricing: https://www.together.ai/pricing
- Serverless model catalog: https://docs.together.ai/docs/serverless-models
- Fine-tuning guide: https://docs.together.ai/docs/fine-tuning-quickstart
- Python SDK: https://github.com/togethercomputer/together-python
- TypeScript SDK: https://github.com/togethercomputer/together-typescript
- Cookbook: https://github.com/togethercomputer/together-cookbook
- Status: https://status.together.ai
