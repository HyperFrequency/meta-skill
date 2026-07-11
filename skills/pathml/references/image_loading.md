# Image Loading & Formats

PathML abstracts vendor-specific whole-slide and multiplex formats behind a small set
of slide classes. You load a slide once, then work with pyramid levels, tiles, masks,
and metadata through a uniform interface. Loading is lazy — pixels are only read when
you tile or request a region.

## Supported formats

PathML reads WSIs through OpenSlide and Bio-Formats, covering 160+ formats. The ones
you will meet in practice:

- **Brightfield WSI:** Aperio SVS (`.svs`), Hamamatsu NDPI (`.ndpi`), Leica SCN
  (`.scn`), 3DHISTECH MRXS (`.mrxs`), Ventana BIF (`.bif`), generic tiled TIFF.
- **Standards:** DICOM WSI (`.dcm`), OME-TIFF (`.ome.tif`).
- **Multiplex:** CODEX (directory of per-cycle TIFFs), Vectra Polaris (`.qptiff`).

OpenSlide handles most brightfield WSIs; Bio-Formats (JVM-backed) handles OME-TIFF,
CODEX, Vectra, and less common formats. Pick with the `backend` argument.

## Slide classes

`SlideData` is the base container. Typed subclasses set sensible defaults for a stain
and platform:

```python
from pathml.core import SlideData, HESlide, VectraSlide, CODEXSlide, MultiparametricSlide

wsi   = HESlide("brightfield.svs")                       # H&E brightfield WSI
vec   = VectraSlide("slide.qptiff")                      # Vectra multiplex IF
codex = CODEXSlide("codex_dir/")                         # CODEX spatial proteomics
mp    = MultiparametricSlide("stack.ome.tiff")           # generic multichannel

# The base class, with an explicit backend when auto-detection is not enough
slide = SlideData("slide.ome.tiff", backend="bioformats")
```

Useful attributes and methods (confirm names against your installed version):

- `slide.slide` — the underlying backend object.
- `slide.tiles` — the tile collection, populated after tiling.
- `slide.masks` — slide-level masks.
- `slide.shape` — pixel dimensions (multichannel slides include a channel axis).
- `slide.name` / `slide.labels` — identity and arbitrary key/value labels.
- `slide.extract_region(location, size, level)` — read one region as a numpy array.
- `slide.generate_tiles(...)` — yield tiles (usually driven for you by `run`).
- `slide.counts` — single-cell `AnnData`, present after `QuantifyMIF`.

## Tiling and pyramid levels

WSIs are multi-resolution pyramids. Level 0 is full resolution (e.g. 40x); each higher
level is downsampled (commonly 4x per step). Tiling is how you avoid loading gigapixel
images into memory. In PathML, tiling parameters are passed to `run` (the pipeline
engine tiles, then applies transforms):

```python
from pathml.preprocessing import Pipeline, TissueDetectionHE

wsi.run(
    Pipeline([TissueDetectionHE()]),
    tile_size=256,      # tile edge in pixels
    tile_stride=256,    # stride == tile_size -> no overlap; smaller -> overlap
    level=0,            # pyramid level (0 = highest resolution)
    pad=False,          # whether to pad edge tiles
)

for tile in wsi.tiles:
    image  = tile.image      # numpy array (H, W, C)
    coords = tile.coords     # (x, y) in level coordinates
    masks  = tile.masks      # dict of masks produced by the pipeline
```

Guidance:

- Use **overlapping tiles** (`tile_stride < tile_size`) for segmentation/detection to
  reduce boundary artifacts; stitch with blending (see `data_management.md`).
- Process at **level 1-2** for most preprocessing and training; reserve **level 0** for
  final high-resolution analysis.
- Inspect the pyramid before committing: the backend exposes level dimensions and
  downsample factors — check them so your `level` choice matches the magnification you
  need.

## Regions and thumbnails

```python
# Read a specific region without tiling the whole slide
region = wsi.extract_region(location=(10000, 15000), size=(512, 512), level=1)

# Low-res thumbnail for QC / visualization (via the backend)
thumb = wsi.slide.get_thumbnail(size=(1024, 1024))
```

## Metadata

Metadata is vendor-specific and lives on the backend. For OpenSlide-backed brightfield
slides the useful keys are the `openslide.*` properties:

- `openslide.objective-power` — scan magnification (e.g. 40).
- `openslide.mpp-x` / `openslide.mpp-y` — microns per pixel (needed for Mesmer
  segmentation and for pixel↔micron conversions in graph construction).
- `openslide.vendor` — scanner vendor.

DICOM WSIs expose DICOM tags (PatientID, StudyDate, ...) through the DICOM backend.
Multiplex slides expose `channel_names` and the number of channels/cycles.

## Batch loading

Process many slides with `SlideDataset` and Dask (see `data_management.md` for the full
distributed workflow):

```python
import glob
from pathml.core import SlideDataset

paths = glob.glob("data/*.svs")
dataset = SlideDataset([HESlide(p) for p in paths])
dataset.run(pipeline, tile_size=512, tile_stride=512, level=1, distributed=True)
```

## Troubleshooting

- **Slide fails to open.** Verify OpenSlide (brightfield) or a working JVM/JDK
  (Bio-Formats) is installed; try the other `backend`; check the path and permissions.
- **Out of memory.** Tile instead of reading full regions; process at a higher pyramid
  level; shrink `tile_size`; enable distributed processing.
- **Color varies across slides.** Apply `StainNormalizationHE` (see `preprocessing.md`).
- **Metadata missing.** Fields differ by vendor and format; inspect what the backend
  actually exposes before relying on a specific key.

## External references

- PathML docs: https://pathml.readthedocs.io/
- OpenSlide: https://openslide.org/ · Bio-Formats: https://www.openmicroscopy.org/bio-formats/
