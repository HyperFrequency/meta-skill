# Styling, colormaps, LaTeX, and export

Everything about making the figure *look* right and saving it in the right format.
Assumes the imports and base `rcParams` from `SKILL.md`.

## Full publication rcParams

The `SKILL.md` block is the minimum. This fuller set also fixes tick direction,
minor ticks, and legend framing that reviewers notice.

```python
plt.rcParams.update({
    "font.size": 12, "axes.labelsize": 14, "axes.titlesize": 15,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 11,
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.3, "lines.linewidth": 1.5,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.top": True, "ytick.right": True,          # ticks on all four sides
    "xtick.minor.visible": True, "ytick.minor.visible": True,
    "legend.frameon": False, "figure.autolayout": False,
    "axes.formatter.use_mathtext": True,             # 1e3 → 10^3 in mathtext
})
```

## LaTeX rendering: the gotchas

There are two math renderers and they behave differently:

- **mathtext** (default, no external deps): `text.usetex=False`. Handles
  `$\alpha$`, `$\frac{a}{b}$`, subscripts, Greek. Good enough for most figures.
- **True LaTeX**: `text.usetex=True`. Uses your system `latex` + `dvipng`
  toolchain — full LaTeX, custom packages, exact journal fonts. **Setting the flag
  does not auto-detect the toolchain**: if `latex`/`dvipng` are missing, every
  text render raises. Guard it:

```python
import shutil
if shutil.which("latex") and shutil.which("dvipng"):
    plt.rcParams.update({"text.usetex": True, "font.family": "serif"})
```

Rules that bite people:

- Always use **raw strings** for math: `r"$\log_{10}|E|$"` — a plain string turns
  `\l`, `\t` into escapes.
- Units belong in labels with math where sensible: `r"$x$ [m]"`, `r"$|\psi|^2$"`,
  `r"$E$ [J]"`. Use `\mathrm{}` for upright unit text inside math.
- With `text.usetex=True`, literal `%`, `&`, `_`, `#` must be escaped (`\%`).
- If usetex fails on a headless box, fall back to mathtext — the figure still
  renders, just with matplotlib's fonts instead of Computer Modern.

## Colormap selection

Match the colormap to the *structure* of the data. The wrong family invents or
hides features.

| Data type | Use | Why |
|---|---|---|
| Sequential — magnitude, density, `|ψ|²`, intensity | `viridis`, `plasma`, `inferno`, `magma`, `cividis` | perceptually uniform, colorblind-safe, grayscale-safe |
| Diverging around a meaningful zero — potential, charge, velocity component, anomaly | `RdBu_r`, `coolwarm`, `bwr` | symmetric, neutral midpoint at 0 |
| Cyclic — phase, angle, wave direction | `twilight`, `twilight_shifted`, `hsv` | wraps: `+π` meets `−π` seamlessly |

**Never use `jet`, `rainbow`, or `gist_rainbow`.** They are not perceptually
uniform: they create sharp false boundaries (a bright cyan/yellow band) where the
data is smooth, and lose ordering in grayscale. This is a known source of
misleading scientific figures.

### Center a diverging colormap on zero

A diverging colormap is only honest if 0 maps to the neutral midpoint. Force it:

```python
import matplotlib.colors as mcolors
vmax = np.nanmax(np.abs(Z))
norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)   # or symmetric vmin/vmax
cf = ax.contourf(X, Y, Z, levels=20, cmap="RdBu_r", norm=norm)
```

For data spanning many orders of magnitude use `LogNorm(vmin, vmax)` (strictly
positive data) or `SymLogNorm(linthresh, vmin=..., vmax=...)` (signed).

## Colorbars and aspect

- Give every color-mapped field a colorbar with a labeled quantity **and units**.
- `ax.set_aspect("equal")` for any plot in real spatial coordinates (fields,
  orbits, potentials) so circles stay circular.
- Shrink a colorbar that dwarfs a 3D axes: `fig.colorbar(surf, shrink=0.6)`.
- One shared colorbar for a panel grid: `fig.colorbar(im, ax=axes.ravel().tolist())`.

## Layout

- Prefer `plt.subplots(..., constrained_layout=True)` — it reserves space for
  colorbars and labels automatically and avoids overlap.
- `fig.tight_layout()` is the older alternative; **do not use both** on one figure.
- Reserve outer margins for panel labels `(a) (b)` placed at `transAxes` coords
  slightly outside the axes (see `references/plot-types.md`).

## Export format decision

| Format | Use for | Notes |
|---|---|---|
| **PDF** | journal submission, any line-art/vector figure | infinitely scalable; embed fonts (`savefig.dpi` irrelevant) |
| **SVG** | web, figures you will hand-edit (Inkscape/Illustrator) | vector, editable |
| **PNG @ 300 dpi** | slides, previews, raster fields | set `dpi=300`; large heatmaps rasterize cleanly |
| **EPS** | only legacy journals that demand it | no transparency; PDF is better if allowed |

Always keep a vector copy alongside the raster:

```python
fig.savefig("figure.png", dpi=300, bbox_inches="tight")
fig.savefig("figure.pdf", bbox_inches="tight")
```

For a figure that mixes a huge rasterizable field with sharp vector overlays
(axes, labels), rasterize just the heavy layer to keep the PDF small:
`ax.pcolormesh(..., rasterized=True)` then save as PDF with `dpi=300`.

## Sizing for a journal

- Match the column width: single-column ≈ 3.4 in, double-column ≈ 7.0 in wide.
  Set `figsize=(3.4, h)` and let font sizes stay at publication values so text is
  legible at print size — do **not** shrink a large figure in the manuscript.
- Keep line widths ≥ 1.0 pt and marker sizes readable after reduction.

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| `RuntimeError` on every text with usetex | `latex`/`dvipng` not installed — guard the flag, fall back to mathtext |
| Backslashes mangled in labels | use raw strings `r"..."` |
| Clipped axis labels in saved file | `bbox_inches="tight"` (already in `savefig.bbox`) or `constrained_layout` |
| PDF is enormous | `rasterized=True` on the heavy mappable; or export PNG |
| Colorbar not centered on 0 | `TwoSlopeNorm(vcenter=0)` or symmetric `vmin=-vmax` |
| Figure looks fine on screen, wrong in print | you scaled it in the manuscript — size it to column width instead |
