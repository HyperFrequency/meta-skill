---
name: nemo-evaluator
description: NVIDIA's container-first SDK (nemo-evaluator-launcher / nel) that evaluates LLMs across 100+ benchmarks from 18+ harnesses (MMLU, HumanEval, GSM8K, IFEval, safety, VLM, function-calling) against OpenAI-compatible endpoints. Use when you need reproducible, scalable benchmarking on local Docker, Slurm HPC, or Lepton cloud, comparing multiple models, or exporting results to MLflow/W&B. Do NOT use for quick single-benchmark local runs with no Docker (use lm-evaluation-harness), code-only benchmarking (bigcode-evaluation-harness), fairness/efficiency studies (HELM), training/fine-tuning, or live inference serving.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Evaluation, NeMo, NVIDIA, Benchmarking, MMLU, HumanEval, Multi-Backend, Slurm, Docker, Reproducible, Enterprise]
dependencies: [nemo-evaluator-launcher>=0.1.25, docker]
---

# NeMo Evaluator SDK - Enterprise LLM Benchmarking

## Quick Start

NeMo Evaluator SDK evaluates LLMs across 100+ benchmarks from 18+ harnesses using containerized, reproducible evaluation with multi-backend execution (local Docker, Slurm HPC, Lepton cloud).

**Installation**:
```bash
pip install nemo-evaluator-launcher
```

**Set API key and run evaluation**:
```bash
export NGC_API_KEY=nvapi-your-key-here

# Create minimal config
cat > config.yaml << 'EOF'
defaults:
  - execution: local
  - deployment: none
  - _self_

execution:
  output_dir: ./results

target:
  api_endpoint:
    model_id: meta/llama-3.1-8b-instruct
    url: https://integrate.api.nvidia.com/v1/chat/completions
    api_key_name: NGC_API_KEY

evaluation:
  tasks:
    - name: ifeval
EOF

# Run evaluation
nemo-evaluator-launcher run --config-dir . --config-name config
```

**View available tasks**:
```bash
nemo-evaluator-launcher ls tasks
```

## Common Workflows

Full step-by-step configs live in [references/workflows.md](references/workflows.md):

1. **Standard benchmarks** — run MMLU/GSM8K/IFEval/HumanEval against any
   OpenAI-compatible endpoint (local Docker).
2. **Slurm HPC** — deploy a checkpoint with vLLM and evaluate at scale on a cluster.
3. **Compare models** — one base config, per-model `-o` overrides, export to compare.
4. **Safety + VLM** — Aegis/WildGuard/garak and OCRBench/ChartQA/MMMU.

That file also contains the **Python API** (`nemo_evaluator.core.evaluate.evaluate`),
the full **`-o` override cookbook**, and **troubleshooting** (container pull, missing
env vars, timeouts, Slurm queueing, non-reproducible results).

## When to Use vs Alternatives

**Use NeMo Evaluator when:**
- Need **100+ benchmarks** from 18+ harnesses in one platform
- Running evaluations on **Slurm HPC clusters** or cloud
- Requiring **reproducible** containerized evaluation
- Evaluating against **OpenAI-compatible APIs** (vLLM, TRT-LLM, NIMs)
- Need **enterprise-grade** evaluation with result export (MLflow, W&B)

**Use alternatives instead** (sibling skills in `neuro-centrifuge/evaluation/`):
- **`lm-evaluation-harness`** skill: simpler setup for quick local, no-Docker evaluation
- **`bigcode-evaluation-harness`** skill: code-only benchmarks (HumanEval, MBPP, MultiPL-E)
- **HELM**: Stanford's broader evaluation (fairness, efficiency) — no local sibling skill
- **Custom scripts**: highly specialized one-off domain evaluation

## Supported Harnesses and Tasks

| Harness | Task Count | Categories |
|---------|-----------|------------|
| `lm-evaluation-harness` | 60+ | MMLU, GSM8K, HellaSwag, ARC |
| `simple-evals` | 20+ | GPQA, MATH, AIME |
| `bigcode-evaluation-harness` | 25+ | HumanEval, MBPP, MultiPL-E |
| `safety-harness` | 3 | Aegis, WildGuard |
| `garak` | 1 | Security probing |
| `vlmevalkit` | 6+ | OCRBench, ChartQA, MMMU |
| `bfcl` | 6 | Function calling v2/v3 |
| `mtbench` | 2 | Multi-turn conversation |
| `livecodebench` | 10+ | Live coding evaluation |
| `helm` | 15 | Medical domain |
| `nemo-skills` | 8 | Math, science, agentic |

## CLI Reference

| Command | Description |
|---------|-------------|
| `run` | Execute evaluation with config |
| `status <id>` | Check job status |
| `info <id>` | View detailed job info |
| `ls tasks` | List available benchmarks |
| `ls runs` | List all invocations |
| `export <id>` | Export results (mlflow/wandb/local) |
| `kill <id>` | Terminate running job |

For `-o` override patterns, the Python API, and troubleshooting, see
[references/workflows.md](references/workflows.md).

## Advanced Topics

- **Workflows, Python API, overrides, troubleshooting**: [references/workflows.md](references/workflows.md)
- **Multi-backend execution** (local/Slurm/Lepton): [references/execution-backends.md](references/execution-backends.md)
- **Configuration deep-dive** (Hydra composition): [references/configuration.md](references/configuration.md)
- **Adapter and interceptor system**: [references/adapter-system.md](references/adapter-system.md)
- **Custom benchmark integration**: [references/custom-benchmarks.md](references/custom-benchmarks.md)

## Requirements

- **Python**: 3.10-3.13
- **Docker**: Required for local execution
- **NGC API Key**: For pulling containers and using NVIDIA Build
- **HF_TOKEN**: Required for some benchmarks (GPQA, MMLU)
- **Version note**: current launcher is `nemo-evaluator-launcher` 0.2.6, which pins `nemo-evaluator>=0.2.0,<0.3.0`. The Python API in `references/workflows.md` (`nemo_evaluator.core.evaluate.evaluate` + `nemo_evaluator.api.api_dataclasses`) applies to that 0.2.x line. A future 0.3.0 is expected to restructure the engine entry point; always verify imports against the installed version.

## Resources

- **GitHub**: https://github.com/NVIDIA-NeMo/Evaluator
- **NGC Containers**: nvcr.io/nvidia/eval-factory/
- **NVIDIA Build**: https://build.nvidia.com (free hosted models)
- **Documentation**: https://github.com/NVIDIA-NeMo/Evaluator/tree/main/docs
