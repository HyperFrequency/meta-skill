# Fireworks AI — On-Demand GPU Deployments

Dedicated deployments give you predictable latency, no serverless rate limits,
and the ability to serve custom or fine-tuned models. They are billed per
GPU-second while running. Use them when serverless throughput or rate limits are
the bottleneck, or when you need a private model endpoint.

Control-plane REST lives under
`https://api.fireworks.ai/v1/accounts/{account_id}/deployments`. The `firectl`
CLI (see [integration-and-troubleshooting.md](integration-and-troubleshooting.md))
is the more stable interface; confirm REST field names against
https://docs.fireworks.ai/api-reference before scripting.

Shared headers:

```python
import os, requests
headers = {
    "Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}",
    "Content-Type": "application/json",
}
```

## Create a deployment

```python
url = "https://api.fireworks.ai/v1/accounts/{account_id}/deployments"
payload = {
    "displayName": "my-llama-deployment",
    "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "deploymentShape": "fast",   # fast | throughput | minimal
    "minReplicaCount": 1,        # >= 1 keeps replicas warm (no cold start)
    "maxReplicaCount": 4,
}
deployment = requests.post(url, headers=headers, json=payload).json()
```

## Deployment shapes

| Shape | Optimized for | Use case |
|-------|---------------|----------|
| `fast` | Lowest latency | Real-time chat, interactive apps |
| `throughput` | Maximum tokens/sec | Batch processing, high volume |
| `minimal` | Lowest cost | Development, testing |

## GPU options and pricing (approximate)

Per GPU-hour; verify at https://fireworks.ai/pricing.

| GPU | VRAM | $/GPU/hr |
|-----|------|----------|
| A100 80GB  | 80 GB  | 2.90 |
| H100 80GB  | 80 GB  | 4.00 |
| H200 141GB | 141 GB | 6.00 |
| B200 180GB | 180 GB | 9.00 |

## Manage deployments

```python
# List
requests.get(f"https://api.fireworks.ai/v1/accounts/{{account_id}}/deployments", headers=headers).json()

# Scale (patch replica bounds)
requests.patch(
    f"https://api.fireworks.ai/v1/{deployment['name']}",
    headers=headers,
    json={"minReplicaCount": 2, "maxReplicaCount": 8},
)

# Delete
requests.delete(f"https://api.fireworks.ai/v1/{deployment['name']}", headers=headers)
```

## Query a deployment

Once live, call it through the same OpenAI-compatible API — just pass the
deployment's model ID as `model`:

```python
response = client.chat.completions.create(
    model="accounts/{account_id}/deployments/{deployment_id}",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

## Failure modes

- **Slow cold start**: set `minReplicaCount >= 1` to keep at least one replica
  warm; scaling from zero incurs load time.
- **Not scaling under load**: `maxReplicaCount` too low, or a shape that trades
  throughput for latency — raise the cap or switch to `throughput`.
- **Idle spend**: deployments bill per GPU-second while up. Delete or scale to
  zero when idle; serverless has no standing cost.
