# DeepSpeed `ds_config` Patterns (verified)

Curated, verified configuration snippets. The `ds_config` (JSON file or Python dict) is the single
source of truth passed to `deepspeed.initialize(config=...)`. Sources: official DeepSpeed docs
(`docs/_pages/config-json.md`, `docs/_tutorials/zero.md`, `docs/code-docs/source/training.md`).

## Batch-size fields (always required, interdependent)

`train_batch_size == train_micro_batch_size_per_gpu * gradient_accumulation_steps * world_size`.
Provide any two and DeepSpeed derives the third.

```json
{
  "train_micro_batch_size_per_gpu": 4,
  "gradient_accumulation_steps": 8,
  "gradient_clipping": 1.0
}
```

## ZeRO stage 1 / 2 (optimizer + gradient sharding)

```json
{
  "bf16": { "enabled": true },
  "zero_optimization": {
    "stage": 2,
    "allgather_partitions": true,
    "allgather_bucket_size": 5e8,
    "overlap_comm": true,
    "reduce_scatter": true,
    "reduce_bucket_size": 5e8,
    "contiguous_gradients": true
  }
}
```

## ZeRO stage 2 with CPU optimizer offload

```json
{
  "train_batch_size": 8,
  "bf16": { "enabled": true },
  "zero_optimization": {
    "stage": 2,
    "offload_optimizer": { "device": "cpu", "pin_memory": true }
  },
  "optimizer": {
    "type": "AdamW",
    "params": { "lr": 2e-5, "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.01 }
  },
  "gradient_accumulation_steps": 1,
  "gradient_clipping": 1.0,
  "zero_allow_untested_optimizer": true
}
```

## ZeRO stage 3 (parameter sharding)

```json
{
  "zero_optimization": {
    "stage": 3,
    "contiguous_gradients": true,
    "stage3_max_live_parameters": 1e9,
    "stage3_max_reuse_distance": 1e9,
    "stage3_prefetch_bucket_size": 5e8,
    "stage3_param_persistence_threshold": 1e6,
    "reduce_bucket_size": 1e7,
    "sub_group_size": 1e9,
    "stage3_gather_16bit_weights_on_model_save": true
  }
}
```

## ZeRO-Infinity (stage 3 + CPU/NVMe offload)

Move optimizer and/or parameter state off the GPU. Use `"device": "nvme"` with an `nvme_path` for
models larger than aggregate CPU RAM (requires the `async_io` op — verify with `ds_report`).

```json
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": { "device": "cpu", "pin_memory": true },
    "offload_param":     { "device": "cpu", "pin_memory": true },
    "stage3_max_live_parameters": 1e9,
    "stage3_prefetch_bucket_size": 1e7,
    "stage3_param_persistence_threshold": 1e5,
    "reduce_bucket_size": 1e7,
    "sub_group_size": 1e9
  }
}
```

NVMe variant: replace a `device` with `"nvme"` and add
`"nvme_path": "/local_nvme"` (plus optional `"buffer_count"`, `"buffer_size"`).

### Full `zero_optimization` field reference

```json
{
  "zero_optimization": {
    "stage": "[0|1|2|3]",
    "allgather_partitions": "[true|false]",
    "allgather_bucket_size": 5e8,
    "overlap_comm": false,
    "reduce_scatter": "[true|false]",
    "reduce_bucket_size": 5e8,
    "contiguous_gradients": "[true|false]",
    "offload_param": { "device": "[cpu|nvme|none]" },
    "offload_optimizer": { "device": "[cpu|nvme|none]" },
    "stage3_max_live_parameters": 1e9,
    "stage3_max_reuse_distance": 1e9,
    "stage3_prefetch_bucket_size": 5e8,
    "stage3_param_persistence_threshold": 1e6,
    "stage3_gather_16bit_weights_on_model_save": "[true|false]",
    "sub_group_size": 1e12,
    "elastic_checkpoint": "[true|false]",
    "ignore_unused_parameters": "[true|false]",
    "round_robin_gradients": "[true|false]",
    "zero_hpz_partition_size": 1,
    "zero_quantized_weights": "[true|false]",
    "zero_quantized_gradients": "[true|false]"
  }
}
```

`zero_quantized_weights` + `zero_hpz_partition_size` enable **ZeRO++** (hierarchical partitioning +
communication quantization).

## Mixed precision

FP16 (with dynamic loss scaling):

```json
{ "fp16": { "enabled": true, "loss_scale": 0, "initial_scale_power": 16, "loss_scale_window": 1000 } }
```

BF16 (preferred on Ampere+/H100; no loss scaling needed):

```json
{ "bf16": { "enabled": true } }
```

`torch.autocast`-based AMP (downcast only listed modules):

```json
{
  "torch_autocast": {
    "enabled": true,
    "dtype": "bfloat16",
    "lower_precision_safe_modules": ["torch.nn.Linear", "torch.nn.Conv2d"]
  }
}
```

## Optimizer + scheduler (managed by DeepSpeed)

```json
{
  "optimizer": {
    "type": "AdamW",
    "params": { "lr": 1e-4, "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": 0.01 }
  },
  "scheduler": {
    "type": "WarmupLR",
    "params": { "warmup_min_lr": 0, "warmup_max_lr": 1e-4, "warmup_num_steps": 1000 }
  }
}
```

`FusedAdam`/`OneBitAdam`/`ZeroOneAdam` are also valid `type` values. For an external optimizer
object, pass it to `deepspeed.initialize(optimizer=...)` and set `zero_allow_untested_optimizer`.

## Tensor parallelism (AutoTP, in-config)

```python
import deepspeed
ds_config = {
    "train_micro_batch_size_per_gpu": 1,
    "zero_optimization": {"stage": 2},
    "tensor_parallel": {"autotp_size": 4},
}
engine, optimizer, _, _ = deepspeed.initialize(
    model=model, optimizer=optimizer, config=ds_config, mpu=mpu  # mpu optional
)
```

## Pipeline parallelism (engine API)

Wrap layers in a `PipelineModule`; DeepSpeed handles micro-batch scheduling.

```python
from deepspeed.pipe import PipelineModule
net = PipelineModule(layers=layer_list, num_stages=2)
engine, _, _, _ = deepspeed.initialize(model=net, config=ds_config, model_parameters=net.parameters())
loss = engine.train_batch()   # runs forward+backward+step over the micro-batch pipeline
```

## Activation (gradient) checkpointing

```json
{
  "activation_checkpointing": {
    "partition_activations": false,
    "cpu_checkpointing": false,
    "contiguous_memory_optimization": false,
    "number_checkpoints": null,
    "synchronize_checkpoint_boundary": false,
    "profile": false
  }
}
```

## Checkpointing API

```python
engine.save_checkpoint(save_dir, tag=step)            # sharded under ZeRO
_, client_state = engine.load_checkpoint(save_dir, tag=step)
```

For a single consolidated fp32 weight file from a ZeRO-3 checkpoint, either set
`stage3_gather_16bit_weights_on_model_save: true` before saving, or run the bundled
`python zero_to_fp32.py <checkpoint_dir> <output.pt>`.
