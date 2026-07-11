---
name: paper-2-web
version: 0.1.0
description: >-
  Drive the Paper2All autonomous pipeline (Paper2Web + Paper2Video + Paper2Poster)
  to turn a finished academic paper — LaTeX source or PDF — into dissemination
  assets: an interactive, layout-aware project website; a narrated presentation
  video (generated slides, TTS narration, cursor motion, optional Hallo2
  talking-head); and a print-ready conference poster at any size. Use when
  preparing conference or promotional materials for an existing paper — a
  companion homepage, a video abstract, a poster-session poster, a social clip,
  or a full package — and you want an LLM-driven pipeline rather than hand
  authoring. Do NOT use to write or edit the paper itself (use `scientific-writer`),
  to hand-craft one poster or slide deck with fine layout control (use
  `latex-posters`, `pptx-posters`, or `scientific-slides`), or to render a single
  standalone diagram (use `scientific-schematics`). Requires a completed paper as
  input plus an external LLM API key (and a large GPU for talking-head video).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Paper2All upstream (github.com/YuhangChen1/Paper2All) publishes no explicit LICENSE as of 2026-07 — treat as all-rights-reserved and confirm terms before redistributing outputs or code"
---

# Paper2All: Paper to Website, Video, and Poster

## Overview

Paper2All (`github.com/YuhangChen1/Paper2All`, arXiv 2510.15842 *"Paper2Web: Let's Make Your Paper Alive!"*) is an autonomous, LLM-driven pipeline that turns a completed academic paper — LaTeX source or PDF — into three dissemination assets:

- **Paper2Web** — an interactive, layout-aware project homepage (not a flat HTML dump of the PDF).
- **Paper2Video** — a narrated presentation video: generated slides, text-to-speech narration, simulated cursor motion, and an optional talking-head (via Hallo2).
- **Paper2Poster** — a print-ready conference poster at custom dimensions.

This skill routes you through choosing components, preparing input, running the pipeline, and reviewing output. It **orchestrates an external tool** — it does not reimplement the underlying models. Expect to supply an LLM API key (OpenAI or OpenRouter) and, for talking-head video, a large NVIDIA GPU.

Paper2All wraps three separately-published component projects (Paper2Web, `showlab/Paper2Video`, Paper2Poster). Their capabilities and flags evolve independently, so **treat the exact command surface below as version-dependent and confirm it against `--help`** (see the caveat under "Run the pipeline").

## When to Use This Skill

- You have a **finished** paper and want a companion **project website** for a preprint (arXiv/bioRxiv), lab page, or permanent showcase.
- You need a **video abstract** or full **presentation video** for a conference talk, journal multimedia submission, course, or social media.
- You need a **print-ready poster** for a poster session or symposium.
- You want a **complete promotional package** (website + poster + video) for a major submission.
- You are **batch-processing** several papers into dissemination assets at once.

Trigger phrases: "convert this paper to a website", "make a video presentation / video abstract from my paper", "generate a conference poster from my LaTeX", "build promotional materials for this paper".

## When NOT to Use This Skill

- **To write or revise the paper itself** → use `scientific-writer` / `scientific-writing`. This skill assumes the science is done.
- **To hand-author one poster or slide deck with fine layout control** → use `latex-posters`, `pptx-posters`, or `scientific-slides`. Paper2All auto-generates; those give you a source you fully control.
- **To render a single standalone diagram** (architecture, pipeline, pathway) → use `scientific-schematics`.
- **To produce a data plot/chart** → use `scientific-visualization` or `matplotlib`/`seaborn`.
- **When you have no completed paper**, only an idea or partial draft — there is nothing to disseminate yet.
- **When you cannot supply an LLM API key**, or need a talking-head video but have no suitable GPU (Hallo2 is GPU-heavy).

## Choose Components

Pick the smallest set that meets the need — each component is independent.

| Need | Component | Notes |
| --- | --- | --- |
| Permanent online presence | Paper2Web | Fastest, most versatile. Deploy to GitHub Pages / Netlify / uni server. |
| Poster-session material | Paper2Poster | Specify exact print dimensions. |
| Oral talk / video abstract / social clip | Paper2Video | Set target duration; talking-head is optional and GPU-heavy. |
| Full submission package | all three | Longest run; generate website first if on a deadline. |

Deadline priority when time is short: **website → poster → video** (video is slowest and can follow later).

## Prepare Input

Prefer **LaTeX source** over PDF — it yields cleaner structure, figure, and equation extraction. One paper per directory:

```
paper_name/
├── main.tex            # main file (or paper.pdf)
├── sections/           # optional split sections
├── figures/            # vector (PDF/SVG/EPS) or 300+ DPI rasters
├── tables/
└── bibliography.bib
```

For batch runs, place each paper in its own subdirectory under one input root. Ensure LaTeX **compiles** (`pdflatex main.tex`) before running — parsing failures usually trace back to a broken build or missing referenced file. Full input rules, PDF caveats, and output-tree layout are in `references/setup-and-usage.md`.

## Run the Pipeline

> **Verify the flags first.** Flag names and, in particular, the meaning of `--model-choice` differ across Paper2All versions and even between docs (some treat it as a model preset, the upstream repo as component selection). Always run `python pipeline_all.py --help` and trust that output over any table here.

Corroborated entry points:

```bash
# Combined pipeline (website / poster / PR materials)
python pipeline_all.py --input-dir <paper_dir> --output-dir <out_dir> [--model-choice N] \
  [--poster-width-inches W --poster-height-inches H] [--pdf-path <file.pdf>]

# Video pipeline (lives under the Paper2Video component)
python pipeline_light.py --model_name_t <text_model> --model_name_v <visual_model> \
  --result_dir <out_dir> --paper_latex_root <paper_dir>
```

Per-component flags, the full documented (but version-dependent) flag set, install steps, API-key config, GPU requirements, batch loops, and worked end-to-end examples live in the references — do not guess flags from memory.

## Component References

- **`references/paper2web.md`** — website generation: layout-aware sections, interactive figures/citations, logo discovery, quality metrics, limitations.
- **`references/paper2video.md`** — video generation: the slide → subtitle → speech → cursor → (optional Hallo2 talking-head) module chain, pacing, voices, GPU needs, troubleshooting.
- **`references/paper2poster.md`** — poster generation: standard sizes, templates, color/typography, QR codes, print/CMYK prep, review checklist.
- **`references/setup-and-usage.md`** — installation, environment/API keys, the full flag surface with caveats, output structure, resource/time/cost estimates, batch processing, and worked examples.

## Review Before Shipping

The pipeline runs automated checks, but **always review outputs manually** — LLM extraction can drop or distort content:

- **Website**: verify figures render, links resolve, and it is mobile-responsive.
- **Poster**: confirm text is readable from 3–6 ft, colors print correctly, no overflow, QR codes resolve.
- **Video**: watch it end to end for audio/slide sync, figure legibility, and narration accuracy.
- **Everywhere**: spot-check that equations and key numbers survived extraction intact — this is the most common failure mode. Consider adding a `scientific-schematics` diagram where a concept reads better as a figure.

## Known Boundaries

- **Complex equations** and multi-column PDF layouts extract imperfectly — prefer LaTeX input and review math closely.
- **Large papers (>50 pp.)** need longer runs and may require trimming sections to the essentials.
- **Talking-head video** (Hallo2) needs a large GPU and a reference image/clip; skip it if unavailable.
- **License**: Paper2All ships no explicit LICENSE upstream (as of 2026-07). Treat the code as all-rights-reserved and confirm terms before redistributing it or the generated assets.
