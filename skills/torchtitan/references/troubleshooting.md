# TorchTitan Troubleshooting

## Out of memory on large models

Enable full activation checkpointing and reduce batch size:
```toml
[activation_checkpoint]
mode = "full"  # instead of "selective"

[training]
local_batch_size = 1
```
Or use gradient accumulation:
```toml
[training]
local_batch_size = 1
global_batch_size = 32  # accumulates gradients
```

## TP causes high memory with async collectives

```bash
export TORCH_NCCL_AVOID_RECORD_STREAMS=1
```

## Float8 training not faster

Float8 only benefits large GEMMs. Filter small layers:
```toml
[quantize.linear.float8]
filter_fqns = ["attention.wk", "attention.wv", "output", "auto_filter_small_kn"]
```

## Checkpoint loading fails after a parallelism change

Use DCP's resharding capability:
```bash
python -m torch.distributed.checkpoint.format_utils \
  dcp_to_torch checkpoint/step-1000 checkpoint.pt
```
See [checkpoint.md](checkpoint.md) for HuggingFace conversion and async checkpointing.

## Pipeline parallelism initialization

Create a seed checkpoint first (Workflow 4, Step 1 in [workflows.md](workflows.md)).
