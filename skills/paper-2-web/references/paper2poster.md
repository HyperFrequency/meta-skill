# Paper2Poster: Conference Poster

Generates a **print-ready** academic poster: extracts key content, designs a balanced layout, and outputs at print resolution.

## Invocation

```bash
python pipeline_all.py \
  --input-dir <paper_dir> \
  --output-dir <out_dir> \
  --model-choice N \
  --poster-width-inches W \
  --poster-height-inches H
```

`--poster-width-inches` / `--poster-height-inches` are corroborated. Additional design flags documented upstream (orientation, DPI, template, color scheme, institution branding, font family, QR codes) are **version-dependent — confirm with `python pipeline_all.py --help`** before relying on them.

## Standard sizes

- 48"×36" (4'×3') — most common conference poster.
- 60"×48" (5'×4') — large format.
- 36"×48" — portrait for narrow spaces.
- A0 (841×1189 mm), A1 (594×841 mm) — international standards.
- Any custom dimensions via the width/height flags.

## Output tree (approximate)

```
<out_dir>/<paper_name>/poster/
├── poster_final.pdf     # print-ready
├── poster_final.png     # high-res raster
├── poster_preview.pdf   # low-res preview
├── poster_source/       # editable: layout.pptx / layout.svg / layout.json
├── assets/{figures,logos,qrcodes}/
└── metadata/            # design_spec.json, content_map.json
```

The editable `poster_source/` (PPTX/SVG) is your escape hatch for manual fixes.

## Sections

Header (title, authors, affiliations, logos) → Introduction/Background → Methods (with workflow diagram) → **Results (largest section)** → Conclusions → References & Contact (with QR codes). Results should dominate; the poster must read at a glance.

## Templates and styling

- **Templates**: Modern (default, minimalist), Academic (traditional/dense), Visual (image-forward, infographic), Technical (equation/code-friendly).
- **Color schemes**: institutional, professional, vibrant, nature, tech, warm, cool — or supply custom hex values (primary/secondary/accent/background/text).
- **Typography size hierarchy** (guideline): title 72–96 pt, section headers 48–60 pt, subsection 36–48 pt, body 24–32 pt, captions 18–24 pt, references 16–20 pt. These minimums keep a large poster legible from a distance.

## Print preparation

- Format PDF/X-1a or PDF/X-4 for professional print; embed all fonts.
- 300 DPI minimum (600 for fine detail); CMYK for print (auto-converted from RGB); 0.125" bleed added.
- Print a Letter/A4 preview before the full-size run.

## QR codes and branding

Auto-generates QR codes for paper DOI/PDF, project site, code repo, data repo, and author profiles (ORCID/Scholar). Institution branding (logo + colors) can be inferred from affiliations; logo lookup needs the web-search API keys (see `setup-and-usage.md`).

## Review checklist

Figures high-res and clear; text readable from 3–6 ft; consistent professional palette; no overlaps/overflow; logos correct; QR codes resolve; author info accurate; key findings prominent; references formatted; file at correct size/resolution for the printer.

## Limitations

Complex equations may need manual tuning; very long papers require content prioritization; custom branding needs manual specification or API access; 3D visualizations lose fidelity in 2D.

## Alternative

For full hand-control over a poster's source rather than an auto-generated one, use the `latex-posters` or `pptx-posters` sibling skills.
