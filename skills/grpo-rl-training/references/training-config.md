# Training Configuration & Model Setup

A complete, runnable training script lives in
[`../templates/basic_grpo_training.py`](../templates/basic_grpo_training.py).
This page documents the config choices and model-loading variants.

## Memory-Optimized Config (Small GPU)
```python
from trl import GRPOConfig

training_args = GRPOConfig(
    output_dir="outputs/grpo-model",

    # Learning rate
    learning_rate=5e-6,             # Lower = more stable
    adam_beta1=0.9,
    adam_beta2=0.99,
    weight_decay=0.1,
    warmup_ratio=0.1,
    lr_scheduler_type='cosine',

    # Batch settings
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,  # Effective batch = 4

    # GRPO-specific
    num_generations=8,              # Group size: 8-16 recommended
    max_prompt_length=256,
    max_completion_length=512,

    # Training duration
    num_train_epochs=1,
    max_steps=None,                 # Or set fixed steps (e.g., 500)

    # Optimization
    bf16=True,                      # Faster on A100/H100
    optim="adamw_8bit",             # Memory-efficient optimizer
    max_grad_norm=0.1,

    # Logging
    logging_steps=1,
    save_steps=100,
    report_to="wandb",              # Or "none" for no logging
)
```

## High-Performance Config (Large GPU)
```python
training_args = GRPOConfig(
    output_dir="outputs/grpo-model",
    learning_rate=1e-5,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=2,
    num_generations=16,             # Larger groups = better signal
    max_prompt_length=512,
    max_completion_length=1024,
    num_train_epochs=1,
    bf16=True,
    use_vllm=True,                  # Fast generation with vLLM
    logging_steps=10,
)
```

When `use_vllm=True`, also consider `vllm_mode="colocate"` (vLLM in the same process as
training) and tune `vllm_gpu_memory_utilization` to share the GPU with the policy.

## Critical Hyperparameters

| Parameter | Impact | Tuning Advice |
|-----------|--------|---------------|
| `num_generations` | Group size for comparison | Start with 8, increase to 16 if GPU allows |
| `learning_rate` | Convergence speed/stability | 5e-6 (safe), 1e-5 (faster, riskier) |
| `max_completion_length` | Output verbosity | Match your task (512 for reasoning, 256 for short answers) |
| `gradient_accumulation_steps` | Effective batch size | Increase if GPU memory limited |
| `beta` | KL penalty strength | 0.0 disables the reference-KL term (DAPO-style) |

## Standard Model Setup (Transformers + PEFT)
```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import GRPOTrainer

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",  # 2-3x faster
    device_map="auto",
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

# Optional: LoRA for parameter-efficient training
peft_config = LoraConfig(
    r=16,                         # Rank (higher = more capacity)
    lora_alpha=32,               # Scaling factor (typically 2*r)
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    task_type="CAUSAL_LM",
    lora_dropout=0.05,
)

trainer = GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    reward_funcs=[
        incremental_format_reward,
        format_reward,
        correctness_reward,
    ],
    args=training_args,
    train_dataset=dataset,
    peft_config=peft_config,      # Remove for full fine-tuning
)
trainer.train()
trainer.save_model("final_model")
```

## Unsloth Setup (2-3x Faster)
```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="google/gemma-3-1b-it",
    max_seq_length=1024,
    load_in_4bit=True,
    fast_inference=True,
    max_lora_rank=32,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=32,
    use_gradient_checkpointing="unsloth",
)

# Rest is identical to the standard setup
trainer = GRPOTrainer(model=model, ...)
trainer.train()
```
