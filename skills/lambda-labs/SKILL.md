---
name: lambda-labs
description: Reserved and on-demand GPU cloud instances (B200/H100/A100/etc.) for ML training and inference via simple SSH, persistent filesystems, and 1-Click Slurm clusters. Use when you need dedicated full-root GPU boxes, multi-node InfiniBand clusters, or the pre-installed Lambda Stack (PyTorch/CUDA/NCCL). Do NOT use for serverless/auto-scaling inference endpoints (use Modal), multi-cloud cost-routing (use SkyPilot), or the cheapest spot/marketplace GPUs (use RunPod or Vast.ai).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Infrastructure, GPU Cloud, Training, Inference, Lambda Labs]
dependencies: [lambda-cloud-client>=1.0.0]
---

# Lambda Labs GPU Cloud

Router for running ML workloads on Lambda Labs: on-demand single/multi-GPU
instances and 1-Click Slurm clusters. Detailed API, CLI, and workflow recipes
live in `references/`.

## When to use Lambda Labs

**Use when you need:**
- Dedicated GPU instances with full root + SSH access
- Long training jobs (hours to days), pay-per-minute, no egress fees
- Persistent filesystems shared across instance restarts
- High-performance multi-node clusters (16-512 GPUs, InfiniBand)
- A pre-installed ML stack (Lambda Stack: PyTorch, TensorFlow, JAX, CUDA, NCCL)

**Use an alternative instead:**
- **Modal** — serverless, auto-scaling inference / scale-to-zero
- **SkyPilot** — multi-cloud orchestration and cost-routing
- **RunPod** — cheaper spot instances and serverless endpoints
- **Vast.ai** — GPU marketplace with the lowest prices

## GPU instances & pricing

| GPU | VRAM | Price/GPU/hr | Best for |
|-----|------|--------------|----------|
| B200 SXM6 | 180 GB | $4.99 | Largest models, fastest training |
| H100 SXM | 80 GB | $2.99-3.29 | Large model training |
| H100 PCIe | 80 GB | $2.49 | Cost-effective H100 |
| GH200 | 96 GB | $1.49 | Single-GPU large models |
| A100 80GB | 80 GB | $1.79 | Production training |
| A100 40GB | 40 GB | $1.29 | Standard training |
| A10 | 24 GB | $0.75 | Inference, fine-tuning |
| A6000 | 48 GB | $0.80 | Good VRAM/price ratio |
| V100 | 16 GB | $0.55 | Budget training |

Counts: 1x (fine-tuning/dev), 2x-4x (medium/large models), 8x (distributed
DDP/FSDP). Launch takes ~3-5 min (single-GPU) to ~15 min (multi-GPU). Prices
drift — confirm current rates at https://lambda.ai/instances.

## Quick start

1. Create an account at https://lambda.ai, add a payment method, generate an API
   key, and add an SSH key (required before launching).
2. Launch from https://cloud.lambda.ai/instances — pick GPU type, region, SSH
   key, and optionally attach a filesystem.
3. Connect once it is running:

```bash
ssh ubuntu@<INSTANCE-IP>           # or: ssh -i ~/.ssh/lambda_key ubuntu@<IP>
nvidia-smi                          # verify GPUs
```

To drive everything from code instead of the console, see
`references/api-and-cli.md`.

## Common issues

| Issue | Solution |
|-------|----------|
| Instance won't launch | Check region availability; try a different GPU |
| SSH connection refused | Wait for init (3-15 min) |
| Data lost after terminate | Use persistent filesystems |
| Slow data transfer | Use a filesystem in the same region |
| GPU not detected | Reboot instance, check drivers |

For deeper diagnosis see `references/troubleshooting.md`.

## References

- **[API & CLI](references/api-and-cli.md)** — Python client, raw `curl`, SSH key management
- **[Workflows](references/workflows.md)** — storage, single/multi-GPU training, 1-Click Clusters, cost optimization
- **[Advanced Usage](references/advanced-usage.md)** — multi-node DDP launcher, API automation
- **[Troubleshooting](references/troubleshooting.md)** — common issues and solutions

## Resources

- Docs: https://docs.lambda.ai · Console: https://cloud.lambda.ai
- Pricing: https://lambda.ai/instances · Support: https://support.lambdalabs.com
