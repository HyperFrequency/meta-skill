---
name: denario
version: 0.1.0
description: >-
  Denario is a multi-agent AI system (built on AG2 + LangGraph) that automates the
  end-to-end scientific research pipeline — data description, hypothesis/idea generation,
  methodology design, computational results with figures, and a publication-ready LaTeX
  paper — driven from a small Python API (the `Denario` class) or a Streamlit GUI. Use it
  to run a project from a dataset to a formatted manuscript, generate ideas from data,
  auto-develop a methodology, execute analysis, or produce a journal-formatted paper; each
  stage is either automated (get_*) or supplied manually
  (set_*) for hybrid control. Do NOT use it for a single isolated step better served by a
  focused sibling skill — plain data analysis (`data-analysis`), only brainstorming
  hypotheses (`hypothesis-generation`), only a literature search (`literature-review`), or
  only drafting/formatting an existing paper (`scientific-writing`) — nor for production ML
  training, nor when you cannot supply Python 3.12+ and LLM provider credentials.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "GPL-3.0"
---

# Denario

## Overview

Denario (upstream: [AstroPilot-AI/Denario](https://github.com/AstroPilot-AI/Denario))
is a multi-agent system that carries a research project from a raw dataset to a
formatted manuscript. It coordinates specialized LLM agents over the AG2 and LangGraph
frameworks, running a five-stage pipeline where each stage consumes the artifact produced
by the previous one:

1. **Data description** — you state what data and tools are available.
2. **Idea** — an agent proposes a hypothesis/research question from that context.
3. **Methodology** — an agent designs the analytical approach.
4. **Results** — an execution agent writes and runs analysis code, producing statistics
   and figures.
5. **Paper** — a writing agent emits a journal-formatted LaTeX manuscript (and PDF when a
   TeX toolchain is present).

Every generative stage has a `get_*` method (let Denario produce it) and a matching
`set_*` method (supply it yourself). This is the core mental model: mix automation and
manual control freely, but respect stage ordering — a stage needs its predecessors present.

Drive it two ways: a Python API (the `Denario` class) for scripted, reproducible runs, or a
Streamlit GUI (`denario run`) for interactive use.

## When to Use This Skill

- You want an autonomous run from a described dataset all the way to a LaTeX paper.
- You want to generate a research idea or a methodology *from data*, not from a blank page.
- You want an agent to write and execute the analysis code and produce figures.
- You want to format existing findings into a journal-styled manuscript.
- You want a **hybrid** run — e.g. fix the idea yourself, auto-generate method + results.
- You want the whole pipeline as version-controllable markdown/LaTeX artifacts on disk.

## When NOT to Use This Skill

- You only need one isolated step and a focused sibling skill is a better fit:
  raw analysis → `data-analysis` or `exploratory-data-analysis`; only ideas →
  `hypothesis-generation`; only prior work → `literature-review`; only writing/formatting
  an existing paper → `scientific-writing`. Reach for Denario when you want the *stages
  wired together*.
- You want a general research orchestrator with its own experiment loops and steering —
  see `autoresearch` / `ml-autoresearch`; Denario is the pipeline engine, not the meta-loop.
- You are building a production ML training/serving pipeline — this targets research
  artifacts (papers, figures), not deployed models.
- You cannot provide Python 3.12+ and at least one LLM provider credential.
- The output must be a specific non-LaTeX format Denario does not emit.

## Installation (quick start)

```bash
uv init
uv add "denario[app]"      # the [app] extra pulls in the Streamlit GUI
```

Requires **Python 3.12+**. Paper compilation needs a LaTeX distribution (or use the Docker
image, which bundles one). For pip, source builds, Docker (`pablovd/denario:latest`, port
8501), LaTeX setup per-OS, and install troubleshooting, see
[references/installation.md](references/installation.md).

## LLM Provider Setup

Denario needs credentials for at least one LLM backend supported by AG2/LangGraph —
commonly OpenAI and Google Gemini / Vertex AI. Supply keys via environment variables or a
`.env` file loaded before import:

```python
from dotenv import load_dotenv
load_dotenv()                       # reads OPENAI_API_KEY, GOOGLE_* , etc.
from denario import Denario
```

For obtaining keys, the full Vertex AI service-account walkthrough, Docker `--env-file`
usage, cost control, and security practices, see
[references/llm-configuration.md](references/llm-configuration.md).

> Denario's exact constructor arguments for per-stage model selection vary by version and
> are configured through environment/upstream config rather than a signature I can pin
> here — confirm against upstream docs before relying on a specific model-routing argument.

## The Research Pipeline

Minimal end-to-end run:

```python
from denario import Denario, Journal

den = Denario(project_dir="./my_research")

den.set_data_description("""
Dataset: monthly global temperature anomalies (1880-2023), CSV [year, month, anomaly]
Tools: pandas, scipy, sklearn, matplotlib
Domain: climate science
Goal: quantify and characterize the long-term warming trend
""")

den.get_idea()                      # hypothesis from the data description
den.get_method()                    # methodology from idea + data
den.get_results()                   # runs analysis, writes figures
den.get_paper(journal=Journal.APS)  # journal-formatted LaTeX (+ PDF if TeX present)
```

Each call persists a markdown/LaTeX artifact into `project_dir` (`idea.md`, `methodology.md`,
`results.md`, `figures/`, `paper.tex`, ...). The **richer the data description, the better
the downstream ideas** — describe format, size, tools, domain, and known data-quality
caveats. Full method signatures, the `Journal` enum, the on-disk project layout, and
stage-ordering errors are in [references/api.md](references/api.md).

## Manual / Hybrid Control

Swap any `get_*` for its `set_*` to inject your own content (string or, for method/results,
a path to a markdown file):

```python
den.set_idea("Investigate El Niño's effect on regional temperature anomalies")
den.get_method()                    # auto method for your idea
den.set_method("methodology.md")    # ...or load your own
den.set_results("results.md")       # bring pre-computed findings
den.get_paper(journal=Journal.APS)  # use Denario purely as a formatter
```

Common patterns — fully automated, custom-idea, format-only, and iterative refinement
(re-run only downstream stages after revising an upstream one) — with worked cross-domain
examples (gene expression, churn ML, time-series forecasting, medical imaging) are in
[references/workflows.md](references/workflows.md).

## Running the GUI

```bash
denario run           # launches the Streamlit app, default http://localhost:8501
```

Same five-stage workflow, interactive. The Docker image serves the same GUI on port 8501.

## Failure Modes & Boundaries

- **Stage ordering**: `get_idea()` needs a data description; `get_results()` needs an idea
  and a method; `get_paper()` needs results. Skipping a prerequisite errors — set it
  manually or run stages in order.
- **LaTeX missing**: `get_paper()` still emits `paper.tex` but PDF compilation fails without
  a TeX toolchain. Install one or use the Docker image.
- **Cost & non-determinism**: every stage makes LLM calls; a full run can be expensive and
  results vary between runs. Review each artifact before proceeding, and version-control
  `project_dir` to track evolution.
- **Literature search**: Denario incorporates prior-work retrieval inside the idea/method
  stages; a stable, separately documented public method name for standalone literature
  search is not something I can confirm — check upstream docs rather than assuming one.
- **Python version**: 3.12+ is mandatory; older interpreters fail at import.

Install and provider-auth troubleshooting live in
[references/installation.md](references/installation.md) and
[references/llm-configuration.md](references/llm-configuration.md).

## References

- [references/installation.md](references/installation.md) — install methods, Docker, LaTeX, updates, troubleshooting.
- [references/llm-configuration.md](references/llm-configuration.md) — providers, key storage, Vertex AI setup, cost, security.
- [references/api.md](references/api.md) — `Denario` class + method reference, `Journal` enum, project layout, error handling.
- [references/workflows.md](references/workflows.md) — worked end-to-end and hybrid examples across domains.

## Attribution & License

Adapted in original wording from the openscience skill collection (Synthetic Sciences,
Apache-2.0). The wrapped library, Denario, is distributed under **GPL-3.0**; using or
redistributing Denario itself is subject to that license.
