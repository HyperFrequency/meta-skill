---
name: infographics
version: 0.1.0
description: "Create professional infographics using Nano Banana Pro AI with smart iterative refinement. Uses Gemini 3 Pro for quality review. Integrates research-lookup and web search for accurate data. Supports 10 infographic types, 8 industry styles, and colorblind-safe palettes. Not for technical diagrams or circuit designs—use scientific-schematics for those."
allowed-tools: Read Write Edit Bash
---

# Infographics

## Overview

Infographics are visual representations of information, data, or knowledge designed to present complex content quickly and clearly. **This skill uses Nano Banana Pro AI for infographic generation with Gemini 3 Pro quality review and Perplexity Sonar for research.**

**How it works:**
- (Optional) **Research phase**: Gather accurate facts and statistics using Perplexity Sonar
- Describe your infographic in natural language
- Nano Banana Pro generates publication-quality infographics automatically
- **Gemini 3 Pro reviews quality** against document-type thresholds
- **Smart iteration**: Only regenerates if quality is below threshold
- Professional-ready output in minutes
- No design skills required

The review threshold is set by `--doc-type` (e.g. `marketing` 8.5/10, `report`
8.0, `presentation`/`default` 7.5, `social`/`internal` 7.0, `draft` 6.5). Full
table and rubric: **`references/quality_review.md`**.

**Simply describe what you want, and Nano Banana Pro creates it.**

## Quick Start

Generate any infographic by simply describing it:

```bash
# Basic: list infographic (default threshold 7.5/10)
python skills/infographics/scripts/generate_infographic.py \
  "5 benefits of regular exercise" \
  -o figures/exercise_benefits.png --type list

# With style + colorblind-safe palette + higher threshold
python skills/infographics/scripts/generate_infographic.py \
  "Heart disease statistics worldwide" \
  -o figures/health_stats.png --type statistical \
  --style healthcare --palette wong --doc-type report

# WITH RESEARCH for accurate, up-to-date data
python skills/infographics/scripts/generate_infographic.py \
  "Global AI market size and growth projections" \
  -o figures/ai_market.png --type statistical --research
```

**What happens behind the scenes:** (optional) Perplexity Sonar gathers facts →
Nano Banana Pro generates → Gemini 3 Pro scores against the document-type
threshold → early-stop if it passes, otherwise improve the prompt and regenerate
up to `--iterations`. This saves API calls when the first try is good enough
while holding marketing materials to a higher bar.

**Output**: Versioned images plus a detailed review log with quality scores, critiques, and early-stop information.

## When to Use This Skill

Use the **infographics** skill when:
- Presenting data or statistics in a visual format
- Creating timeline visualizations for project milestones or history
- Explaining processes, workflows, or step-by-step guides
- Comparing options, products, or concepts side-by-side
- Summarizing key points in an engaging visual format
- Creating geographic or map-based data visualizations
- Building hierarchical or organizational charts
- Designing social media content or marketing materials

**Use scientific-schematics instead for:**
- Technical flowcharts and circuit diagrams
- Biological pathways and molecular diagrams
- Neural network architecture diagrams
- CONSORT/PRISMA methodology diagrams

---

## Research Integration

Add `--research` to automatically gather accurate, up-to-date facts and
statistics with **Perplexity Sonar Pro** before generating. Best for
statistical, market, scientific, or current-events topics where accuracy
matters; skip it for simple conceptual or internal infographics or when you
already supply all the data. Research is folded into the prompt and saved to
`{name}_research.json`.

For the full when-to-use guidance, worked examples, and output schema, see
**`references/research_integration.md`**.

---

## Infographic Types

Pass the closest match to `--type`. Each type maps to a layout the generator
optimizes for.

| `--type`       | Best for                                          | Key elements |
|----------------|---------------------------------------------------|--------------|
| `statistical`  | Numbers, percentages, survey/quantitative data    | Charts, large numeric callouts, trend indicators |
| `timeline`     | Historical events, milestones, evolution          | Chronological flow, date markers, event nodes |
| `process`      | Step-by-step instructions, workflows              | Numbered steps, arrows, action icons |
| `comparison`   | Product/option comparisons, pros-cons, before-after | Side-by-side layout, check/cross indicators |
| `list`         | Tips, facts, key points, quick reference          | Numbered/bulleted points, icons, hierarchy |
| `geographic`   | Regional/location data, global trends             | Map visualization, color coding, legend |
| `hierarchical` | Org structures, priority/importance ranking       | Pyramid/tree, distinct levels |
| `anatomical`   | Complex systems via visual metaphor               | Central metaphor image, labeled parts |
| `resume`       | Personal branding, CVs, portfolios                | Photo area, skills viz, timeline |
| `social`       | Instagram/LinkedIn/X posts, shareable graphics    | Bold headline, minimal text, vibrant colors |

```bash
python skills/infographics/scripts/generate_infographic.py \
  "History of AI: 1950 Turing Test, 1956 Dartmouth Conference, \
   1997 Deep Blue, 2016 AlphaGo, 2022 ChatGPT" \
  -o figures/ai_history.png --type timeline --style technology
```

For per-type prompt templates, layout patterns, and worked example prompts, see
**`references/infographic_types.md`**.

---

## Styles & Palettes

Pass `--style` for an industry look and `--palette` for a colorblind-safe
color set:

- **`--style`**: `corporate`, `healthcare`, `technology`, `nature`,
  `education`, `marketing`, `finance`, `nonprofit` — each maps to an
  audience-appropriate color scheme.
- **`--palette`**: `wong` (most widely recommended), `ibm` (IBM accessible),
  `tol` (12-color extended for many categories) — colorblind-safe.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Q4 Results" -o q4.png --type statistical --style corporate --palette wong
```

For exact hex values, per-style swatches, and prompt snippets, see
**`references/color_palettes.md`**.

---

## Smart Iterative Refinement

The generator regenerates only while quality is below the document-type
threshold, then early-stops. Each run produces versioned images plus a JSON
review log with scores and critiques.

For the full loop diagram, the 5-category (10-point) Gemini review rubric, and
the review-log schema, see **`references/quality_review.md`**.

---

## Command-Line Reference

```bash
python skills/infographics/scripts/generate_infographic.py [OPTIONS] PROMPT

Arguments:
  PROMPT                    Description of the infographic content

Options:
  -o, --output PATH         Output file path (required)
  -t, --type TYPE           Infographic type preset
  -s, --style STYLE         Industry style preset
  -p, --palette PALETTE     Colorblind-safe palette
  -b, --background COLOR    Background color (default: white)
  --doc-type TYPE           Document type for quality threshold
  --iterations N            Maximum refinement iterations (default: 3)
  --api-key KEY             OpenRouter API key
  -v, --verbose             Verbose output
  --list-options            List all available options
```

### List All Options

```bash
python skills/infographics/scripts/generate_infographic.py --list-options
```

---

## Configuration

### API Key Setup

Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY='your_api_key_here'
```

Get an API key at: https://openrouter.ai/keys

---

## Prompt Engineering Tips

Be specific and include concrete data — vague prompts produce weak layouts.

- ✓ `"5 benefits of meditation: reduces stress, improves focus, better sleep,
  lower blood pressure, emotional balance"` — ✗ `"meditation infographic"`
- ✓ `"Market growth from $10B (2020) to $45B (2025), CAGR 35%"` — ✗ `"market is growing"`
- ✓ Name visual elements: `"Timeline showing 5 milestones with icons for each event"`

For deeper guidance on hierarchy, layout, and typography, see
**`references/design_principles.md`**.

---

## Reference Files

For detailed guidance, load these reference files:

- **`references/infographic_types.md`**: Extended templates for all 10+ types
- **`references/design_principles.md`**: Visual hierarchy, layout, typography
- **`references/color_palettes.md`**: Full palette specifications
- **`references/quality_review.md`**: Thresholds, review rubric, log schema
- **`references/research_integration.md`**: `--research` guidance, examples, output schema

---

## Troubleshooting

### Common Issues

**Problem**: Text in infographic is unreadable
- **Solution**: Reduce text content; use --type to specify layout type

**Problem**: Colors clash or are inaccessible
- **Solution**: Use `--palette wong` for colorblind-safe colors

**Problem**: Quality score too low
- **Solution**: Increase iterations with `--iterations 3`; use more specific prompt

**Problem**: Wrong infographic type generated
- **Solution**: Always specify `--type` flag for consistent results

**Problem**: Generation fails with a model-not-found / invalid-model error
- **Solution**: The bundled script pins the image model slug
  `google/gemini-3-pro-image-preview`; that preview slug was scheduled to retire
  2026-06-25. Update `self.image_model` to the GA slug `google/gemini-3-pro-image`
  in `scripts/generate_infographic_ai.py` (the review model stays
  `google/gemini-3-pro`).

---

## Integration with Other Skills

- **scientific-schematics**: For technical diagrams and flowcharts
- **market-research-reports**: Infographics for business reports
- **scientific-slides**: Infographic elements for presentations
- **generate-image**: For non-infographic visuals

---

## Quick Reference Checklist

- **Before**: specific content description, `--type` selected, `--style` suited
  to audience, `-o` output path set, API key configured.
- **After**: review the generated image, check the review log scores, regenerate
  with a more specific prompt if needed.

---

Use this skill to create professional, accessible infographics with Nano Banana Pro AI and intelligent quality review.
