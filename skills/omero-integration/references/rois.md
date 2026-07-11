# Regions of Interest (ROIs)

An OMERO ROI is a container linked to an image; it holds one or more **shapes**, and each
shape can be pinned to a specific Z-section, timepoint, and (for masks) channel.

Shape types: `RectangleI`, `EllipseI`, `LineI`, `PointI`, `PolygonI`, `PolylineI`, `MaskI`.

> Model fields need Ice `rtypes`: `rdouble`, `rint`, `rstring`. Read them back with `.getValue()`.

## Helpers

```python
from omero.rtypes import rdouble, rint, rstring
import omero.model

def create_roi(conn, image, shapes):
    roi = omero.model.RoiI()
    roi.setImage(image._obj)
    for s in shapes:
        roi.addShape(s)
    return conn.getUpdateService().saveAndReturnObject(roi)

def rgba_to_int(r, g, b, a=255):
    """OMERO stores colors as a signed 32-bit int."""
    return int.from_bytes([r, g, b, a], byteorder='big', signed=True)
```

## Creating shapes

```python
# Rectangle
rect = omero.model.RectangleI()
rect.x, rect.y = rdouble(50), rdouble(100)
rect.width, rect.height = rdouble(200), rdouble(150)
rect.theZ, rect.theT = rint(0), rint(0)
rect.textValue = rstring("Cell Region")
rect.fillColor   = rint(rgba_to_int(255, 0, 0, 50))     # translucent red
rect.strokeColor = rint(rgba_to_int(255, 255, 0, 255))  # yellow border

# Ellipse (x,y are the CENTER; radiusX/radiusY the semi-axes)
ell = omero.model.EllipseI()
ell.x, ell.y = rdouble(250), rdouble(250)
ell.radiusX, ell.radiusY = rdouble(100), rdouble(75)
ell.theZ, ell.theT = rint(0), rint(0)

# Line
ln = omero.model.LineI()
ln.x1, ln.y1, ln.x2, ln.y2 = rdouble(100), rdouble(100), rdouble(300), rdouble(200)
ln.theZ, ln.theT = rint(0), rint(0)

# Point
pt = omero.model.PointI()
pt.x, pt.y = rdouble(150), rdouble(150)
pt.theZ, pt.theT = rint(0), rint(0)

# Polygon (points = "x1,y1 x2,y2 ..." string)
poly = omero.model.PolygonI()
poly.points = rstring("10,20 50,150 200,200 250,75")
poly.theZ, poly.theT = rint(0), rint(0)
from omero.model.enums import UnitsLength
poly.strokeWidth = omero.model.LengthI(2, UnitsLength.PIXEL)

roi = create_roi(conn, image, [rect, ell])   # one ROI can hold many shapes
roi.getId().getValue()
```

### Mask shapes

Masks store a bit-packed binary array. Build the packed bytes, then set geometry + channel:

```python
mask = omero.model.MaskI()
mask.setX(rdouble(x)); mask.setY(rdouble(y))
mask.setWidth(rdouble(w)); mask.setHeight(rdouble(h))
mask.setTheZ(rint(z)); mask.setTheT(rint(t)); mask.setTheC(rint(c))
mask.setBytes(packed_bytes)     # 1-bit-per-pixel packed mask
mask.textValue = rstring("Segmentation Mask")
```

The packing turns a 0/1 array into big-endian bit-packed bytes (8 px/byte for 1 byte-per-pixel).
See the source `references/rois.md` in upstream for a full `create_mask_bytes` implementation
if you need to author masks from NumPy; for reading segmentation results back, `getShapeStats`
(below) is usually enough.

## Retrieving and parsing ROIs

```python
roi_service = conn.getRoiService()
result = roi_service.findByImage(image_id, None)   # result.rois is a list

for roi in result.rois:
    for shape in roi.copyShapes():
        shape.getId().getValue()
        z = shape.getTheZ().getValue() if shape.getTheZ() else None
        label = shape.getTextValue().getValue() if shape.getTextValue() else ""
        if isinstance(shape, omero.model.RectangleI):
            shape.getX().getValue(), shape.getY().getValue(), \
            shape.getWidth().getValue(), shape.getHeight().getValue()
        elif isinstance(shape, omero.model.EllipseI):
            shape.getRadiusX().getValue(), shape.getRadiusY().getValue()
        elif isinstance(shape, omero.model.PolygonI):
            shape.getPoints().getValue()
        # LineI -> getX1/Y1/X2/Y2; PointI -> getX/getY; MaskI -> getX/Y/Width/Height
```

## Intensity statistics inside shapes

Prefer the server-side stats service over manual pixel extraction — it is faster and handles
non-rectangular shapes correctly.

```python
shape_ids = [s.id.val for roi in result.rois for s in roi.copyShapes()]
z, t, channels = 0, 0, [0]
stats = roi_service.getShapeStatsRestricted(shape_ids, z, t, channels)

for i, st in enumerate(stats):
    st.pointsCount[0]   # pixel count (area)
    st.min[0]; st.mean[0]; st.max[0]; st.sum[0]; st.stdDev[0]   # indexed by channel
```

For simple rectangles you can also slice the NumPy plane directly
(`plane[y:y+h, x:x+w]`), but the stats service is the general solution.

## Editing and deleting

```python
# Modify a shape, then re-save its ROI
shape.setWidth(rdouble(150)); shape.setTextValue(rstring("Updated"))
conn.getUpdateService().saveAndReturnObject(roi._obj)

# Remove a shape from an ROI
roi.removeShape(shape)
conn.getUpdateService().saveAndReturnObject(roi)

# Delete whole ROIs (asynchronous; wait=True blocks until done)
roi_ids = [roi.getId().getValue() for roi in result.rois]
conn.deleteObjects("Roi", roi_ids, wait=True)
```

## Guidance

- Always set `theZ`/`theT`; an unset plane means "applies to all planes", which is rarely intended.
- Validate coordinates fall within `getSizeX()/getSizeY()` before saving.
- Group related shapes under one ROI; use `textValue` for stable labels.
- Batch-create ROIs across a dataset or across a Z-stack by building a shape list, then one `create_roi`.
- Persist ROI measurements into an OMERO.table keyed by `ImageColumn`/`RoiColumn` (`tables.md`).
