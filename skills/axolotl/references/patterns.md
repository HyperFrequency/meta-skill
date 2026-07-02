# Axolotl Common Patterns

Distilled, context-annotated patterns extracted from the official Axolotl docs.
Each entry states *what it controls* and *when you'd reach for it*. For the full
config reference and API surface see `api.md`; for dataset shapes see
`dataset-formats.md`; for everything else see `other.md`.

## Multi-GPU / scaling

### FSDP2 (Fully Sharded Data Parallel, v2)
Shards model params/grads/optimizer state across GPUs so a model that won't fit
on one GPU can still train. Use when a single GPU OOMs on the model itself.

```yaml
fsdp_version: 2
fsdp_config:
  offload_params: true                         # spill params to CPU when idle (slower, less VRAM)
  state_dict_type: FULL_STATE_DICT             # gather full weights on save
  auto_wrap_policy: TRANSFORMER_BASED_WRAP     # wrap per transformer block
  transformer_layer_cls_to_wrap: LlamaDecoderLayer  # the block class for your arch
  reshard_after_forward: true                  # free shards after fwd to save VRAM
```

### Context parallelism (sequence parallelism)
`context_parallel_size` is the number of GPUs each sequence is split across, so
you can train on contexts longer than one GPU can hold. It must divide the total
GPU count. Reaching for it means: long-context fine-tuning that OOMs on
activations (not on weights — that's FSDP).

```yaml
context_parallel_size: 4   # each example split across 4 GPUs
```

Throughput tradeoff: with 8 GPUs and no sequence parallelism you process 8
batches/step. With `context_parallel_size: 4` you process only 2 batches/step
(each split across 4 GPUs). If `micro_batch_size: 2`, the global batch size drops
from 16 to 4 — compensate with gradient accumulation if you need the old batch.

Can be composed with `tensor_parallel_size` and `dp_shard_size` for FSDP+TP+CP
(e.g. `2 × 2 × 2 = 8` GPUs). See also Axolotl's ALST + `tiled_mlp` for very long
context.

### NCCL bandwidth sanity check
Before blaming Axolotl for slow multi-GPU runs, confirm the interconnect itself
delivers acceptable all-reduce bandwidth. Run the NVIDIA NCCL Tests:

```bash
./build/all_reduce_perf -b 8 -e 128M -f 2 -g 3   # -g = GPU count
```

## Checkpointing

### Compressed checkpoints
`save_compressed: true` writes checkpoints in a compressed format: ~40% less
disk, still loadable by vLLM (fast inference) and llmcompressor (further
quantization). Use it when checkpoint disk usage is the constraint.

```yaml
save_compressed: true
```

## Extending Axolotl

### Custom integrations / plugins
Integrations need not live in Axolotl's `integrations` folder — any importable
package in your Python env works. Reference example:
`https://github.com/axolotl-ai-cloud/diff-transformer`. Plugins are registered in
the `plugins:` list (e.g. `axolotl.integrations.liger.LigerPlugin`).

### Custom dataset prompt strategies
When writing a custom prompt strategy / tokenization callable, handle both
single and batched samples:
- single example: `sample['input_ids']` is a `list[int]`
- batched: `sample['input_ids']` is a `list[list[int]]`

Long-sequence dropping helper:
```python
utils.trainer.drop_long_seq(sample, sequence_len=2048, min_sequence_len=2)
```

## Selected API entry points

Full signatures live in `api.md`; these are the ones you reach for most.

- `core.trainers.base.AxolotlTrainer(*_args, bench_data_collator=None, eval_data_collator=None, dataset_tags=None, **kwargs)`
  — Axolotl's `transformers.Trainer` subclass; the object that actually runs
  training. You rarely instantiate it directly (the CLI does) but subclass/patch
  it for custom training loops.
- `core.trainers.base.AxolotlTrainer.log(logs, start_time=None)` — logging hook;
  override to push metrics to custom backends.
- `prompt_strategies.input_output.RawInputOutputPrompter()` — prompter for the
  raw `input`/`output` dataset format (no chat template applied).
- `cli.cloud.modal_.ModalCloud(config, app=None)` — wrapper to launch a training
  run on Modal.
- `cli.cloud.modal_.run_cmd(cmd, run_folder, volumes=None)` — execute a command
  inside the Modal run environment.
</content>
</invoke>
