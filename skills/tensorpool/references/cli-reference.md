# TensorPool CLI reference

Full command surface for the `tp` CLI, the `tp.config.toml` schema, and the status machines.
Commands are stable; **pricing and instance availability are volatile** — see
`instance-types-pricing.md`.

## SSH keys

Clusters require a public key at creation. Generate one if you don't have it:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519      # produces id_ed25519 (private) + .pub
tp cluster create -i ~/.ssh/id_ed25519.pub -t 1xH100
tp ssh <instance_id>                             # connects using the matching private key
```

## Clusters

### Create

```bash
# Single-node variants
tp cluster create -i ~/.ssh/id_ed25519.pub -t 1xH100
tp cluster create -i ~/.ssh/id_ed25519.pub -t 8xH200
tp cluster create -i ~/.ssh/id_ed25519.pub -t 1xL40S --name my-cluster

# Multi-node (SLURM + InfiniBand preinstalled; only 8xH200 and 8xB200 support -n > 1)
tp cluster create -i ~/.ssh/id_ed25519.pub -t 8xH200 -n 2    # 2 nodes  = 16 GPUs
tp cluster create -i ~/.ssh/id_ed25519.pub -t 8xB200 -n 4    # 4 nodes  = 32 GPUs
```

Flags: `-i` SSH public key (required), `-t` instance type (required), `-n` node count
(multi-node types only), `--name` friendly name.

### Manage

```bash
tp cluster list                                   # your clusters
tp cluster list --org                             # organization-wide
tp cluster info <cluster_id>                       # detailed status
tp cluster edit <cluster_id> --name "new-name"
tp cluster edit <cluster_id> --deletion-protection true
tp cluster destroy <cluster_id>                    # terminate — stops billing
```

### Cluster status machine

```
PENDING → PROVISIONING → CONFIGURING → RUNNING → DESTROYING → DESTROYED
```

If any instance fails to come up, the cluster reports `FAILED`. You cannot `tp ssh` until the
cluster reaches `RUNNING`.

### Multi-node architecture (jumphost + workers)

Multi-node clusters give you:

- **Jumphost** — `{cluster_id}-jumphost`, has a **public IP**, runs the SLURM login/controller.
- **Worker nodes** — `{cluster_id}-0`, `{cluster_id}-1`, … have **private IPs only**.

You reach workers *through* the jumphost:

```bash
tp ssh <jumphost-instance-id>     # SSH into the jumphost (public IP)
# then, from the jumphost shell:
ssh <cluster_id>-0
ssh <cluster_id>-1
```

Submit distributed work with SLURM from the jumphost (`srun` / `sbatch`); see
`workflows-troubleshooting.md` for a full `srun` + `torchrun` example.

## Jobs

Git-style batch interface. You pay only while the job runs — there is no box to remember to
destroy.

### Lifecycle

```bash
tp job init                        # scaffold tp.config.toml in the current dir
tp job push tp.config.toml         # upload cwd (minus `ignore`) and run; prints a job_id
tp job list                        # your jobs
tp job list --org                  # organization-wide
tp job info <job_id>               # details
tp job listen <job_id>             # stream live logs
tp job pull <job_id>               # download declared outputs into cwd
tp job pull <job_id> --force       # overwrite local files on pull
tp job cancel <job_id>             # cancel a running job (prompts)
tp job cancel <job_id> --no-input  # cancel without confirmation
```

### `tp.config.toml` schema

```toml
# Commands run in order on the remote instance, in the uploaded working directory.
commands = [
    "pip install -r requirements.txt",
    "python train.py --epochs 100",
]

# One instance type per job.
instance_type = "1xH100"

# Files/dirs to bring back with `tp job pull`. Paths are relative to the working dir.
outputs = [
    "checkpoints/",
    "model.pth",
    "results.json",
]

# Excluded from upload (keeps pushes fast; avoids shipping venvs/caches).
ignore = [
    ".venv",
    "venv/",
    "__pycache__/",
    ".git",
    "*.pyc",
]
```

### Job status machine

```
Pending → Running → Completed | Error | Failed | Canceled
```

- **Error** — user-level failure: your commands exited non-zero. Read logs with `tp job
  listen`, fix the script, and `tp job push` again.
- **Failed** — system-level failure: a node/GPU fault on TensorPool's side, not your code.
- **Pending** stuck for a long time usually means the requested `instance_type` has no
  capacity; cancel and retry a different type.

### Multiple experiments in parallel

`tp job push` accepts any config path, so keep several configs side by side and push each:

```bash
tp job init            # → tp.config.toml   (rename, e.g. tp.baseline.toml)
tp job init            # → tp.config1.toml  (rename, e.g. tp.experiment.toml)

tp job push tp.baseline.toml
tp job push tp.experiment.toml
```

Each push is an independent job with its own `job_id`, logs, and billing window.

## Storage

Two backends with very different characteristics — pick by access pattern.

### Shared NFS (`-t shared`)

- POSIX-compliant, high aggregate read throughput.
- **Multi-node clusters only** (2+ nodes).
- For datasets and checkpoints read/written across all nodes.

```bash
tp storage create -t shared -s 500 --name training-data   # 500 GB volume
tp cluster attach <cluster_id> <storage_id>               # mount under /mnt/shared-<storage_id>
tp cluster detach <cluster_id> <storage_id>
tp storage destroy <storage_id>
```

### Object storage (`-t object`)

- S3-compatible, cheaper per TB, works on **any** cluster type.
- **Not POSIX.** Mounted via FUSE under `/mnt/object-<storage_id>`, but for performance
  prefer `boto3` or `rclone` directly against the bucket.
- Do **not** create Python virtualenvs on object storage — thousands of tiny files incur
  per-request overhead and will crawl.

```bash
tp storage create -t object --name models
tp cluster attach <cluster_id> <storage_id>               # mount under /mnt/object-<storage_id>
```

### Storage management

```bash
tp storage create -t <shared|object> [-s <GB>] [--name <name>]
tp storage list
tp storage info <storage_id>
tp storage edit <storage_id> --name "new-name"
tp storage edit <storage_id> --deletion-protection true
tp storage destroy <storage_id>
```

Confirm storage status is `READY` before attaching. Shared storage will refuse to attach to a
single-node cluster.

## Account

```bash
tp me     # account identity and key validation
```
