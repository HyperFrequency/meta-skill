# HQQ Integration Guide

Usage patterns for HuggingFace Transformers, vLLM, and PEFT/LoRA, plus end-to-end
workflows. For backend tuning and mixed-precision strategy see
[advanced-usage.md](advanced-usage.md); for errors see [troubleshooting.md](troubleshooting.md).

## Core API

### BaseQuantizeConfig + HQQLinear (low level)

```python
from hqq.core.quantize import BaseQuantizeConfig, HQQLinear
import torch.nn as nn

config = BaseQuantizeConfig(
    nbits=4,           # bits per weight (1-8)
    group_size=64,     # weights per quantization group
    axis=1,            # 0=input dim, 1=output dim
)

linear = nn.Linear(4096, 4096)
hqq_linear = HQQLinear(linear, config)
output = hqq_linear(input_tensor)

# Inspect the quantized state
W_q   = hqq_linear.W_q          # packed quantized weights
scale = hqq_linear.scale        # scale factors
zero  = hqq_linear.zero         # zero points
W_dequant = hqq_linear.dequantize()
```

Aggressive low-bit configs use smaller groups, e.g. `BaseQuantizeConfig(nbits=2, group_size=16, axis=1)`.

### Backends

```python
from hqq.core.quantize import HQQLinear

# pytorch | pytorch_compile | aten | torchao_int4 | gemlite | bitblas | marlin
HQQLinear.set_backend("torchao_int4")   # global
hqq_layer.set_backend("marlin")          # per layer
```

| Backend | Best for | Requirements |
|---------|----------|--------------|
| pytorch | Compatibility | Any GPU |
| pytorch_compile | Moderate speedup | torch>=2.0 |
| aten | Good balance | CUDA GPU |
| torchao_int4 | 4-bit inference | torchao installed |
| marlin | Maximum 4-bit speed | Ampere+ GPU |
| bitblas | Flexible bit-widths | bitblas installed |

## HuggingFace Transformers

### Quantize, save, and push

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, HqqConfig
import torch

quant_config = HqqConfig(nbits=4, group_size=64)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    dtype=torch.float16,
    quantization_config=quant_config,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

model.save_pretrained("./llama-8b-hqq-4bit")
model.push_to_hub("my-org/Llama-3.1-8B-HQQ-4bit")
```

### Load a pre-quantized model

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "mobiuslabsgmbh/Llama-3.1-8B-HQQ-4bit",
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")
inputs = tokenizer("Hello, world!", return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=50)
```

### Per-layer (dynamic) precision

`dynamic_config` keys are full linear-layer paths (not abbreviations). Especially
useful for MoEs, which tolerate lower precision in MLP/expert layers.

```python
from transformers import AutoModelForCausalLM, HqqConfig
import torch

q4 = {"nbits": 4, "group_size": 64}
q3 = {"nbits": 3, "group_size": 32}
quant_config = HqqConfig(dynamic_config={
    "self_attn.q_proj": q4,
    "self_attn.k_proj": q4,
    "self_attn.v_proj": q4,
    "self_attn.o_proj": q4,
    "mlp.gate_proj": q3,
    "mlp.up_proj":   q3,
    "mlp.down_proj": q3,
})

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    dtype=torch.float16,
    device_map="auto",
    quantization_config=quant_config,
)
```

## vLLM

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="mobiuslabsgmbh/Llama-3.1-8B-HQQ-4bit",
    quantization="hqq",
    dtype="float16",
)
sampling_params = SamplingParams(temperature=0.7, max_tokens=100)
outputs = llm.generate(["What is machine learning?"], sampling_params)
```

## PEFT / LoRA fine-tuning

```python
from transformers import AutoModelForCausalLM, HqqConfig, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

quant_config = HqqConfig(nbits=4, group_size=64)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    quantization_config=quant_config,
    device_map="auto",
)

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)

training_args = TrainingArguments(
    output_dir="./hqq-lora-output",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    num_train_epochs=3,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
)
trainer = Trainer(model=model, args=training_args,
                  train_dataset=train_dataset, data_collator=data_collator)
trainer.train()
```

## End-to-end workflows

### Quick compression (no calibration)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, HqqConfig

config = HqqConfig(nbits=4, group_size=64)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B", quantization_config=config, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

inputs = tokenizer("The capital of France is", return_tensors="pt").to(model.device)
print(tokenizer.decode(model.generate(**inputs, max_new_tokens=20)[0]))

model.save_pretrained("./llama-8b-hqq")
tokenizer.save_pretrained("./llama-8b-hqq")
```

### Optimize for inference speed

```python
from hqq.core.quantize import HQQLinear
from transformers import AutoModelForCausalLM, HqqConfig
import torch

config = HqqConfig(nbits=4, group_size=64)
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B", quantization_config=config, device_map="auto")

HQQLinear.set_backend("marlin")          # or "torchao_int4"
model = torch.compile(model, mode="reduce-overhead")
```
