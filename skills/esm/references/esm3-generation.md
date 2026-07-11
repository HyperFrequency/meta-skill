# ESM3 Generation Reference

ESM3 is a multimodal generative protein language model. It reasons jointly over
three **tracks** — `sequence`, `structure`, and `function` — using iterative
masked-token generation: you supply a partially-masked protein, and each call
unmasks tokens on one track over `num_steps` denoising steps.

## Models

Local `from_pretrained` names use underscores; Forge model IDs are hyphenated
and dated. Names change over time — treat this table as a starting point and
confirm the current list from the EvolutionaryScale repo README and the
HuggingFace `EvolutionaryScale` organization.

| Model | Params | Access | Notes |
|-------|--------|--------|-------|
| `esm3_sm_open_v1` (local) / `esm3-small-2024-08` (Forge) | 1.4B | Open weights + Forge | Dev, prototyping, fine-tuning |
| `esm3-medium-2024-08` | 7B | Forge only | Balanced production default |
| `esm3-large-2024-03` | 98B | Forge only | Highest quality |
| `esm3-medium-multimer-2024-09` | 7B | Forge only | Protein complexes (experimental) |

Open weights are gated on HuggingFace — run `huggingface_hub.login()` with a
read token once before the first `from_pretrained` call.

## Load a local model

```python
from esm.models.esm3 import ESM3
from esm.sdk.api import ESM3InferenceClient, ESMProtein, GenerationConfig

model: ESM3InferenceClient = ESM3.from_pretrained("esm3_sm_open_v1").to("cuda")
```

The same `ESM3InferenceClient` interface is implemented by the local model and
by the Forge client (see `forge.md`), so generation code is portable between
them.

## ESMProtein

The central object. Every field is optional; unset tracks are treated as fully
masked and become generation targets.

```python
protein = ESMProtein(
    sequence="MPRT___KEND",          # '_' = masked residue to generate
    coordinates=coords,               # (L, 37, 3) atom coordinates, optional
    function_annotations=[...],       # list[FunctionAnnotation], optional
    secondary_structure="CCHHHEEE",   # H/E/C string, optional
    sasa=sasa_values,                 # per-residue solvent accessibility, optional
)

protein = ESMProtein.from_pdb("input.pdb")   # load structure + sequence from PDB
protein.to_pdb("output.pdb")                  # write predicted structure to disk
```

Masking conventions on the `sequence` track:

- `"MPRT______END"` — generate the masked span, keep the flanks fixed.
- `"_" * 200` — generate a 200-residue protein from scratch.
- Set `protein.sequence = None` to mask the whole sequence track (e.g. for
  inverse folding, where you keep `coordinates` and regenerate `sequence`).

## GenerationConfig

```python
config = GenerationConfig(
    track="sequence",     # "sequence" | "structure" | "function"
    num_steps=8,          # iterative unmasking steps
    temperature=0.7,      # 0.0 greedy .. ~1.0 diverse
    top_p=1.0,            # nucleus sampling cutoff
)
protein = model.generate(protein, config)
```

Parameter guidance:

- **num_steps** — more steps generally means higher quality and slower runtime.
  A common heuristic for full generation is `num_steps ≈ len(sequence) // 2`;
  short infills need only a handful of steps.
- **temperature** — 0.0 is deterministic (greedy); 0.5–0.7 balances quality and
  novelty; near 1.0 maximizes diversity at some cost to quality. Anneal from
  high to low across successive `generate` calls for design-then-refine loops.
- **top_p** — restricts sampling to the top probability mass; combine with
  temperature for controlled diversity.

The `GenerationConfig` class may expose additional structure-conditioning flags
in your installed version — inspect its signature rather than assuming, since
these have changed across releases.

## Common patterns

### Sequence completion

```python
protein = ESMProtein(sequence="MPRTK____LIVHSP____END")
completed = model.generate(protein, GenerationConfig(track="sequence", num_steps=12, temperature=0.5))
```

### Structure prediction (sequence -> coordinates)

```python
protein = ESMProtein(sequence="MPRTKEINDAGLIVHSPQWFYK")
folded = model.generate(protein, GenerationConfig(track="structure", num_steps=len(protein.sequence)))
folded.to_pdb("predicted.pdb")     # folded.coordinates holds the 3D atoms
```

### Inverse folding (structure -> sequence)

```python
target = ESMProtein.from_pdb("target.pdb")
target.sequence = None             # mask the sequence, keep the backbone
designed = model.generate(target, GenerationConfig(track="sequence", num_steps=50, temperature=0.7))
```

### Function-conditioned generation

```python
from esm.sdk.api import FunctionAnnotation

protein = ESMProtein(
    sequence="_" * 150,
    function_annotations=[FunctionAnnotation(label="enzymatic_activity", start=30, end=90)],
)
functional = model.generate(protein, GenerationConfig(track="sequence", num_steps=75, temperature=0.6))
```

### Chain-of-thought (multi-track)

Generate one track, then condition the next track on the result. This mimics the
model's own iterative reasoning and produces more self-consistent designs than a
single all-tracks-at-once pass.

```python
protein = ESMProtein(sequence="MPRT" + "_" * 100)
protein = model.generate(protein, GenerationConfig(track="sequence",  num_steps=50, temperature=0.6))
protein = model.generate(protein, GenerationConfig(track="structure", num_steps=50))
protein = model.generate(protein, GenerationConfig(track="function",  num_steps=20))
```

### Constrained generation (fix an active site)

Mask everything except positions you want preserved, then regenerate the rest.

```python
def mask_except(sequence, keep_positions):
    residues = ["_"] * len(sequence)
    for i in keep_positions:
        residues[i] = sequence[i]
    return "".join(residues)

fixed = ESMProtein(sequence=mask_except(original, active_site=[23, 24, 25, 45, 46, 89]))
result = model.generate(fixed, GenerationConfig(track="sequence", num_steps=50))
```

### Variant library

```python
import numpy as np

variants = []
for _ in range(10):
    residues = list(base_sequence)
    for i in np.random.choice(len(residues), size=5, replace=False):
        residues[i] = "_"
    v = model.generate(ESMProtein(sequence="".join(residues)),
                       GenerationConfig(track="sequence", num_steps=8, temperature=0.8))
    variants.append(v.sequence)
```

## Failure modes and performance

- **GPU OOM** — use a smaller model, `.half()` precision, call
  `torch.cuda.empty_cache()` between generations, or move to Forge. Catch
  `torch.cuda.OutOfMemoryError` and fall back.
- **Invalid inputs** — malformed sequences (non-standard residue letters) or
  mismatched coordinate lengths raise `ValueError`; validate before calling.
- **Under-stepping** — too few `num_steps` for a long masked span yields
  low-quality output; scale steps with the number of masked positions.
- **In-silico only** — generated sequences are hypotheses. Validate with
  structure prediction, orthogonal folding tools, and wet-lab experiments before
  drawing biological conclusions.

## Citation

Hayes, T. et al. (2025). *Simulating 500 million years of evolution with a
language model.* Science. DOI: 10.1126/science.ads0018
