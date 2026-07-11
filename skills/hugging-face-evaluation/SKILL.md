---
name: hugging-face-evaluation
version: 0.1.0
description: >-
  Publish and manage structured evaluation results in Hugging Face model-card
  metadata (the Papers-with-Code model-index format) with the huggingface_hub
  library. Use when adding benchmark scores (MMLU, GSM8K, HumanEval, GPQA, ARC,
  HellaSwag) to a model card so they render in the eval widget and feed
  leaderboards, when lifting an eval table already written in a README into
  model-index YAML, when importing scores from the Artificial Analysis API, or
  when running your own benchmarks with lighteval or inspect-ai (vLLM/accelerate
  backends, locally or on HF Jobs) and writing the numbers back. NOT for
  training or fine-tuning models, NOT for building a standalone leaderboard app,
  and NOT for non-Hugging-Face model registries — this skill only manages eval
  metadata on HF model cards and drives the tools that produce those scores.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "huggingface_hub Apache-2.0; lighteval MIT; inspect-ai MIT"
---

# Hugging Face Evaluation Results

## Overview

A Hugging Face model card can carry machine-readable evaluation results in its
YAML frontmatter under a `model-index` key. The Hub renders these as the model
page's evaluation widget, and downstream tools (leaderboards, Papers with Code)
read the same structure. This skill covers the four ways to populate that
metadata:

1. **Author results directly** with `huggingface_hub` (`ModelCard` +
   `model-index`), pushing to the Hub or opening a pull request.
2. **Extract** an evaluation table already written into a README and convert it
   to model-index YAML.
3. **Import** benchmark scores from the Artificial Analysis API.
4. **Run** your own benchmarks with `lighteval` or `inspect-ai` (vLLM /
   accelerate backends, locally or on HF Jobs), then write the scores back.

The model-index schema is the single source of truth for all four paths; read
`references/model-index-format.md` first if the format is unfamiliar.

## When to Use This Skill

- You have benchmark numbers for a model and want them on the HF model card in a
  structured, leaderboard-readable form (not just a markdown table).
- A README already lists scores in a table and you want them promoted into the
  card's `model-index` metadata.
- You want to pull published scores for a frontier model from Artificial
  Analysis and attach them to a mirror/derivative repo.
- You need to actually produce the scores — run MMLU, GSM8K, HumanEval, etc. —
  before publishing them.
- You are contributing eval results to a model you do not own and need to open a
  clean pull request.

## When NOT to Use This Skill

- **Training, fine-tuning, or SFT/RLHF** — this skill only records and produces
  eval numbers, it does not train. Use `transformers` / `pytorch-lightning`.
- **Building a leaderboard UI or aggregation service** — this writes per-model
  card metadata, not a ranking app.
- **Non-Hugging-Face registries** (internal MLflow, W&B model registries, etc.)
  — the metadata format and APIs here are HF-specific.
- **Statistical comparison of two models' eval deltas** — compute significance
  with `statistical-analysis`; this skill just stores the point estimates.

## Prerequisites

- `pip install huggingface_hub` (for card read/write). Add `markdown-it-py`
  and `pyyaml` for README table extraction, `requests` for the Artificial
  Analysis import.
- `HF_TOKEN` env var with **write** access for pushing cards or opening PRs.
- `AA_API_KEY` env var for the Artificial Analysis import.
- For running benchmarks: `lighteval[vllm,accelerate]` or `inspect-ai` +
  `inspect-evals`, plus a GPU (or an HF Jobs flavor). These are heavy; install
  only for the run path.

Prefer `uv run` for the benchmark scripts so PEP 723 dependency headers resolve
per-invocation instead of polluting your environment.

## The model-index Format (at a glance)

```yaml
model-index:
  - name: My-Model-7B          # plain text, exact model name, no markdown
    results:
      - task:
          type: text-generation
        dataset:
          name: MMLU
          type: mmlu
        metrics:
          - name: MMLU (5-shot)
            type: mmlu
            value: 68.4
        source:
          name: lighteval
          url: https://huggingface.co/My-Model-7B
```

Full schema, the `huggingface_hub` write APIs, merge/validation rules, and the
benchmark→`type` mapping table live in `references/model-index-format.md`.

## Capability 1 — Author and publish results

Load the card, set or merge `model-index`, then push or open a PR. In outline:

```python
from huggingface_hub import ModelCard
card = ModelCard.load("user/model", token=HF_TOKEN)
card.data["model-index"] = [{"name": "model", "results": results}]
card.push_to_hub("user/model", token=HF_TOKEN, create_pr=True)
```

Merge carefully so you never clobber existing results, and validate the schema
before pushing. See `references/model-index-format.md` for the merge routine,
the higher-level `EvalResult` helper, and validation.

## Capability 2 — Extract results from a README table

Parse the README with a GFM-aware markdown parser, detect whether the table is
"benchmarks-as-rows" or transposed ("models-as-rows"), match the target model
by exact normalized-token comparison, preview the YAML, then apply. The
model-matching algorithm (which avoids grabbing a neighbor model's or a
checkpoint's column) and the full extraction workflow are in
`references/readme-extraction.md`.

Always preview the generated YAML against the source table before writing.

## Capability 3 — Import from Artificial Analysis

Fetch a model's published scores from the Artificial Analysis v2 API
(`x-api-key` header), map its `evaluations` object to model-index metrics, and
attach them with source attribution. Endpoint, auth, response shape, and the
mapping code are in `references/artificial-analysis.md`.

## Capability 4 — Run your own benchmarks

Produce the scores with either framework, then feed the numbers into Capability
1:

- **lighteval** (HF's eval library) — task syntax `suite|task|num_fewshot`,
  e.g. `leaderboard|mmlu|5`; vLLM or accelerate backend.
- **inspect-ai** (UK AISI) — task names like `mmlu`, `gsm8k`, `humaneval`;
  vLLM or HF Transformers backend, tensor parallelism for large models.

Both run standalone on a local GPU or as an HF Job via `hf jobs uv run`. Task
catalogs, backend flags, hardware-sizing table, and OOM / trust-remote-code /
chat-template troubleshooting are in `references/running-benchmarks.md`.

## Safety — check for existing PRs before opening one

Before opening a PR against a model you do not own, list open discussions/PRs so
you do not spam maintainers with a duplicate:

```python
from huggingface_hub import get_repo_discussions
open_prs = [d for d in get_repo_discussions("owner/model")
            if d.is_pull_request and d.status == "open"]
```

If open PRs already exist, surface their URLs to the user and only proceed on
explicit confirmation. (The Hub also exposes this via
`GET https://huggingface.co/api/models/{repo_id}/discussions`.)

## Related skills

- `transformers` — load, run, and generate from the models you are evaluating.
- `statistical-analysis` — test whether an eval delta between two models is
  significant before you claim an improvement.

## References

- `references/model-index-format.md` — full schema, `huggingface_hub` write/
  merge/validate APIs, benchmark→type mapping.
- `references/readme-extraction.md` — table parsing + model-matching algorithm
  and the preview-then-apply workflow.
- `references/artificial-analysis.md` — AA v2 API endpoint, auth, response shape,
  mapping.
- `references/running-benchmarks.md` — lighteval / inspect-ai task catalogs,
  vLLM & HF Jobs, hardware sizing, troubleshooting.
