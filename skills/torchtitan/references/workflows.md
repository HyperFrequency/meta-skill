# TorchTitan Workflows

Step-by-step training workflows. Configs are TOML; launch via `./run_train.sh`
(reads `CONFIG_FILE`) or `torchrun -m torchtitan.train --job.config_file ...`.

## Workflow 1: Pretrain Llama 3.1 8B on a single node (8 GPUs)

```
- [ ] Step 1: Download tokenizer
- [ ] Step 2: Configure training (TOML)
- [ ] Step 3: Launch training
- [ ] Step 4: Monitor and checkpoint
```

**Step 1 — Download tokenizer** (HF token from https://huggingface.co/settings/tokens):
```bash
python scripts/download_hf_assets.py \
  --repo_id meta-llama/Llama-3.1-8B \
  --assets tokenizer \
  --hf_token=YOUR_HF_TOKEN
```

**Step 2 — Configure training** (`llama3_8b_custom.toml`):
```toml
[job]
dump_folder = "./outputs"
description = "Llama 3.1 8B training"

[model]
name = "llama3"
flavor = "8B"
hf_assets_path = "./assets/hf/Llama-3.1-8B"

[optimizer]
name = "AdamW"
lr = 3e-4

[lr_scheduler]
warmup_steps = 200

[training]
local_batch_size = 2
seq_len = 8192
max_norm = 1.0
steps = 1000
dataset = "c4"

[parallelism]
data_parallel_shard_degree = -1  # Use all GPUs for FSDP

[activation_checkpoint]
mode = "selective"
selective_ac_option = "op"

[checkpoint]
enable = true
folder = "checkpoint"
interval = 500
```

**Step 3 — Launch** (8 GPUs single node):
```bash
CONFIG_FILE="./llama3_8b_custom.toml" ./run_train.sh
# or explicitly:
torchrun --nproc_per_node=8 -m torchtitan.train \
  --job.config_file ./llama3_8b_custom.toml
```

**Step 4 — Monitor** (TensorBoard logs in `./outputs/tb/`):
```bash
tensorboard --logdir ./outputs/tb
```

## Workflow 2: Multi-node training with SLURM (70B on 256 GPUs)

**Step 1 — Configure parallelism for scale:**
```toml
[parallelism]
data_parallel_shard_degree = 32  # FSDP across 32 ranks
tensor_parallel_degree = 8        # TP within node
pipeline_parallel_degree = 1      # No PP for 70B
context_parallel_degree = 1       # Increase for long sequences
```

**Step 2 — SLURM script** (`multinode_trainer.slurm`):
```bash
#!/bin/bash
#SBATCH --job-name=llama70b
#SBATCH --nodes=32
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-node=8

srun torchrun \
  --nnodes=32 --nproc_per_node=8 \
  --rdzv_backend=c10d \
  --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
  -m torchtitan.train \
  --job.config_file ./llama3_70b.toml
```

**Step 3 — Submit:** `sbatch multinode_trainer.slurm`

**Step 4 — Resume:** training auto-resumes if a checkpoint exists in the
configured folder.

## Workflow 3: Float8 training for H100s (30-50% speedup)

**Step 1 — Install torchao:**
```bash
USE_CPP=0 pip install git+https://github.com/pytorch/ao.git
```

**Step 2 — Configure Float8** (add to TOML):
```toml
[model]
converters = ["quantize.linear.float8"]

[quantize.linear.float8]
enable_fsdp_float8_all_gather = true
precompute_float8_dynamic_scale_for_fsdp = true
filter_fqns = ["output"]  # Exclude output layer

[compile]
enable = true
components = ["model", "loss"]
```

**Step 3 — Launch with compile:**
```bash
CONFIG_FILE="./llama3_8b.toml" ./run_train.sh \
  --model.converters="quantize.linear.float8" \
  --quantize.linear.float8.enable_fsdp_float8_all_gather \
  --compile.enable
```

See [float8.md](float8.md) for tensorwise vs rowwise scaling recipes.

## Workflow 4: 4D parallelism for 405B models (512 GPUs)

**Step 1 — Create seed checkpoint** (required for consistent init across PP stages):
```bash
NGPU=1 CONFIG_FILE=./llama3_405b.toml ./run_train.sh \
  --checkpoint.enable \
  --checkpoint.create_seed_checkpoint \
  --parallelism.data_parallel_shard_degree 1 \
  --parallelism.tensor_parallel_degree 1 \
  --parallelism.pipeline_parallel_degree 1
```

**Step 2 — Configure 4D parallelism:**
```toml
[parallelism]
data_parallel_shard_degree = 8   # FSDP
tensor_parallel_degree = 8       # TP within node
pipeline_parallel_degree = 8     # PP across nodes
context_parallel_degree = 1      # CP for long sequences

[training]
local_batch_size = 32
seq_len = 8192
```

**Step 3 — Launch on 512 GPUs** (64 nodes x 8):
```bash
srun torchrun --nnodes=64 --nproc_per_node=8 \
  -m torchtitan.train \
  --job.config_file ./llama3_405b.toml
```
