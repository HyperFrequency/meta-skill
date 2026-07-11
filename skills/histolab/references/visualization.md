# Visualization

Visualization in histolab is mostly: use its few built-in preview helpers to validate a
pipeline, then use plain matplotlib on top of histolab outputs for reports. Previewing before
extraction is the cheapest way to catch a bad mask or a wrong `tissue_percent`.

For richer plotting idioms see the `matplotlib` and `seaborn` skills.

## Built-in previews

| Call | Shows |
| --- | --- |
| `slide.thumbnail` | PIL overview image of the whole slide |
| `slide.thumbnail.save(path)` | write the PIL thumbnail to disk (no `save_thumbnail()` method) |
| `slide.show()` | opens the thumbnail (interactive sessions) |
| `slide.locate_mask(mask)` | mask boundary overlaid on the thumbnail |
| `tiler.locate_tiles(slide, ...)` | chosen tile boxes drawn on a rescaled thumbnail |

```python
slide.locate_mask(TissueMask())
tiler.locate_tiles(slide, scale_factor=32, alpha=128, outline="red")
```

`locate_tiles` takes `scale_factor`, `alpha`, `outline`, `linewidth` (and an optional `tiles`
list) — **not** `n_tiles`.

## Mask visualization (manual)

Side-by-side original / mask / overlay:

```python
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from histolab.masks import TissueMask

mask = TissueMask()(slide)
fig, ax = plt.subplots(1, 3, figsize=(20, 7))
ax[0].imshow(slide.thumbnail);            ax[0].set_title("Slide")
ax[1].imshow(mask, cmap="gray");          ax[1].set_title("Tissue mask")
ax[2].imshow(slide.thumbnail)
ax[2].imshow(mask, cmap=ListedColormap(["none", "red"]), alpha=0.3)
ax[2].set_title("Overlay")
for a in ax: a.axis("off")
plt.tight_layout(); plt.show()
```

## Displaying extracted tiles

Tiles are PNGs under `processed_path`; load with PIL and grid them:

```python
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

paths = list(Path("output/tiles/").glob("*.png"))[:16]
fig, axes = plt.subplots(4, 4, figsize=(12, 12))
for ax, p in zip(axes.ravel(), paths):
    ax.imshow(Image.open(p)); ax.set_title(p.stem, fontsize=8); ax.axis("off")
plt.tight_layout(); plt.show()
```

## Score analysis (`ScoreTiler`)

Load the report CSV and inspect the distribution — a fast sanity check on your scorer:

```python
import pandas as pd, matplotlib.pyplot as plt

df = pd.read_csv("output/tiles_report.csv")
plt.hist(df["score"], bins=30, edgecolor="black"); plt.xlabel("score"); plt.show()
```

Compare the highest- vs lowest-scoring saved tiles to confirm the scorer is picking what you
expect (top rows should look cell-dense for `NucleiScorer`):

```python
df = pd.read_csv("output/tiles_report.csv").sort_values("score", ascending=False)
top, bottom = df.head(8), df.tail(8)
# imshow each tile image from output/tiles/<tile_name> in a 2-row grid
```

## Multi-slide overviews

Thumbnail grid across a cohort, or a bar chart of tissue coverage per slide:

```python
from pathlib import Path
from histolab.slide import Slide
from histolab.masks import TissueMask
import matplotlib.pyplot as plt

names, coverage = [], []
for sp in Path("slides/").glob("*.svs"):
    s = Slide(str(sp), processed_path="output/")
    m = TissueMask()(s)
    names.append(s.name); coverage.append(m.sum() / m.size * 100)

plt.bar(range(len(names)), coverage)
plt.xticks(range(len(names)), names, rotation=45, ha="right")
plt.ylabel("Tissue coverage (%)"); plt.tight_layout(); plt.show()
```

## Filter-effect visualization

Show a pipeline step by step to tune parameters (grayscale → Otsu → dilation → cleanup):

```python
from histolab.filters.compositions import Compose
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
from histolab.filters.morphological_filters import BinaryDilation, RemoveSmallObjects

steps = [
    ("Original", None),
    ("Grayscale", RgbToGrayscale()),
    ("Otsu", Compose([RgbToGrayscale(), OtsuThreshold()])),
    ("Dilated", Compose([RgbToGrayscale(), OtsuThreshold(), BinaryDilation(disk_size=5)])),
]
fig, axes = plt.subplots(1, len(steps), figsize=(20, 4))
for ax, (title, fn) in zip(axes, steps):
    ax.imshow(slide.thumbnail if fn is None else fn(slide.thumbnail),
              cmap=None if fn is None else "gray")
    ax.set_title(title); ax.axis("off")
plt.tight_layout(); plt.show()
```

## Exporting

- High-res figure: `plt.savefig("fig.png", dpi=300, bbox_inches="tight")`.
- Multi-page PDF report: `matplotlib.backends.backend_pdf.PdfPages` — one `pdf.savefig(fig)`
  per page (thumbnail, mask, tile locations).

## Tips

- Preview mask and tiles **before** extracting; it is far cheaper than a failed full run.
- Use `cmap="gray"` for binary masks, `"viridis"` for continuous heatmaps.
- Export at 300 DPI for publication figures; label axes and titles.
