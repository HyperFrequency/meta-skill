---
name: llama-factory
description: Expert guidance for fine-tuning LLMs with LLaMA-Factory via its `llamafactory-cli` and zero-code WebUI (LlamaBoard). Covers SFT/PT/RM/PPO/DPO/KTO/ORPO training, LoRA/QLoRA (2-8 bit) and full/freeze tuning across 100+ models (LLaMA, Qwen, Gemma, Mistral, ChatGLM, LLaVA and other multimodal), Alpaca/ShareGPT dataset prep via dataset_info.json, LoRA merge/export, quantized export (GPTQ/AWQ), and inference/eval/API serving. Use when configuring YAML training runs, launching the WebUI, preparing custom datasets, merging adapters, or debugging LLaMA-Factory CLI errors. Do NOT use for raw HuggingFace Trainer/PEFT/TRL scripting without LLaMA-Factory, for serving frameworks (vLLM/TGI/Ollama) outside LLaMA-Factory's own inference wrappers, for pretraining-from-scratch infra, or for non-LLM model training.
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Fine-Tuning, LLaMA Factory, LLM, WebUI, No-Code, QLoRA, LoRA, Multimodal, HuggingFace, Llama, Qwen, Gemma]
dependencies: [llmtuner, torch, transformers, datasets, peft, accelerate, gradio]
---

# Llama-Factory Skill

Fine-tune large language models with LLaMA-Factory — a zero-code WebUI plus a
unified `llamafactory-cli` driven by YAML configs. Supports 100+ models, every
common training stage (pre-training, SFT, RM, PPO, DPO, KTO, ORPO), LoRA/QLoRA
(2/3/4/5/6/8-bit via AQLM/AWQ/GPTQ/LLM.int8/HQQ/EETQ), and multimodal inputs.

## When to Use This Skill

- Writing or debugging a LLaMA-Factory training/inference/eval YAML config.
- Launching the WebUI (LlamaBoard) for no-code fine-tuning.
- Preparing a custom dataset (Alpaca/ShareGPT) and wiring `dataset_info.json`.
- Merging a LoRA adapter into a base model, or exporting a quantized model.
- Choosing finetuning_type (lora/qlora/freeze/full) or a training stage.

**When NOT to use:** hand-rolling HuggingFace `Trainer`/PEFT/TRL scripts without
LLaMA-Factory; standalone serving stacks (vLLM/TGI/Ollama) outside LLaMA-Factory's
wrappers; pretraining-from-scratch infrastructure; non-LLM model training.

**Related sibling skills (`neuro-centrifuge/fine-tuning/`):** use **peft** for
direct PEFT/LoRA library scripting, **unsloth** for single-GPU 2-4x speedups and
memory savings, and **axolotl** for axolotl YAML-config tuning. Prefer this skill
when the user is specifically in LLaMA-Factory's CLI/WebUI/YAML ecosystem.

## Quick Reference

All commands use the `llamafactory-cli <subcommand> <config.yaml>` pattern. Pin
GPUs with `CUDA_VISIBLE_DEVICES` (or `ASCEND_RT_VISIBLE_DEVICES` on Ascend NPUs).

### Common Patterns

```bash
# Verify installation
llamafactory-cli version

# Launch zero-code WebUI (LlamaBoard): Train / Eval & Predict / Chat / Export
llamafactory-cli webui

# LoRA SFT from a config; override any YAML key inline
llamafactory-cli train examples/train_lora/llama3_lora_sft.yaml
llamafactory-cli train examples/train_lora/llama3_lora_sft.yaml learning_rate=1e-4

# Restrict to specific GPUs
CUDA_VISIBLE_DEVICES=0,1 llamafactory-cli train examples/train_lora/llama3_lora_sft.yaml

# Chat with a fine-tuned model (CLI or browser); use HF or vLLM backend
llamafactory-cli chat examples/inference/llama3_lora_sft.yaml
llamafactory-cli webchat examples/inference/llama3_lora_sft.yaml

# Serve an OpenAI-style API (default port adjustable via API_PORT)
API_PORT=8000 CUDA_VISIBLE_DEVICES=0 llamafactory-cli api examples/inference/llama3_lora_sft.yaml

# Merge LoRA adapter into the base model (use an UNQUANTIZED base; no quantization_bit)
llamafactory-cli export examples/merge_lora/llama3_lora_sft.yaml

# Benchmark eval (mmlu_test / ceval_validation / cmmlu_test) and NLG (BLEU/ROUGE)
llamafactory-cli eval examples/train_lora/llama3_lora_eval.yaml
llamafactory-cli train examples/extras/nlg_eval/llama3_lora_predict.yaml

# Fast batch inference with vLLM
python scripts/vllm_infer.py --model_name_or_path path_to_merged_model --dataset alpaca_en_demo
```

### Key config fields (YAML)

- `model_name_or_path` — base model (HF id or local path); must match `template`.
- `template` — chat template; must correspond to the model (e.g. `llama3`, `qwen`).
- `stage` — `pt` | `sft` | `rm` | `ppo` | `dpo` | `kto` | `orpo`.
- `finetuning_type` — `lora` | `freeze` | `full`; `quantization_bit` enables QLoRA.
- `lora_target` — target modules for LoRA (default `all`).
- `dataset` — name(s) registered in `data/dataset_info.json`.
- `adapter_name_or_path` — adapter dir (= training `output_dir`) for inference/merge.
- `infer_backend` — `huggingface` (default) or `vllm`.
- Export quantization: `export_quantization_bit`, `export_quantization_dataset`,
  `export_size`, `export_legacy_format`.
- Training knobs: `per_device_train_batch_size`, `gradient_accumulation_steps`,
  `learning_rate`, `lr_scheduler_type` (`linear`/`cosine`/`polynomial`/`constant`).

### Gotchas

- Custom datasets MUST be declared in `data/dataset_info.json` (Alpaca or ShareGPT
  format) or training fails. ShareGPT: `human`/`observation` on odd turns,
  `gpt`/`function` on even turns. Pretraining does not support ShareGPT.
- When merging LoRA, do NOT pass a quantized base model or set `quantization_bit`.
- Multimodal data: `images`/`videos`/`audios` count must exactly match the
  `<image>`/`<video>`/`<audio>` tags in the text.
- On Windows, QLoRA and FlashAttention-2 need CUDA-matched `bitsandbytes` /
  `flash-attention` wheels.

## Reference Files

Detailed documentation lives in `references/` (sourced from the official docs at
https://llamafactory.readthedocs.io):

- **getting_started.md** — installation, WebUI, data prep, SFT, merge, inference, eval.
- **advanced.md** — distributed training, advanced optimizers (GaLore, BAdam, DoRA,
  LongLoRA, LoRA+, LoftQ, PiSSA), acceleration, and stage-specific guidance.
- **other.md** — framework overview and feature matrix.
- **_images.md** — figures referenced by the docs.
- **index.md** — category index for the reference set.

Read the relevant reference file with `view` when you need full parameter tables
or end-to-end walkthroughs.
