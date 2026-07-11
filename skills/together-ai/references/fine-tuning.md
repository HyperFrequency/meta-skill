# Fine-tuning

Together runs LoRA and full fine-tuning as managed jobs. You upload JSONL,
create a job, poll it, then either serve the resulting model serverless or
download the weights/adapter.

> The `together` SDK's `fine_tuning` method names and parameter defaults have
> changed across releases. Treat the calls below as the current shape and
> confirm signatures against your installed version (`pip show together`) and
> the live reference: https://docs.together.ai/reference. The CLI (below) is the
> most stable interface and is a good fallback.

## Data format

Training data is JSONL, one chat-style example per line. `system` is optional;
the model learns to produce the `assistant` turns.

```jsonl
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "What is the capital of France?"}, {"role": "assistant", "content": "The capital of France is Paris."}]}
{"messages": [{"role": "user", "content": "Explain photosynthesis."}, {"role": "assistant", "content": "Photosynthesis is how plants convert sunlight, water, and CO2 into glucose and oxygen."}]}
```

Validate before uploading: every line must parse as JSON and contain a
`messages` array. A single malformed line fails the whole job.

## Upload training data

```python
from together import Together

client = Together()

uploaded = client.files.upload(file="training_data.jsonl")
print(f"File ID: {uploaded.id}")
```

## Create a fine-tuning job

```python
from together import Together

client = Together()

job = client.fine_tuning.create(
    training_file="file-abc123",
    model="meta-llama/Meta-Llama-3.1-8B-Instruct-Reference",
    n_epochs=3,
    learning_rate=1e-5,
    batch_size=4,
    lora=True,          # False for full fine-tuning where supported
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    suffix="my-custom-model",
)

print(f"Job ID: {job.id}  Status: {job.status}")
```

Start with LoRA (`lora=True`): cheaper, faster, and available on more models
than full fine-tuning. Move to full only when a LoRA adapter measurably
underfits your task.

## Monitor a job

```python
from together import Together

client = Together()

job = client.fine_tuning.retrieve(id="ft-abc123")
print(job.status)

for j in client.fine_tuning.list():
    print(j.id, j.status)

for event in client.fine_tuning.list_events(id="ft-abc123"):
    print(event)          # training logs / loss events

client.fine_tuning.cancel(id="ft-abc123")
```

## CLI (most stable path)

```bash
pip install --upgrade together

together files upload training_data.jsonl

together fine-tuning create \
    --training-file file-abc123 \
    -m meta-llama/Meta-Llama-3.1-8B-Instruct-Reference

together fine-tuning status ft-abc123
together fine-tuning list-events ft-abc123
together fine-tuning list-checkpoints ft-abc123
together fine-tuning download --ft-id ft-abc123
together fine-tuning cancel ft-abc123
```

## Using the fine-tuned model

Once the job completes, the model ID (base model + your `suffix`) is available
for `chat.completions.create` like any other Together model. For LoRA jobs you
can also download the adapter with `together fine-tuning download` and serve it
yourself elsewhere.

## Supported models (selection)

Availability changes; confirm at https://docs.together.ai/docs/fine-tuning-models.

| Model | LoRA | Full |
|-------|------|------|
| `meta-llama/Meta-Llama-3.1-8B-Instruct-Reference` | Yes | Yes |
| `meta-llama/Llama-3.3-70B-Instruct-Reference` | Yes | Yes |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | Yes | No |
| `deepseek-ai/DeepSeek-V3` | Yes | No |
| `deepseek-ai/DeepSeek-R1` | Yes | No |
| `Qwen/Qwen3-8B` | Yes | Yes |
| `Qwen/Qwen3-32B` | Yes | Yes |
| `Qwen/Qwen3-235B-A22B` | Yes | No |
| `google/gemma-3-27b-it` | Yes | Yes |
| `google/gemma-3-4b-it` | Yes | Yes |

## When to fine-tune elsewhere

If you want to own the training loop, iterate offline, or fine-tune models
Together does not host, use a local framework instead: `unsloth` (fast single-GPU
LoRA/QLoRA), `peft` (the adapter primitives), `axolotl` or `llama-factory`
(config-driven multi-recipe training).
