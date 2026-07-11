# Metadata & Annotations

Annotations attach metadata to any OMERO object (Image, Dataset, Project, ...). Each annotation
is created once, then **linked** to one or more objects.

## Annotation types

| Wrapper class (`omero.gateway.*`) | Holds                                   |
| --------------------------------- | --------------------------------------- |
| `TagAnnotationWrapper`            | a text label for categorization         |
| `MapAnnotationWrapper`            | ordered key-value pairs                 |
| `FileAnnotationWrapper`           | a file attachment (CSV, PDF, ...)       |
| `CommentAnnotationWrapper`        | free text                               |
| `LongAnnotationWrapper`           | one integer                             |
| `DoubleAnnotationWrapper`         | one float                               |
| `BooleanAnnotationWrapper`        | one bool                                |
| `TimestampAnnotationWrapper`      | a date/time                             |

## Create-and-link pattern

Every annotation follows the same shape: construct with `conn`, set value + namespace, `save()`,
then `obj.linkAnnotation(ann)`.

```python
import omero.gateway

tag = omero.gateway.TagAnnotationWrapper(conn)
tag.setValue("Experiment 2024")
tag.setDescription("optional")
tag.save()
conn.getObject("Project", project_id).linkAnnotation(tag)

# Reuse an existing tag across many images (don't create duplicates)
tag = conn.getObject("TagAnnotation", tag_id)
for image in conn.getObjects("Image", [img1, img2, img3]):
    image.linkAnnotation(tag)
```

## Map (key-value) annotations

```python
import omero.constants.metadata

kv = [["Drug", "Monastrol"], ["Concentration", "5 mg/ml"], ["Time", "24 h"]]
m = omero.gateway.MapAnnotationWrapper(conn)
m.setNs(omero.constants.metadata.NSCLIENTMAPANNOTATION)  # shows in web UI KV panel
m.setValue(kv)
m.save()
conn.getObject("Image", image_id).linkAnnotation(m)

# Read back
for ann in image.listAnnotations():
    if isinstance(ann, omero.gateway.MapAnnotationWrapper):
        for key, value in ann.getValue():
            print(key, value)
```

Use `NSCLIENTMAPANNOTATION` for values you want visible/editable in OMERO.web; use a custom
namespace (reverse-domain, e.g. `org.mylab.microscopy.v1`) for machine-owned metadata.

## File annotations

```python
# Upload + attach
file_ann = conn.createFileAnnfromLocalFile(
    "results.csv", mimetype="text/csv",
    ns="org.mylab.analysis", desc="segmentation results")
conn.getObject("Dataset", dataset_id).linkAnnotation(file_ann)

# Download (filter by namespace, stream in chunks)
for ann in image.listAnnotations(ns="org.mylab.analysis"):
    if isinstance(ann, omero.gateway.FileAnnotationWrapper):
        with open(ann.getFile().getName(), 'wb') as f:
            for chunk in ann.getFileInChunks():
                f.write(chunk)

# Inspect
of = ann.getFile()
of.getName(); of.getSize(); of.getMimetype()
```

Common mimetypes: `text/csv`, `text/plain`, `application/pdf`, `application/json`,
`image/png`, `application/zip`, `application/octet-stream`.

## Comments and numeric annotations

```python
c = omero.gateway.CommentAnnotationWrapper(conn); c.setValue("Good staining"); c.save()
image.linkAnnotation(c)

n = omero.gateway.LongAnnotationWrapper(conn); n.setValue(42); n.setNs("org.mylab.cell_count"); n.save()
d = omero.gateway.DoubleAnnotationWrapper(conn); d.setValue(3.14159); d.setNs("org.mylab.intensity"); d.save()
```

## Listing, filtering, counting

```python
for ann in project.listAnnotations():          # all annotations on an object
    ann.getId(); ann.OMERO_TYPE

image.listAnnotations(ns="org.mylab.qc")        # only that namespace
dataset.getAnnotation("org.mylab.analysis")     # first annotation with a namespace, or None

conn.countAnnotations('Image', [1, 2, 3])       # -> {id: count}

# Links across many parents in one call
for link in conn.getAnnotationLinks('Image', parent_ids=[1, 2, 3]):
    link.getParent().getId(); link.getChild()   # child is the annotation
```

## Linking, unlinking, deleting

`linkAnnotation` is the normal path. To build links manually:

```python
link = omero.model.ImageAnnotationLinkI()
link.setParent(omero.model.ImageI(image_id, False))
link.setChild(omero.model.TagAnnotationI(tag_id, False))
conn.getUpdateService().saveAndReturnObject(link)
```

**Delete the annotation** (removes it everywhere):

```python
ids = [a.getId() for a in image.listAnnotations(ns="org.mylab.temp")]
conn.deleteObjects('Annotation', ids, wait=True)
```

**Unlink only** (keep the annotation, drop the association) — delete the *link*, e.g.
`ImageAnnotationLink`:

```python
link_ids = [a.link.getId() for a in image.listAnnotations()
            if isinstance(a, omero.gateway.TagAnnotationWrapper)]
conn.deleteObjects("ImageAnnotationLink", link_ids, wait=True)
```

## Guidance

- Namespace everything; reverse-domain notation with an optional version keeps schemas evolvable.
- Reuse tags instead of creating near-duplicates.
- Prefer map annotations over free-text comments for anything structured/queryable.
- Deletes are async — pass `wait=True` or monitor a callback (`advanced.md`).
- To store many rows of measurements, use OMERO.tables (`tables.md`), not one annotation per value.
