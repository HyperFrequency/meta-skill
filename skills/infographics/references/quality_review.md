# Quality Review & Smart Iterative Refinement

Detailed reference for the Gemini-based review loop used by
`scripts/generate_infographic.py`. Load this when you need to understand or
tune the iteration behavior, scoring, or review-log format.

## Quality Thresholds by Document Type (`--doc-type`)

The script keeps regenerating until the review score meets the threshold for
the chosen document type (or `--iterations` is exhausted).

| Document Type | Threshold | Description |
|---------------|-----------|-------------|
| marketing     | 8.5/10    | Marketing materials - must be compelling |
| report        | 8.0/10    | Business reports - professional quality |
| presentation  | 7.5/10    | Slides, talks - clear and engaging |
| social        | 7.0/10    | Social media content |
| internal      | 7.0/10    | Internal use |
| draft         | 6.5/10    | Working drafts |
| default       | 7.5/10    | General purpose |

## Refinement Loop

```
┌─────────────────────────────────────────────────────┐
│  1. Generate infographic with Nano Banana Pro        │
│                    ↓                                  │
│  2. Review quality with Gemini 3 Pro                 │
│                    ↓                                  │
│  3. Score >= threshold?                              │
│       YES → DONE! (early stop)                       │
│       NO  → Improve prompt, go to step 1             │
│                    ↓                                  │
│  4. Repeat until quality met OR max iterations       │
└─────────────────────────────────────────────────────┘
```

Benefits: saves API calls when the first generation is good enough, enforces
higher standards for marketing materials, and gives faster turnaround for
drafts/internal use.

## Review Criteria (Gemini 3 Pro, 10 points total)

1. **Visual Hierarchy & Layout** (0-2) — clear hierarchy, logical reading flow,
   balanced composition.
2. **Typography & Readability** (0-2) — readable text, bold headlines, no
   overlapping.
3. **Data Visualization** (0-2) — prominent numbers, clear charts/icons, proper
   labels.
4. **Color & Accessibility** (0-2) — professional colors, sufficient contrast,
   colorblind-friendly.
5. **Overall Impact** (0-2) — professional appearance, free of visual bugs,
   achieves the communication goal.

## Review Log Format

Each run writes a JSON review log alongside the image:

```json
{
  "user_prompt": "5 benefits of exercise...",
  "infographic_type": "list",
  "style": "healthcare",
  "doc_type": "marketing",
  "quality_threshold": 8.5,
  "iterations": [
    {
      "iteration": 1,
      "image_path": "figures/exercise_v1.png",
      "score": 8.7,
      "needs_improvement": false,
      "critique": "SCORE: 8.7\nSTRENGTHS:..."
    }
  ],
  "final_score": 8.7,
  "early_stop": true,
  "early_stop_reason": "Quality score 8.7 meets threshold 8.5"
}
```
