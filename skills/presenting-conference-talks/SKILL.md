---
name: presenting-conference-talks
description: Generates conference presentation slides (Beamer LaTeX PDF and editable PPTX) from a compiled paper, with speaker notes and an optional talk script. Use when preparing oral, spotlight, poster, or invited talks for ML and systems conferences (NeurIPS, ICML, OSDI, SOSP, ASPLOS, NSDI). Routes to references/ for slide structures, Beamer/PPTX templates, and delivery guidance. NOT for writing the paper itself (use ml-paper-writing / systems-paper-writing) or for creating publication-quality plots (use academic-plotting).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [Presenting Conference Talks, Beamer, PPTX, Slides, Speaker Notes, OSDI, SOSP, ASPLOS, NeurIPS, ICML]
dependencies: [python-pptx>=0.6.21]
---

# Presenting Conference Talks: From Paper to Slides

Generate conference presentation slides from a compiled research paper. Produces both
**Beamer LaTeX PDF** (polished typesetting) and **editable PPTX** (last-minute adjustments),
with speaker notes and an optional talk script.

This SKILL.md is a router. Detailed slide outlines, full Beamer/PPTX code, and delivery
guidance live in `references/` — load them when you reach the relevant step.

## When to Use This Skill

| Scenario | Use This Skill | Use Other Skills Instead |
|----------|---------------|--------------------------|
| Preparing oral/spotlight/poster/invited talk slides | yes | |
| Generating Beamer PDF + PPTX from a paper | yes | |
| Speaker notes and talk script | yes | |
| Writing the paper itself | | ml-paper-writing |
| Structuring a systems paper | | systems-paper-writing |
| Creating publication-quality plots | | academic-plotting |

## Talk Types and Slide Counts

| Talk Type | Duration | Slides | Content Depth |
|-----------|----------|--------|---------------|
| poster-talk | 3–5 min | 5–8 | Problem + key result only |
| spotlight | 5–8 min | 8–12 | Problem + approach + key results |
| oral | 15–20 min | 15–22 | Full story with evaluation highlights |
| invited | 30–45 min | 25–40 | Deep dive with context and demos |

**Rule of thumb**: ~1 slide per minute for oral, ~1.5 slides per minute for spotlight.

## Workflow

1. **Content extraction** — Read the compiled paper (PDF or LaTeX). Identify thesis,
   contributions, architecture figure, and key eval figures. Note talk type and duration.
2. **Outline** — Pick the matching slide structure from
   [references/slide-structures.md](references/slide-structures.md) and map paper sections to
   slide groups, allocating time per group.
3. **Slide generation** — Generate Beamer source slide by slide using the templates in
   [references/slide-templates.md](references/slide-templates.md); add speaker notes per slide;
   copy paper figures into `slides/figures/`; generate the python-pptx script for the PPTX version.
4. **Review and polish** — Confirm slide count matches duration; verify figures are readable at
   presentation resolution; compile (`latexmk -pdf slides.tex`) and run the PPTX script
   (`python3 generate_slides.py`); review notes for timing and transitions. Work through the
   checklist in [references/delivery-guide.md](references/delivery-guide.md).

## References

- [references/slide-structures.md](references/slide-structures.md) — Per-talk-type slide outlines
  (poster, spotlight, oral, invited).
- [references/slide-templates.md](references/slide-templates.md) — Complete Beamer template code
  and python-pptx generation script.
- [references/delivery-guide.md](references/delivery-guide.md) — Systems-talk specifics, speaker
  notes (Mike Dahlin's layered approach), color schemes, checklist, and troubleshooting.
- Mike Dahlin, "Giving a Conference Talk" — https://www.cs.utexas.edu/~dahlin/professional/goodTalk.pdf

**Attribution**: Structure draws inspiration from the ARIS paper-slides skill (poster/spotlight/
oral/invited with Beamer+PPTX). This is an independent implementation for the
AI-Research-SKILLs ecosystem.
