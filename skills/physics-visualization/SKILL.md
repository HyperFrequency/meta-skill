---
name: physics-visualization
version: 0.1.0
description: >-
  Publication-quality physics figures with matplotlib: 2D vector fields (quiver)
  and streamlines for E&M or fluid flow, filled and labeled contour/heatmap maps
  for potentials and wavefunctions, 3D surfaces for energy landscapes,
  phase-space and Poincaré trajectory plots, spectrograms, time-evolving
  animations (GIF/MP4), and multi-panel journal layouts — all with LaTeX labels,
  perceptually-uniform colormaps, and 300-dpi PNG/PDF export. Use when a physics
  result needs a figure formatted for a paper or talk. NOT for general-purpose or
  statistical plotting (use `matplotlib` or `seaborn`), interactive/dashboard
  charts, exact editable vector schematics or block/system diagrams (use
  `scientific-schematics`), or the physics computation itself — phase portraits
  and bifurcations belong to `dynamical-systems`, flow fields to `fluid-dynamics`;
  this skill only renders results other skills compute.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Matplotlib License (PSF-based, BSD-compatible)"
---

# Physics Visualization

## Overview

Turn a computed physics result — a field, a potential, a trajectory, a
time-series, a wavefunction — into a figure that is ready for journal submission
or a talk. This skill is a thin, opinionated layer over `matplotlib`: it fixes a
publication-quality style (LaTeX labels, serif fonts, 300-dpi export,
perceptually-uniform colormaps) and gives you correct, copy-paste recipes for the
plot types physics actually needs but that generic plotting guides skip: vector
fields, streamlines, contour/heatmap potential maps, 3D surfaces, phase-space and
Poincaré plots, spectrograms, animations, and labeled multi-panel figures.

This SKILL.md is a router. The runnable recipe for each plot type lives in
`references/` — read the file for the figure you are making. You supply the
physics arrays (`X`, `Y`, `U`, `V`, `Z`, a time-series, a trajectory); this skill
formats them correctly.

## When to Use This Skill

- Any **physics result that needs a figure** formatted for a paper, thesis, or
  slide: proper axis labels with units, LaTeX math, symmetric colorbars, panel
  labels `(a) (b) (c)`.
- **Vector fields**: electric/magnetic fields, gravitational fields, velocity
  fields — as `quiver` arrows or `streamplot` field lines.
- **Scalar-field maps**: electrostatic potential, temperature distribution, a 2D
  wavefunction `|ψ|²`, a pressure field — as filled + labeled contours or heatmaps.
- **3D surfaces**: energy/potential landscapes `V(x,y)`, dispersion surfaces.
- **Phase-space / Poincaré** plots of a trajectory you already integrated.
- **Spectrograms** of a signal (time–frequency intensity map).
- **Animations** of a time-evolving system (wave, orbit, diffusion) to GIF/MP4.
- **Multi-panel comparison** figures with shared axes and automatic panel labels.

## When NOT to Use This Skill

- **Generic or statistical plotting** — a line chart, histogram, scatter, bar,
  box, or violin plot with no physics-specific formatting. Use `matplotlib`
  (full control) or `seaborn` (statistical defaults) directly.
- **Interactive / dashboard / web** plots (zoomable, hover, live). Use a
  browser-oriented library such as plotly or bokeh.
- **Exact, editable vector schematics** — a labeled apparatus diagram, circuit,
  block/system diagram, or methodology flowchart. Use `scientific-schematics`
  (or TikZ/Schemdraw) instead; this skill draws *data*, not annotated diagrams.
- **The physics itself.** This skill only renders arrays. To *compute* phase
  portraits, fixed points, or bifurcation diagrams use `dynamical-systems`; for
  the flow field itself use `fluid-dynamics`/`fluidsim`; to solve a PDE use
  `autoregressive-neural-pde-solver`; to non-dimensionalize first use
  `dimensional-analysis`.

## Setup: the publication style

Set this once at the top of a plotting script. It applies to every figure and is
what separates a journal-ready plot from a default matplotlib one. Use the `Agg`
backend for headless/batch scripts.

```python
import numpy as np
import matplotlib
matplotlib.use("Agg")            # non-interactive backend for scripts/CI
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 12, "axes.labelsize": 14, "axes.titlesize": 15,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 11,
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.3, "lines.linewidth": 1.5,
})

# Real LaTeX if a TeX install is present; otherwise matplotlib's mathtext.
# NOTE: text.usetex=True only takes effect if latex+dvipng are installed —
# setting it does NOT auto-detect. See references/styling-and-export.md.
import shutil
if shutil.which("latex"):
    plt.rcParams.update({"text.usetex": True, "font.family": "serif"})
```

## Quick Start: a vector field

The most common physics figure. Full recipes for every other type are in
`references/plot-types.md`.

```python
def plot_vector_field(ax, X, Y, U, V, normalize=True, cmap="viridis"):
    """2D vector field colored by magnitude. normalize=True shows direction
    only (equal-length arrows); False preserves true magnitude in arrow length."""
    magnitude = np.hypot(U, V)
    if normalize:
        U, V = U / (magnitude + 1e-12), V / (magnitude + 1e-12)
    q = ax.quiver(X, Y, U, V, magnitude, cmap=cmap, alpha=0.85)
    plt.colorbar(q, ax=ax, label=r"$|\mathbf{F}|$")
    ax.set_aspect("equal")
    return q

x = y = np.linspace(-3, 3, 20)
X, Y = np.meshgrid(x, y)
r2 = X**2 + Y**2 + 1e-9
Ex, Ey = X / r2**1.5, Y / r2**1.5          # point-charge field
fig, ax = plt.subplots(figsize=(7, 7))
plot_vector_field(ax, X, Y, Ex, Ey)
ax.set_xlabel(r"$x$ [m]"); ax.set_ylabel(r"$y$ [m]")
fig.savefig("field.png", dpi=300, bbox_inches="tight")
fig.savefig("field.pdf", bbox_inches="tight")   # always keep a vector copy
```

## Plot-Type Map

Pick the figure you need and read the referenced file for the complete recipe.

| Figure | Function / call | Reference |
|---|---|---|
| Vector field (arrows) | `ax.quiver` | `references/plot-types.md` |
| Field lines / streamlines | `ax.streamplot` | `references/plot-types.md` |
| Potential / density map | `ax.contourf` + `ax.contour` + `clabel` | `references/plot-types.md` |
| Heatmap of a field | `ax.pcolormesh` / `imshow` | `references/plot-types.md` |
| 3D surface | `ax.plot_surface` (`projection="3d"`) | `references/plot-types.md` |
| Phase space / Poincaré | `ax.plot` / scatter of crossings | `references/plot-types.md` |
| Spectrogram | `scipy.signal.spectrogram` + `pcolormesh` | `references/plot-types.md` |
| Multi-panel with `(a)(b)` labels | `plt.subplots` + panel labeler | `references/plot-types.md` |
| Time-evolving animation → GIF/MP4 | `FuncAnimation` + writer | `references/animation.md` |

## Colormap discipline (the one rule that matters)

Choose the colormap by data type, and **never use `jet` or `rainbow`** — they are
not perceptually uniform, invent false structure, and fail in grayscale/colorblind
viewing.

| Data | Colormap |
|---|---|
| Sequential (magnitude, density, `|ψ|²`) | `viridis`, `plasma`, `inferno` |
| Diverging around 0 (potential, charge, anomaly) | `RdBu_r`, `coolwarm` (set symmetric `vmin=-vmax`) |
| Cyclic (phase, angle) | `twilight`, `hsv` |

The full colormap rationale, symmetric-normalization helper, LaTeX-rendering
gotchas, colorbar/aspect tips, and the format decision table are in
`references/styling-and-export.md`.

## Export

Always save **both** a raster and a vector copy:

```python
fig.savefig("figure.png", dpi=300, bbox_inches="tight")   # slides, previews
fig.savefig("figure.pdf", bbox_inches="tight")            # journal (vector)
```

PDF/SVG for line-art and vector figures; PNG at 300 dpi for slides and raster
previews; EPS only when a legacy journal demands it. Details and per-journal notes
in `references/styling-and-export.md`.

## Related Skills

- `matplotlib` — the underlying library; use it directly for non-physics or fully
  custom plots. `seaborn` — statistical plots with attractive defaults.
- `scientific-schematics` — annotated apparatus/circuit/block diagrams (not data).
- `dynamical-systems` — *computes* phase portraits, fixed points, bifurcations,
  Poincaré sections (this skill renders the trajectories it produces).
- `fluid-dynamics` / `fluidsim` — produce the velocity/vorticity fields you feed
  into the vector-field and streamline recipes here.
- `dimensional-analysis` — set physical scales and dimensionless axes before you
  plot. `astropy` — astronomy-specific figures and WCS-projected sky maps.
