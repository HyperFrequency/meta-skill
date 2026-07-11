# API Reference

The low-level `tinker` SDK. Three clients plus a handful of value types. Every network call returns
a future — call `.result()` (sync) or `await` the `*_async` variant.

## Clients

### ServiceClient

Entry point. Creates the other clients.

```python
import tinker
service_client = tinker.ServiceClient()

for m in service_client.get_server_capabilities().supported_models:
    print(m.model_name)
```

| Method | Purpose |
|--------|---------|
| `get_server_capabilities()` | List supported models |
| `create_lora_training_client(base_model, rank=32, seed=None, train_mlp=True, train_attn=True, train_unembed=True)` | New LoRA training client |
| `create_training_client_from_state(path)` | Resume from checkpoint (weights only) |
| `create_training_client_from_state_with_optimizer(path)` | Resume (weights + optimizer) |
| `create_sampling_client(model_path=None, base_model=None)` | Inference client (from a saved path or a base model) |
| `create_rest_client()` | REST client |

### TrainingClient

| Method | Purpose |
|--------|---------|
| `forward(data, loss_fn, loss_fn_config=None)` | Forward pass, no gradients |
| `forward_backward(data, loss_fn, loss_fn_config=None)` | Compute gradients |
| `forward_backward_custom(data, loss_fn)` | Python loss callback (~1.5× FLOPs, up to 3× wall time) |
| `optim_step(adam_params)` | Apply the accumulated gradients |
| `save_state(name)` | Save weights + optimizer state (resumable) |
| `load_state(path)` / `load_state_with_optimizer(path)` | Restore |
| `save_weights_for_sampler(name)` | Save lightweight inference weights |
| `save_weights_and_get_sampling_client(name)` | Save + return a `SamplingClient` in one call |
| `get_info()` / `get_tokenizer()` | Model info / tokenizer |

A step is always **`forward_backward` then `optim_step`**; submit both futures before blocking so
they overlap.

### SamplingClient

| Method | Purpose |
|--------|---------|
| `sample(prompt, num_samples, sampling_params, include_prompt_logprobs=False, topk_prompt_logprobs=None)` | Generate completions |
| `compute_logprobs(prompt)` | Prompt logprobs |

## Value Types (`tinker.types`)

### Datum
```python
types.Datum(
    model_input=ModelInput,
    loss_fn_inputs={"target_tokens": ..., "weights": ...},  # keys depend on loss_fn
)
```

### ModelInput
```python
types.ModelInput.from_ints(tokens=[1, 2, 3])                    # from a token list
types.ModelInput(chunks=[EncodedTextChunk(...), ImageChunk(...)])  # multimodal
model_input.to_ints()    # -> token list
model_input.length()     # -> total context length
```

### AdamParams
```python
types.AdamParams(learning_rate=1e-4, beta1=0.9, beta2=0.95, eps=1e-8,
                 weight_decay=0.0, grad_clip_norm=0.0)  # grad_clip_norm 0 = off
```

### SamplingParams
```python
types.SamplingParams(max_tokens=100, temperature=0.7, top_p=0.9,
                     top_k=-1, stop=["<|endoftext|>"], seed=42)  # top_k -1 = no limit
```

### TensorData
```python
types.TensorData.from_numpy(np.array([...]))
types.TensorData.from_torch(torch.tensor([...]))
td.to_numpy(); td.to_torch()
```

### EncodedTextChunk / ImageChunk / LoraConfig
```python
types.EncodedTextChunk(tokens=[1, 2, 3])
types.ImageChunk(data=image_bytes, format="png", expected_tokens=None)   # "png" or "jpeg"
types.LoraConfig(rank=32, seed=42, train_unembed=False, train_mlp=True, train_attn=True)
```

## Response Types

```python
fb = fwdbwd_future.result()
fb.loss_fn_outputs   # list of dicts, each with "logprobs"
fb.metrics           # training metrics

s = sample_future.result()
s.sequences              # list[SampledSequence]
s.prompt_logprobs        # if include_prompt_logprobs=True
s.topk_prompt_logprobs   # if topk_prompt_logprobs set

seq = s.sequences[0]
seq.tokens        # generated token ids
seq.logprobs      # per-token logprobs
seq.stop_reason   # why generation stopped

save = training_client.save_state(name).result()
save.path         # "tinker://<model_id>/<name>"
```

## Checkpoints

```python
checkpoint.checkpoint_id
checkpoint.checkpoint_type   # "training" | "sampler"
checkpoint.time
checkpoint.tinker_path
checkpoint.size_bytes
checkpoint.public

parsed = ParsedCheckpointTinkerPath.from_tinker_path("tinker://...")
parsed.training_run_id; parsed.checkpoint_type; parsed.checkpoint_id
```

## Preparing Data Manually

Shift by one: input is `tokens[:-1]`, targets are `tokens[1:]`, weights are `0.0` on prompt tokens
and `1.0` on completion tokens.

```python
import numpy as np
from tinker import types

def process_example(example, tokenizer) -> types.Datum:
    prompt_tokens     = tokenizer.encode(f"English: {example['input']}\nPig Latin:", add_special_tokens=True)
    completion_tokens = tokenizer.encode(f" {example['output']}\n\n", add_special_tokens=False)
    tokens  = prompt_tokens + completion_tokens
    weights = np.array([0] * len(prompt_tokens) + [1] * len(completion_tokens), dtype=np.float32)
    return types.Datum(
        model_input=types.ModelInput.from_ints(tokens=tokens[:-1]),
        loss_fn_inputs=dict(weights=weights[1:], target_tokens=np.array(tokens[1:], dtype=np.int64)),
    )
```

## Sampling & Logprobs

```python
prompt = types.ModelInput.from_ints(tokens=tokenizer.encode("English: coffee break\nPig Latin:", add_special_tokens=True))
result = sampling_client.sample(
    prompt=prompt, num_samples=8,
    sampling_params=types.SamplingParams(max_tokens=20, temperature=0.0, stop=["\n"]),
).result()
for i, seq in enumerate(result.sequences):
    print(i, repr(tokenizer.decode(seq.tokens)))

# prompt logprobs (and top-k)
r = sampling_client.sample(
    prompt=prompt, num_samples=1,
    sampling_params=types.SamplingParams(max_tokens=1),
    include_prompt_logprobs=True, topk_prompt_logprobs=5,
).result()
r.prompt_logprobs        # [None, -9.5, -1.6, ...]
r.topk_prompt_logprobs   # [None, [(token_id, logprob), ...], ...]
```

## Vision Inputs (low level)

```python
model_input = tinker.ModelInput(chunks=[
    types.EncodedTextChunk(tokens=tokenizer.encode("<|im_start|>user\n<|vision_start|>")),
    types.ImageChunk(data=image_bytes, format="png"),
    types.EncodedTextChunk(tokens=tokenizer.encode("<|vision_end|>What is this?<|im_end|>\n<|im_start|>assistant\n")),
])
```

Prefer a vision **renderer** over hand-built chunks — see [Rendering](rendering.md).

## Sync vs Async

Every method has an `_async` twin. Async uses a double await (await the call, then await the future):

```python
# sync
result = client.forward_backward(data, loss_fn).result()

# async — submit both before awaiting so they overlap on one clock cycle
fb  = await client.forward_backward_async(batch, loss_fn)
opt = await client.optim_step_async(adam_params)
fb_result  = await fb
opt_result = await opt
```
