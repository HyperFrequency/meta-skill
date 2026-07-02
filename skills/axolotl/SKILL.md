---
name: axolotl
description: Expert guidance for fine-tuning LLMs with Axolotl — the YAML-config-driven trainer wrapping HuggingFace/PEFT/Accelerate/DeepSpeed. Use WHEN authoring or debugging Axolotl YAML configs, picking LoRA/QLoRA/full fine-tuning, running preference tuning (DPO/KTO/ORPO/GRPO/SIMPO), scaling across GPUs (FSDP2, tensor/context/sequence parallelism, DeepSpeed), wiring datasets/prompt strategies, multimodal fine-tuning, or launching on Modal/cloud. Use WHEN-NOT for non-Axolotl trainers — reach for the sibling `unsloth` (single-GPU speed/VRAM), `llama-factory` (alt YAML/GUI trainer), or `peft` (raw PEFT/transformers loops) skills instead; not for inference serving, RL environments, or data prep unrelated to Axolotl tokenization.
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Fine-Tuning, Axolotl, LLM, LoRA, QLoRA, DPO, KTO, ORPO, GRPO, YAML, HuggingFace, DeepSpeed, Multimodal]
dependencies: [axolotl, torch, transformers, datasets, peft, accelerate, deepspeed]
---

# Axolotl Skill

Router for fine-tuning LLMs with [Axolotl](https://github.com/axolotl-ai-cloud/axolotl):
a YAML-config-driven trainer on top of HuggingFace Transformers, PEFT, Accelerate
and DeepSpeed. You write one config; `axolotl train config.yaml` runs it.

## When to use

- Authoring or debugging an Axolotl **YAML config**.
- Choosing a fine-tuning method: full FT, **LoRA/QLoRA**, or preference tuning
  (**DPO/KTO/ORPO/GRPO/SIMPO**).
- **Scaling** a run across GPUs: FSDP2, DeepSpeed, tensor / context / sequence
  parallelism.
- Wiring **datasets** and prompt/tokenization strategies, including multimodal.
- Launching on **Modal** or other cloud backends.

### When NOT to use (sibling skills)

- `unsloth` — single-GPU fine-tuning optimized for speed and low VRAM.
- `llama-factory` — alternative YAML/GUI fine-tuning framework.
- `peft` — hand-rolled PEFT + `transformers.Trainer` loops (no Axolotl).
- `distributed-training` / `optimize-for-gpu` — general multi-GPU/perf concerns
  beyond Axolotl config.
- Not for inference/serving, RL environment design, or generic data prep.

## How to answer with this skill

1. Skim the **patterns** below for the common config knobs.
2. For a specific config key, full API signature, or dataset shape, open the
   matching reference file rather than guessing — Axolotl's config surface is
   large and version-sensitive.

## Common patterns (quick orientation)

Each is explained with context in `references/patterns.md`:

- **FSDP2** (`fsdp_version: 2`) — shard a model too big for one GPU.
- **Context/sequence parallelism** (`context_parallel_size: N`) — split each
  sequence across N GPUs to scale context length; N must divide total GPU count.
  Lowers batches/step, so adjust gradient accumulation.
- **Compressed checkpoints** (`save_compressed: true`) — ~40% less disk, still
  vLLM/llmcompressor compatible.
- **NCCL bandwidth check** (`all_reduce_perf`) — rule out interconnect before
  blaming Axolotl for slow multi-GPU runs.
- **Custom integrations/plugins** — any importable package; registered in
  `plugins:`.
- **Custom prompt strategies** — must handle single (`list[int]`) and batched
  (`list[list[int]]`) `input_ids`.
- Key API entry points: `core.trainers.base.AxolotlTrainer`,
  `prompt_strategies.input_output.RawInputOutputPrompter`,
  `cli.cloud.modal_.ModalCloud`.

## Reference files

- `references/patterns.md` — annotated common patterns (start here).
- `references/api.md` — full API reference (~150 pages of signatures).
- `references/dataset-formats.md` — supported dataset/prompt formats.
- `references/other.md` — guides, tutorials, integrations, and everything else.
- `references/index.md` — page-count index of the above.

## Notes

- Originally generated from official Axolotl documentation; patterns curated and
  cross-checked against the upstream config reference.
- Reference files preserve source structure, examples, and links to the docs.
- To refresh: re-scrape upstream docs and rebuild the `references/` set.
</content>
