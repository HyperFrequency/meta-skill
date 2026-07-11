# Workflows and troubleshooting

Three end-to-end workflows, then the common failure modes with fixes. Command details are in
`cli-reference.md`; pricing is in `instance-types-pricing.md`.

## Workflow 1 — single-node batch job

Best default for a self-contained training script: you never touch a live box, and billing
stops when the run finishes.

```bash
# 1. Scaffold and edit tp.config.toml
tp job init
#    commands      = ["pip install -r requirements.txt", "python train.py"]
#    instance_type = "1xH100"
#    outputs       = ["checkpoints/", "model.pth"]

# 2. Submit (uploads cwd minus `ignore`, returns a job_id)
tp job push tp.config.toml

# 3. Watch it run
tp job listen <job_id>

# 4. Bring the outputs home
tp job pull <job_id>
```

If the job ends in **Error**, fix the script and re-push — no cleanup needed. There is no
cluster to destroy.

## Workflow 2 — multi-node distributed training (SLURM)

For runs that need more than one node. Provision an 8xH200 or 8xB200 cluster, stage data on
shared NFS, and launch with SLURM from the jumphost.

```bash
# 1. Provision a 4-node cluster and a shared volume, then attach
tp cluster create -i ~/.ssh/id_ed25519.pub -t 8xH200 -n 4
tp storage create -t shared -s 1000 --name dataset
tp cluster attach <cluster_id> <storage_id>

# 2. SSH into the jumphost (public IP; workers are private-only)
tp ssh <jumphost-instance-id>

# 3. Stage data onto shared storage (visible to every node)
cd /mnt/shared-<storage_id>
# rsync / wget / huggingface-cli download your dataset here

# 4. Launch across all nodes with SLURM + torchrun
srun --nodes=4 --ntasks-per-node=8 --gpus-per-node=8 \
  torchrun --nnodes=4 --nproc_per_node=8 \
  --rdzv_backend=c10d --rdzv_endpoint=$MASTER_ADDR:29500 \
  train.py

# 5. Tear everything down — clusters bill until destroyed
tp cluster detach <cluster_id> <storage_id>
tp cluster destroy <cluster_id>
tp storage destroy <storage_id>     # if the dataset is no longer needed
```

For the distributed-training code itself (sharding, parallelism strategy, communication
tuning) see the `distributed-training` and `optimize-for-gpu` skills — this workflow only
provisions the hardware and launches the launcher.

## Workflow 3 — interactive development

When you want a live GPU box to iterate on. Remember it bills the entire time it exists.

```bash
tp cluster create -i ~/.ssh/id_ed25519.pub -t 1xH100 --name dev-box
tp cluster info <cluster_id>          # wait for RUNNING
tp ssh <instance_id>
#   git clone <repo> && pip install -r requirements.txt && python train.py
tp cluster destroy <cluster_id>        # the moment you're done — stops the meter
```

## Troubleshooting

**`TENSORPOOL_KEY` not set**
```bash
[ -n "$TENSORPOOL_KEY" ] && echo "set" || echo "not set"
```
Export a valid key (do not echo the value). Confirm with `tp me`.

**Cluster stuck in `PENDING` / `PROVISIONING`**
Check `tp cluster info <cluster_id>`. This usually means the requested instance type has no
capacity right now — wait, or destroy and recreate with a different type/region.

**Can't SSH into a cluster**
- Wait until status is `RUNNING` (provisioning can take several minutes).
- Confirm the `-i` public key you passed at creation matches your local private key.
- Multi-node: you can only SSH the **jumphost** directly; workers are reachable only from the
  jumphost shell.

**Multi-node workers not accessible**
Workers have private IPs only. SSH the jumphost first, then `ssh <cluster_id>-0` from there.

**Storage won't attach**
- Shared NFS attaches only to multi-node clusters (2+ nodes).
- Object storage attaches to any cluster.
- Confirm the volume is `READY` (`tp storage info <storage_id>`) before attaching.

**Job stuck in `Pending`**
```bash
tp job info <job_id>        # usually an instance-type capacity issue
tp job cancel <job_id>      # cancel and retry a different instance_type
```

**Job ends in `Error` (non-zero exit)**
Your commands failed. Stream the logs, fix, re-push:
```bash
tp job listen <job_id>
# fix train.py / requirements, then:
tp job push tp.config.toml
```
`Failed` (not `Error`) is a TensorPool-side node/GPU fault, not your code — retry.

**Object storage slow on many small files**
Per-request HTTP overhead dominates. Use `boto3` or `rclone` instead of the FUSE mount, and
never place Python venvs or package caches (thousands of tiny files) on an object volume —
put those on local disk or shared NFS.

**Runaway spend**
The classic mistake is a forgotten cluster. List everything and destroy what you're not using:
```bash
tp cluster list
tp cluster destroy <id>
tp storage list
tp storage destroy <id>
```
