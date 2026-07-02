---
name: lm-evaluation-harness
description: Evaluates LLMs across 60+ academic benchmarks (MMLU, HumanEval, GSM8K, TruthfulQA, HellaSwag) using EleutherAI's standardized harness. Use when benchmarking model quality, comparing models on shared metrics, reporting reproducible academic results, or tracking training progress; supports hf, vLLM, and API backends (OpenAI, Anthropic). Do NOT use for instruction-following / chat preference quality (use AlpacaEval or MT-Bench), broad responsible-AI dimensions like fairness/calibration (use HELM), pure code-generation suites with rich containerized execution (use sibling bigcode-evaluation-harness), or NeMo-native eval pipelines (use sibling nemo-evaluator).
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Evaluation, LM Evaluation Harness, Benchmarking, MMLU, HumanEval, GSM8K, EleutherAI, Model Quality, Academic Benchmarks, Industry Standard]
dependencies: [lm-eval, transformers, vllm]
---

# lm-evaluation-harness - LLM Benchmarking

EleutherAI's industry-standard harness for evaluating LLMs across 60+ academic
benchmarks with standardized prompts and metrics. Used by HuggingFace's Open LLM
Leaderboard and most model releases. This file is a router; deep detail lives in
`references/`.

## Quick start

```bash
pip install lm-eval

# List available tasks (current CLI; the old `--tasks list` is deprecated)
lm-eval ls tasks

# Evaluate a HuggingFace model on core benchmarks, 5-shot (paper-standard)
lm_eval --model hf \
  --model_args pretrained=meta-llama/Llama-2-7b-hf \
  --tasks mmlu,gsm8k,hellaswag,truthfulqa,arc_challenge \
  --num_fewshot 5 \
  --device cuda:0 \
  --batch_size auto \
  --output_path results/ \
  --log_samples
```

Results land in `results/` as JSON: `results.<task>.<metric>` (e.g.
`mmlu.acc`, `gsm8k.exact_match`, `hellaswag.acc_norm`) plus a matching
`*_stderr`. The run config (model_args, num_fewshot) is recorded for reproducibility.

## Key flags

- `--model` — backend: `hf`, `vllm`, `openai-completions`, `local-completions`,
  `anthropic-chat-completions`, `sglang`, `nemo_lm`, and more.
- `--model_args` — comma-separated, e.g. `pretrained=...,dtype=bfloat16,load_in_4bit=True`.
- `--tasks` — comma-separated task names or a group (e.g. `mmlu`, `mmlu_stem`).
- `--num_fewshot` — shots per prompt (`5` is the common paper default; `0` for speed).
- `--batch_size` — integer or `auto` (auto-detect largest that fits).
- `--output_path` / `--log_samples` — save results / per-sample predictions.
- `--confirm_run_unsafe_code` — required for tasks that execute generated Python
  (HumanEval, MBPP).

## Pick a benchmark

- Reasoning / knowledge: MMLU (57 subjects), ARC, HellaSwag, BBH, WinoGrande.
- Math: GSM8K, MATH.
- Code: HumanEval, MBPP (need `--confirm_run_unsafe_code`).
- Truthfulness: TruthfulQA.
- Fast for frequent checkpoint eval: GSM8K (~5m), HellaSwag (~10m), PIQA (~2m).
- Slow / batch only: full MMLU (~2h on a 7B).

Full catalogue with descriptions and interpretation: see references below.

## Detailed guides (references/)

- **[references/workflows.md](references/workflows.md)** — step-by-step workflows:
  standard evaluation, tracking training progress, comparing multiple models,
  the vLLM backend, plus a troubleshooting section (OOM, slow runs, mismatched
  scores, code-execution tasks).
- **[references/benchmark-guide.md](references/benchmark-guide.md)** — all 60+
  tasks: what each measures and how to read the metrics.
- **[references/custom-tasks.md](references/custom-tasks.md)** — author
  domain-specific tasks via YAML (+ Python utilities).
- **[references/api-evaluation.md](references/api-evaluation.md)** — evaluate
  OpenAI, Anthropic, and other API / OpenAI-compatible models.
- **[references/distributed-eval.md](references/distributed-eval.md)** — multi-GPU
  data-parallel and tensor/pipeline-parallel evaluation.

## When to use vs alternatives

Use lm-evaluation-harness for standardized, reproducible academic benchmarking
and cross-model comparison on shared prompts and metrics. Reach for something
else when:

- **AlpacaEval / MT-Bench** — instruction-following or multi-turn chat quality
  judged by an LLM, not fixed-answer accuracy.
- **HELM (Stanford)** — broad responsible-AI dimensions (fairness, calibration,
  efficiency, toxicity).
- **bigcode-evaluation-harness** (sibling skill) — code-generation suites needing
  rich, sandboxed multi-language execution.
- **nemo-evaluator** (sibling skill) — NVIDIA NeMo-native evaluation pipelines.
- **Custom scripts** — proprietary, domain-specific metrics not worth a task YAML.

## Hardware requirements

- GPU: NVIDIA (CUDA 11.8+); CPU works but is very slow.
- VRAM: 7B ~16GB (bf16) / ~8GB (8-bit); 13B ~28GB / ~14GB; 70B needs multi-GPU
  or quantization.
- Time (7B, single A100): HellaSwag ~10m, GSM8K ~5m, MMLU full ~2h, HumanEval ~20m.

## Resources

- GitHub: https://github.com/EleutherAI/lm-evaluation-harness
- Docs: https://github.com/EleutherAI/lm-evaluation-harness/tree/main/docs
- Open LLM Leaderboard (built on this harness):
  https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard
