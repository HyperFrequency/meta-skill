# Lambda Labs Workflows: Storage, Training, Clusters & Cost

## Persistent storage (filesystems)

Filesystems persist data across instance restarts and must be created in the
same region as the instance and attached **at launch time** (console selection
or `file_system_names` in the launch request). Mount path:

```
/lambda/nfs/<FILESYSTEM_NAME>
```

Layout pattern — keep durable data on the filesystem, scratch on local SSD:

```
/lambda/nfs/storage/        # persists: datasets/ checkpoints/ models/ outputs/
/home/ubuntu/working/       # local SSD, faster but ephemeral
```

## Lambda Stack & verification

Every instance ships Ubuntu 22.04 LTS with the latest NVIDIA driver, CUDA 12.x,
cuDNN, NCCL, PyTorch, TensorFlow, JAX, and JupyterLab pre-installed.

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
nvcc --version
```

Launch JupyterLab from the console "Cloud IDE" column, or manually:

```bash
jupyter lab --ip=0.0.0.0 --port=8888   # then SSH-tunnel 8888 locally
```

## Single-GPU training

```bash
ssh ubuntu@<IP>
git clone https://github.com/user/project && cd project
pip install -r requirements.txt
python train.py --epochs 100 --checkpoint-dir /lambda/nfs/storage/checkpoints
```

## Multi-GPU training (single node, DDP)

```python
# train_ddp.py
import torch, torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

def main():
    dist.init_process_group("nccl")
    device = dist.get_rank() % torch.cuda.device_count()
    model = DDP(MyModel().to(device), device_ids=[device])
    # training loop...

if __name__ == "__main__":
    main()
```

```bash
torchrun --nproc_per_node=8 train_ddp.py
```

Checkpoint to the persistent filesystem so interrupted runs can resume:

```python
import os
checkpoint_dir = "/lambda/nfs/my-storage/checkpoints"
os.makedirs(checkpoint_dir, exist_ok=True)
torch.save({
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'loss': loss,
}, f"{checkpoint_dir}/checkpoint_{epoch}.pt")
```

## 1-Click Clusters (multi-node)

High-performance Slurm clusters with 16-512 NVIDIA H100 or B200 GPUs, NVIDIA
Quantum-2 400 Gb/s InfiniBand, GPUDirect RDMA at 3200 Gb/s, OFED drivers, NCCL,
Open MPI, and PyTorch DDP/FSDP pre-installed. Each compute node has 24 TB
ephemeral NVMe; use Lambda filesystems for persistent data.

```bash
srun --nodes=4 --ntasks-per-node=8 --gpus-per-node=8 \
  torchrun --nnodes=4 --nproc_per_node=8 \
  --rdzv_backend=c10d --rdzv_endpoint=$MASTER_ADDR:29500 \
  train.py
```

See `advanced-usage.md` for the full multi-node DDP launcher and API automation.

## Networking

- Inter-instance (same region): up to 200 Gbps.
- Internet outbound: 20 Gbps max.
- Find private IP: `ip addr show | grep 'inet '`.

## End-to-end workflows

### Fine-tuning an LLM (8x H100 + filesystem)

```bash
ssh ubuntu@<IP>
pip install transformers accelerate peft
python -c "from transformers import AutoModelForCausalLM; \
AutoModelForCausalLM.from_pretrained('meta-llama/Llama-2-7b-hf') \
.save_pretrained('/lambda/nfs/storage/models/llama-2-7b')"
accelerate launch --num_processes 8 train.py \
  --model_path /lambda/nfs/storage/models/llama-2-7b \
  --output_dir /lambda/nfs/storage/outputs \
  --checkpoint_dir /lambda/nfs/storage/checkpoints
```

### Batch inference (cost-effective A10)

```bash
python inference.py \
  --model /lambda/nfs/storage/models/fine-tuned \
  --input /lambda/nfs/storage/data/inputs.jsonl \
  --output /lambda/nfs/storage/data/outputs.jsonl
```

## Cost optimization

| Task | Recommended GPU |
|------|-----------------|
| LLM fine-tuning (7B) | A100 40GB |
| LLM fine-tuning (70B) | 8x H100 |
| Inference | A10, A6000 |
| Development | V100, A10 |
| Maximum performance | B200 |

- **Use filesystems** to avoid re-downloading data.
- **Checkpoint frequently** to resume interrupted training.
- **Right-size** GPUs; don't over-provision.
- **Terminate idle instances** — there is no auto-stop; billing is pay-per-minute.
- Monitor real-time GPU utilization in the dashboard or via the API.
