# Molecular Figure Style Guide

Conventions for publication- and presentation-grade molecular graphics: atom
colors, resolution, dimensions, fonts, interaction coloring, colorblind safety,
and the 2D-vs-3D decision. Treat these as sensible defaults, not hard rules —
match the target journal or venue when it specifies otherwise.

## CPK atom colors

The Corey-Pauling-Koltun scheme is the near-universal convention for element
coloring in 3D and colored 2D depictions.

| Element | Color | Hex |
|---------|-------|-----|
| Carbon (C) | Dark gray | `#333333` |
| Nitrogen (N) | Blue | `#3050F8` |
| Oxygen (O) | Red | `#FF0D0D` |
| Sulfur (S) | Yellow | `#FFFF30` |
| Phosphorus (P) | Orange | `#FF8000` |
| Fluorine (F) | Light green | `#90E050` |
| Chlorine (Cl) | Green | `#1FF01F` |
| Bromine (Br) | Dark red | `#A62929` |
| Iodine (I) | Violet | `#940094` |
| Hydrogen (H) | White | `#FFFFFF` |
| Boron (B) | Salmon | `#FFB5B5` |

In 2D drawings, hydrogens are implicit unless they are stereochemically relevant
or explicitly requested.

## Resolution

| Medium | Minimum DPI | Recommended DPI |
|--------|-------------|-----------------|
| Journal print | 300 | 600 |
| Journal online | 150 | 300 |
| Poster | 150 | 300 |
| Screen / slide | 72 | 150 |

Vector formats (SVG, PDF, EPS) are preferred for print — they scale without loss
and stay editable. Use raster (PNG/TIFF) only when vector is unsupported. RDKit's
Cairo drawer has no DPI field; size the canvas in pixels to hit the physical size
you need (roughly `inches × target_DPI` pixels).

## Figure dimensions (pixels)

| Context | Single molecule | Grid cell | Interaction diagram |
|---------|-----------------|-----------|---------------------|
| Manuscript, single column | 400 × 300 | 200 × 150 | 600 × 600 |
| Manuscript, double column | 800 × 600 | 300 × 250 | 800 × 800 |
| Poster | 600 × 450 | 400 × 300 | 1000 × 1000 |
| Slide | 500 × 375 | 250 × 200 | 700 × 700 |
| Patent figure | 400 × 300 | 200 × 150 | n/a |

## Fonts

| Element | Minimum | Recommended |
|---------|---------|-------------|
| Atom labels | 10 pt | 12 pt |
| Atom-index annotations | 7 pt | 8 pt |
| Molecule name (grid) | 10 pt | 12 pt |
| Property annotations | 8 pt | 10 pt |
| Figure title | 12 pt | 14 pt |
| Residue labels | 8 pt | 10 pt |
| Distance labels | 6 pt | 8 pt |

Use sans-serif (Helvetica, Arial, DejaVu Sans). Serif fonts interfere with bond
line readability in dense structures.

## Bond rendering

- Bond line width: 1.5-2.5 px (2.0 is a good default).
- Wedge/hash width: 2.0-3.0 px for stereochemistry.
- Aromatic rings: Kekulized (alternating single/double) is preferred for print
  over the inner-circle notation; RDKit kekulizes on request.

## Interaction coloring (2D diagrams)

| Interaction | Color | Hex | Line |
|-------------|-------|-----|------|
| Hydrogen bond | Green | `#27AE60` | Dashed |
| Hydrophobic | Gray | `#95A5A6` | Dashed |
| Pi-stacking | Orange | `#E67E22` | Dashed |
| Salt bridge | Red | `#E74C3C` | Dashed |
| Water bridge | Cyan | `#00BCD4` | Dotted |
| Halogen bond | Purple | `#9B59B6` | Dashed |
| Metal coordination | Brown | `#795548` | Solid |

Residue box backgrounds (light tints of the above): H-bond `#D5F5E3`, hydrophobic
`#EAECEE`, pi-stacking `#FDEBD0`, salt bridge `#FADBD8`.

## Colorblind-safe choices

Roughly 8% of men and 0.5% of women have a color-vision deficiency; red/green is
the most common confusion. Prefer:

- **Two-color** (scaffold / R-group): blue `#4A90D9` / orange `#E6850D`.
- **Four-color** (interaction types): blue `#2171B5`, gray `#95A5A6`, yellow-orange
  `#FEC44F`, dark purple `#6A3D9A`.
- **Continuous scales**: viridis, plasma, or cividis (all colorblind-safe). Avoid
  jet/rainbow.

Add a redundant channel — line style (dashed vs dotted), shape, or text labels —
so meaning survives grayscale printing. Test with a simulator (Color Oracle,
Coblis).

## 2D vs 3D

| Scenario | Use | Why |
|----------|-----|-----|
| SAR tables | 2D | Compact, comparable, reproducible |
| Patent structures | 2D | Standard legal format, unambiguous |
| Virtual-screening hit lists | 2D grid | Rapid visual triage |
| Binding-mode analysis | 3D | Spatial relationships are the point |
| Docking pose review | 3D | Pose geometry matters |
| Supplementary material | 3D interactive HTML | Reader can explore freely |
| Med-chem presentations | 2D + 3D | 2D to compare, 3D for context |
| Conference poster | 2D primary, 3D inset | 2D reads at distance, 3D for detail |

## 3D best practices

- Protein as cartoon for fold context; ligand as sticks with element coloring.
- Translucent pocket surface (opacity 0.2-0.4) for shape without hiding the
  ligand.
- Distinct chain colors (spectrum or by chain id).
- White background for print, dark background for projected slides.
- Include hydrogens only when they carry meaning (H-bonding, tautomers).

## File formats

| Format | Type | Best for |
|--------|------|----------|
| SVG | Vector | Print; editable, scales perfectly |
| PDF | Vector | Print; wide compatibility |
| EPS | Vector | Legacy journal submission |
| PNG | Raster | Web, slides (size for 300 DPI if printing) |
| TIFF | Raster | Journal submission; lossless, large |
| HTML | Interactive | Supplementary / web (self-contained py3Dmol) |
