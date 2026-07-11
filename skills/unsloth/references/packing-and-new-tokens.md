# Packing and Adding New Tokens

Two Unsloth specifics not covered by the scraped `llms-*.md` doc set. Both verified against the official Unsloth wiki (github.com/unslothai/unsloth/wiki/Home).

_Portions adapted from openscience (Apache-2.0)._

## Sequence packing (`packing = True`)

Pass `packing = True` to the TRL trainer to concatenate short examples until each sequence fills `max_seq_length`, instead of padding each example individually. This removes wasted compute on padding tokens and can noticeably shorten training — the gain is largest on datasets with many short rows and shrinks toward zero when rows already approach `max_seq_length`.

```python
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model = model, tokenizer = tokenizer, train_dataset = dataset,
    args = SFTConfig(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        max_seq_length = 2048,
        packing = True,          # pack short sequences to cut padding waste
        # ... lr, optim, output_dir, etc.
    ),
)
```

Notes:
- Unsloth's packing uses attention masking so packed examples do not attend across their boundaries; keep TRL current, since older TRL packing did leak attention across concatenated examples.
- Pair packing with `train_on_responses_only` as usual — masking still applies per example.
- If you see unexpected loss behavior, disable packing to isolate whether the packer or the data is at fault.

## Adding new tokens — order matters

To train custom tokens (special tags, character names, control tokens like `<THINKING>` or `<SCRATCH_PAD>`), call `add_new_tokens` **before** `get_peft_model`. Calling it afterward means the resized embedding rows are not wrapped as trainable, so the model never learns the new tokens and the LoRA attach can break.

```python
from unsloth import FastLanguageModel, add_new_tokens

model, tokenizer = FastLanguageModel.from_pretrained(...)

# 1. Add tokens FIRST — resizes + registers the new embeddings
add_new_tokens(model, tokenizer, new_tokens = ["<CHARACTER_1>", "<THINKING>", "<SCRATCH_PAD>"])

# 2. THEN attach LoRA adapters
model = FastLanguageModel.get_peft_model(model, r = 16, lora_alpha = 16, ...)
```

Symptom of the wrong order: the added tokens stay frozen / produce gibberish after fine-tuning, or `get_peft_model` errors on a mismatched embedding size.
