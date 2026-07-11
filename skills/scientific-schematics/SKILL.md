---
name: scientific-schematics
version: 0.2.0
description: Generate publication-quality scientific DIAGRAMS (neural-net architectures, system/block diagrams, methodology flowcharts like CONSORT/PRISMA, biological pathways, circuits) from a natural-language description, using Nano Banana 2 (google/gemini-3.1-flash-image-preview) for image generation and Gemini 3.1 Pro Preview (google/gemini-3.1-pro-preview) for quality review, both via OpenRouter. Use when you need a conceptual figure drawn from a prompt with smart iterative refinement to a per-document-type quality bar. NOT for data plots/charts (use scientific-visualization), exact editable vector schematics (use code tools like matplotlib/Schemdraw/TikZ), or text-defined Mermaid/PlantUML diagrams.
allowed-tools: Read Write Edit Bash
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Scientific Schematics and Diagrams

Turn a natural-language description into a publication-quality scientific diagram. No
coding, templates, or manual drawing — you describe the figure, the AI draws and refines it.

**Two models, one provider (OpenRouter):**
- **Nano Banana 2** (`google/gemini-3.1-flash-image-preview`) generates the image.
- **Gemini 3.1 Pro Preview** (`google/gemini-3.1-pro-preview`) reviews quality.

Both are called as plain OpenRouter chat-completions requests
(`https://openrouter.ai/api/v1/chat/completions`); no Google SDK is used. Image generation
sends `modalities: ["image","text"]` and reads the base64 result from the message `images`
field. See [references/ai_generation.md](references/ai_generation.md) for the full invocation
detail and the iteration internals.

## Setup

```bash
export OPENROUTER_API_KEY='your_api_key_here'   # get one at https://openrouter.ai/keys
```

## Quick start

```bash
python scripts/generate_schematic.py "your diagram description" -o output.png
```

Add `--doc-type <type>` to set the quality bar, `--iterations 2` for harder diagrams, and
`-v` for verbose logs. Full options, Python API, and worked examples (CONSORT, Transformer,
MAPK pathway, IoT architecture) are in [references/ai_generation.md](references/ai_generation.md).

## Smart iterative refinement

The system generates, then has Gemini 3.1 Pro Preview score the result against the threshold
for your document type. If the score meets the bar it stops early; otherwise it improves the
prompt from the critique and regenerates (max 2 iterations). It writes a JSON review log with
scores, critiques, and early-stop reason.

**Quality thresholds by document type:**

| Document type | Threshold | Use for |
|---------------|-----------|---------|
| journal | 8.5/10 | Nature, Science, peer-reviewed journals |
| conference | 8.0/10 | Conference papers |
| thesis | 8.0/10 | Dissertations, theses |
| grant | 8.0/10 | Grant proposals |
| preprint | 7.5/10 | arXiv, bioRxiv |
| report | 7.5/10 | Technical reports |
| poster | 7.0/10 | Academic posters |
| presentation | 6.5/10 | Slides, talks |
| default | 7.5/10 | General purpose |

The review rubric (5 axes, 0–2 each), example review output, and the review-log JSON schema
are documented in [references/ai_generation.md](references/ai_generation.md).

## When to use this skill

Use for conceptual, prompt-drawn figures:
- Neural network architectures (Transformers, CNNs, RNNs)
- System / data-flow / block diagrams and network topologies
- Methodology flowcharts (CONSORT, PRISMA) and algorithm/pipeline workflows
- Biological pathways and molecular interactions
- Circuit / electrical schematics and conceptual frameworks

See [references/diagram_types.md](references/diagram_types.md) for what each type needs in
the prompt.

## When NOT to use this skill

- **Data plots / statistical charts** (line, bar, scatter, heatmap) → use
  **scientific-visualization** (matplotlib/seaborn).
- **Exact, editable vector schematics** that must be pixel-correct → code tools
  (Schemdraw, NetworkX, TikZ).
- **Text-defined diagrams** (Mermaid/PlantUML) → a Mermaid-focused skill.

## Writing good prompts

Be specific about **type, components, flow/direction, labels, style, and color**. Example:
"Transformer encoder-decoder, encoder stack left / decoder stack right, multi-head and
cross-attention shown with dashed lines, light blue encoder / light red decoder, label all
components." Detailed prompt-engineering tips and good-vs-vague examples are in
[references/ai_generation.md](references/ai_generation.md).

Scientific-quality guidelines applied automatically: clean light background, high contrast,
readable labels (≥10 pt), sans-serif typography, Okabe-Ito colorblind-safe palette, generous
spacing, and legends/scale bars where appropriate.

## Troubleshooting (quick)

- Overlaps, poor connections, or low quality → `--iterations 2` and a more specific prompt.
- Colorblind/grayscale issues → request Okabe-Ito explicitly and add redundant encoding.
- Text too small in print → design at final size, ≥7–8 pt fonts, export 300+ DPI.

Full troubleshooting and a pre-submission checklist are in
[references/ai_generation.md](references/ai_generation.md).

## References

- [references/ai_generation.md](references/ai_generation.md) — invocation detail, iteration internals, Python API, CLI, examples, troubleshooting, checklist
- [references/diagram_types.md](references/diagram_types.md) — catalog of diagram types and required prompt elements
- [references/best_practices.md](references/best_practices.md) — publication standards, file formats, accessibility
- [references/QUICK_REFERENCE.md](references/QUICK_REFERENCE.md) — one-page cheat sheet

## Related skills

- **scientific-visualization** — data plots and statistical figures (shares color palettes/styling)
- **scientific-writing** — figure captions and in-text references
- **latex-posters** / **research-grants** — diagrams for posters and proposals
- **peer-review** — evaluating diagram clarity and accessibility
