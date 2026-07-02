---
name: torchtitan
description: PyTorch-native distributed LLM pretraining via torchtitan with composable 4D parallelism (FSDP2, TP, PP, CP), Float8, torch.compile, and distributed (DCP) checkpointing. Use when pretraining Llama 3.1/4, DeepSeek V3, or custom models from scratch at 8 to 512+ GPU scale on H100-class clusters, and when you want interoperable checkpoints with torchtune/HuggingFace. NOT for fine-tuning/SFT/RLHF (use Axolotl or TRL), inference serving (use vLLM), NVIDIA-only maximum-throughput runs (Megatron-LM), broad ZeRO/offload ecosystems (DeepSpeed), or small educational-scale training (LitGPT).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Model Architecture, Distributed Training, TorchTitan, FSDP2, Tensor Parallel, Pipeline Parallel, Context Parallel, Float8, Llama, Pretraining]
dependencies: [torch>=2.6.0, torchtitan>=0.2.0, torchao>=0.5.0]
---

# TorchTitan - PyTorch Native Distributed LLM Pretraining

PyTorch's official platform for large-scale LLM pretraining with composable 4D
parallelism (FSDP2, TP, PP, CP), Float8, and `torch.compile` — 65%+ speedups over
baselines on H100s. This file is a router; detailed configs live in `references/`.

## Install

```bash
pip install torchtitan                 # stable from PyPI
# or from source (latest, needs PyTorch nightly):
git clone https://github.com/pytorch/torchtitan && cd torchtitan
pip install -r requirements.txt
```

Download a tokenizer, then launch:
```bash
python scripts/download_hf_assets.py --repo_id meta-llama/Llama-3.1-8B \
  --assets tokenizer --hf_token=...
CONFIG_FILE="./torchtitan/models/llama3/train_configs/llama3_8b.toml" ./run_train.sh
```

## Workflows → [references/workflows.md](references/workflows.md)

1. **Single-node 8B (8 GPUs)** — tokenizer → TOML config → `run_train.sh` → TensorBoard.
2. **Multi-node SLURM (70B, 256 GPUs)** — FSDP+TP, `sbatch` + `torchrun` rendezvous, auto-resume.
3. **Float8 on H100** — `torchao` converter + `torch.compile` for 30-50% speedup; see [references/float8.md](references/float8.md).
4. **4D parallelism (405B, 512 GPUs)** — seed checkpoint → FSDP+TP+PP+CP launch.

## When to use vs alternatives

Use TorchTitan to pretrain LLMs from scratch (8B–405B+) when you need a
PyTorch-native, composable 4D-parallel stack with Float8 and DCP checkpoints
interoperable with torchtune/HuggingFace. Otherwise:

- **Megatron-LM** — maximum throughput on NVIDIA-only deployments.
- **DeepSpeed** — broader ZeRO/offload ecosystem and inference support.
- **Axolotl / TRL** — fine-tuning / SFT / RLHF rather than pretraining.
- **LitGPT** — educational, smaller-scale training.

## Supported models

| Model | Sizes | Status |
|-------|-------|--------|
| Llama 3.1 | 8B, 70B, 405B | Production |
| Llama 4 | Various | Experimental |
| DeepSeek V3 | 16B, 236B, 671B (MoE) | Experimental |
| GPT-OSS | 20B, 120B (MoE) | Experimental |
| Qwen 3 | Various | Experimental |
| Flux | Diffusion | Experimental |

## Performance (H100, TPS/GPU)

| Model | GPUs | Parallelism | TPS/GPU |
|-------|------|-------------|---------|
| Llama 8B | 8 | FSDP | 5,762 (baseline) |
| Llama 8B | 8 | FSDP+compile+FP8 | 8,532 (+48%) |
| Llama 70B | 256 | FSDP+TP+AsyncTP | 876 |
| Llama 405B | 512 | FSDP+TP+PP | 128 |

## Deeper references

- **Troubleshooting** (OOM, async-TP memory, slow Float8, checkpoint reshard): [references/troubleshooting.md](references/troubleshooting.md)
- **FSDP2** (vs FSDP1, ZeRO equivalents): [references/fsdp.md](references/fsdp.md)
- **Float8** (tensorwise vs rowwise scaling): [references/float8.md](references/float8.md)
- **Checkpointing** (HF conversion, async DCP): [references/checkpoint.md](references/checkpoint.md)
- **Custom models** (TrainSpec protocol): [references/custom-models.md](references/custom-models.md)

## Resources

- GitHub: https://github.com/pytorch/torchtitan
- Paper: https://arxiv.org/abs/2410.06511 (ICLR 2025)
- Forum: https://discuss.pytorch.org/c/distributed/torchtitan/44
