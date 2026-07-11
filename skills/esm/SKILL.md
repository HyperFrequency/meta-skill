---
name: esm
version: 0.1.0
description: >-
  Drive EvolutionaryScale's `esm` protein language models from Python. ESM3 does
  multimodal generative protein design over three tracks — sequence, structure,
  and function — via iterative masked-token generation: completion, structure
  prediction, inverse folding (sequence from a backbone), function-conditioned
  generation, and chain-of-thought refinement. ESM C produces per-residue and
  pooled embeddings for similarity, clustering, classification, and frozen
  features. Use when generating, completing, folding, or embedding protein
  sequences, or designing sequences for a structure — locally on GPU or via the
  hosted Forge API for large models and batch throughput. Do NOT use for one-shot
  single-sequence structure prediction (use `structure-prediction` / ESMFold),
  fetching precomputed structures by UniProt ID (use `alphafold-database`), 2D
  protein rendering (use `protein-diagram`), small-molecule cheminformatics (use
  `rdkit`), or non-protein sequence modeling.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "esm SDK (EvolutionaryScale); ESM3/ESM C model weights under the EvolutionaryScale Cambrian Non-Commercial License — verify terms before commercial use"
---

# ESM: Protein Language Models (ESM3 + ESM C)

## Overview

The EvolutionaryScale `esm` package ships two model families behind a single
Python SDK:

- **ESM3** — a generative model that reasons jointly over a protein's
  `sequence`, `structure`, and `function`. You give it a partially-masked
  protein and it unmasks one track at a time over `num_steps` denoising steps.
- **ESM C** — an encoder that turns a sequence into embedding vectors for
  representation tasks (similarity, clustering, classification, features).

This SKILL is a **router**: it gives the mental model, the quick-start path, and
the boundaries, then delegates deep API surface, parameters, and full workflows
to `references/`. The one object you always touch is `ESMProtein`; almost every
task is "build an `ESMProtein`, mask what you want generated, call `generate`
(ESM3) or `encode` + `logits` (ESM C)".

## When to Use This Skill

Reach for this skill when you need to:

- Generate or complete a protein **sequence**, with or without functional
  constraints.
- **Predict structure** from sequence, or run **inverse folding** — design a
  sequence for a given backbone.
- Do **chain-of-thought protein design**: iterate across sequence → structure →
  function tracks, refining a design step by step.
- Produce **protein embeddings** (per-residue or pooled) for similarity search,
  clustering, classification, or as frozen features for a downstream model.
- Run any of the above at scale via the hosted **Forge API** (7B/98B ESM3,
  `esmc-6b`) when you lack a local GPU or need batch throughput.

## When NOT to Use This Skill

- **Simple single-sequence structure prediction** with no design intent — use
  `structure-prediction` (ESMFold) for a lighter, single-purpose API.
- **Fetching an already-known structure** by UniProt ID — use
  `alphafold-database`; no model inference or GPU needed.
- **Rendering 2D protein figures** — use `protein-diagram`.
- **Small-molecule / cheminformatics** work — use `rdkit`.
- **Non-protein sequence modeling** (DNA/RNA language models, general NLP) — ESM
  is protein-specific.

## Installation and access

```bash
uv pip install esm
uv pip install flash-attn --no-build-isolation   # optional, faster attention
```

Open weights are gated on HuggingFace — run `huggingface_hub.login()` with a
read token once before the first local `from_pretrained`. For hosted models, set
a Forge token as an environment variable (never hard-code it); see
`references/forge.md`.

## Capability map

| Task | Family | Entry point | Reference |
|------|--------|-------------|-----------|
| Sequence generation / completion | ESM3 | `model.generate(..., track="sequence")` | `references/esm3-generation.md` |
| Structure prediction | ESM3 | `track="structure"` | `references/esm3-generation.md` |
| Inverse folding | ESM3 | mask sequence, `track="sequence"` | `references/esm3-generation.md` |
| Function conditioning | ESM3 | `FunctionAnnotation` + `track="function"` | `references/esm3-generation.md` |
| Embeddings / representations | ESM C | `encode` + `logits(LogitsConfig(...))` | `references/esmc-embeddings.md` |
| Hosted / large-model / batch | both | `ESM3ForgeInferenceClient` | `references/forge.md` |
| End-to-end recipes | both | design, screen, cluster | `references/workflows.md` |

## Quick start — ESM3 generation

```python
from esm.models.esm3 import ESM3
from esm.sdk.api import ESM3InferenceClient, ESMProtein, GenerationConfig

model: ESM3InferenceClient = ESM3.from_pretrained("esm3_sm_open_v1").to("cuda")

protein = ESMProtein(sequence="MPRT___KEND")            # '_' marks masked residues
protein = model.generate(protein, GenerationConfig(track="sequence", num_steps=8, temperature=0.7))
print(protein.sequence)

folded = model.generate(protein, GenerationConfig(track="structure", num_steps=len(protein.sequence)))
folded.to_pdb("prediction.pdb")
```

The local model and the Forge client share the `ESM3InferenceClient` interface,
so this code moves to hosted inference by swapping only the constructor.

## Quick start — ESM C embeddings

Request embeddings explicitly via `LogitsConfig(return_embeddings=True)` — a bare
`forward()` does not return them. The tokenizer adds start/end tokens, so the
embedding length is `L + 2`; drop those two positions before per-residue work or
pooling.

```python
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig

client = ESMC.from_pretrained("esmc_300m").to("cuda")
tensor = client.encode(ESMProtein(sequence="MPRTKEINDAGLIVHSPQWFYK"))
out = client.logits(tensor, LogitsConfig(sequence=True, return_embeddings=True))

pooled = out.embeddings[:, 1:-1, :].mean(dim=1)          # (1, hidden) fixed-size vector
```

## Model selection

- **Local dev / fine-tuning:** `esm3_sm_open_v1` (1.4B), `esmc_300m`, `esmc_600m`
  — open weights, run on a consumer GPU.
- **Production quality:** `esm3-medium-2024-08` (7B) via Forge.
- **Maximum accuracy:** `esm3-large-2024-03` (98B) or `esmc-6b` via Forge.
- **High throughput:** Forge with bounded concurrency + caching.

Local `from_pretrained` names use underscores (`esm3_sm_open_v1`, `esmc_300m`);
Forge IDs are hyphenated and dated (`esm3-medium-2024-08`). Names evolve — treat
the tables in `references/` as a starting point and confirm the current list from
the EvolutionaryScale repo README and HuggingFace organization.

## Failure modes and boundaries

- **GPU OOM** — use a smaller model, `.half()` precision,
  `torch.cuda.empty_cache()` between calls, or move to Forge. Catch
  `torch.cuda.OutOfMemoryError`.
- **Too few `num_steps`** for a long masked span gives low-quality output; scale
  steps with the number of masked positions (`≈ length // 2` for full
  generation).
- **Special tokens in embeddings** — forgetting to strip the BOS/EOS positions
  silently corrupts per-residue analysis and pooled vectors.
- **In-silico only** — generated proteins are hypotheses. Validate with
  orthogonal structure prediction and wet-lab experiments before biological
  claims.
- **Forge limits** — respect rate limits with exponential backoff on HTTP 429;
  checkpoint long batch jobs. See `references/forge.md`.

## References

- `references/esm3-generation.md` — ESM3 models, `ESMProtein`,
  `GenerationConfig`, and every generation pattern (completion, folding, inverse
  folding, function conditioning, chain-of-thought, constrained generation).
- `references/esmc-embeddings.md` — ESM C models, the correct embedding API,
  pooling, similarity/classification/clustering, and performance.
- `references/forge.md` — hosted inference: setup, concurrency, rate limits,
  retries, checkpointing, cost control, SageMaker.
- `references/workflows.md` — end-to-end recipes: de novo design, variant
  libraries, structure-based optimization, function prediction, corpus
  clustering.

## Sibling skills

- `structure-prediction` — single-sequence folding via ESMFold (simpler, no
  design).
- `alphafold-database` — retrieve precomputed structures by UniProt ID.
- `protein-diagram` — render 2D protein visualizations.
- `rdkit` — small-molecule cheminformatics.
- `umap-learn`, `scikit-learn` — dimensionality reduction and clustering for ESM
  C embedding spaces.

## Responsible use and licensing

ESM is intended for beneficial protein engineering, drug discovery, and research.
Follow the Responsible Biodesign Framework (https://responsiblebiodesign.ai/) and
weigh biosafety before experimental validation. The `esm` SDK is open source, but
ESM3 / ESM C **model weights** are released under the EvolutionaryScale Cambrian
Non-Commercial License — confirm the current terms before any commercial use.
