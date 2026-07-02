---
name: peft
description: Parameter-efficient fine-tuning for LLMs with HuggingFace PEFT — LoRA, QLoRA, DoRA and 25+ adapter methods that train <1% of parameters. Use when fine-tuning 7B-70B models under GPU-memory limits, training small swappable adapters (~MBs) for multi-adapter serving, or pairing LoRA with 4-bit quantization (QLoRA). Use for picking LoRA rank/alpha/target_modules, loading/merging adapters, or integrating with TRL/Axolotl/vLLM. NOT for full fine-tuning of small (<1B) models, cases needing all weights updated for maximum quality with ample compute, prompt engineering / in-context learning, or RLHF reward modeling (use trl). Integrated with transformers, accelerate, diffusers; current PEFT line is 0.19.x.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Fine-Tuning, PEFT, LoRA, QLoRA, Parameter-Efficient, Adapters, Low-Rank, Memory Optimization, Multi-Adapter]
dependencies: [peft>=0.13.0, transformers>=4.45.0, torch>=2.0.0, bitsandbytes>=0.43.0]
---

# PEFT (Parameter-Efficient Fine-Tuning)

Fine-tune LLMs by training <1% of parameters using LoRA, QLoRA, and 25+ adapter methods.

## When to use

**LoRA** — fine-tune 7B-70B on consumer GPUs (RTX 4090, A100), train ~MB adapters
instead of the full model, iterate fast, and serve many task-specific variants from one base.

**QLoRA** (LoRA + 4-bit quantization) — when memory is the binding constraint (e.g. 70B on a
single 24GB GPU); accept a small (~5%) quality trade-off vs full fine-tuning.

**Use full fine-tuning instead** when training small models (<1B), when you need maximum
quality and have the compute, or when a large domain shift requires updating all weights.

For other PEFT methods (DoRA, AdaLoRA, IA3, VeRA, prefix/prompt tuning, ...) and how to
choose, see [references/methods.md](references/methods.md).

## Install

```bash
pip install peft transformers accelerate bitsandbytes datasets
```

## LoRA quick start

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import get_peft_model, LoraConfig, TaskType

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B", torch_dtype="auto", device_map="auto"
)

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                 # rank: 8-64, higher = more capacity
    lora_alpha=32,        # scaling, typically 2*r
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    bias="none",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# trainable params: 13,631,488 || all params: 8,043,307,008 || trainable%: 0.17%

# ... train with transformers Trainer or trl SFTTrainer ...

model.save_pretrained("./lora-llama-adapter")  # saves only the adapter (~MBs)
```

For a full training loop (Trainer/SFTTrainer + tokenization + collator) and task-specific
recipes, see [references/advanced-usage.md](references/advanced-usage.md).

## QLoRA quick start (memory-efficient)

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import get_peft_model, LoraConfig, prepare_model_for_kbit_training

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",          # NormalFloat4, best for LLMs
    bnb_4bit_compute_dtype="bfloat16",
    bnb_4bit_use_double_quant=True,     # nested quantization
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-70B", quantization_config=bnb_config, device_map="auto"
)
model = prepare_model_for_kbit_training(model)  # enables gradient checkpointing

lora_config = LoraConfig(
    r=64, lora_alpha=128, lora_dropout=0.1,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    bias="none", task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)  # 70B now fits on one 24GB GPU
```

## Choosing LoRA parameters

### Rank (r) — capacity vs efficiency

| Rank | Trainable Params | Quality | Use Case |
|------|-----------------|---------|----------|
| 4 | ~3M | Lower | Simple tasks, prototyping |
| **8** | ~7M | Good | **Recommended starting point** |
| **16** | ~14M | Better | **General fine-tuning** |
| 32 | ~27M | High | Complex tasks |
| 64 | ~54M | Highest | Domain adaptation, 70B models |

### Alpha and target modules

- **Alpha**: start with `lora_alpha = 2 * r`. Lower alpha = milder effect, higher = stronger.
- **Target modules** by architecture:
  - Llama / Mistral / Qwen: `["q_proj","v_proj","k_proj","o_proj","gate_proj","up_proj","down_proj"]`
  - GPT-2 / GPT-Neo: `["c_attn","c_proj","c_fc"]`
  - Falcon / BLOOM: `["query_key_value","dense","dense_h_to_4h","dense_4h_to_h"]`
  - `"all-linear"` — auto-detect every linear layer (PEFT 0.6.0+).

For targeting specific layers, training embeddings/lm_head, or vocabulary extension, see
[references/advanced-usage.md](references/advanced-usage.md).

## Loading, merging, and multi-adapter

```python
from peft import AutoPeftModelForCausalLM

# Load an adapter on top of its base (resolved from adapter_config.json)
model = AutoPeftModelForCausalLM.from_pretrained("./lora-llama-adapter", device_map="auto")

# Merge into base weights for zero-overhead deployment
merged = model.merge_and_unload()
merged.save_pretrained("./llama-merged")

# Serve multiple adapters from one base and switch at runtime
model.load_adapter("./adapter-task2", adapter_name="task2")
model.set_adapter("task2")
with model.disable_adapter():   # fall back to the base model
    base_out = model.generate(**inputs)
```

Adapter composition/stacking (`add_weighted_adapter`) and batched multi-adapter vLLM serving
are in [references/advanced-usage.md](references/advanced-usage.md).

## Best practices

1. Start with **r=8-16**; increase only if quality is insufficient.
2. Use **alpha = 2 * r** as the default.
3. Target **attention + MLP** layers (or `"all-linear"`) for best quality/efficiency.
4. **Enable gradient checkpointing** (`prepare_model_for_kbit_training`) to save memory.
5. Save adapters frequently — they are small and make rollback cheap.
6. Evaluate on held-out data **before** merging.
7. Use **QLoRA for 70B+ models** on consumer hardware.

## References

- **[methods.md](references/methods.md)** — full 25+ method catalogue, comparison table, IA3 / prefix / prompt tuning configs
- **[advanced-usage.md](references/advanced-usage.md)** — DoRA, LoftQ, rsLoRA, custom targeting, training recipes, multi-adapter composition
- **[integrations.md](references/integrations.md)** — TRL, Axolotl, vLLM integration + memory/speed/quality benchmarks
- **[troubleshooting.md](references/troubleshooting.md)** — OOM, NaN loss, adapter-not-training, loading/merge errors, QLoRA issues

## Resources

- GitHub: https://github.com/huggingface/peft
- Docs: https://huggingface.co/docs/peft
- LoRA paper: arXiv:2106.09685 · QLoRA paper: arXiv:2305.14314
