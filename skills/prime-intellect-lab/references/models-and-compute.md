# Models, Decision Matrix, and the Compute API

## Platform decision matrix

| Task | Where it belongs |
| --- | --- |
| SFT / LoRA instruction tuning | `tinker` (supervised) |
| Hosted RL with environments | **Prime Intellect Lab** (this skill) |
| Agentic multi-turn RL | **Prime Intellect Lab** |
| GEPA prompt optimization | **Prime Intellect Lab** |
| Local RL with custom rewards | self-hosted `prime-rl`, or TRL / verl |
| On-demand GPU clusters | `tensorpool`, or the Compute API below |
| Custom serverless compute | `modal-ml-training`, `modal-research-gpu` |
| Cost estimation for hosted training | `tinker-training-cost` |

## Supported models

Exact IDs and availability change — always confirm with `prime models list`.
Common open-weight targets:

| Model | Type | Typical use |
| --- | --- | --- |
| `Qwen/Qwen3-4B-Instruct-2507` | Instruct | Quick iteration, prototyping |
| `Qwen/Qwen3-4B-Thinking-2507` | Thinking | Reasoning-focused training |
| `Qwen/Qwen3-30B-Instruct-2507` | Instruct (MoE) | Strong general purpose |
| `Qwen/Qwen3-30B-Thinking-2507` | Thinking (MoE) | Reasoning at scale |
| `Qwen/Qwen3-235B-Instruct-2507` | Instruct (MoE) | Frontier-level, agentic tasks |
| `Qwen/Qwen3-235B-Thinking-2507` | Thinking (MoE) | Frontier reasoning |
| `PrimeIntellect/INTELLECT-3` | — | Prime Intellect's own model |

Start prototyping with the 4B instruct model; scale up only after a small run
shows the reward moving.

## Compute API — direct GPU provisioning

Beyond hosted training, Prime Intellect exposes raw GPU pods. Reach for this only
when you need a bare cluster rather than the managed RL loop (for managed
alternatives see `tensorpool` / `modal-research-gpu`).

```bash
prime compute availability                 # check GPU availability
prime compute provision --gpu H100 --count 8
prime compute list                          # running pods
prime compute ssh <pod-id>                  # SSH in
prime compute delete <pod-id>               # tear down (do this — pods bill hourly)
```

The CLI wraps a Bearer-token REST API (auth via `PRIME_API_KEY`). Representative
endpoints — confirm the current surface in Prime Intellect's API docs:

- `GET /api/v1/availability/gpus` — check availability
- `POST /api/v1/provision-gpu` — provision instances
- `GET /api/v1/managing-pods` — list pods
- `DELETE /api/v1/managing-pods/{pod_id}` — delete a pod
- `POST /api/v1/sandbox/create-sandbox-endpoint` — create a sandbox

Always `prime compute delete` idle pods — provisioned GPUs bill until torn down.
