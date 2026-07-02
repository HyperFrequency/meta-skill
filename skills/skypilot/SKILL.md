---
name: skypilot
description: Run ML training, batch, and serving workloads across 20+ clouds (AWS, GCP, Azure, Kubernetes, Lambda, RunPod) from one YAML/CLI, with automatic cheapest-cloud selection, spot instances + auto-recovery, multi-node distributed jobs, and Sky Serve autoscaling. Use when you need to run jobs across multiple clouds, cut GPU cost via spot/region arbitrage, run long spot jobs that survive preemption, or avoid vendor lock-in. NOT for simple serverless Python GPU calls (use Modal), single persistent pods (use RunPod), pure-Ray orchestration (use Ray directly), or when you already run everything inside one existing Kubernetes cluster and need no cross-cloud routing.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Infrastructure, Multi-Cloud, Orchestration, GPU, Cost Optimization, SkyPilot]
dependencies: [skypilot>=0.7.0]
---

# SkyPilot Multi-Cloud Orchestration

Router for running ML workloads across clouds with SkyPilot. This file gives the
trigger, the quick start, and the command surface; deep detail lives in
`references/` (relocated to keep this lean). For canonical docs see
https://docs.skypilot.co.

## When to use SkyPilot

- Running ML training/batch/serving across multiple clouds (AWS, GCP, Azure, K8s, Lambda, RunPod, 20+ providers)
- Cutting GPU cost via automatic cheapest cloud/region selection and spot-instance arbitrage
- Long jobs on spot instances that must auto-recover from preemption
- Multi-node distributed training with gang scheduling
- Avoiding vendor lock-in behind one unified YAML/CLI interface

**Use something else when:**
- **Modal** — simple serverless GPU with a Python-native API, no cluster lifecycle
- **RunPod** — a single persistent pod on one cloud
- **Ray** (directly) — pure Ray-based orchestration with no cross-cloud routing
- **Kubernetes** (directly) — everything already runs in one existing K8s cluster

## Quick start

```bash
pip install "skypilot[aws,gcp,azure,kubernetes]"
sky check          # verify cloud credentials
```

`hello.yaml`:
```yaml
resources:
  accelerators: T4:1
run: |
  nvidia-smi
  echo "Hello from SkyPilot!"
```

```bash
sky launch -c hello hello.yaml   # provision + run
ssh hello                        # SSH into the cluster
sky down hello                   # terminate
```

## Minimal task YAML

```yaml
name: my-task
resources:
  accelerators: A100:4   # auto-selects cheapest cloud/region if cloud omitted
  use_spot: true
workdir: .               # synced to ~/sky_workdir (NOT persisted)
setup: pip install -r requirements.txt
run: python train.py
```

Full schema (GPUs, fallbacks, distributed env vars, storage modes, Sky Serve,
secrets, workflows) → **`references/task-yaml-reference.md`**.

## Key commands

| Command | Purpose |
|---------|---------|
| `sky launch -c NAME task.yaml` | Provision cluster and run task |
| `sky exec NAME task.yaml` | Run on existing cluster (skip setup) |
| `sky status [-a]` | Show cluster status |
| `sky stop` / `sky down NAME` | Stop (preserve state) / terminate |
| `sky logs NAME` | Stream task logs |
| `sky queue NAME` | Show job queue |
| `sky jobs launch -n NAME task.yaml` | Launch managed job (spot auto-recovery) |
| `sky jobs queue` / `sky jobs logs` | Manage managed jobs |
| `sky serve up -n NAME svc.yaml` | Deploy autoscaling serving endpoint |

## Spot auto-recovery (most common pitfall)

To survive spot preemption, launch as a **managed job** and use `job_recovery`
(the old `spot_recovery` field is deprecated):

```yaml
resources:
  accelerators: A100:8
  use_spot: true
  job_recovery:
    strategy: EAGER_NEXT_REGION   # immediately retry in a new region
    max_restarts_on_errors: 3
```
```bash
sky jobs launch -n my-job train.yaml
```
Always checkpoint to persistent `file_mounts` storage. Details in
`references/task-yaml-reference.md`.

## References

- **[Task YAML & core reference](references/task-yaml-reference.md)** — schema, GPUs, distributed training, storage, Sky Serve, workflows
- **[Advanced usage](references/advanced-usage.md)** — multi-cloud strategies, production managed jobs, Kubernetes, API server, observability
- **[Troubleshooting](references/troubleshooting.md)** — quotas, launch failures, mounts, distributed networking, billing

## Resources

- Docs: https://docs.skypilot.co
- GitHub: https://github.com/skypilot-org/skypilot
- Examples: https://github.com/skypilot-org/skypilot/tree/master/examples
- Slack: https://slack.skypilot.co
