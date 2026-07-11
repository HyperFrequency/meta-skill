# Models & LoRA

## Model roster

Query live availability with `service_client.get_server_capabilities().supported_models`. Typical
lineup:

| Model | Type | Architecture |
|-------|------|--------------|
| Qwen/Qwen3-VL-235B-A22B-Instruct | Vision | MoE Large |
| Qwen/Qwen3-VL-30B-A3B-Instruct | Vision | MoE Medium |
| Qwen/Qwen3-235B-A22B-Instruct-2507 | Instruction | MoE Large |
| Qwen/Qwen3-30B-A3B-Instruct-2507 | Instruction | MoE Medium |
| Qwen/Qwen3-30B-A3B | Hybrid | MoE Medium |
| Qwen/Qwen3-30B-A3B-Base | Base | MoE Medium |
| Qwen/Qwen3-32B | Hybrid | Dense Medium |
| Qwen/Qwen3-8B (+ -Base) | Hybrid / Base | Dense Small |
| Qwen/Qwen3-4B-Instruct-2507 | Instruction | Dense Compact |
| openai/gpt-oss-120b | Reasoning | MoE Medium |
| openai/gpt-oss-20b | Reasoning | MoE Small |
| deepseek-ai/DeepSeek-V3.1 (+ -Base) | Hybrid / Base | MoE Large |
| meta-llama/Llama-3.1-8B (+ -Instruct) | Base / Instruction | Dense Small |
| meta-llama/Llama-3.3-70B-Instruct | Instruction | Dense Large |
| meta-llama/Llama-3.1-70B | Base | Dense Large |
| meta-llama/Llama-3.2-3B, -1B | Base | Dense Compact |
| moonshotai/Kimi-K2-Thinking | Reasoning | MoE Large |

**Sizes:** Compact (1–4B) · Small (8B) · Medium (30–32B) · Large (70B+).

**Types:** *Base* (no chat template — for post-training research) · *Instruction* (chat-tuned, fast)
· *Hybrid* (thinking + non-thinking) · *Reasoning* (always CoT) · *Vision* (VLM).

## Indicative training prices ($/M tokens)

Confirm current pricing in the console before quoting a run.

| Model | $/M |
|-------|-----|
| Llama-3.2-1B | 0.09 |
| Qwen3-4B-Instruct-2507 | 0.22 |
| Qwen3-30B-A3B | 0.36 |
| Qwen3-8B / Llama-3.1-8B | 0.40 |
| Qwen3-VL-30B-A3B-Instruct | 0.53 |
| GPT-OSS-120B | 0.52 |
| Qwen3-32B | 1.47 |
| Llama-3.1-70B | 3.16 |
| DeepSeek-V3.1 | 3.38 |

## Selection tips

- **Cost:** MoE beats dense (Qwen3-30B-A3B at $0.36/M).
- **Experimentation:** start at 8B.
- **Vision:** Qwen3-VL-30B-A3B-Instruct.
- **Reasoning:** Hybrid/Reasoning models with CoT.
- **Latency:** Instruction models without CoT.

## LoRA

Tinker is LoRA-only. `W' = W + BA` with `B (n×r)`, `A (r×n)`, default `r=32` — think of it as an
efficient random projection of parameter space.

### When LoRA matches full fine-tuning
- SL on small–medium instruction datasets: **on par with full FT**.
- RL: **equivalent to full FT even at small ranks**.
- Best results when applied to **all** weight matrices (attention + MLP + MoE). Attention-only
  underperforms even at matched parameter counts.

### Limitations
- **Large batch sizes:** LoRA tolerates them worse than full FT and pays a growing loss penalty past
  a point. Raising rank does **not** fix it — it is a property of the product-of-matrices form.
- **Very large SL datasets:** once the dataset exceeds LoRA capacity, training efficiency degrades
  (increase rank).

### Learning rate — the critical detail
LoRA needs **20–100× the LR of full fine-tuning**. Never hand-pick it.

```python
from tinker_cookbook.hyperparam_utils import get_lr, get_lora_lr_over_full_finetune_lr, get_lora_param_count

lr     = get_lr("meta-llama/Llama-3.1-8B")
factor = get_lora_lr_over_full_finetune_lr("meta-llama/Llama-3.1-8B")  # ~50 (1B→32, 70B→128)
params = get_lora_param_count("meta-llama/Llama-3.1-8B", lora_rank=32)
```

Optimal LR is **independent of rank**. Rule of thumb for SL: **LoRA params ≥ completion tokens**.
Small ranks are fine for RL.

### Configuration

```python
training_client = service_client.create_lora_training_client(
    base_model="meta-llama/Llama-3.1-8B",
    rank=32,
    train_attn=True, train_mlp=True,   # train all layers — best practice
    train_unembed=False,               # output embedding, optional
    seed=42,
)
```
