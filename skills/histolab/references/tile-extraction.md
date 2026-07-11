# Tile Extraction

Tile extraction crops small, manageable regions from a gigapixel WSI. Histolab offers three
extractors that share a common parameter set and differ only in *how* they choose tile
locations. All live in `histolab.tiler`.

## Common constructor parameters

Shared across `RandomTiler`, `GridTiler`, `ScoreTiler`:

| Param | Meaning | Typical |
| --- | --- | --- |
| `tile_size` | `(width, height)` in pixels | `(512, 512)` |
| `level` | pyramid level (0 = highest resolution) | `0`, or `1`/`2` for speed |
| `check_tissue` | keep only tiles with enough tissue | `True` |
| `tissue_percent` | minimum tissue coverage % to keep a tile | `70`–`90` |
| `prefix` | subdirectory / filename prefix under `processed_path` | `"random/"` |
| `suffix` | file extension | `".png"` |

The tissue **mask is not a constructor argument** — it is passed to `extract()` and
`locate_tiles()` as `extraction_mask` (default `BiggestTissueBoxMask`).

## `RandomTiler`

Extracts up to `n_tiles` randomly positioned tiles from the masked region.

```python
from histolab.tiler import RandomTiler

tiler = RandomTiler(
    tile_size=(512, 512),
    n_tiles=100,          # upper bound (see note)
    level=0,
    seed=42,              # reproducible placement
    check_tissue=True,
    tissue_percent=80.0,
    max_iter=1000,        # max attempts to hit n_tiles valid tiles
)
tiler.extract(slide)                              # default mask
tiler.extract(slide, extraction_mask=TissueMask())
```

- `n_tiles` is an **upper bound**: on sparse slides, `check_tissue` + `max_iter` may yield
  fewer. Raise `max_iter` or lower `tissue_percent` if you need more.
- Fast and reproducible; good for sampling diverse morphology and building balanced training
  sets. Trade-off: no coverage guarantee, may miss rare patterns.

## `GridTiler`

Systematically tiles the entire masked region on a grid.

```python
from histolab.tiler import GridTiler

tiler = GridTiler(
    tile_size=(512, 512),
    level=0,
    check_tissue=True,
    tissue_percent=80.0,
    pixel_overlap=0,      # 0 = disjoint tiles; >0 = sliding-window overlap
)
tiler.extract(slide)
```

- `pixel_overlap` controls the sliding window: `0` gives non-overlapping tiles; a positive
  value overlaps adjacent tiles (useful for seamless reconstruction / segmentation).
- Complete coverage and preserved spatial layout, at the cost of compute and potentially
  thousands of tiles per slide. Prefer a higher `level` to keep counts sane.

## `ScoreTiler`

Grids the slide, scores every candidate tile, and saves the top `n_tiles`.

```python
from histolab.tiler import ScoreTiler
from histolab.scorer import NucleiScorer

tiler = ScoreTiler(
    scorer=NucleiScorer(),
    tile_size=(512, 512),
    n_tiles=50,           # keep the 50 highest-scoring tiles (0 = keep all, ranked)
    level=0,
    check_tissue=True,
    tissue_percent=80.0,
    pixel_overlap=0,
)
tiler.extract(slide, report_path="output/tiles_report.csv")
```

Extraction: find tissue → generate grid tiles → keep tiles with enough tissue → sort by score
descending → save the top `n_tiles` → (if `report_path` given) write a CSV of saved tiles and
scores. Slower than the others because every candidate must be scored.

### Scorers (`histolab.scorer`)

- **`NucleiScorer`** — hybrid nuclei-segmentation score, `nuclei_ratio · tanh(tissue_fraction)`;
  surfaces cell-rich / tumor-dense regions. Best at higher magnification where nuclei are
  discernible.
- **`CellularityScorer(consider_tissue=True)`** — hematoxylin-fraction cellularity score.
  Meant for **low-resolution** tiles where individual nuclei are not resolvable and
  `NucleiScorer` degrades. `consider_tissue=True` normalizes by detected tissue area;
  `False` normalizes by the whole tile.
- **`RandomScorer`** — assigns random scores; a baseline / sanity check.
- **Custom** — subclass `Scorer` and implement `__call__(self, tile)` returning a float:

```python
import numpy as np
from histolab.scorer import Scorer

class ColorVarianceScorer(Scorer):
    def __call__(self, tile):
        arr = np.array(tile.image)
        return float(np.var(arr, axis=(0, 1)).sum())

tiler = ScoreTiler(scorer=ColorVarianceScorer(), tile_size=(512, 512), n_tiles=30)
```

> Rule of thumb: `NucleiScorer` for high-magnification tiles (nuclei visible),
> `CellularityScorer` for low-magnification tiles (nuclei blurred together).

### Report CSV

With `report_path`, `ScoreTiler` writes one row per saved tile — filename, coordinates, and
score — which you can load with pandas to audit the score distribution (see
`visualization.md`).

## Previewing before extraction

`locate_tiles` draws the chosen tile boxes on a rescaled thumbnail. It does **not** take
`n_tiles`; control the view with `scale_factor`, `alpha`, and `outline`:

```python
tiler.locate_tiles(slide, scale_factor=32, alpha=128, outline="red")
tiler.locate_tiles(slide, extraction_mask=TissueMask())   # preview against a specific mask
```

## Advanced patterns

**Multi-level** — extract the same slide at several resolutions:

```python
for lvl in (0, 1, 2):
    RandomTiler(tile_size=(512, 512), n_tiles=50, level=lvl,
                seed=42, prefix=f"level{lvl}/").extract(slide)
```

**Post-extraction blur filtering** — histolab writes tiles to disk; prune blurry ones with a
Laplacian-variance pass afterward:

```python
import cv2, numpy as np
from pathlib import Path
from PIL import Image

def drop_blurry(tile_dir, threshold=100.0):
    for p in Path(tile_dir).glob("*.png"):
        gray = np.array(Image.open(p).convert("L"))
        if cv2.Laplacian(gray, cv2.CV_64F).var() < threshold:
            p.unlink()
```

## Performance and troubleshooting

- **No tiles** → lower `tissue_percent`; confirm the thumbnail has tissue; check the mask
  covers it; verify `tile_size` is sane for the chosen `level`.
- **Too many background tiles** → `check_tissue=True`, raise `tissue_percent`, tighten the
  mask.
- **Too slow** → extract at `level=1`/`2`, reduce `n_tiles`, prefer `BiggestTissueBoxMask`,
  avoid `GridTiler` for mere sampling.
- **`GridTiler` tiles overlap too much** → lower or zero out `pixel_overlap`.
