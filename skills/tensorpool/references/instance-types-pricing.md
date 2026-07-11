# Instance types and pricing

**All figures below are volatile.** Prices, GPU availability, and which types support
multi-node change over time. **Verify against the TensorPool dashboard or pricing page before
quoting a number to anyone**, and never state a price from memory in front of a user. Use
these only as order-of-magnitude anchors.

## Instance catalogue

| Instance type | Multi-node (`-n > 1`) |
|---------------|-----------------------|
| `1xB300` / `2xB300` / `4xB300` / `8xB300` | No |
| `1xB200` / `2xB200` / `4xB200` / `8xB200` | **Yes** (8xB200) |
| `1xH200` / `2xH200` / `4xH200` / `8xH200` | **Yes** (8xH200) |
| `1xH100` / `2xH100` / `4xH100` / `8xH100` | No |
| `1xL40S` | No |
| `32xCPU` / `64xCPU` | No |

Only the **8xB200** and **8xH200** types can form multi-node SLURM clusters. Everything else
is single-node.

## Approximate GPU pricing (per GPU-hour, prorated to the second)

| GPU | Anchor rate |
|-----|-------------|
| B300 SXM | ~$5–6 / GPU-hr |
| B200 SXM | ~$5 / GPU-hr |
| H200 SXM | ~$3 / GPU-hr |
| H100 SXM | ~$2 / GPU-hr |
| L40S | ~$1.5 / GPU-hr |
| CPU | ~$0.015 / GPU-hr |

Per-node cost scales with GPU count, e.g. an 8-GPU H200 node is roughly 8× the H200 GPU rate,
and a 2-node 8xH200 cluster is roughly 16× — order-of-magnitude only; confirm live.

## Storage pricing anchors

| Backend | Anchor rate | POSIX | Cluster requirement |
|---------|-------------|-------|---------------------|
| Shared NFS | ~$100 / TB / month | Yes | Multi-node (2+ nodes) |
| Object (S3-compatible) | ~$20 / TB / month | No | Any cluster |

Object storage typically has no ingress/egress fees. Storage bills for as long as the volume
exists, independent of whether a cluster is attached — destroy volumes you no longer need.

## Cost-estimate checklist before you provision

1. Look up the **current** per-GPU-hr rate (dashboard/pricing page), not this table.
2. Multiply by GPUs-per-node × node count to get the cluster's hourly burn.
3. Multiply by expected runtime for a total, and add storage $/TB/month if attaching volumes.
4. Present that number to the user and get explicit approval **before** running any
   `tp cluster create` / `tp job push` / `tp storage create`.
5. For build-vs-buy and break-even reasoning (is renting these GPUs even worth it?), hand off
   to the `model-economics` skill first.
