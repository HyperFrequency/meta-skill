# Querying and Schema Reference

Deep reference for the `idc-index` metadata tables: the table catalogue, join keys, schema
discovery, key `index` columns, and copy-paste SQL recipes. All queries run through
`client.sql_query(sql)` and return a pandas DataFrame.

## Index Tables

`idc-index` provides several metadata tables. `index` and `prior_versions_index` load automatically
when `IDCClient()` is constructed; the rest require `client.fetch_index("<name>")` before you query
them. Each table is also exposed as a pandas attribute (`client.index`, `client.sm_index`, ...).

| Table | 1 row = | Load | Contents |
|-------|---------|------|----------|
| `index` | 1 DICOM series | auto | Primary metadata for all current IDC data |
| `prior_versions_index` | 1 DICOM series | auto | Series from previous IDC releases (deprecated data) |
| `collections_index` | 1 collection | `fetch_index` | Collection-level metadata: cancer types, tumor locations, species |
| `analysis_results_index` | 1 analysis-result collection | `fetch_index` | Derived datasets (annotations, segmentations) and their source collections |
| `clinical_index` | 1 clinical column | `fetch_index` | Dictionary mapping clinical table columns to collections |
| `sm_index` | 1 slide-microscopy series | `fetch_index` | Pathology series metadata (objective power, pixel spacing) |
| `sm_instance_index` | 1 slide-microscopy instance | `fetch_index` | Instance-level (SOPInstanceUID) slide-microscopy metadata |
| `seg_index` | 1 DICOM Segmentation series | `fetch_index` | Segmentation metadata: algorithm, segment count, source-image reference |

## Schema Discovery — the Authoritative Source

Column names and types vary with the installed `idc-index` version. **Always** consult
`client.indices_overview` (a dict) or `client.get_index_schema("<table>")` rather than assuming
columns. Many columns are populated directly from DICOM attributes; the column description says so.

```python
# List every table with its install state and description
for name, info in client.indices_overview.items():
    print(name, info['installed'], info['description'])

# Full schema for one table
schema = client.indices_overview["index"]["schema"]     # or: client.get_index_schema("index")
print(schema['table_description'])
for col in schema['columns']:
    print(col['name'], col['type'], col.get('description', ''))

# Which columns come straight from DICOM attributes
dicom_cols = [c['name'] for c in schema['columns'] if 'DICOM' in c.get('description', '').upper()]
```

## Key Columns in the Primary `index` Table

Most-used columns (query `indices_overview` for the complete list). "DICOM" marks columns whose value
is the same-named DICOM attribute.

| Column | Type | DICOM | Notes |
|--------|------|-------|-------|
| `collection_id` | STRING | no | IDC collection identifier |
| `analysis_result_id` | STRING | no | Present when the series belongs to an analysis-result collection |
| `source_DOI` | STRING | no | DOI of the dataset publication; basis for citations |
| `PatientID` | STRING | yes | Patient identifier (join key to clinical data) |
| `StudyInstanceUID` | STRING | yes | DICOM Study UID |
| `SeriesInstanceUID` | STRING | yes | DICOM Series UID — pass to downloads and the viewer |
| `Modality` | STRING | yes | CT, MR, PT, SM, SEG, RTSTRUCT, SR, ... |
| `BodyPartExamined` | STRING | yes | Anatomical region (values are inconsistent across collections — explore first) |
| `SeriesDescription` | STRING | yes | Free-text series description |
| `Manufacturer` / `ManufacturerModelName` | STRING | yes | Acquisition equipment |
| `StudyDate`, `PatientSex`, `PatientAge` | STRING | yes | Study/patient attributes |
| `license_short_name` | STRING | no | CC BY 4.0, CC BY-NC 4.0, ... |
| `series_size_MB` | FLOAT | no | Series size in MB — use to estimate downloads |
| `instanceCount` | INTEGER | no | Number of DICOM instances in the series |
| `series_aws_url` | STRING | no | S3 URL to the series folder |
| `crdc_series_uuid` | STRING | no | Immutable version identifier — pin for reproducibility |

## Join Keys

Key columns are not formally labeled; this is a practical subset for joins.

| Join column | Tables | Use |
|-------------|--------|-----|
| `collection_id` | index, prior_versions_index, collections_index, clinical_index | Link series to collection or clinical metadata |
| `SeriesInstanceUID` | index, prior_versions_index, sm_index, sm_instance_index, seg_index | Link a series across tables |
| `StudyInstanceUID` / `PatientID` | index, prior_versions_index | Link studies/patients across current and historical data |
| `analysis_result_id` | index, analysis_results_index | Link series to analysis-result metadata |
| `source_DOI` | index, analysis_results_index | Link by publication DOI |
| `segmented_SeriesInstanceUID` | seg_index → index | Link a segmentation to its **source** image (`seg_index.segmented_SeriesInstanceUID = index.SeriesInstanceUID`) |

> `Subjects`, `Updated`, and `Description` appear in multiple tables with **different meanings**
> (counts vs identifiers, differing update contexts) — check the schema before relying on them.

## SQL Recipes

### Discover filter values (do this before filtering)

```python
client.sql_query("SELECT DISTINCT Modality, COUNT(*) n FROM index GROUP BY Modality ORDER BY n DESC")
client.sql_query("""SELECT DISTINCT BodyPartExamined, COUNT(*) n FROM index
                    WHERE Modality='CT' AND BodyPartExamined IS NOT NULL
                    GROUP BY BodyPartExamined ORDER BY n DESC LIMIT 20""")
```

### Filter by cancer type (join to collections_index)

```python
client.fetch_index("collections_index")
client.sql_query("""
    SELECT i.collection_id, i.PatientID, i.SeriesInstanceUID, i.Modality
    FROM index i JOIN collections_index c ON i.collection_id = c.collection_id
    WHERE c.CancerTypes LIKE '%Breast%' AND i.Modality = 'MR' LIMIT 20
""")
```

### Find segmentations and structure sets

Not all derived objects live in analysis-result collections — some are deposited alongside images.
Search by `Modality` to catch them all (`SEG` = DICOM Segmentation, `RTSTRUCT` = RT Structure Set).

```python
# All segmentations/structure sets, by collection
client.sql_query("""SELECT collection_id, Modality, COUNT(*) n FROM index
                    WHERE Modality IN ('SEG','RTSTRUCT') GROUP BY collection_id, Modality ORDER BY n DESC""")

# seg_index: segmentations joined to their source image
client.fetch_index("seg_index")
client.sql_query("""
    SELECT s.SeriesInstanceUID AS seg_series, s.AlgorithmName, s.total_segments,
           src.collection_id, src.Modality AS source_modality, src.BodyPartExamined
    FROM seg_index s JOIN index src ON s.segmented_SeriesInstanceUID = src.SeriesInstanceUID
    WHERE s.AlgorithmType = 'AUTOMATIC' LIMIT 10
""")

# Curated analysis-result collections
client.fetch_index("analysis_results_index")
client.sql_query("""SELECT analysis_result_id, analysis_result_title, Collections, Modalities
                    FROM analysis_results_index""")
```

### Slide microscopy (pathology)

```python
client.fetch_index("sm_index")
client.sql_query("""
    SELECT i.collection_id, COUNT(*) AS slides, MIN(s.min_PixelSpacing_2sf) AS min_resolution
    FROM sm_index s JOIN index i ON s.SeriesInstanceUID = i.SeriesInstanceUID
    GROUP BY i.collection_id ORDER BY slides DESC
""")
```

### Estimate download size

```python
client.sql_query("""SELECT SUM(series_size_MB) AS total_mb, COUNT(*) AS series_count
                    FROM index WHERE collection_id='nlst' AND Modality='CT'""")
```

### Locate clinical data

```python
client.fetch_index("clinical_index")
client.sql_query("""SELECT collection_id, table_name, COUNT(DISTINCT column_label) AS columns
                    FROM clinical_index GROUP BY collection_id, table_name ORDER BY collection_id""")
```

See [clinical-data.md](clinical-data.md) for loading and joining clinical tables to imaging.
