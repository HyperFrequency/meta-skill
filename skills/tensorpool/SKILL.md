---
name: tensorpool
version: 0.1.0
description: >-
  On-demand GPU clusters and git-style batch training jobs through the TensorPool `tp` CLI:
  provision single- or multi-node clusters (H100/H200/B200/B300/L40S) with SSH access and
  SLURM+InfiniBand, submit reproducible jobs via `tp job push`/`tp job pull`, and attach
  persistent NFS or S3-compatible storage, all billed per-second. Use when you need raw
  SSH-accessible GPU boxes, multi-node distributed-training clusters, or fire-and-forget
  batch experiments whose outputs you pull back locally. NOT for serverless auto-scaling
  inference, managed fine-tuning with zero infra (use `fine-tuning`, `together-ai`), deciding
  whether renting GPUs is worth it (use `model-economics`), the actual training or serving
  code (use `distributed-training`, `optimize-for-gpu`, `inference-serving`), or multi-cloud
  cost arbitrage across providers.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# TensorPool GPU Cloud

## Overview

TensorPool is a GPU cloud you drive from one CLI, `tp`. It exposes two ways to get compute,
and picking the right one is the whole game:

- **Clusters** — long-lived, SSH-accessible GPU machines you provision, log into, and tear
  down yourself. Single-node for interactive work, or multi-node with SLURM + InfiniBand
  preinstalled for distributed training. You pay for wall-clock time the cluster exists.
- **Jobs** — a git-style batch interface. You describe a run in `tp.config.toml`, `tp job
  push` it, stream logs, and `tp job pull` the outputs back to your machine. You pay only for
  the seconds the job actually runs. No box to remember to destroy.

Everything is billed per-second (prorated), with persistent NFS or S3-compatible storage you
can attach to clusters. This skill is a router: keep the mental model and the guardrails
here, and reach into `references/` for the full command surface, config schema, pricing, and
worked workflows.

## When to Use This Skill

- You need a raw, SSH-accessible GPU box (single H100/H200/B200/L40S) to iterate interactively.
- You want multi-node distributed training with SLURM + InfiniBand already wired up.
- You have a self-contained training script and want fire-and-forget batch runs whose
  checkpoints/results download back to you (`tp job push` → `tp job pull`).
- You want per-second billing and no egress fees, and you are willing to manage lifecycle
  (create/destroy) yourself.
- You need shared high-throughput NFS across cluster nodes, or cheap object storage for
  datasets and checkpoints.

## When NOT to Use This Skill

- **Serverless, auto-scaling, scale-to-zero inference** — TensorPool clusters do not
  auto-scale; you provision and destroy them. Use a serverless GPU platform.
- **Managed fine-tuning with zero infrastructure** — if you want to hand off a dataset and
  get a model back, use `fine-tuning` or `together-ai`, not raw boxes.
- **Deciding whether renting GPUs pays off at all** — run `model-economics` first to get the
  build-vs-buy / break-even numbers; this skill is how you provision once you've decided.
- **Writing the training or serving code itself** — the distributed-training recipe, kernel
  and memory tuning, or inference server live in `distributed-training`, `optimize-for-gpu`,
  and `inference-serving`. This skill only gets you the hardware.
- **Multi-cloud cost arbitrage** — if the goal is "cheapest GPU across every provider," use a
  multi-cloud orchestrator, not a single-provider CLI.

## Setup

```bash
pip install tensorpool

# Authenticate: the CLI reads TENSORPOOL_KEY from the environment
export TENSORPOOL_KEY="tp_..."

# Verify (never echo the key itself)
[ -n "$TENSORPOOL_KEY" ] && echo "TENSORPOOL_KEY set" || echo "NOT SET"

tp me   # confirm the key resolves to your account
```

If `TENSORPOOL_KEY` is unset, get a key from the TensorPool dashboard and export it (or add
it to your shell profile / secrets manager). Do not print or log the key value.

## Cost safety — confirm before you provision

TensorPool bills real money per-second the moment a resource exists. Treat every
create/attach command as a spend commitment:

- **Before creating any cluster or job, state the instance type, the per-hour rate, and the
  expected runtime, then get explicit human approval.** Present a number like "8xH200 × 2
  nodes ≈ $X/hr" — never provision silently.
- **A cluster bills until you `tp cluster destroy` it**, even idle. Jobs stop billing when
  they finish. Prefer jobs for anything fire-and-forget.
- **Always tear down**: `tp cluster destroy <id>` and detach/destroy storage when done. A
  forgotten multi-GPU cluster is the most expensive mistake on this platform.
- Set `--deletion-protection true` on resources you must not lose, but remember protection
  does not stop billing.

Current published rates (verify — pricing is volatile) sit around ~$2/GPU-hr for H100 up to
~$5–6/GPU-hr for B300; the full table is in `references/instance-types-pricing.md`. Do not
quote a price from memory in front of a user — check the reference or the dashboard.

## Clusters — the short version

```bash
# Single-node, SSH-accessible box
tp cluster create -i ~/.ssh/id_ed25519.pub -t 1xH100 --name dev-box
tp cluster info <cluster_id>          # wait for RUNNING
tp ssh <instance_id>                  # log in
tp cluster destroy <cluster_id>       # stop the meter

# Multi-node (SLURM + InfiniBand preinstalled; 8xH200 and 8xB200 only)
tp cluster create -i ~/.ssh/id_ed25519.pub -t 8xH200 -n 4   # 4 nodes, 32 GPUs
```

Multi-node clusters expose a **jumphost** (public IP, SLURM controller) plus private-IP
**worker nodes** you reach *through* the jumphost. Full lifecycle, status machine, and the
jumphost→worker access pattern are in `references/cli-reference.md`.

## Jobs — the short version

Describe the run in `tp.config.toml`, push it, watch it, pull the results:

```bash
tp job init                    # scaffold tp.config.toml
tp job push tp.config.toml     # submit; returns a job_id
tp job listen <job_id>         # stream logs live
tp job pull <job_id>           # download the declared outputs
```

A minimal config declares the commands to run, the instance type, the output paths to bring
back, and an ignore list:

```toml
commands      = ["pip install -r requirements.txt", "python train.py --epochs 100"]
instance_type = "1xH100"
outputs       = ["checkpoints/", "model.pth", "results.json"]
ignore        = [".venv", "venv/", "__pycache__/", ".git", "*.pyc"]
```

Job status distinguishes **Error** (your non-zero exit — read the logs, fix, re-push) from
**Failed** (a node/GPU fault on TensorPool's side). Full config schema, the status machine,
and running multiple experiments from parallel configs are in `references/cli-reference.md`.

## Storage — the short version

- **Shared NFS** (`-t shared`): POSIX, high aggregate throughput, **multi-node clusters
  only**. For datasets and checkpoints read/written across nodes.
- **Object storage** (`-t object`): S3-compatible, cheaper, works on any cluster, **not
  POSIX**. Prefer `boto3`/`rclone` over the FUSE mount, and never place Python venvs (many
  tiny files) on it.

```bash
tp storage create -t shared -s 500 --name training-data
tp cluster attach <cluster_id> <storage_id>     # mounts under /mnt/...
```

Attach/detach rules, mount paths, and pricing per TB are in `references/cli-reference.md` and
`references/instance-types-pricing.md`.

## Worked workflows and troubleshooting

Three end-to-end walkthroughs — single-node batch job, multi-node SLURM distributed training
with shared storage, and interactive development — plus the common failure modes (stuck
PENDING, SSH failures, storage attach errors, object-storage slowness) live in
`references/workflows-troubleshooting.md`.

## Command quick reference

| Command | Purpose |
|---------|---------|
| `tp cluster create -t <type> [-n <nodes>] -i <pubkey>` | Provision a cluster |
| `tp cluster info <id>` / `tp cluster list` | Status / list |
| `tp cluster destroy <id>` | Terminate (stops billing) |
| `tp cluster attach\|detach <cluster_id> <storage_id>` | Mount / unmount storage |
| `tp ssh <instance_id>` | SSH into a node |
| `tp job init` / `push <config>` / `listen <id>` / `pull <id>` | Job lifecycle |
| `tp job cancel <id>` | Cancel a running job |
| `tp storage create -t <shared\|object> [-s <GB>]` | Create storage |
| `tp me` | Account / key check |

Exhaustive flags and every subcommand: `references/cli-reference.md`.

## References

- `references/cli-reference.md` — full `tp cluster` / `tp job` / `tp storage` / `tp ssh`
  command surface, the `tp.config.toml` schema, cluster and job status machines, multi-node
  jumphost architecture, and multiple-experiment patterns.
- `references/instance-types-pricing.md` — instance catalogue (which types support
  multi-node), per-GPU-hour and per-TB pricing anchors, and a **verify-before-quoting**
  note (all figures volatile).
- `references/workflows-troubleshooting.md` — three worked end-to-end workflows and the
  common failure modes with fixes.
