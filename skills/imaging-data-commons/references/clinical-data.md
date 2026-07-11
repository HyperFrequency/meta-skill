# Clinical Data Reference

Many IDC collections carry clinical / tabular data — staging, outcomes, demographics, treatment —
alongside the images. `idc-index` exposes it with no authentication; the same data is also in
BigQuery (`idc_current_clinical`) for heavier cross-collection joins. Clinical data began at IDC v11,
so not every collection has it.

## Load Clinical Data via idc-index

`clinical_index` is a dictionary that maps clinical table columns to collections. Fetching it also
downloads the underlying clinical tables so you can load them as DataFrames.

```python
from idc_index import IDCClient
client = IDCClient()

client.fetch_index("clinical_index")

# What clinical tables/columns exist, per collection
client.sql_query("""SELECT DISTINCT collection_id, table_name, column_label
                    FROM clinical_index ORDER BY collection_id""")

# Load one clinical table as a pandas DataFrame
clinical_df = client.get_clinical_table("nlst_canc")
```

## Discover Fields Across Collections

`clinical_index` is a data dictionary — search it to find which collections record a variable you
care about before loading any table.

```python
# Collections that record tumor stage
client.sql_query("""SELECT DISTINCT collection_id, table_name, column_label
                    FROM clinical_index WHERE LOWER(column_label) LIKE '%stage%'""")

# All columns for one collection's table
client.sql_query("""SELECT column_label FROM clinical_index
                    WHERE collection_id='nlst' AND table_name='nlst_canc'""")
```

## Join Clinical to Imaging

The join key is `PatientID`: the DICOM `PatientID` in the imaging `index` matches the patient
identifier in the clinical tables (called `dicom_patient_id` in BigQuery). Do the join in pandas after
loading both sides.

```python
import pandas as pd

client.fetch_index("clinical_index")
clinical = client.get_clinical_table("nlst_canc")          # clinical rows keyed by patient
imaging = client.sql_query("""SELECT PatientID, StudyInstanceUID, SeriesInstanceUID, Modality
                              FROM index WHERE collection_id='nlst' AND Modality='CT'""")

# Align the patient-id column names, then merge
merged = imaging.merge(clinical, left_on="PatientID",
                       right_on="dicom_patient_id", how="inner")
```

> Clinical schemas vary substantially by collection — column names, encodings, and value conventions
> differ. Always inspect the table's columns (via `clinical_index` or the loaded DataFrame) before
> assuming a field exists.

## Value Mapping

Clinical values are often coded (e.g. a stage stored as `400` meaning "Stage IV"). The
`clinical_index` dictionary carries the human-readable labels/descriptions for columns — consult it to
decode values rather than guessing. In BigQuery the equivalent decoding lives in the `values` field of
`column_metadata` (see [bigquery.md](bigquery.md)).

Typical pattern:

1. Find the table and column in `clinical_index`.
2. Read the column's label/value descriptions to build a code → meaning map.
3. Load the table with `get_clinical_table` and apply the map (e.g. `df['stage'].map(code_to_label)`).

## Cohort Selection Workflow

1. Search `clinical_index` for collections and columns matching your clinical criterion.
2. Load the relevant clinical table(s) with `get_clinical_table`.
3. Filter to the patients meeting the criterion → a set of `PatientID`s.
4. Query `index` for those patients' imaging series (by `PatientID` / `collection_id`).
5. Download with `download_from_selection` and save the Series UIDs / `crdc_series_uuid`s as a manifest
   for reproducibility (see [download-and-cli.md](download-and-cli.md) and
   [cloud-storage.md](cloud-storage.md)).

## When to Use BigQuery Instead

Use the BigQuery clinical datasets when you need cross-collection clinical queries, joins that span
many tables, or SQL-side filtering the local tables make awkward. The content is identical; BigQuery
requires a billing-enabled GCP project. See [bigquery.md](bigquery.md) for `table_metadata`,
`column_metadata`, and `dicom_patient_id` join examples.

## Links

[IDC clinical data docs](https://learn.canceridc.dev/data/clinical-data) ·
[idc-index docs](https://idc-index.readthedocs.io/)
