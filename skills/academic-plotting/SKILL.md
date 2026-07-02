---
name: academic-plotting
description: Generates publication-quality figures for ML/AI conference papers from research context. WHAT - extracts system components/relationships from a paper section to produce architecture diagrams via Gemini image generation, and auto-selects chart type from results/data to produce data-driven figures via matplotlib/seaborn. WHEN - creating any figure (architecture diagram, training curve, ablation bar, heatmap, leaderboard, scaling law) for NeurIPS/ICML/ICLR/ACL/AAAI submissions. WHEN NOT - interactive/web dashboards (use Plotly), LaTeX-native vector diagrams you want to hand-edit (use TikZ/draw.io/Mermaid), posters (use latex-posters), slides (use scientific-slides), or general non-paper plotting (use the matplotlib/seaborn skills directly).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Academic Writing, Visualization, Matplotlib, Seaborn, Plotting, Figures, Diagrams, NeurIPS, ICML, ICLR, LaTeX]
dependencies: [matplotlib>=3.8.0, seaborn>=0.13.0, numpy, google-genai>=1.0.0]
---

# Academic Plotting for ML Papers

Generate publication-quality figures for ML/AI conference papers. This SKILL.md is a router;
detailed style blocks, prompt templates, and runnable code live in `references/`.

Two distinct workflows:

1. **Diagram figures** (architecture, system design, workflows, pipelines) — AI image generation via Gemini → [references/diagram-generation.md](references/diagram-generation.md)
2. **Data figures** (line, bar, scatter, heatmap, ablations) — matplotlib/seaborn → [references/data-visualization.md](references/data-visualization.md)

Cross-cutting venue dimensions, LaTeX integration, fonts, accessibility → [references/style-guide.md](references/style-guide.md)

## When to Use Which Workflow

| Figure Type | Tool | Why |
|-------------|------|-----|
| Architecture / system diagram | Gemini (Workflow 1) | Complex spatial layouts with boxes, arrows, labels |
| Workflow / pipeline / lifecycle | Gemini (Workflow 1) | Multi-step processes with connections |
| Bar / line / scatter | matplotlib (Workflow 2) | Precise numerical data, reproducible |
| Heatmap / confusion matrix | matplotlib/seaborn (Workflow 2) | Structured grid data |
| Ablation as chart | matplotlib (Workflow 2) | Grouped bars or line comparisons |
| Training curves | matplotlib (Workflow 2) | Loss/accuracy over steps/epochs |

**Rule of thumb**: numerical axes → matplotlib; boxes and arrows → Gemini.

---

## Step 0: Context Analysis & Extraction

The user typically provides raw input, not a ready-made spec. Identify the input type, then extract.

| Input Type | Example | What to Extract |
|-----------|---------|-----------------|
| Paper / section draft | "Here's our method section..." | Components, relationships, data flow |
| Description paragraph | "Our system has three layers that..." | Entities, hierarchy, connections |
| Raw results / table | "MMLU: 85.2, HumanEval: 72.1..." | Metrics, methods, comparison structure |
| CSV / JSON data | Experiment log files | Variables, trends, grouping dimensions |
| Vague request | "Make a figure for the overview" | Read surrounding paper context to infer content |

**For diagrams**: identify visual entities (named modules/layers/stages; if >8, group), classify
relationships (data flow = solid arrow, control = gray, error = dashed red), pick a layout pattern
(sequential = L→R, layered = stacked bands, hub-and-spoke, hierarchical tree), assign one accent
color per group, and transcribe every label exactly from the paper.

**For data charts**: identify the categorical axis (what is compared: methods/models/configs), the
value axis (metric), and any time/step dimension; then auto-select the chart type:

| Data Pattern | Chart |
|-------------|-------|
| Step/time axis | Line plot (training curves, scaling laws) |
| N methods × M benchmarks | Grouped bar chart |
| Single ranking | Horizontal bar (leaderboard) |
| Two continuous variables | Scatter plot |
| Square matrix | Heatmap |
| Part of whole | Stacked bar (avoid pie charts) |
| Distribution | Violin / box plot |

Always highlight "our method" in a distinct color (coral `#E76F51`); baselines recede (gray).

**Examples.** "Planner sends plans to Executor, Executor returns to Verifier, Verifier feeds back to
Planner on failure" → 3 entities, cycle layout, dashed feedback arrow → Workflow 1. "GPT-4: MMLU
86.4; Ours: 88.1; Llama-3: 79.3" → 3 methods × benchmarks → Workflow 2 grouped bar, highlight "Ours".

---

## Workflow 1: Architecture & System Diagrams (Gemini)

Generate diagrams with Gemini image generation (model `gemini-3-pro-image-preview`). **Choosing a
visual style is the single biggest quality factor** — pick one style for the whole paper.

Steps:

1. Extract entities + relationships (Step 0).
2. **Choose a visual style**: A Sketch/简笔画 · B Modern Minimal · C Illustrated Technical · D Classic Accent Bar. Full style blocks → [references/diagram-generation.md](references/diagram-generation.md#visual-style-library-abcd).
3. **Choose a color palette** consistent across figures (Ocean Dusk, Ink & Wash, Nord; hex codes in the reference).
4. Set `GEMINI_API_KEY` (never hardcode). Get a key at https://aistudio.google.com/apikey.
5. Write a **6-section prompt**: Framing → Visual Style → Color Palette → Layout → Connections → Constraints. Full structure, materiality guidance, and complete worked examples → [references/diagram-generation.md](references/diagram-generation.md#prompt-architecture-6-sections).
6. Save the generation script at `figures/gen_fig_<name>.py` and **run 3 attempts** (quality varies). Script template → [references/diagram-generation.md](references/diagram-generation.md#generation-script-template).
7. Review, pick the best, save as `figures/fig_<name>.png`.

Quick alternatives: TikZ for LaTeX-native diagrams, Mermaid to prototype the logical flow before
investing in Gemini — both in the reference.

---

## Workflow 2: Data-Driven Charts (matplotlib/seaborn)

For any figure with numerical data, axes, or quantitative comparisons.

Steps:

1. Extract methods, metrics, comparison structure (Step 0); auto-select chart type.
2. Prepare data (inline arrays, dict, or CSV).
3. Apply the **publication styling rcParams** (serif/Times, no top/right spines, faint grid, 300 DPI) → [references/data-visualization.md](references/data-visualization.md#setup-and-imports).
4. Use a colorblind-safe palette; highlight "our method", recede baselines → [references/data-visualization.md](references/data-visualization.md#color-palettes).
5. Copy the matching chart pattern (training curve, grouped bar, heatmap, scatter, leaderboard, multi-panel, violin, stacked bar, scaling law) → [references/data-visualization.md](references/data-visualization.md).
6. **Export both PDF (vector, for LaTeX) and PNG (300 DPI)**; verify LaTeX font compatibility.
7. Save the script at `figures/gen_fig_<name>.py` for reproducibility.

---

## Publication Quick Reference

| Venue | Single Col | Full Width | Font |
|-------|-----------|------------|------|
| NeurIPS | 5.5 in | 5.5 in | Times |
| ICML | 3.25 in | 6.75 in | Times |
| ICLR | 5.5 in | 5.5 in | Times |
| ACL | 3.3 in | 6.8 in | Times |
| AAAI | 3.3 in | 7.0 in | Times |

**Always export PDF** for vector quality; PNG only for AI-generated diagrams or raster fallback.
Venue-specific dimensions, LaTeX integration, font matching, math typesetting, and the accessibility
checklist → [references/style-guide.md](references/style-guide.md).

## Common Issues

| Issue | Solution |
|-------|----------|
| Fonts look wrong in LaTeX | Export PDF, set `text.usetex=True`, or use `font.family=serif` |
| Figure too large for column | Check venue width limits, set `figsize` in inches |
| Colors indistinguishable in print | Colorblind-safe palette + distinct line styles/markers |
| Gemini misspells labels | Spell out every label exactly; add "SPELL EXACTLY" constraint |
| Gemini ignores style | More negative constraints; be more specific about hex colors |
| Blurry figures in PDF | Export vector PDF, not PNG; or 300+ DPI for PNG |
| Legend overlaps data | `bbox_to_anchor`, `loc="upper left"`, or external legend |
| Too many tick labels | `ax.xaxis.set_major_locator(MaxNLocator(5))` |

## When to Use vs Alternatives

| Need | This Skill | Alternative |
|------|-----------|-------------|
| Architecture diagrams | Gemini generation | TikZ (manual), draw.io (interactive), Mermaid (simple) |
| Data charts | matplotlib/seaborn | Plotly (interactive), R/ggplot2 (stats-heavy) |
| Full paper writing | Pair with `ml-paper-writing` | — |
| Poster figures | — | `latex-posters` skill |
| Presentation figures | — | `scientific-slides`, PowerPoint/Keynote |

---

## File Naming Convention

```
figures/
├── gen_fig_<name>.py        # Generation script (always save for reproducibility)
├── fig_<name>.pdf           # Final vector output (for LaTeX)
├── fig_<name>.png           # Raster output (300 DPI, AI-generated or fallback)
└── fig_<name>_attempt*.png  # Gemini attempts (keep for comparison)
```
