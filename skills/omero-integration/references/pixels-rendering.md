# Pixels, Rendering & Image Creation

Reading raw pixel data as NumPy, rendering RGB views, projections, and writing new images.

> **Channel indexing gotcha:** pixel access is **0-indexed** (`getPlane(z, c, t)` with
> `c=0..N-1`); rendering methods (`setActiveChannels`, colors, windows) are **1-indexed**.

## Reading raw pixels

`getPlane`/`getPlanes`/`getTiles` return NumPy arrays with the image's native dtype.

```python
pixels = image.getPrimaryPixels()

# One plane (Y, X)
plane = pixels.getPlane(z, c, t)         # e.g. getPlane(0, 0, 0)
plane.shape, plane.dtype, plane.min(), plane.max()

# Many planes at once — pass (z, c, t) tuples; returns a generator
zct = [(z, 0, 0) for z in range(image.getSizeZ())]
z_stack = np.array(list(pixels.getPlanes(zct)))   # (Z, Y, X)

# A tile / sub-region: append (x, y, w, h) to each coordinate
tile = (50, 50, 100, 100)                 # x, y, width, height
tile_data = list(pixels.getTiles([(0, 0, 0, tile)]))[0]   # shape (h, w)
```

For very large images, iterate tiles instead of loading whole planes to bound memory.

## Histograms

```python
# hist for channel 0 at z=0, t=0 with 256 bins
hist = image.getHistogram([0], 256, False, 0, 0)
# pass multiple channel indices to get one histogram per channel
```

## Rendering to RGB / thumbnails

`renderImage(z, t)` returns a PIL `Image` using the current rendering settings.

```python
from PIL import Image
from io import BytesIO

z, t = image.getSizeZ() // 2, 0
image.renderImage(z, t).save("view.jpg")

thumb_bytes = image.getThumbnail(size=(96, 96))   # JPEG bytes
Image.open(BytesIO(thumb_bytes)).save("thumb.jpg")
```

### Rendering settings (1-indexed channels)

```python
image.isGreyscaleRenderingModel(); image.getDefaultZ(); image.getDefaultT()
for ch in image.getChannels():
    ch.getLabel(); ch.getColor().getHtml(); ch.isActive()
    ch.getWindowStart(); ch.getWindowEnd(); ch.getWindowMin(); ch.getWindowMax()

image.setGreyscaleRenderingModel()          # or setColorRenderingModel()
image.setActiveChannels([1, 3])             # activate channels 1 and 3
image.setActiveChannels([1, 2, 3], colors=['FF0000', '00FF00', '0000FF'])  # hex; None keeps existing
image.setActiveChannels([1, 2], windows=[[100.0, 500.0], [50.0, 300.0]])   # intensity range
image.setDefaultZ(5); image.setDefaultT(0)

image.saveDefaults()                        # persist current settings
image.resetDefaults(save=True)              # back to import settings
```

### Projections

```python
image.setProjection('intmax')   # 'normal' | 'intmax' | 'intmean' | 'intmin'
image.renderImage(0, 0).save("max_projection.jpg")
image.setProjection('normal')   # reset
```

## Creating images from NumPy

`conn.createImageFromNumpySeq(plane_gen, name, sizeZ, sizeC, sizeT, description=..., dataset=...)`
consumes a generator that yields 2D arrays in **Z, C, T order** (outer→inner loop: z, then c,
then t). Using a generator keeps memory bounded.

```python
def plane_gen():
    for z in range(size_z):
        for c in range(size_c):
            for t in range(size_t):
                yield np.random.randint(0, 255, (size_y, size_x), dtype=np.uint8)

new_image = conn.createImageFromNumpySeq(
    plane_gen(), "Result", size_z, size_c, size_t,
    description="from analysis", dataset=source.getParent(),  # dataset=None to leave orphaned
)
new_image.getId()
```

Match your array dtype to the intended OMERO pixel type. For a derived image (e.g. averaging
channels or a Z max-projection), read source planes inside the generator and yield the
computed result, setting `sizeZ`/`sizeC` to the output shape.

## Setting physical pixel size on a new image

```python
from omero.model.enums import UnitsLength
import omero.model

pix = new_image.getPrimaryPixels()._obj
pix.setPhysicalSizeX(omero.model.LengthI(0.325, UnitsLength.MICROMETER))
pix.setPhysicalSizeY(omero.model.LengthI(0.325, UnitsLength.MICROMETER))
pix.setPhysicalSizeZ(omero.model.LengthI(1.0,   UnitsLength.MICROMETER))
conn.getUpdateService().saveObject(pix)
```

`UnitsLength` members: `ANGSTROM, NANOMETER, MICROMETER, MILLIMETER, CENTIMETER, METER, PIXEL`.
When you derive a projection, copy X/Y sizes from the source and drop Z.

## Tips

- Prefer generators for `createImageFromNumpySeq` — never build the full 5D array in RAM.
- Cache/reuse rendering settings when batch-rendering many images.
- Cast to `float` for math, then back to the source dtype before yielding a derived plane.
- Once you have the NumPy arrays, hand segmentation/quantification to `bioimage-analysis`
  or `histolab`; write results back via `tables.md` or `metadata.md`.
