# Slide Management

The `Slide` class is the entry point for every histolab workflow. It wraps an OpenSlide-backed
whole-slide image and exposes the metadata, thumbnails, and pyramid structure you need before
extracting anything.

## Loading a slide

```python
from histolab.slide import Slide

slide = Slide(
    "path/to/slide.svs",          # slide_path: any OpenSlide-readable WSI
    processed_path="output/",      # where thumbnails, tiles, reports are written
)
```

- `slide_path` — SVS, TIFF, NDPI, MRXS, and other OpenSlide-supported formats.
- `processed_path` — a directory histolab creates outputs under. Give each slide its own
  subdirectory in batch runs so tiles do not collide.

### Built-in sample slides

Histolab bundles small TCGA sample slides, handy for smoke-testing a pipeline without your
own data. Each returns `(openslide.OpenSlide, path)`; pass the path to `Slide`:

```python
from histolab.data import (
    prostate_tissue, ovarian_tissue, breast_tissue, heart_tissue, kidney_tissue,
)

_, prostate_path = prostate_tissue()
slide = Slide(prostate_path, processed_path="output/")
```

## Inspecting a slide

```python
print(slide.name)                       # filename stem
print(slide.dimensions)                 # (width, height) at level 0
print(slide.levels)                     # list of available pyramid levels
print(slide.level_dimensions(level=1))  # METHOD — dimensions at a given level
print(slide.properties)                 # OpenSlide properties dict
```

`level_dimensions` is a **method that takes a `level` argument**, not a property. Read
magnification and micron-per-pixel from the properties dict, whose keys depend on the
scanner vendor:

```python
props = slide.properties
props.get("openslide.objective-power")  # e.g. "40" — nominal objective power
props.get("openslide.mpp-x")            # microns per pixel, X
props.get("openslide.mpp-y")            # microns per pixel, Y
props.get("openslide.vendor")           # scanner vendor
```

Not every slide populates every key; always `.get(...)` with a default.

## Pyramid levels

WSIs are stored as an image pyramid: level 0 is native (highest) resolution, and each higher
level is a downsampled copy for faster, coarser access. Extract at the level that matches your
target resolution — working at level 1 or 2 is dramatically faster and often sufficient.

```python
for level in slide.levels:
    print(level, slide.level_dimensions(level=level))
```

## Thumbnails

```python
thumb = slide.thumbnail                     # PIL.Image, a small whole-slide overview
slide.thumbnail.save("output/thumb.png")    # save it yourself (no save_thumbnail() method)
slide.show()                                # opens the thumbnail (interactive sessions)
```

Thumbnails are the substrate for `locate_mask` and `locate_tiles` previews (see
`visualization.md`), and the cheapest way to confirm a slide actually contains tissue before
you launch an extraction.

## Multi-slide processing

Give every slide an isolated output directory and reuse one tiler config:

```python
from pathlib import Path
from histolab.slide import Slide
from histolab.tiler import RandomTiler

tiler = RandomTiler(tile_size=(512, 512), n_tiles=50, level=0, seed=42)

for slide_path in Path("slides/").glob("*.svs"):
    out = Path("output/") / slide_path.stem
    out.mkdir(parents=True, exist_ok=True)
    slide = Slide(str(slide_path), processed_path=str(out))
    slide.thumbnail.save(out / "thumbnail.png")
    tiler.extract(slide)
```

## Practical notes

- **Check dimensions before level-0 work.** Level-0 operations on large slides are
  memory-hungry; a quick `slide.dimensions` tells you what you are committing to.
- **Verify tissue is present** via the thumbnail before extraction — blank or mostly-glass
  slides silently yield zero tiles.
- **Enable logging** (`logging.basicConfig(level=logging.INFO)`) for long batch runs so you
  see per-tile progress.
