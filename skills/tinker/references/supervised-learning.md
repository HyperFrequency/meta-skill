# Supervised Learning

## Fastest start

```bash
python -m tinker_cookbook.recipes.sl_basic
```

## Blueprint pattern (recommended)

`chz.Blueprint` builds a validated `train.Config`; `make_from_argv` lets you override any field from
the CLI.

```python
import chz, sys, asyncio
from tinker_cookbook.supervised import train
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
from tinker_cookbook.supervised.data import FromConversationFileBuilder
from tinker_cookbook.renderers import TrainOnWhat
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.hyperparam_utils import get_lr

def build() -> chz.Blueprint[train.Config]:
    model_name = "meta-llama/Llama-3.1-8B"
    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=model_name,
        renderer_name=get_recommended_renderer_name(model_name),
        max_length=2048, batch_size=128,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    builder = FromConversationFileBuilder(common_config=common, file_path="data.jsonl")
    return chz.Blueprint(train.Config).apply({
        "log_path": "/tmp/training", "model_name": model_name, "dataset_builder": builder,
        "learning_rate": get_lr(model_name), "lr_schedule": "linear",
        "num_epochs": 3, "lora_rank": 32,
    })

if __name__ == "__main__":
    bp = build(); bp.make_from_argv(sys.argv[1:])
    asyncio.run(train.main(bp.make()))
```

## Data format

JSONL, one conversation per line:

```json
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

## Dataset builders

### From a HuggingFace dataset

```python
from tinker_cookbook.supervised.types import ChatDatasetBuilder
from tinker_cookbook.supervised.data import SupervisedDatasetFromHFDataset, conversation_to_datum
import datasets

@chz.chz
class MyDatasetBuilder(ChatDatasetBuilder):
    common_config: ChatDatasetBuilderCommonConfig

    def __call__(self):
        hf = datasets.load_dataset("HuggingFaceH4/no_robots", split="train")
        split = hf.train_test_split(test_size=0.1, seed=42)

        def map_fn(row):
            messages = [{"role": "user", "content": row["prompt"]},
                        {"role": "assistant", "content": row["completion"]}]
            return conversation_to_datum(messages=messages, renderer=self.renderer,
                                         max_length=self.common_config.max_length,
                                         train_on_what=self.common_config.train_on_what)

        make = lambda part: SupervisedDatasetFromHFDataset(
            hf_dataset=split[part], batch_size=self.common_config.batch_size, map_fn=map_fn)
        return make("train"), make("test")
```

### Streaming (>1M examples)

Use `StreamingSupervisedDatasetFromHFDataset` with `streaming=True` on the HF load and an explicit
`length`. Prevents OOM on dataset load.

```python
from tinker_cookbook.supervised.data import StreamingSupervisedDatasetFromHFDataset

ds = datasets.load_dataset("open-thoughts/OpenThoughts3-1.2M", split="train", streaming=True)
train_dataset = StreamingSupervisedDatasetFromHFDataset(
    hf_dataset=ds, batch_size=self.common_config.batch_size,
    length=self.max_prompts,   # required for streaming
    map_fn=map_fn, buffer_size=10000,
)
return train_dataset, train_dataset.take(1000)
```

### From a JSONL file

```python
from tinker_cookbook.supervised.data import FromConversationFileBuilder
dataset_builder = FromConversationFileBuilder(common_config=common, file_path="/path/data.jsonl")
```

## TrainOnWhat

```python
from tinker_cookbook.renderers import TrainOnWhat
TrainOnWhat.ALL_ASSISTANT_MESSAGES  # standard SFT / multi-turn
TrainOnWhat.LAST_ASSISTANT_MESSAGE  # classification, CoT where only the final answer matters
```

`build_supervised_example` **defaults to `LAST_ASSISTANT_MESSAGE`** — always set this explicitly or
you will silently skip most of your labels.

## Custom SupervisedDataset

`renderer.build_supervised_example(messages, train_on_what=...)` returns `(model_input, weights)`.
Build `Datum`s with the one-position shift (input `tokens[:-1]`, target `tokens[1:]`, weight
`weights[1:]`).

```python
from tinker_cookbook.supervised.types import SupervisedDataset
from tinker.types import Datum, ModelInput, TensorData
import numpy as np

class CustomDataset(SupervisedDataset):
    def __iter__(self):
        for item in self.data:
            model_input, weights = self.renderer.build_supervised_example(
                messages=self._preprocess(item),
                train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
            )
            tokens = model_input.to_ints()
            yield Datum(
                model_input=ModelInput.from_ints(tokens=tokens[:-1]),
                loss_fn_inputs={
                    "target_tokens": TensorData.from_numpy(np.array(tokens[1:], dtype=np.int64)),
                    "weights":       TensorData.from_numpy(np.array(weights[1:], dtype=np.float32)),
                },
            )
```

## Hyperparameters

### Learning rate
```python
from tinker_cookbook.hyperparam_utils import get_lr
recommended_lr = get_lr("meta-llama/Llama-3.2-1B")
```
Underlying form: `LR = lr_base · M_LoRA · (2000 / H_m)^P_m` with `lr_base=5e-5`, `M_LoRA=10`, and a
per-family exponent `P_m`.

### Batch size
- Smaller batches (128) generally fine-tune better.
- Scale LR with `LR ∝ √batch_size`.
- Aim for ≥100 steps (1000+ for best results). If you see only one step per epoch, `batch_size` is
  too large for the dataset.

## Checkpoints

| Method | Path contains | Use |
|--------|---------------|-----|
| `save_weights_for_sampler(name)` | `/sampler_weights/` | Inference only (lightweight) |
| `save_state(name)` | `/weights/` | Full optimizer state, resumable |

```python
path = training_client.save_weights_for_sampler(name="final").result().path
sampling_client = service_client.create_sampling_client(model_path=path)

state = training_client.save_state(name="checkpoint").result().path
training_client.load_state(state)
```

## Output files

`log_path/` holds `metrics.jsonl`, `checkpoints.jsonl`, `config.json`.

```python
import pandas
df = pandas.read_json("/tmp/training/metrics.jsonl", lines=True)
# plot df["train_mean_nll"] and df["test/nll"].dropna()
```
