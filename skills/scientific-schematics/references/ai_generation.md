# AI Generation Mode — Deep Reference

Detailed mechanics of the Nano Banana 2 + Gemini 3.1 Pro Preview generation/review
loop. SKILL.md holds the lean router; load this file when you need the internals.

## How models are invoked (OpenRouter only)

Both models are reached through a single OpenRouter endpoint — there is no separate
Google/Gemini SDK. Everything is a standard chat-completions POST.

- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Auth: `Authorization: Bearer $OPENROUTER_API_KEY`
- Image generation: `model="google/gemini-3.1-flash-image-preview"` (Nano Banana 2)
  with `modalities: ["image", "text"]`. The generated image comes back base64-encoded
  in the assistant message's `images` field (not in `content`).
- Quality review: `model="google/gemini-3.1-pro-preview"` (Gemini 3.1 Pro Preview).
  The previous image is passed back in as an `image_url` data URL; the model returns
  a text critique with a `SCORE:` line.

Implementation lives in `scripts/generate_schematic_ai.py`
(`ScientificSchematicGenerator._make_request`, `_extract_image_from_response`).

Model slugs are verified against OpenRouter's catalog:
- `google/gemini-3.1-flash-image-preview` — "Nano Banana 2" (image gen/edit, Flash speed)
- `google/gemini-3.1-pro-preview` — Gemini 3.1 Pro Preview (frontier vision + reasoning)

(Note: `google/gemini-3-pro-image-preview` is the *Pro* image model, "Nano Banana Pro" —
a different, slower/higher-cost model this skill does not use by default.)

## Model-slug maintenance (when generation fails with "model not found")

Both slugs above are **preview** models, hard-coded in
`ScientificSchematicGenerator.__init__` (`scripts/generate_schematic_ai.py`). Providers
retire preview models on a schedule, so a run can start failing with a model-not-found /
404 error even though nothing in your own setup changed — this is the most common
non-obvious failure of this skill. The script calls one image model with **no automatic
fallback**: a failed generation returns `None` and the run records `success: false` in the
review log rather than silently substituting another model.

Fix: edit the `self.image_model` / `self.review_model` literals to a current slug from
https://openrouter.ai/models (filter for Google image + vision models). Known alternates,
in decreasing quality/cost — verify each against the live catalog before using:

| Role   | Current default (preview)               | Higher quality                                | Cheaper / more stable                                            |
|--------|-----------------------------------------|-----------------------------------------------|------------------------------------------------------------------|
| Image  | `google/gemini-3.1-flash-image-preview` | `google/gemini-3-pro-image` (Nano Banana Pro) | `google/gemini-2.5-flash-image` (Nano Banana Standard, non-preview) |
| Review | `google/gemini-3.1-pro-preview`         | `google/gemini-3-pro`                         | any current Gemini vision model                                  |

## Smart iterative refinement workflow

The system only regenerates if quality is below the threshold for your document type
(see the thresholds table in SKILL.md).

```
┌─────────────────────────────────────────────────────┐
│  1. Generate image with Nano Banana 2               │
│                    ↓                                 │
│  2. Review quality with Gemini 3.1 Pro Preview      │
│                    ↓                                 │
│  3. Score >= threshold?                              │
│       YES → DONE! (early stop)                       │
│       NO  → Improve prompt, go to step 1             │
│                    ↓                                 │
│  4. Repeat until quality met OR max iterations (≤2)  │
└─────────────────────────────────────────────────────┘
```

**Iteration 1** prompt = scientific-diagram guidelines + user request → `diagram_v1.png`.

If below threshold, the system extracts the specific issues from the review, enhances
the prompt with improvement instructions, and regenerates. Max 2 iterations.

## Quality review rubric

Gemini 3.1 Pro Preview scores the diagram on five axes (0–2 each, 10 total):

1. **Scientific Accuracy** — correct concepts, notation, relationships
2. **Clarity and Readability** — easy to understand, clear hierarchy
3. **Label Quality** — complete, readable, consistent labels
4. **Layout and Composition** — logical flow, balanced, no overlaps
5. **Professional Appearance** — publication-ready quality

Example review output:

```
SCORE: 8.0

STRENGTHS:
- Clear flow from top to bottom
- All phases properly labeled
- Professional typography

ISSUES:
- Participant counts slightly small
- Minor overlap on exclusion box

VERDICT: ACCEPTABLE (for poster, threshold 7.0)
```

Decision: score ≥ threshold → **STOP** (early); score < threshold → improve and retry.
Example: poster (7.0) with score 7.5 → done after 1 iteration; journal (8.5) with 7.5 → retry.

## Review log

Every run writes a JSON log with early-stop info:

```json
{
  "user_prompt": "CONSORT participant flow diagram...",
  "doc_type": "poster",
  "quality_threshold": 7.0,
  "iterations": [
    {
      "iteration": 1,
      "image_path": "figures/consort_v1.png",
      "score": 7.5,
      "needs_improvement": false,
      "critique": "SCORE: 7.5\nSTRENGTHS:..."
    }
  ],
  "final_score": 7.5,
  "early_stop": true,
  "early_stop_reason": "Quality score 7.5 meets threshold 7.0 for poster"
}
```

## Python API

```python
from scripts.generate_schematic_ai import ScientificSchematicGenerator

generator = ScientificSchematicGenerator(api_key="your_openrouter_key", verbose=True)

results = generator.generate_iterative(
    user_prompt="Transformer architecture diagram",
    output_path="figures/transformer.png",
    iterations=2,  # max 2
)

print(f"Final score: {results['final_score']}/10")
print(f"Final image: {results['final_image']}")
for iteration in results['iterations']:
    print(f"Iteration {iteration['iteration']}: {iteration['score']}/10")
    print(f"Critique: {iteration['critique']}")
```

## Command-line options

```bash
# Basic (default threshold 7.5/10)
python scripts/generate_schematic.py "diagram description" -o output.png

# Document type sets the quality threshold
python scripts/generate_schematic.py "diagram" -o out.png --doc-type journal      # 8.5
python scripts/generate_schematic.py "diagram" -o out.png --doc-type conference   # 8.0
python scripts/generate_schematic.py "diagram" -o out.png --doc-type poster       # 7.0
python scripts/generate_schematic.py "diagram" -o out.png --doc-type presentation # 6.5

# Custom max iterations (1-2), verbose, explicit key
python scripts/generate_schematic.py "complex diagram" -o diagram.png --iterations 2
python scripts/generate_schematic.py "flowchart" -o flow.png -v
python scripts/generate_schematic.py "diagram" -o out.png --api-key "sk-or-v1-..."
```

## Prompt engineering tips

Effective prompts are specific about layout, quantities, style, labels, and color.

- **Layout:** "vertical flow, top to bottom"; "encoder on left, decoder on right"; "circular, clockwise".
- **Quantitative detail:** "input layer (784 nodes), hidden (128), output (10)"; "n=500 screened, n=150 excluded".
- **Visual style:** "minimalist block diagram with clean lines"; "engineering notation".
- **Labels:** "label all arrows with activation/inhibition"; "include layer dimensions in each box".
- **Color:** "colorblind-friendly colors"; "grayscale-compatible"; "blue=input, green=processing, red=output".

Good vs. vague:
- ✓ "CONSORT flowchart showing participant flow from screening (n=500) through randomization to analysis"
- ✓ "Transformer with encoder stack left, decoder stack right, multi-head + cross-attention connections"
- ✗ "Make a flowchart" / "Neural network" / "Pathway diagram" (too generic)

## Worked examples

### CONSORT flowchart
```bash
python scripts/generate_schematic.py \
  "CONSORT participant flow diagram for randomized controlled trial. \
   Start with 'Assessed for eligibility (n=500)' at top. \
   Show 'Excluded (n=150)' with reasons: age<18 (n=80), declined (n=50), other (n=20). \
   Then 'Randomized (n=350)' splits into 'Treatment group (n=175)' and 'Control group (n=175)'. \
   Each arm shows 'Lost to follow-up' (n=15 and n=10). End with 'Analyzed' (n=160 and n=165). \
   Use blue boxes for process steps, orange for exclusion, green for final analysis." \
  -o figures/consort.png
```

### Neural network architecture
```bash
python scripts/generate_schematic.py \
  "Transformer encoder-decoder architecture diagram. \
   Left: encoder stack (input embedding, positional encoding, multi-head self-attention, \
   add & norm, feed-forward, add & norm). \
   Right: decoder stack (output embedding, positional encoding, masked self-attention, \
   add & norm, cross-attention from encoder, add & norm, feed-forward, add & norm, linear & softmax). \
   Show cross-attention connection from encoder to decoder with a dashed line. \
   Light blue for encoder, light red for decoder. Label all components." \
  -o figures/transformer.png --iterations 2
```

### Biological pathway
```bash
python scripts/generate_schematic.py \
  "MAPK signaling pathway diagram. EGFR receptor at cell membrane (top), \
   arrow down to RAS (with GTP), to RAF, to MEK, to ERK, final arrow to nucleus (gene transcription). \
   Label each arrow 'phosphorylation' or 'activation'. Rounded rectangles for proteins, \
   distinct colors. Include membrane boundary line at top." \
  -o figures/mapk_pathway.png
```

### System architecture
```bash
python scripts/generate_schematic.py \
  "IoT system architecture block diagram. Bottom: sensors (temperature, humidity, motion) in green. \
   Middle: microcontroller (ESP32) in blue, connected to WiFi module (orange) and display (purple). \
   Top: cloud server (gray) connected to mobile app (light blue). \
   Data-flow arrows between all components, labeled with protocols: I2C, UART, WiFi, HTTPS." \
  -o figures/iot_architecture.png
```

## Troubleshooting

**Overlapping text/elements, poor connections, low quality**
- Increase iterations: `--iterations 2`.
- Make the prompt more specific about connections, layout, and spacing.

**Colorblind contrast poor / indistinguishable in grayscale**
- Request the Okabe-Ito palette explicitly and add redundant encoding (shapes, patterns, line styles).
- Increase contrast between adjacent elements by at least ~20%.

**Text too small when printed**
- Design at final size; request minimum 7–8 pt fonts; export at 300+ DPI for print.

For publication standards, file formats, and accessibility guidance see
[best_practices.md](best_practices.md). For a one-page cheat sheet see
[QUICK_REFERENCE.md](QUICK_REFERENCE.md).

## Pre-submission checklist

**Visual quality**
- [ ] No overlapping elements; adequate spacing; clean alignment
- [ ] All arrows connect to intended targets

**Accessibility**
- [ ] Colorblind-safe palette (Okabe-Ito); works in grayscale; sufficient contrast
- [ ] Redundant encoding (shapes + colors) where appropriate

**Typography**
- [ ] Text ≥ 7–8 pt at final size; complete labels; consistent font; units included

**Publication standards**
- [ ] Consistent styling with other figures; comprehensive caption (all abbreviations defined)
- [ ] Referenced in text; meets journal dimension requirements; correct export format

**Documentation / version control**
- [ ] Prompt + generated image committed; review log archived; regeneration steps documented

**Integration**
- [ ] Displays correctly in compiled manuscript; `\ref{}` cross-references resolve; figure number matches citations
