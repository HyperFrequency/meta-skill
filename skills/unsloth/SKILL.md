---
name: unsloth
description: "Expert guidance for fast LLM fine-tuning with Unsloth — 2-5x faster training and 50-80% less VRAM via LoRA/QLoRA, full fine-tuning, and RL (GRPO/DPO/ORPO/KTO) on a single GPU. Covers FastLanguageModel/FastModel/FastVisionModel loading, get_peft_model adapters, TRL SFTTrainer integration, chat templates, train_on_responses_only, and exporting to GGUF/Ollama/vLLM. Use WHEN: fine-tuning Llama, Mistral, Gemma, Qwen, Phi, gpt-oss or vision/TTS models on limited VRAM; converting a HF/PEFT training loop to Unsloth's faster kernels; debugging OOM, dtype, gradient-checkpointing, or saving/quantization issues; or running single-GPU RL. Use WHEN-NOT: multi-GPU/multi-node or FSDP/DeepSpeed sharded training (Unsloth's free tier is single-GPU — use a sibling instead); generic PEFT/adapter theory not tied to Unsloth kernels (use peft); config-file-driven recipe pipelines (use axolotl or llama-factory); pretraining from scratch; or pure inference/serving with no training."
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Fine-Tuning, Unsloth, Fast Training, LoRA, QLoRA, Memory-Efficient, Optimization, Llama, Mistral, Gemma, Qwen, GRPO, RL]
dependencies: [unsloth, torch, transformers, trl, datasets, peft]
---

# Unsloth Skill

Fast, memory-efficient fine-tuning and RL for LLMs/VLMs. Unsloth hand-writes Triton kernels and a manual autograd backward pass to deliver 2-5x faster training with 50-80% less VRAM versus stock HF + PEFT, with no accuracy loss. It is a drop-in front end over `transformers` + `trl`: you swap model loading and adapter attachment, then train with the normal TRL trainers.

## When to Use This Skill

- Fine-tuning Llama, Mistral, Gemma, Qwen, Phi, gpt-oss, DeepSeek, or vision/TTS models on a single GPU (incl. free Colab T4, consumer RTX, Blackwell RTX 50, B200).
- Porting an existing HF/PEFT/TRL training script to Unsloth's faster kernels.
- QLoRA (4-bit), LoRA (16-bit), or `full_finetuning = True`.
- Single-GPU RL: GRPO (reasoning), DPO/ORPO/KTO (preference), GSPO, vision RL.
- Debugging OOM, dtype mismatches, gradient checkpointing, chat-template/masking, or export/quantization.

Use a sibling instead when: multi-GPU/FSDP/DeepSpeed sharded training; generic PEFT theory (`peft`); YAML-recipe pipelines (`axolotl`, `llama-factory`); pretraining; or inference-only.

## Quick Reference

### 1. Load a model (QLoRA, 4-bit)
```python
from unsloth import FastLanguageModel  # FastModel for new/multimodal; FastVisionModel for VLMs
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name      = "unsloth/llama-3.1-8b-bnb-4bit",  # pre-quantized = faster download, no OOM
    max_seq_length  = 2048,     # RoPE-scaled internally; pick any length
    dtype           = None,     # None = auto (bf16 on Ampere+, else fp16)
    load_in_4bit    = True,     # QLoRA; set False for 16-bit LoRA
    full_finetuning = False,    # [NEW] True for full FT (more VRAM)
    # token = "hf_...",         # for gated repos
)
```

### 2. Attach LoRA adapters
```python
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,                     # rank: 8-128; higher = more capacity + VRAM
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,            # common rule: alpha = r (or 2*r)
    lora_dropout = 0,           # 0 is optimized (fastest path)
    bias = "none",              # "none" is optimized
    use_gradient_checkpointing = "unsloth",  # "unsloth" = ~30% less VRAM, longer context
    random_state = 3407,
    use_rslora = False,         # rank-stabilized LoRA
    # loftq_config = None,
)
```

### 3. Train with TRL `SFTTrainer`
```python
from trl import SFTTrainer, SFTConfig
from unsloth import is_bfloat16_supported

trainer = SFTTrainer(
    model = model, tokenizer = tokenizer, train_dataset = dataset,
    args = SFTConfig(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,   # effective batch = 2*4 = 8
        warmup_steps = 5, max_steps = 60,  # or num_train_epochs = 1
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(), bf16 = is_bfloat16_supported(),
        optim = "adamw_8bit", weight_decay = 0.01,
        lr_scheduler_type = "linear", seed = 3407, output_dir = "outputs",
    ),
)
trainer.train()
```

### 4. Chat templates + response-only masking (instruction tuning)
```python
from unsloth.chat_templates import get_chat_template, train_on_responses_only
tokenizer = get_chat_template(tokenizer, chat_template = "llama-3.1")
# Mask the prompt so loss is computed only on assistant turns:
trainer = train_on_responses_only(
    trainer,
    instruction_part = "<|start_header_id|>user<|end_header_id|>\n\n",
    response_part    = "<|start_header_id|>assistant<|end_header_id|>\n\n",
)
```

### 5. Inference + save / export
```python
FastLanguageModel.for_inference(model)  # ~2x faster generation
# Save LoRA adapters only:
model.save_pretrained("lora_model"); tokenizer.save_pretrained("lora_model")
# Merge + save 16-bit, or export GGUF for Ollama/llama.cpp:
model.save_pretrained_merged("merged_16bit", tokenizer, save_method = "merged_16bit")
model.save_pretrained_gguf("gguf_model", tokenizer, quantization_method = "q4_k_m")
```

### Common pitfalls
- **OOM:** lower `per_device_train_batch_size`, raise `gradient_accumulation_steps`, keep `use_gradient_checkpointing = "unsloth"`, use a `-bnb-4bit` model.
- **`dtype` errors:** leave `dtype = None`; let `is_bfloat16_supported()` drive `fp16`/`bf16`.
- **Loss not dropping / leaks:** verify the chat template matches the base model and apply `train_on_responses_only`.
- **Pinning a 4-bit repo:** pass `use_exact_model_name = True` with the exact `...-unsloth-bnb-4bit` name.
- **RL:** import `PatchDPOTrainer()`/`PatchFastRL()` before constructing the TRL trainer.

## Reference Files

Detailed docs live in `references/` (scraped from the official Unsloth docs):

- `index.md` — category index of the documentation set.
- `llms.md` — compact link map of all 136 documentation pages (start here to locate a topic).
- `llms-txt.md` — full documentation text, lightly formatted.
- `llms-full.md` — full documentation incl. complete code blocks (verified source for the snippets above).

Search these with `grep` for a topic (e.g. `grep -n "GRPO" references/llms-full.md`) and read the matching span, rather than loading whole files.

## Related Skills

- `peft` — adapter/LoRA theory and the underlying PEFT library (Unsloth wraps it).
- `axolotl`, `llama-factory` — YAML-recipe fine-tuning pipelines; prefer for config-driven or multi-GPU runs.
- `distributed-training`, `optimize-for-gpu` — multi-GPU/FSDP and GPU performance tuning beyond Unsloth's single-GPU scope.
- `transformers`, `tokenization` — base model/tokenizer mechanics.

<!-- Trigger re-upload 1763621536 -->
