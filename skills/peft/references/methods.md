# PEFT Methods Catalogue

PEFT ships 25+ parameter-efficient methods (verified against PEFT v0.19.0). Pick by
the trade-off you care about: trainable-parameter count, memory, inference overhead,
or task type (causal LM, NLU, generation control, diffusion).

## Method comparison (LLM fine-tuning)

| Method | Trainable % | Memory | Inference overhead | Best for |
|--------|------------|--------|--------------------|----------|
| **LoRA** | 0.1-1% | Low | None (mergeable) | General fine-tuning |
| **QLoRA** (LoRA + 4-bit bnb) | 0.1-1% | Very Low | None (mergeable) | Memory-constrained, 70B on 24GB |
| **DoRA** (`use_dora=True`) | 0.1-1% | Low (+~10%) | None (mergeable) | Quality-critical, beats LoRA on instruction tasks |
| AdaLoRA | 0.1-1% | Low | None | Automatic per-layer rank allocation |
| rsLoRA (`use_rslora=True`) | 0.1-1% | Low | None | Stable training at high rank (r>32) |
| IA3 | ~0.01% | Minimal | Small | Few-shot adaptation, lowest param count |
| VeRA | <0.01% | Minimal | Small | Many adapters from shared frozen random matrices |
| FourierFT | <0.01% | Minimal | Small | Extreme parameter compression |
| Prefix Tuning | ~0.1% | Low | KV-cache cost | Generation control |
| Prompt Tuning | ~0.001% | Minimal | Tiny | Simple single-task adaptation |
| P-Tuning / P-Tuning v2 | ~0.1% | Low | Small | NLU tasks |

## Full method list (by family)

- **Low-rank**: LoRA, QLoRA, DoRA, rsLoRA, PiSSA / OLoRA / LoftQ (LoRA init variants),
  AdaLoRA, VeRA, FourierFT, X-LoRA (mixture-of-LoRA), HRA, VBLoRA, Bone.
- **LyCORIS** (matrix-decomposition, popular for diffusion): LoHa, LoKr.
- **Orthogonal**: OFT, BOFT.
- **Soft prompts**: Prompt Tuning, Prefix Tuning, P-Tuning, P-Tuning v2,
  Multitask Prompt Tuning, CPT.
- **Adapter / scaling**: IA3, Llama-Adapter (`AdaptionPrompt`), Polytropon, LN Tuning.

LoftQ, DoRA, and rsLoRA are covered in `advanced-usage.md`.

## IA3 (minimal parameters)

```python
from peft import IA3Config, get_peft_model

ia3_config = IA3Config(
    target_modules=["q_proj", "v_proj", "k_proj", "down_proj"],
    feedforward_modules=["down_proj"],
)
model = get_peft_model(model, ia3_config)  # trains ~0.01% of parameters
```

## Prefix Tuning

```python
from peft import PrefixTuningConfig, get_peft_model

prefix_config = PrefixTuningConfig(
    task_type="CAUSAL_LM",
    num_virtual_tokens=20,   # prepended virtual tokens
    prefix_projection=True,  # use MLP projection
)
model = get_peft_model(model, prefix_config)
```

## Prompt Tuning

```python
from peft import PromptTuningConfig, PromptTuningInit, get_peft_model

prompt_config = PromptTuningConfig(
    task_type="CAUSAL_LM",
    num_virtual_tokens=8,
    prompt_tuning_init=PromptTuningInit.TEXT,
    prompt_tuning_init_text="Classify the sentiment of this review:",
    tokenizer_name_or_path="meta-llama/Llama-3.1-8B",
)
model = get_peft_model(model, prompt_config)
```
