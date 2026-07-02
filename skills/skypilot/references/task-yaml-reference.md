# SkyPilot Task YAML & Core Reference

Mid-level reference for the SkyPilot task YAML schema, GPUs, distributed
training, storage, managed jobs, Sky Serve, and common workflows. For
production patterns see `advanced-usage.md`; for failures see `troubleshooting.md`.

## Task YAML structure

```yaml
name: my-task              # Optional task name

resources:
  cloud: aws               # Optional: auto-select cheapest if omitted
  region: us-west-2        # Optional: auto-select if omitted
  accelerators: A100:4     # GPU type and count
  cpus: 8+                 # Minimum CPUs
  memory: 32+              # Minimum memory (GB)
  use_spot: true           # Use spot instances
  disk_size: 256           # Disk size (GB)

num_nodes: 2               # Nodes for distributed training
workdir: .                 # Synced to ~/sky_workdir (NOT persisted)

setup: |                   # Runs once on provisioning
  pip install -r requirements.txt

run: |                     # Runs the task
  python train.py
```

## GPU configuration

```yaml
# NVIDIA: T4:1, L4:1, A10G:1, L40S:1, A100:4, A100-80GB:8, H100:8
# Cloud-specific: V100:4 (AWS/GCP), TPU-v4-8 (GCP TPUs)
accelerators: A100:8
```

GPU fallback across types and clouds:

```yaml
resources:
  accelerators: {H100: 8, A100-80GB: 8, A100: 8}
  any_of:
    - cloud: gcp
    - cloud: aws
    - cloud: azure
```

## Spot instances & recovery

Spot saves ~3-6x. For auto-recovery on preemption, launch as a *managed job*
(`sky jobs launch`) and configure `job_recovery` (NOT the old `spot_recovery`):

```yaml
resources:
  accelerators: A100:8
  use_spot: true
  job_recovery:
    strategy: EAGER_NEXT_REGION   # immediately try a new region on preemption
    max_restarts_on_errors: 3     # retries on non-preemption (user code) errors
    recover_on_exit_codes: [1, 137]
# Shorthand for same-region-first retry:  job_recovery: FAILOVER
```

```bash
sky jobs launch -n my-job train.yaml   # managed job with auto-recovery
sky jobs queue                         # list managed jobs
sky jobs logs <job_id>                 # stream logs
sky jobs cancel my-job                 # cancel
```

Always checkpoint to persistent storage so your code can resume after recovery.

## Autostop

```yaml
resources:
  accelerators: A100:4
  autostop:
    idle_minutes: 30
    down: true        # terminate instead of stop
```

```bash
sky autostop mycluster -i 30 --down
```

## Distributed (multi-node) training

```yaml
resources:
  accelerators: A100:8
num_nodes: 4          # 4 nodes x 8 GPUs = 32 GPUs total
run: |
  torchrun \
    --nnodes=$SKYPILOT_NUM_NODES \
    --nproc_per_node=$SKYPILOT_NUM_GPUS_PER_NODE \
    --node_rank=$SKYPILOT_NODE_RANK \
    --master_addr=$(echo "$SKYPILOT_NODE_IPS" | head -n1) \
    --master_port=12355 \
    train.py
```

| Variable | Description |
|----------|-------------|
| `SKYPILOT_NODE_RANK` | Node index (0 to num_nodes-1) |
| `SKYPILOT_NODE_IPS` | Newline-separated IP addresses |
| `SKYPILOT_NUM_NODES` | Total number of nodes |
| `SKYPILOT_NUM_GPUS_PER_NODE` | GPUs per node |

Head-node-only work: `if [ "${SKYPILOT_NODE_RANK}" == "0" ]; then ... fi`

## File mounts & storage

```yaml
workdir: ./my-project          # synced to ~/sky_workdir

file_mounts:
  /data/config.yaml: ./config.yaml      # local file sync
  /datasets:
    source: s3://my-bucket/datasets
    mode: MOUNT                          # stream from cloud
  /outputs:
    name: my-outputs
    store: s3
    mode: MOUNT_CACHED                   # cache with async upload
```

| Mode | Description | Best for |
|------|-------------|----------|
| `MOUNT` | Stream from cloud | Large datasets, read-heavy |
| `COPY` | Pre-fetch to disk | Small files, random access |
| `MOUNT_CACHED` | Cache + async upload | Checkpoints, outputs |

Note: data in `~/sky_workdir` is NOT persisted — use `file_mounts` for anything
that must survive cluster teardown or preemption.

## Sky Serve (model serving)

```yaml
service:
  readiness_probe: /health
  replica_policy:
    min_replicas: 1
    max_replicas: 10
    target_qps_per_replica: 2.0
    upscale_delay_seconds: 60
    downscale_delay_seconds: 300
  load_balancing_policy: round_robin

resources:
  accelerators: A100:1

run: |
  python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf --port 8000
```

```bash
sky serve up -n my-service service.yaml
sky serve status my-service           # status + endpoint
```

## Secrets & environment variables

```yaml
envs:
  WANDB_API_KEY: $WANDB_API_KEY        # inherited from local env
secrets:
  - HF_TOKEN                           # hidden in logs
```

## Common workflows

Fine-tuning with checkpoints on spot:

```yaml
name: llm-finetune
file_mounts:
  /checkpoints: {name: finetune-checkpoints, store: s3, mode: MOUNT_CACHED}
resources: {accelerators: A100:8, use_spot: true}
setup: pip install transformers accelerate
run: python train.py --checkpoint-dir /checkpoints --resume
```

Hyperparameter sweep (launch many managed jobs):

```bash
for i in {1..10}; do
  sky jobs launch sweep.yaml \
    --env RUN_ID=$i \
    --env LEARNING_RATE=$(python -c "import random; print(10**random.uniform(-5,-3))")
done
```

## Cost optimization

Omit `cloud`/`region` to let the optimizer pick the cheapest option. Inspect
its decision with `sky launch task.yaml --dryrun`. Constrain candidates with
`any_of` (see GPU fallback above).
