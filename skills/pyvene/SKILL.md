---
name: pyvene
description: Guidance for causal interventions on PyTorch models using pyvene's declarative, dict-based intervention framework. Use when conducting causal tracing (ROME-style), activation patching, interchange intervention training (IIT/DAS), model steering, or testing causal hypotheses about specific model components, and when you want to save/share intervention experiments via HuggingFace. Do NOT use for exploratory activation analysis or hooks (use TransformerLens), training/analyzing sparse autoencoders (use SAELens), or remote execution on very large models you cannot host locally (use nnsight).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Causal Intervention, pyvene, Activation Patching, Causal Tracing, Interpretability]
dependencies: [pyvene>=0.1.8, torch>=2.0.0, transformers>=4.30.0]
---

# pyvene: Causal Interventions for Neural Networks

pyvene is Stanford NLP's library for performing causal interventions on PyTorch models. It provides a declarative, dict-based framework for activation patching, causal tracing, and interchange intervention training - making intervention experiments reproducible and shareable.

- **GitHub**: [stanfordnlp/pyvene](https://github.com/stanfordnlp/pyvene)
- **Paper**: [pyvene: A Library for Understanding and Improving PyTorch Models via Interventions](https://aclanthology.org/2024.naacl-demo.16) (NAACL 2024, [arXiv:2403.07809](https://arxiv.org/abs/2403.07809))

This file is a router. Detailed recipes, the full API surface, and troubleshooting
live in `references/` (see [Reference Documentation](#reference-documentation)).

## When to Use pyvene

**Use pyvene when you need to:**
- Perform causal tracing (ROME-style localization)
- Run activation patching experiments
- Conduct interchange intervention training (IIT) or DAS
- Test causal hypotheses about model components
- Share/reproduce intervention experiments via HuggingFace
- Work with any PyTorch architecture (not just transformers)

**Consider sibling skills instead when:**
- You need exploratory activation analysis or hooks → **TransformerLens**
- You want to train/analyze SAEs → **SAELens**
- You need remote execution on massive models, or lower-level control → **nnsight**

## Installation

```bash
pip install pyvene
```

```python
import pyvene as pv
```

## Core Concepts

### IntervenableModel

The main class wraps any PyTorch model with intervention capabilities. You declare
*what* to intervene on with an `IntervenableConfig` of `RepresentationConfig`s, then
call the wrapped model with `base` and `sources`:

```python
import pyvene as pv
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

config = pv.IntervenableConfig(
    representations=[
        pv.RepresentationConfig(
            layer=8,
            component="block_output",
            intervention_type=pv.VanillaIntervention,
        )
    ]
)

intervenable = pv.IntervenableModel(config, model)
```

### Intervention Types

| Type | Description | Use Case |
|------|-------------|----------|
| `VanillaIntervention` | Swap activations between runs | Activation patching |
| `AdditionIntervention` | Add activations to base run | Steering, ablation |
| `SubtractionIntervention` | Subtract activations | Ablation |
| `ZeroIntervention` | Zero out activations | Component knockout |
| `NoiseIntervention` | Add Gaussian noise | Corruption (causal tracing) |
| `CollectIntervention` | Collect activations | Probing, analysis |
| `RotatedSpaceIntervention` | Trainable rotation | Causal discovery (IIT) |
| `LowRankRotatedSpaceIntervention` | Low-rank trainable rotation | DAS |
| `LoRAIntervention` | LoRA adapter as intervention | Steering (v0.1.8+) |

### Component Targets

```python
components = [
    "block_input",      # Input to transformer block
    "block_output",     # Output of transformer block
    "mlp_input",        # Input to MLP
    "mlp_output",       # Output of MLP
    "mlp_activation",   # MLP hidden activations
    "attention_input",  # Input to attention
    "attention_output", # Output of attention
    "attention_value_output",  # Attention value vectors
    "query_output",     # Query vectors
    "key_output",       # Key vectors
    "value_output",     # Value vectors
    "head_attention_value_output",  # Per-head values
]
```

## Workflows (in references/)

Full step-by-step recipes live in [references/workflows.md](references/workflows.md):

1. **Causal tracing (ROME-style)** - corrupt inputs, restore activations, sweep layers/positions.
2. **Activation patching for circuit analysis** - patch components, measure logit difference (IOI).
3. **Interchange intervention training (IIT) and DAS** - train rotations to find causal subspaces.
4. **Model steering** - load a pre-trained intervention and steer during generation.

Shorter single-concept walkthroughs (position-specific interventions, collecting
activations, generation) are in [references/tutorials.md](references/tutorials.md).

## Key Classes Reference

| Class | Purpose |
|-------|---------|
| `IntervenableModel` | Main wrapper for interventions |
| `IntervenableConfig` | Configuration container |
| `RepresentationConfig` | Single intervention specification |
| `VanillaIntervention` | Activation swapping |
| `RotatedSpaceIntervention` | Trainable DAS intervention |
| `CollectIntervention` | Activation collection |

Full signatures, saving/sharing, and the forward-pass contract: [references/api.md](references/api.md).

## Supported Models

pyvene works with any PyTorch model. Tested on GPT-2 (all sizes), LLaMA / LLaMA-2,
Pythia, Mistral / Mixtral, OPT, BLIP (vision-language), ESM (protein models), and
Mamba (state space).

## Troubleshooting

Common failure modes (wrong component name, dimension mismatch, memory on large
models, LoRA integration) are documented in
[references/troubleshooting.md](references/troubleshooting.md).

## Reference Documentation

| File | Contents |
|------|----------|
| [references/README.md](references/README.md) | Overview and quick start guide |
| [references/api.md](references/api.md) | Complete API reference for IntervenableModel, intervention types, configurations |
| [references/workflows.md](references/workflows.md) | End-to-end recipes: causal tracing, activation patching, IIT/DAS, steering, saving/sharing |
| [references/tutorials.md](references/tutorials.md) | Single-concept tutorials: patching, tracing, DAS, position-specific, collecting, generation |
| [references/troubleshooting.md](references/troubleshooting.md) | Common issues and fixes |

## External Resources

- [Official Docs](https://stanfordnlp.github.io/pyvene/) · [API Reference](https://stanfordnlp.github.io/pyvene/api/)
- Tutorials: [pyvene 101](https://stanfordnlp.github.io/pyvene/tutorials/pyvene_101.html) · [Causal Tracing](https://stanfordnlp.github.io/pyvene/tutorials/advanced_tutorials/Causal_Tracing.html) · [IOI Replication](https://stanfordnlp.github.io/pyvene/tutorials/advanced_tutorials/IOI_Replication.html) · [DAS Introduction](https://stanfordnlp.github.io/pyvene/tutorials/advanced_tutorials/DAS_Main_Introduction.html)
- Papers: [ROME](https://arxiv.org/abs/2202.05262) (Meng et al. 2022) · [Inference-Time Intervention](https://arxiv.org/abs/2306.03341) (Li et al. 2023) · [Interpretability in the Wild](https://arxiv.org/abs/2211.00593) (Wang et al. 2022)

## Comparison with Other Tools

| Feature | pyvene | TransformerLens | nnsight |
|---------|--------|-----------------|---------|
| Declarative config | Yes | No | No |
| HuggingFace sharing | Yes | No | No |
| Trainable interventions | Yes | Limited | Yes |
| Any PyTorch model | Yes | Transformers only | Yes |
| Remote execution | No | No | Yes (NDIF) |
