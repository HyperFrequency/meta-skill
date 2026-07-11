# TRL Training Methods, Dataset Formats, and Templates

TRL provides several fine-tuning / alignment methods. Pick by what data you have
and what you are trying to change about the model. When in doubt, fetch the live
docs: `hf_doc_search("your query", product="trl")` or
`hf_doc_fetch("https://huggingface.co/docs/trl/dataset_formats")`.

## Method selection

| Method | Class / config | Data required | Dataset columns | Use case |
|--------|----------------|---------------|-----------------|----------|
| **SFT** | `SFTTrainer` / `SFTConfig` | Demonstrations | `messages` (conversational), OR `text`, OR `prompt`+`completion` | Initial instruction tuning; teach a task/domain |
| **DPO** | `DPOTrainer` / `DPOConfig` | Paired preferences | `prompt`, `chosen`, `rejected` | Align to preferences after SFT (no reward model) |
| **GRPO** | `GRPOTrainer` / `GRPOConfig` | Prompts + reward fn | prompt-only (`prompt`) | Online RL where reward is computable (math, code, verifiers) |
| **Reward** | `RewardTrainer` / `RewardConfig` | Paired preferences | `chosen`, `rejected` | Train a scorer for a PPO/RLHF pipeline |

**Recommended pipeline for most work:** SFT → (optional) DPO → (optional) GGUF
export. For verifiable-reward tasks, SFT → GRPO.

## Validate the dataset format first

Format mismatch is the top cause of failed jobs. **DPO is especially strict**:
most public preference datasets use non-standard column names (e.g.
`instruction` / `chosen_response` / `rejected_response`) and must be remapped to
`prompt` / `chosen` / `rejected`. Validating on CPU costs pennies; a failed GPU
job costs dollars and 30–60 min.

Skip validation only for known TRL-native datasets (`trl-lib/Capybara`,
`trl-lib/ultrafeedback_binarized`, `HuggingFaceH4/ultrachat_200k`, …). Otherwise
load a slice and inspect the columns before submitting:

```python
from datasets import load_dataset
ds = load_dataset("some/dataset", split="train[:5]")
print(ds.column_names)   # confirm they match the method's expected columns
```

Example DPO remap when columns don't match:

```python
def to_dpo(example):
    return {
        "prompt":   example["instruction"],
        "chosen":   example["chosen_response"],
        "rejected": example["rejected_response"],
    }
dataset = dataset.map(to_dpo, remove_columns=dataset.column_names)
```

Some environments also expose a hosted `dataset_inspector.py` (run via
`uv run <url>` or an `hf jobs` CPU job) that prints per-method compatibility
(`READY` / `NEEDS MAPPING` + generated mapping code / `INCOMPATIBLE`). Use it if
available; the manual check above is always sufficient.

## SFT template (production-ready)

Complete inline script: LoRA, train/eval split, checkpoints, Trackio, Hub push.
Submit its content inline, from a URL, or via `trl-jobs`.

```python
# /// script
# dependencies = ["trl>=0.12.0", "peft>=0.7.0", "transformers>=4.36.0", "accelerate>=0.24.0", "trackio"]
# ///

import trackio
from datasets import load_dataset
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

dataset = load_dataset("trl-lib/Capybara", split="train")
split = dataset.train_test_split(test_size=0.1, seed=42)   # eval split for monitoring

config = SFTConfig(
    output_dir="qwen-capybara-sft",
    push_to_hub=True,                 # CRITICAL — ephemeral runner
    hub_model_id="username/qwen-capybara-sft",
    hub_strategy="every_save",        # push each checkpoint
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,    # effective batch = 4 * 4 = 16
    learning_rate=2e-5,
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_strategy="steps", save_steps=100, save_total_limit=2,
    eval_strategy="steps", eval_steps=100,   # REQUIRES eval_dataset below, or training hangs
    report_to="trackio",
    project="my-sft", run_name="baseline-run",
    # max_length=1024 is the default in recent TRL — only set to override
)

trainer = SFTTrainer(
    model="Qwen/Qwen2.5-0.5B",
    train_dataset=split["train"],
    eval_dataset=split["test"],       # MUST be present whenever eval_strategy != "no"
    args=config,
    peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                           bias="none", task_type="CAUSAL_LM",
                           target_modules=["q_proj", "v_proj"]),
)

trainer.train()
trainer.push_to_hub()
trackio.finish()
```

**Demo shortcut:** on a small GPU (t4-small), drop `eval_dataset`/`eval_strategy`
(set `eval_strategy="no"`) to save ~40% memory — you still see training loss.

## DPO template

```python
# /// script
# dependencies = ["trl>=0.12.0", "trackio"]
# ///
from datasets import load_dataset
from trl import DPOTrainer, DPOConfig
import trackio

dataset = load_dataset("trl-lib/ultrafeedback_binarized", split="train")
split = dataset.train_test_split(test_size=0.1, seed=42)

config = DPOConfig(
    output_dir="dpo-model",
    push_to_hub=True, hub_model_id="username/dpo-model",
    num_train_epochs=1,
    beta=0.1,                      # KL penalty; higher = stay closer to the ref model
    eval_strategy="steps", eval_steps=50,
    report_to="trackio", run_name="dpo-baseline",
)

trainer = DPOTrainer(
    model="Qwen/Qwen2.5-0.5B-Instruct",   # start from an instruct/SFT'd model
    train_dataset=split["train"],
    eval_dataset=split["test"],
    args=config,
)
trainer.train()
trainer.push_to_hub()
trackio.finish()
```

## GRPO (online RL)

GRPO benefits from a maintained script rather than hand-rolled reward plumbing.
Run TRL's example directly by URL (see
[jobs-and-hardware.md](jobs-and-hardware.md) for `--script-args` / `script_args`
handling):

```bash
hf jobs uv run --flavor a10g-large --timeout 4h --secrets HF_TOKEN \
  "https://raw.githubusercontent.com/huggingface/trl/main/examples/scripts/grpo.py" \
  --model_name_or_path Qwen/Qwen2.5-0.5B-Instruct \
  --dataset_name trl-lib/math_shepherd \
  --output_dir grpo-model --push_to_hub --hub_model_id username/grpo-model
```

Docs: `hf_doc_fetch("https://huggingface.co/docs/trl/grpo_trainer")`.

## Evaluation contract (applies to every method)

If `eval_strategy="steps"` or `"epoch"` is set, you **must** pass an
`eval_dataset` to the trainer, or training silently **hangs** at "Starting
training". Either provide the split (recommended) or set `eval_strategy="no"`.
See [troubleshooting.md](troubleshooting.md).

## See also

- [jobs-and-hardware.md](jobs-and-hardware.md) — how to submit these scripts, and on what GPU
- [hub-and-monitoring.md](hub-and-monitoring.md) — Hub persistence + Trackio setup
- [troubleshooting.md](troubleshooting.md) — hangs, OOM, format errors
- TRL docs: `hf_doc_fetch("https://huggingface.co/docs/trl/sft_trainer")` (and `/dpo_trainer`, `/reward_trainer`)
