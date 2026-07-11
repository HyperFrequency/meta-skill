# Recipes

Runnable cookbook scripts. Run any with `python -m tinker_cookbook.recipes.<name>` and override
fields on the CLI (`--learning_rate 1e-4 --batch_size 64`, or `key=value` for the preference/
distillation entrypoints).

## sl_basic — supervised learning

```python
import chz, sys, asyncio
from tinker_cookbook import cli_utils, model_info
from tinker_cookbook.recipes.chat_sl import chat_datasets
from tinker_cookbook.renderers import TrainOnWhat
from tinker_cookbook.supervised import train
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
from tinker_cookbook.hyperparam_utils import get_lr

def build() -> chz.Blueprint[train.Config]:
    model_name = "meta-llama/Llama-3.1-8B"
    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=model_name,
        renderer_name=model_info.get_recommended_renderer_name(model_name),
        max_length=32768, batch_size=128, train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES)
    dataset = chat_datasets.NoRobotsBuilder(common_config=common)
    # custom file instead:
    # from tinker_cookbook.supervised.data import FromConversationFileBuilder
    # dataset = FromConversationFileBuilder(common_config=common, file_path="/path/data.jsonl")
    return chz.Blueprint(train.Config).apply({
        "log_path": "/tmp/tinker-examples/sl_basic", "model_name": model_name,
        "dataset_builder": dataset, "learning_rate": get_lr(model_name),
        "lr_schedule": "linear", "num_epochs": 1, "eval_every": 8})

def main(config: train.Config):
    cli_utils.check_log_dir(config.log_path, behavior_if_exists="ask")
    asyncio.run(train.main(config))

if __name__ == "__main__":
    bp = build(); bp.make_from_argv(sys.argv[1:]); main(bp.make())
```

## sl_loop — manual SL loop

Hand-rolled loop with linear LR decay, useful when you need per-step control.

```python
import chz, datasets, tinker
from tinker_cookbook import model_info, renderers
from tinker_cookbook.supervised.common import compute_mean_nll
from tinker_cookbook.supervised.data import conversation_to_datum
from tinker_cookbook.tokenizer_utils import get_tokenizer
from tinker_cookbook.hyperparam_utils import get_lr

@chz.chz
class Config:
    log_path: str = "/tmp/tinker-examples/sl-loop"
    model_name: str = "meta-llama/Llama-3.1-8B"
    batch_size: int = 128
    learning_rate: float = get_lr("meta-llama/Llama-3.1-8B")
    max_length: int = 32768
    train_on_what: renderers.TrainOnWhat = renderers.TrainOnWhat.ALL_ASSISTANT_MESSAGES
    lora_rank: int = 32

def main(config: Config):
    tokenizer = get_tokenizer(config.model_name)
    renderer  = renderers.get_renderer(model_info.get_recommended_renderer_name(config.model_name), tokenizer)
    train_ds  = datasets.load_dataset("HuggingFaceH4/no_robots")["train"].shuffle(seed=0)
    n_batches = len(train_ds) // config.batch_size

    service_client  = tinker.ServiceClient()
    training_client = service_client.create_lora_training_client(base_model=config.model_name, rank=config.lora_rank)

    for i in range(n_batches):
        lr_mult = max(0.0, 1.0 - i / n_batches)                     # linear decay
        adam = tinker.AdamParams(learning_rate=config.learning_rate * lr_mult)
        rows = train_ds.select(range(i * config.batch_size, (i + 1) * config.batch_size))
        batch = [conversation_to_datum(r["messages"], renderer, config.max_length, config.train_on_what) for r in rows]

        fb = training_client.forward_backward(batch, loss_fn="cross_entropy")
        training_client.optim_step(adam).result()
        fb_result = fb.result()
        nll = compute_mean_nll([x["logprobs"] for x in fb_result.loss_fn_outputs],
                               [d.loss_fn_inputs["weights"] for d in batch])
        print(f"Step {i}, NLL: {nll:.4f}")

if __name__ == "__main__":
    chz.nested_entrypoint(main)
```

## rl_basic — reinforcement learning

```python
import asyncio, chz, sys
from tinker_cookbook import cli_utils, model_info
from tinker_cookbook.recipes.math_rl.math_env import Gsm8kDatasetBuilder
from tinker_cookbook.rl import train

def build() -> chz.Blueprint[train.Config]:
    model_name = "meta-llama/Llama-3.1-8B"
    builder = Gsm8kDatasetBuilder(
        batch_size=128, group_size=16,
        renderer_name=model_info.get_recommended_renderer_name(model_name),
        model_name_for_tokenizer=model_name)
    return chz.Blueprint(train.Config).apply({
        "model_name": model_name, "log_path": "/tmp/tinker-examples/rl_basic",
        "dataset_builder": builder, "learning_rate": 4e-5, "max_tokens": 256, "eval_every": 0})

def main(config: train.Config):
    cli_utils.check_log_dir(config.log_path, behavior_if_exists="ask")
    asyncio.run(train.main(config))

if __name__ == "__main__":
    bp = build(); bp.make_from_argv(sys.argv[1:]); main(bp.make())
```

## rl_loop — manual RL loop (GSM8K)

Full sampling → reward → advantage → `forward_backward` loop with a math grader.

```python
import chz, datasets, torch, tinker
from tinker import types
from tinker.types.tensor_data import TensorData
from tinker_cookbook import model_info, renderers
from tinker_cookbook.recipes.math_rl.math_grading import extract_boxed, grade_answer
from tinker_cookbook.tokenizer_utils import get_tokenizer

@chz.chz
class Config:
    model_name: str = "meta-llama/Llama-3.1-8B"
    batch_size: int = 128
    group_size: int = 16
    learning_rate: float = 4e-5
    max_tokens: int = 256

def get_reward(response: str, answer: str) -> float:
    try:
        return 1.0 if grade_answer(extract_boxed(response), answer) else 0.0
    except ValueError:
        return 0.0

def main(config: Config):
    tokenizer = get_tokenizer(config.model_name)
    renderer  = renderers.get_renderer(model_info.get_recommended_renderer_name(config.model_name), tokenizer)
    dataset   = datasets.load_dataset("openai/gsm8k", "main")["train"]

    service_client  = tinker.ServiceClient()
    training_client = service_client.create_lora_training_client(base_model=config.model_name, rank=32)
    sampling_params = types.SamplingParams(max_tokens=config.max_tokens, stop=renderer.get_stop_sequences())
    adam = types.AdamParams(learning_rate=config.learning_rate)

    for i in range(len(dataset) // config.batch_size):
        path = training_client.save_weights_for_sampler(name=f"{i:06d}").result().path
        sampling_client = service_client.create_sampling_client(model_path=path)
        rows = dataset.select(range(i * config.batch_size, (i + 1) * config.batch_size))

        datums = []
        for question, answer in zip(rows["question"], rows["answer"]):
            prompt = renderer.build_generation_prompt([{"role": "user", "content": question}])
            prompt_tokens = prompt.to_ints()
            result = sampling_client.sample(prompt=prompt, num_samples=config.group_size,
                                            sampling_params=sampling_params).result()
            rewards = [get_reward(renderers.get_text_content(renderer.parse_response(s.tokens)[0]), answer)
                       for s in result.sequences]
            mean = sum(rewards) / len(rewards)
            advantages = [r - mean for r in rewards]
            if all(a == 0 for a in advantages):
                continue
            for seq, adv in zip(result.sequences, advantages):
                tokens = prompt_tokens + seq.tokens
                ob_len = len(prompt_tokens) - 1
                datums.append(types.Datum(
                    model_input=types.ModelInput.from_ints(tokens=tokens[:-1]),
                    loss_fn_inputs={
                        "target_tokens": TensorData.from_torch(torch.tensor(tokens[1:])),
                        "logprobs":      TensorData.from_torch(torch.tensor([0.0]*ob_len + list(seq.logprobs))),
                        "advantages":    TensorData.from_torch(torch.tensor([0.0]*ob_len + [adv]*(len(tokens)-1-ob_len))),
                    }))

        training_client.forward_backward(datums, loss_fn="importance_sampling").result()
        training_client.optim_step(adam).result()

if __name__ == "__main__":
    chz.nested_entrypoint(main)
```

## Preference / distillation / multi-step

```bash
# DPO (datasets: hhh, helpsteer3, ultrafeedback) — see preference-and-distillation.md
python -m tinker_cookbook.recipes.preference.train \
    log_path=/tmp/dpo model_name=meta-llama/Llama-3.2-1B \
    dataset=hhh renderer_name=role_colon learning_rate=1e-5 dpo_beta=0.1

# Prompt distillation
python -m tinker_cookbook.recipes.prompt_distillation.create_data \
    output_file=/tmp/tinker-datasets/prompt_distillation_lang.jsonl
python -m tinker_cookbook.recipes.prompt_distillation.train

# Multi-step RL (question-asking agent guesses hidden words) — good template for custom envs
python -m tinker_cookbook.recipes.twenty_questions.train
```
