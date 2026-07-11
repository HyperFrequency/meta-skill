# Reinforcement Learning

## Fastest start

```bash
python -m tinker_cookbook.recipes.rl_basic
```

Fine-tunes Llama-3.1-8B on GSM8K with reward `1[correct] + 0.1·(1[format] − 1)`. ~1 min/iteration,
~63% accuracy after ~15 iterations.

## Cookbook config

```python
import chz, asyncio, sys
from tinker_cookbook.rl import train
from tinker_cookbook import model_info
from tinker_cookbook.recipes.math_rl.math_env import Gsm8kDatasetBuilder

def build() -> chz.Blueprint[train.Config]:
    model_name = "meta-llama/Llama-3.1-8B"
    builder = Gsm8kDatasetBuilder(
        batch_size=128, group_size=16,
        renderer_name=model_info.get_recommended_renderer_name(model_name),
        model_name_for_tokenizer=model_name,
    )
    return chz.Blueprint(train.Config).apply({
        "model_name": model_name, "log_path": "/tmp/rl_basic",
        "dataset_builder": builder, "learning_rate": 4e-5, "max_tokens": 256,
    })

if __name__ == "__main__":
    bp = build(); bp.make_from_argv(sys.argv[1:])
    asyncio.run(train.main(bp.make()))
```

## Key metrics

| Metric | Meaning |
|--------|---------|
| `env/all/correct` | Accuracy |
| `env/all/format` | Format compliance |
| `env/all/reward/total` | Mean total reward |
| `ac_tokens_per_turn` | Tokens per completion |
| `entropy` | Per-token entropy |
| `kl_sample_train_v1/v2` | KL between sampler and learner — keep < 0.01 |

## Environment classes (`tinker_cookbook.rl.types`)

Environments operate on **tokens**, not strings, because training needs exact tokens and logprobs.

- **`Env`** — one agent episode; discard after use.
  ```python
  class MyEnv(Env):
      async def initial_observation(self) -> tuple[Observation, StopCondition]: ...
      async def step(self, action: Action) -> StepResult: ...
  ```
- **`EnvGroupBuilder`** — builds a group of envs (multi-agent / paired comparisons).
  ```python
  class MyEnvGroupBuilder(EnvGroupBuilder):
      async def make_envs(self) -> list[Env]: return [MyEnv() for _ in range(group_size)]
  ```
- **`RLDataset`** — a dataset of `EnvGroupBuilder`s.
  ```python
  class MyDataset(RLDataset):
      def get_batch(self, index: int) -> list[EnvGroupBuilder]: ...
  ```

Complete multi-step reference: `python -m tinker_cookbook.recipes.twenty_questions.train`.

## Completers (policy abstractions)

- **`TokenCompleter`** — token-level, used by RL algorithms.
  `async def __call__(self, model_input, stop) -> TokensWithLogprobs`
- **`MessageCompleter`** — message-level, for judges / evaluation / multi-agent.
  `async def __call__(self, messages) -> Message`

Concrete: `TinkerTokenCompleter`, `TinkerMessageCompleter` (wrap `tinker.SamplingClient`).

## Custom GRPO loop

The canonical pattern: snapshot weights → sample a group → reward → **center advantages** → build
`Datum`s → `forward_backward(loss_fn="importance_sampling")` → `optim_step`.

```python
import torch, tinker
from tinker import types
from tinker.types.tensor_data import TensorData
from tinker_cookbook import model_info, renderers
from tinker_cookbook.tokenizer_utils import get_tokenizer

service_client  = tinker.ServiceClient()
training_client = service_client.create_lora_training_client(base_model=model_name, rank=32)
renderer = renderers.get_renderer(model_info.get_recommended_renderer_name(model_name),
                                  training_client.get_tokenizer())
sampling_params = types.SamplingParams(max_tokens=256, stop=renderer.get_stop_sequences())
adam = types.AdamParams(learning_rate=4e-5)

for batch_idx, batch_rows in enumerate(dataset):
    path = training_client.save_weights_for_sampler(name=f"{batch_idx:06d}").result().path
    sampling_client = service_client.create_sampling_client(model_path=path)

    datums = []
    for question, answer in batch_rows:
        prompt = renderer.build_generation_prompt([{"role": "user", "content": question}])
        prompt_tokens = prompt.to_ints()
        result = sampling_client.sample(prompt=prompt, num_samples=16,
                                        sampling_params=sampling_params).result()

        rewards = [compute_reward(renderer.parse_response(s.tokens)[0], answer) for s in result.sequences]
        mean = sum(rewards) / len(rewards)
        advantages = [r - mean for r in rewards]
        if all(a == 0 for a in advantages):     # no learning signal — skip the group
            continue

        for seq, adv in zip(result.sequences, advantages):
            tokens = prompt_tokens + seq.tokens
            ob_len = len(prompt_tokens) - 1      # prompt tokens carry no advantage
            datums.append(types.Datum(
                model_input=types.ModelInput.from_ints(tokens=tokens[:-1]),
                loss_fn_inputs={
                    "target_tokens": TensorData.from_torch(torch.tensor(tokens[1:])),
                    "logprobs":      TensorData.from_torch(torch.tensor([0.0]*ob_len + list(seq.logprobs))),
                    "advantages":    TensorData.from_torch(torch.tensor([0.0]*ob_len + [adv]*(len(tokens)-1-ob_len))),
                },
            ))

    training_client.forward_backward(datums, loss_fn="importance_sampling").result()
    training_client.optim_step(adam).result()
```

Loss options: `importance_sampling`, `ppo`, `cispo`, `dro` — see [Loss Functions](loss-functions.md).

## Scaling knobs

- **`batch_size`** unique problems per iteration; **`group_size`** rollouts per problem. Scale
  `LR ∝ √batch_size`. Few problems? Raise `group_size` to synthesize more data.
- **`num_substeps`** (PPO) splits the batch into mini-batches (`batch_size` must divide evenly).
  Start at 2–4; higher risks off-distribution updates.
- **Streaming minibatch** (`StreamMinibatchConfig(groups_per_batch=128, num_minibatches=8)`) overlaps
  sampling and training — on-policy, pipeline efficiency only.
- **Async off-policy** (`AsyncConfig(max_steps_off_policy=3, groups_per_batch=64)`) for long rollouts
  (CoT, tool use, agents). Keep `max_steps_off_policy < 5` and watch KL.

## Sequence-extension property (multi-turn efficiency)

When each timestep's observation is a **prefix extension** of the previous one, compute is O(T)
instead of O(T²) via KV-cache reuse. It holds only when thinking blocks are preserved in history:

- `Qwen3Renderer(strip_thinking_from_history=False)` → `renderer.has_extension_property == True`.
- default `strip_thinking_from_history=True` strips `<think>` blocks → prefix breaks → separate
  `Datum` per timestep, O(T²).

Check `renderer.has_extension_property`. **Hybrid compaction**: keep thinking visible for N turns,
strip once at turn N+1, repeat — amortizes recomputation with bounded context growth.

## Monitoring

- **KL** (`kl_sample_train_v1/v2`) should stay < 0.01. Non-zero KL even on-policy is expected; a
  threshold crossing signals numerical instability.
- KL regularization belongs in the **reward**, not the loss — see `incorporate_kl_penalty` in the
  cookbook.
