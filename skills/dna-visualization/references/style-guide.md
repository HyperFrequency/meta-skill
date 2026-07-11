# DNA Figure Style Guide

Defaults that make DNA/RNA figures publication-ready and consistent across the
five output families in this skill.

## Resolution & format

- **Vector (SVG or PDF) is preferred for print** — plasmid maps, gene tracks, and
  logos stay crisp at any zoom. Choose by the `savefig` extension.
- **Raster (PNG) at `dpi=300`** for slides, web, or when a downstream tool cannot
  ingest vectors.
- Always pass `bbox_inches="tight"` so labels that extend past the axes (enzyme
  labels, feature names) are not clipped.
- Use the headless `Agg` backend (`matplotlib.use("Agg")` before importing
  `pyplot`) so figures render without a display.

## Feature-color conventions

Consistent colors let readers transfer meaning between figures. Defaults used by
the plasmid and gene-track outputs:

| Feature | Color | Hex |
|---------|-------|-----|
| CDS / gene | blue | `#3498db` / `#2980b9` |
| promoter / regulatory | green | `#2ecc71` |
| terminator | red | `#e74c3c` |
| rep_origin | orange | `#f39c12` |
| misc_feature | purple | `#9b59b6` |
| primer_bind | teal | `#1abc9c` |
| mobile_element | dark orange | `#e67e22` |
| tRNA / rRNA / ncRNA | teal family | `#1abc9c` / `#16a085` / `#48c9b0` |
| intron | grey | `#bdc3c7` |
| unknown | neutral grey | `#95a5a6` |

Keep this mapping stable across a figure set so the same feature type is always
the same color.

## Colorblind safety

The enzyme palette in `references/restriction-maps.md` and the feature colors
above are chosen to stay distinguishable under common color-vision deficiencies,
but **many categories on one axis will still collide**. When you have >8
categories, distinguish by shape/position (tick markers, stacked rows) rather
than color alone, or draw from a perceptually-ordered palette (`viridis`,
`cividis`) and label directly.

## Font sizes

- Feature / enzyme labels: **9-10 pt minimum** (smaller becomes unreadable at
  print size).
- Axis labels: 11-12 pt. Titles: 13-14 pt bold.
- Nucleotide-position ticks: 8 pt.

## Default figure dimensions (inches)

| Output | Default | Notes |
|--------|---------|-------|
| Circular plasmid map | 8 × 8 | square; `figure_width=8` |
| Linear map / gene track | 14 × 4 | wide; `figure_width=14` |
| Sequence logo | 10 × 3 | height grows with alphabet |
| Restriction map | 14 × (1 + n·0.4) | height scales with enzyme count |
| GC-content plot | 12 × 4 | wide line plot |

## Sequence-logo scale

- **Information (bits)** for conservation/motif analysis — y-axis maxes at
  `log2(alphabet size)` (2.0 bits for DNA, ~4.32 for protein).
- **Probability** for raw frequency communication — y-axis 0-1.

## Handoff

Once individual panels exist, assemble multi-panel manuscript figures (shared
axes, panel letters, unified sizing) with `scientific-figure` rather than laying
them out by hand. For non-sequence quantitative plots that accompany these
figures, use `scientific-visualization`.
