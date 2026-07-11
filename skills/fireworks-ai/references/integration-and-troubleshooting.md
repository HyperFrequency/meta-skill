# Fireworks AI — Integration, CLI & Troubleshooting

## OpenAI SDK as a drop-in

Fireworks speaks the OpenAI wire protocol. Point the SDK at Fireworks and every
`chat.completions`, `embeddings`, and `batches` call works unchanged:

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.fireworks.ai/inference/v1",
    api_key=os.environ["FIREWORKS_API_KEY"],
)
```

Or configure it through the standard OpenAI env vars, so libraries that build
their own client (LangChain, LlamaIndex, etc.) pick Fireworks up with no code
change:

```bash
export OPENAI_API_BASE="https://api.fireworks.ai/inference/v1"
export OPENAI_API_KEY="fw_..."
```

## Native Fireworks SDK (optional)

```python
import os, fireworks.client

fireworks.client.api_key = os.environ["FIREWORKS_API_KEY"]

response = fireworks.client.ChatCompletion.create(
    model="accounts/fireworks/models/llama-v3p3-70b-instruct",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

Prefer the OpenAI-compatible path for portability; reach for the native SDK only
for Fireworks-specific helpers.

## firectl CLI

`firectl` is the recommended interface for control-plane work (models,
deployments, fine-tuning).

```bash
# Install
brew tap fw-ai/firectl && brew install firectl     # macOS / Linux
curl -sSL https://cli.fireworks.ai/install.sh | bash
choco install firectl                              # Windows
firectl version && firectl upgrade

# Auth
firectl signin        # interactive login
firectl whoami        # current account

# Models
firectl model create my-model /path/to/weights
firectl model list
firectl model get accounts/{account_id}/models/my-model
firectl model delete accounts/{account_id}/models/my-model

# Deployments
firectl deployment create accounts/fireworks/models/llama-v3p3-70b-instruct --display-name "prod-llama"
firectl deployment list
firectl deployment scale {deployment_id} --min-replica-count 2 --max-replica-count 8
firectl deployment delete {deployment_id}

# Fine-tuning
firectl supervised-fine-tuning-job create my-sft-job \
    --model accounts/fireworks/models/llama-v3p3-70b-instruct \
    --dataset accounts/{account_id}/datasets/my-dataset
firectl reinforcement-fine-tuning-job create my-rl-job \
    --base-model accounts/fireworks/models/llama-v3p3-70b-instruct \
    --reward-model accounts/{account_id}/models/my-reward-model
firectl fine-tuning-job list
firectl fine-tuning-job get my-sft-job
firectl fine-tuning-job stop my-sft-job
firectl fine-tuning-job resume my-sft-job
```

## Cost optimization

### Prompt caching (automatic)

Fireworks caches repeated prompt prefixes and reuses their KV state — no config
required. To maximize hits:

- Put static system prompts at the **start** of `messages`.
- Keep dynamic, per-request content at the **end**.
- Reuse identical system prompts across requests.

### Batch inference (~50% off)

For non-latency-sensitive workloads, submit a JSONL batch through the
OpenAI-compatible batch API. Each line is a request:
`{"custom_id": "req-1", "method": "POST", "url": "/v1/chat/completions", "body": {...}}`.

```python
batch_file = client.files.create(file=open("batch_requests.jsonl", "rb"), purpose="batch")

batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)
print(batch.id, batch.status)

status = client.batches.retrieve(batch.id)
print(status.status)   # completed → download results via the output file id
```

See the cost checklist in [models-and-pricing.md](models-and-pricing.md).

## Common issues

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | `FIREWORKS_API_KEY` unset or invalid; get a key at https://fireworks.ai/api-keys |
| `Model not found` | Use the full ID: `accounts/fireworks/models/{name}` |
| `Context length exceeded` | Reduce input or set `extra_body={"context_length_exceeded_behavior": "truncate"}` |
| Rate limited (serverless) | Move to an on-demand deployment (no rate limits) — see [deployments.md](deployments.md) |
| Deployment cold-start latency | Set `minReplicaCount >= 1` to keep a replica warm |
| Fine-tuning job stuck | Dataset JSONL does not match the method's schema; check `firectl fine-tuning-job get` |
| Tool calls ignored | Use a function-calling model (Llama 3.3, Qwen, DeepSeek V3) |
| JSON mode returns invalid JSON | Use `response_format` with an explicit `schema` — see [inference.md](inference.md) |
| Streaming usage stats missing | `openai >= 1.6.1` and `stream_options={"include_usage": True}`; usage is in the final chunk |
| Deployment not scaling | Raise `maxReplicaCount`; review the deployment shape |

## Resources

- Docs: https://docs.fireworks.ai
- API reference: https://docs.fireworks.ai/api-reference/introduction
- Model catalog: https://fireworks.ai/models
- Pricing: https://fireworks.ai/pricing
- `firectl`: https://docs.fireworks.ai/tools-sdks/firectl/firectl
- OpenAI compatibility: https://docs.fireworks.ai/tools-sdks/openai-compatibility
- Fine-tuning guide: https://docs.fireworks.ai/fine-tuning/fine-tuning-models
- Cookbook: https://github.com/fw-ai/cookbook
- Status: https://status.fireworks.ai
