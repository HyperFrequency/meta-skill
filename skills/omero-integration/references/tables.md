# OMERO.tables

OMERO.tables stores structured, columnar data (HDF5-backed) on the server and can attach it to
objects. Use it for per-image / per-ROI / per-well measurements you want to query later.

> Tables hold a server resource — **always `table.close()`** when finished.

## Column types (`omero.grid.*`)

| Column                  | Constructor args                          | Stores                     |
| ----------------------- | ----------------------------------------- | -------------------------- |
| `LongColumn`            | `(name, desc, values)`                    | 64-bit ints                |
| `DoubleColumn`          | `(name, desc, values)`                    | floats                     |
| `StringColumn`          | `(name, desc, maxlen, values)`            | text (fixed max length)    |
| `BoolColumn`            | `(name, desc, values)`                    | booleans                   |
| `LongArrayColumn` / `DoubleArrayColumn` | `(name, desc, values)`    | arrays per row             |
| `ImageColumn` / `RoiColumn` / `WellColumn` / `FileColumn` | `(name, desc, values)` | references to OMERO objects |

`StringColumn` **requires** a max length argument. Reference columns store object ids and make
rows clickable/joinable in OMERO clients.

## Create, fill, link

Initialize with empty-valued columns, then `addData` with the same columns carrying values.

```python
import omero.grid, omero.model

# 1. define schema (empty value lists)
cols = [
    omero.grid.ImageColumn('Image', 'Source image', []),
    omero.grid.DoubleColumn('MeanIntensity', 'Mean pixel value', []),
    omero.grid.LongColumn('CellCount', 'Cells detected', []),
    omero.grid.StringColumn('Category', 'Classification', 64, []),
]

# 2. create table in the default repository
resources = conn.c.sf.sharedResources()
repo_id = resources.repositories().descriptions[0].getId().getValue()
table = resources.newTable(repo_id, f"Analysis_{dataset_id}")
table.initialize(cols)

# 3. add rows (columns of equal length)
table.addData([
    omero.grid.ImageColumn('Image', '', image_ids),
    omero.grid.DoubleColumn('MeanIntensity', '', means),
    omero.grid.LongColumn('CellCount', '', counts),
    omero.grid.StringColumn('Category', '', 64, categories),
])

orig_file = table.getOriginalFile()
table.close()

# 4. wrap the file in a FileAnnotation and link it to the dataset
file_ann = omero.model.FileAnnotationI()
file_ann.setFile(omero.model.OriginalFileI(orig_file.id.val, False))
file_ann = conn.getUpdateService().saveAndReturnObject(file_ann)
link = omero.model.DatasetAnnotationLinkI()
link.setParent(omero.model.DatasetI(dataset_id, False))
link.setChild(omero.model.FileAnnotationI(file_ann.getId().getValue(), False))
conn.getUpdateService().saveAndReturnObject(link)
```

## Open and read

```python
of = conn.getObject("OriginalFile", attributes={'name': table_name})
table = resources.openTable(of._obj)
table.getNumberOfRows()
[ (c.name, c.description) for c in table.getHeaders() ]

# all rows
data = table.readCoordinates(range(table.getNumberOfRows()))
for col in data.columns:
    col.name, col.values

# a row slice: read(column_indices, start, stop)
data = table.read([0, 2], 0, table.getNumberOfRows())
table.close()
```

## Query with `getWhereList`

Returns matching row indices; feed them to `readCoordinates`. Conditions use column names and
PyTables-style operators (`&`, `|`, `==`, `<`, `>`).

```python
rows = table.getWhereList("(CellCount > 100)", variables={},
                          start=0, stop=table.getNumberOfRows(), step=0)
rows = table.getWhereList("(MeanIntensity > 100) & (MeanIntensity < 150)", {}, 0, n, 0)
rows = table.getWhereList("(Category == 'Good') | (Category == 'Excellent')", {}, 0, n, 0)

data = table.readCoordinates(rows)
```

## Append / delete

```python
# append: open existing table, addData, close
table = resources.openTable(orig_file._obj)
table.addData([...])          # same column schema
table.close()

# delete the whole table (deletes the underlying file)
conn.deleteObjects("OriginalFile", [file_id], wait=True)

# unlink only (keep table, drop the dataset association)
conn.deleteObjects("DatasetAnnotationLink", [ann.link.getId()], wait=True)
```

## Finding tables on an object

```python
for ann in dataset.listAnnotations():
    if isinstance(ann, omero.gateway.FileAnnotationWrapper):
        name = ann.getFile().getName()
        if "Table" in name or name.endswith(".h5"):
            table = resources.openTable(ann.getFile()._obj)
            table.getNumberOfRows(); [h.name for h in table.getHeaders()]
            table.close()
```

## Schema patterns

```python
# ROI measurements
[ ImageColumn('Image', '', []), RoiColumn('ROI', '', []),
  LongColumn('ChannelIndex', '', []), DoubleColumn('Area', '', []),
  DoubleColumn('MeanIntensity', '', []), DoubleColumn('IntegratedDensity', '', []),
  StringColumn('CellType', '', 32, []) ]

# Screening results
[ WellColumn('Well', '', []), LongColumn('FieldIndex', '', []),
  DoubleColumn('CellCount', '', []), DoubleColumn('Viability', '', []),
  StringColumn('Phenotype', '', 128, []), BoolColumn('Hit', '', []) ]
```

## Guidance

- `close()` every table (create and read paths both open a server handle).
- Size `StringColumn` max length generously; it is fixed at creation.
- Use `ImageColumn`/`RoiColumn`/`WellColumn` for references so rows link back to objects.
- Query with `getWhereList` rather than reading all rows and filtering in Python.
- Add data in batches for large result sets; give columns descriptions.
- For downstream stats, read the table into `polars`/`pandas` and analyze with `exploratory-data-analysis`.
