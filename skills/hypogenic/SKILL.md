---
name: hypogenic
version: 0.1.0
description: Automated LLM-driven hypothesis generation and testing on tabular datasets using the `hypogenic` package (HypoGeniC / HypoRefine / Union methods). Use when you want to systematically generate and validate hypotheses about patterns in empirical labeled data (e.g. deception detection, AI-content detection, content analysis), optionally grounded in literature PDFs. NOT for manual one-off hypothesis formulation (use hypothesis-generation), NOT for open-ended creative ideation (use scientific-brainstorming), and NOT for general EDA or model interpretability (use exploratory-data-analysis / shap).
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Hypogenic

Automated, LLM-driven hypothesis generation and testing for labeled tabular/text datasets, via the open-source [`hypogenic`](https://github.com/ChicagoHAI/hypothesis-generation) package (ChicagoHAI, MIT). This SKILL.md is a router; the deep how-to lives in `references/`.

## What it does

Three method families (details in `references/methods.md`):
- **HypoGeniC** — data-driven hypothesis generation with iterative refinement (no literature needed).
- **HypoRefine** — agentic integration of literature PDFs + data.
- **Union** — `Literature∪HypoGeniC` / `Literature∪HypoRefine`, mechanistically combining literature-only hypotheses with framework output.

## When to use

- Generating + validating testable hypotheses from a labeled dataset.
- Comparing many competing hypotheses systematically by held-out accuracy/F1.
- Grounding hypotheses in research papers (HypoRefine/Union).

## When NOT to use

- Manual, single-hypothesis formulation from observations → `hypothesis-generation`.
- Open-ended creative ideation → `scientific-brainstorming`.
- Plain data profiling or feature importance → `exploratory-data-analysis`, `shap`.
- You have no labels — the framework scores hypotheses against ground-truth labels.

## Quick start

```bash
# conda env on Python 3.10 recommended by upstream
conda create --name hypogenic python=3.10 && conda activate hypogenic
pip install hypogenic                                          # API models only
git clone https://github.com/ChicagoHAI/HypoGeniC-datasets.git ./data

# adapt the example scripts (custom-task CLI lands in a later release):
python ./examples/generation.py     # build a hypothesis bank
python ./examples/inference.py       # evaluate it on the test split
```

CLI entry points for the shipped tasks: `hypogenic_generation --help`, `hypogenic_inference --help`.

> API note: there is **no** `hypogenic.BaseTask(...).generate_hypotheses()/.inference()`
> convenience API. The real Python workflow wires `BaseTask` + explicit `DefaultGeneration`,
> `DefaultInference`, `DefaultUpdate` algorithm classes — see `references/usage.md`.

## References

- `references/usage.md` — install, CLI, real Python API, dataset format, `config.yaml`, `extract_label`, literature/GROBID processing, repo layout, troubleshooting, publications.
- `references/methods.md` — HypoGeniC / HypoRefine / Union details, reported results, end-to-end workflow examples.
- `references/config_template.yaml` — complete annotated task configuration.
- `references/citations.bib` — ready-to-cite BibTeX for the framework's three source papers (HypoGeniC / HypoRefine / HypoBench).
