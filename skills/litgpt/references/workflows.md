# LitGPT Workflows

End-to-end command/code walkthroughs for the four most common LitGPT tasks,
plus a troubleshooting appendix. SKILL.md routes here for full detail.

For tuned hyperparameters per model size see [training-recipes.md](training-recipes.md);
for multi-GPU/multi-node setup see [distributed-training.md](distributed-training.md).

---

## Workflow 1: Fine-tune on a custom dataset

```
Fine-Tuning Setup:
- [ ] Step 1: Download pretrained model
- [ ] Step 2: Prepare dataset
- [ ] Step 3: Configure training
- [ ] Step 4: Run fine-tuning
```

**Step 1: Download pretrained model**

```bash
# Download Llama 3 8B
litgpt download meta-llama/Meta-Llama-3-8B

# Download Phi-2 (smaller, faster)
litgpt download microsoft/phi-2

# Download Gemma 2B
litgpt download google/gemma-2b
```

Models are saved to the `checkpoints/` directory.

**Step 2: Prepare dataset**

LitGPT supports multiple formats. Alpaca format (instruction-response):

```json
[
  {
    "instruction": "What is the capital of France?",
    "input": "",
    "output": "The capital of France is Paris."
  },
  {
    "instruction": "Translate to Spanish: Hello, how are you?",
    "input": "",
    "output": "Hola, ¿cómo estás?"
  }
]
```

Save as `data/my_dataset.json`.

**Step 3: Configure training**

```bash
# Full fine-tuning (requires 40GB+ GPU for 7B models)
litgpt finetune \
  meta-llama/Meta-Llama-3-8B \
  --data JSON \
  --data.json_path data/my_dataset.json \
  --train.max_steps 1000 \
  --train.learning_rate 2e-5 \
  --train.micro_batch_size 1 \
  --train.global_batch_size 16

# LoRA fine-tuning (efficient, 16GB GPU)
litgpt finetune_lora \
  microsoft/phi-2 \
  --data JSON \
  --data.json_path data/my_dataset.json \
  --lora_r 16 \
  --lora_alpha 32 \
  --lora_dropout 0.05 \
  --train.max_steps 1000 \
  --train.learning_rate 1e-4
```

**Step 4: Run fine-tuning**

Training saves checkpoints to `out/finetune/` automatically.

```bash
# View logs
tail -f out/finetune/logs.txt

# TensorBoard (if using --train.logger_name tensorboard)
tensorboard --logdir out/finetune/lightning_logs
```

---

## Workflow 2: LoRA fine-tuning on a single GPU

Most memory-efficient option.

```
LoRA Training:
- [ ] Step 1: Choose base model
- [ ] Step 2: Configure LoRA parameters
- [ ] Step 3: Train with LoRA
- [ ] Step 4: Merge LoRA weights (optional)
```

**Step 1: Choose base model** — for limited GPU memory (12-16GB):
- **Phi-2** (2.7B) — best quality/size tradeoff
- **Llama 3 1B** — smallest, fastest
- **Gemma 2B** — good reasoning

**Step 2: Configure LoRA parameters**

```bash
litgpt finetune_lora \
  microsoft/phi-2 \
  --data JSON \
  --data.json_path data/my_dataset.json \
  --lora_r 16 \             # LoRA rank (8-64, higher=more capacity)
  --lora_alpha 32 \         # LoRA scaling (typically 2×r)
  --lora_dropout 0.05 \     # Prevent overfitting
  --lora_query true \       # Apply LoRA to query projection
  --lora_key false \        # Usually not needed
  --lora_value true \       # Apply LoRA to value projection
  --lora_projection true \  # Apply LoRA to output projection
  --lora_mlp false \        # Usually not needed
  --lora_head false         # Usually not needed
```

LoRA rank guide:
- `r=8`: lightweight, 2-4MB adapters
- `r=16`: standard, good quality
- `r=32`: high capacity, use for complex tasks
- `r=64`: maximum quality, 4× larger adapters

**Step 3: Train with LoRA**

```bash
litgpt finetune_lora \
  microsoft/phi-2 \
  --data JSON \
  --data.json_path data/my_dataset.json \
  --lora_r 16 \
  --train.epochs 3 \
  --train.learning_rate 1e-4 \
  --train.micro_batch_size 4 \
  --train.global_batch_size 32 \
  --out_dir out/phi2-lora

# Memory usage: ~8-12GB for Phi-2 with LoRA
```

**Step 4: Merge LoRA weights** (optional) — merge adapters into base model for deployment:

```bash
litgpt merge_lora \
  out/phi2-lora/final \
  --out_dir out/phi2-merged
```

```python
from litgpt import LLM
llm = LLM.load("out/phi2-merged")
```

---

## Workflow 3: Pretrain from scratch

```
Pretraining:
- [ ] Step 1: Prepare pretraining dataset
- [ ] Step 2: Configure model architecture
- [ ] Step 3: Set up multi-GPU training
- [ ] Step 4: Launch pretraining
```

**Step 1: Prepare pretraining dataset** — LitGPT expects tokenized data:

```bash
python scripts/prepare_dataset.py \
  --source_path data/my_corpus.txt \
  --checkpoint_dir checkpoints/tokenizer \
  --destination_path data/pretrain \
  --split train,val
```

**Step 2: Configure model architecture**

```yaml
# config/pythia-160m.yaml
model_name: pythia-160m
block_size: 2048
vocab_size: 50304
n_layer: 12
n_head: 12
n_embd: 768
rotary_percentage: 0.25
parallel_residual: true
bias: true
```

**Step 3: Set up multi-GPU training**

```bash
# Single GPU
litgpt pretrain \
  --config config/pythia-160m.yaml \
  --data.data_dir data/pretrain \
  --train.max_tokens 10_000_000_000

# Multi-GPU with FSDP
litgpt pretrain \
  --config config/pythia-1b.yaml \
  --data.data_dir data/pretrain \
  --devices 8 \
  --train.max_tokens 100_000_000_000
```

**Step 4: Launch pretraining** — for large-scale pretraining on a cluster:

```bash
# Using SLURM
sbatch --nodes=8 --gpus-per-node=8 pretrain_script.sh

# pretrain_script.sh content:
litgpt pretrain \
  --config config/pythia-1b.yaml \
  --data.data_dir /shared/data/pretrain \
  --devices 8 \
  --num_nodes 8 \
  --train.global_batch_size 512 \
  --train.max_tokens 300_000_000_000
```

---

## Workflow 4: Convert and deploy a model

```
Model Deployment:
- [ ] Step 1: Test inference locally
- [ ] Step 2: Quantize model (optional)
- [ ] Step 3: Convert to GGUF (for llama.cpp)
- [ ] Step 4: Deploy with API
```

**Step 1: Test inference locally**

```python
from litgpt import LLM

llm = LLM.load("out/phi2-lora/final")

# Single generation
print(llm.generate("What is machine learning?"))

# Streaming
for token in llm.generate("Explain quantum computing", stream=True):
    print(token, end="", flush=True)

# Batch inference
prompts = ["Hello", "Goodbye", "Thank you"]
results = [llm.generate(p) for p in prompts]
```

**Step 2: Quantize model** (optional) — reduce size with minimal quality loss:

```bash
# 4-bit NF4 quantization
litgpt convert_lit_checkpoint \
  out/phi2-lora/final \
  --dtype bfloat16 \
  --quantize bnb.nf4

# 4-bit NF4 with double quantization (extra size reduction)
litgpt convert_lit_checkpoint \
  out/phi2-lora/final \
  --quantize bnb.nf4-dq
```

**Step 3: Convert to GGUF** (for llama.cpp)

```bash
python scripts/convert_lit_checkpoint.py \
  --checkpoint_path out/phi2-lora/final \
  --output_path models/phi2.gguf \
  --model_name microsoft/phi-2
```

**Step 4: Deploy with API**

```python
from fastapi import FastAPI
from litgpt import LLM

app = FastAPI()
llm = LLM.load("out/phi2-lora/final")

@app.post("/generate")
def generate(prompt: str, max_tokens: int = 100):
    result = llm.generate(prompt, max_new_tokens=max_tokens, temperature=0.7)
    return {"response": result}

# Run: uvicorn api:app --host 0.0.0.0 --port 8000
```

LitGPT also ships a built-in server: `litgpt serve out/phi2-lora/final`.

---

## Troubleshooting

**Out of memory during fine-tuning** — use LoRA instead of full fine-tuning
(`litgpt finetune_lora` needs ~12-16GB vs 40GB+ for `litgpt finetune`), and/or
accumulate gradients:

```bash
litgpt finetune_lora ... --train.gradient_accumulation_iters 4
```

**Training too slow** — Flash Attention is automatic on Ampere+ GPUs (A100, RTX
30/40 series), no config needed. Shrink the micro-batch and accumulate:

```bash
--train.micro_batch_size 1 \
--train.global_batch_size 32 \
--train.gradient_accumulation_iters 32   # effective batch = 32
```

**Model not loading** — confirm the name and that it is downloaded:

```bash
litgpt download list                          # list all available models
litgpt download meta-llama/Meta-Llama-3-8B    # download if missing
ls checkpoints/                               # expect meta-llama/Meta-Llama-3-8B/
```

**LoRA adapters too large** — reduce rank (`--lora_r 8`) or apply LoRA to fewer
projections (`--lora_projection false`, `--lora_mlp false`).
