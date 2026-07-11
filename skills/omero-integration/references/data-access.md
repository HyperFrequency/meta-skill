# Data Access & Retrieval

Navigating the OMERO object graph and pulling objects out of it. All calls assume a live
`conn` (see `connection.md`).

## Hierarchies

```
Project ─< Dataset ─< Image                      # standard
Screen  ─< Plate   ─< Well ─< WellSample ─ Image  # high-content screening
```

## Retrieving objects

`getObject(type, id)` returns one wrapper or `None`. `getObjects(type, ...)` returns a
generator. Supported `type` strings include `Project`, `Dataset`, `Image`, `Screen`, `Plate`,
`Well`, `Roi`, `Experimenter`, `ExperimenterGroup`, `Fileset`, and annotation types
(`TagAnnotation`, `FileAnnotation`, `MapAnnotation`, ...).

```python
image = conn.getObject("Image", image_id)          # single, or None
if image is None:
    ...  # not found OR wrong group context

projects = conn.getObjects("Project", [1, 2, 3])   # by id list
```

### Filtering, sorting, pagination with `opts`

```python
me = conn.getUser().getId()
grp = conn.getEventContext().groupId

conn.getObjects("Image", opts={
    'owner': me,                    # filter by owner id
    'group': grp,                   # filter by group id
    'dataset': dataset_id,          # images in this dataset
    'orphaned': True,               # only objects with no parent
    'order_by': 'lower(obj.name)',  # add ' desc' for descending
    'limit': 100,
    'offset': 0,
})
```

Paginate large sets by looping `offset` in `limit`-sized steps until an empty page returns.

### Query by attribute value

```python
conn.getObjects("Image", attributes={"name": "sample_001.tif"})
conn.getObjects("TagAnnotation", attributes={"textValue": "experiment_tag"})
conn.getObjects("MapAnnotation", attributes={"ns": "custom.namespace"})
```

## Walking the hierarchy

```python
# Down
project = conn.getObject("Project", project_id)
for dataset in project.listChildren():
    for image in dataset.listChildren():
        ...

# Up
dataset = image.getParent()      # None if orphaned
project = dataset.getParent()

# Cheap counts (no child load)
dataset.countChildren()          # images in dataset
image.countAnnotations()
```

## Image dimensions and metadata

```python
image.getSizeX(); image.getSizeY()          # pixels
image.getSizeZ(); image.getSizeC(); image.getSizeT()   # Z-sections, channels, timepoints
image.getPixelsType()                        # 'uint8', 'uint16', 'float', ...

# Physical pixel size (OMERO 5.1+): units=True gives a Length object
px = image.getPixelSizeX(units=True)
px.getValue(); px.getSymbol()                # e.g. 0.325 'µm'
image.getPixelSizeX()                         # plain float in µm

# Channels
for ch in image.getChannels():
    ch.getLabel(); ch.getColor().getRGB(); ch.getEmissionWave()

# Provenance
image.getAcquisitionDate()
d = image.getDetails()
d.getOwner().getFullName(); d.getGroup().getName(); d.getCreationEvent().getTime()
```

## Screening data (plates & wells)

```python
plate = conn.getObject("Plate", plate_id)
plate.getGridSize()          # e.g. (8, 12) for a 96-well plate
plate.getNumberOfFields()

for well in plate.listChildren():
    well.row, well.column
    n = well.countWellSample()          # fields (images) in the well
    for i in range(n):
        img = well.getImage(i)          # image for field i

well = plate.getWell(row=0, column=0)   # direct access
for ws in well.listChildren():          # WellSample objects
    ws.getImage()
```

## Orphans and counts

```python
conn.getObjects("Dataset", opts={'orphaned': True})   # not in any project
conn.getObjects("Image",   opts={'orphaned': True})   # not in any dataset
conn.getObjects("Plate",   opts={'orphaned': True})
```

## Practical guidance

- Always null-check `getObject()`; a `None` is often a group-context problem (`connection.md`).
- Filter server-side with `opts`/`attributes` rather than pulling everything and filtering in Python.
- Use `countChildren()` to decide whether to load a large dataset.
- Reuse fetched wrappers instead of re-querying the same object.
