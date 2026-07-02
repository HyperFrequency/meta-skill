# PEFT Integrations and Benchmarks

## With TRL (SFTTrainer)

Pass a `LoraConfig` directly — `SFTTrainer` calls `get_peft_model` for you.

```python
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig

lora_config = LoraConfig(r=16, lora_alpha=32, target_modules="all-linear")

trainer = SFTTrainer(
    model=model,
    args=SFTConfig(output_dir="./output", max_seq_length=512),
    train_dataset=dataset,
    peft_config=lora_config,
)
trainer.train()
```

## With Axolotl (YAML config)

```yaml
# axolotl config.yaml
adapter: lora
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
lora_target_linear: true  # target all linear layers
```

## With vLLM (inference)

```python
from vllm import LLM
from vllm.lora.request import LoRARequest

llm = LLM(model="meta-llama/Llama-3.1-8B", enable_lora=True)

outputs = llm.generate(
    prompts,
    lora_request=LoRARequest("adapter1", 1, "./lora-adapter"),
)
```

See `advanced-usage.md` for batched multi-adapter vLLM serving.

## Performance benchmarks

### Memory usage (Llama 3.1 8B)

| Method | GPU Memory | Trainable Params |
|--------|-----------|------------------|
| Full fine-tuning | 60+ GB | 8B (100%) |
| LoRA r=16 | 18 GB | 14M (0.17%) |
| QLoRA r=16 | 6 GB | 14M (0.17%) |
| IA3 | 16 GB | 800K (0.01%) |

### Training speed (A100 80GB)

| Method | Tokens/sec | vs Full FT |
|--------|-----------|------------|
| Full FT | 2,500 | 1x |
| LoRA | 3,200 | 1.3x |
| QLoRA | 2,100 | 0.84x |

### Quality (MMLU benchmark)

| Model | Full FT | LoRA | QLoRA |
|-------|---------|------|-------|
| Llama 2-7B | 45.3 | 44.8 | 44.1 |
| Llama 2-13B | 54.8 | 54.2 | 53.5 |

Numbers are indicative; actual results depend on rank, target modules, data, and
hyperparameters.
