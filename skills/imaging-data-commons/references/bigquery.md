# BigQuery Reference

Escalate to BigQuery only when the `idc-index` mini-index cannot answer the question. Use it for the
full DICOM tag set (thousands of tags, not the ~50 in the mini-index), nested DICOM sequence
attributes, private vendor elements, or complex cross-collection / clinical joins. For discovery and
downloads, stay on `idc-index`.

## Prerequisites

A Google account, a GCP project with billing enabled (first 1 TB/month free), and either the BigQuery
console or the `google-cloud-bigquery` package.

```bash
gcloud auth application-default login
pip install google-cloud-bigquery
```

## Datasets

All IDC tables live in the `bigquery-public-data` project.

- `bigquery-public-data.idc_current.*` and `...idc_current_clinical.*` — latest release (exploration).
- `bigquery-public-data.idc_v{N}.*` and `...idc_v{N}_clinical.*` — pinned version (**use for reproducibility**).

## Key Tables

- **`dicom_all`** — primary table joining complete DICOM metadata with IDC columns (`collection_id`, `gcs_url`, `license_short_name`). Prefer this over `dicom_metadata` (smaller, cheaper).
- **`segmentations`**, **`measurement_groups`**, **`qualitative_measurements`**, **`quantitative_measurements`** — derived SR/SEG tables.
- **`original_collections_metadata`** — collection descriptions (unnest `Sources`).

```sql
SELECT collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID,
       Modality, BodyPartExamined, gcs_url, license_short_name
FROM `bigquery-public-data.idc_current.dicom_all`
WHERE Modality = 'CT' AND BodyPartExamined = 'CHEST'
LIMIT 10
```

## Common Patterns

```sql
-- Collections by criteria
SELECT collection_id, COUNT(DISTINCT PatientID) patients,
       ARRAY_AGG(DISTINCT Modality) modalities
FROM `bigquery-public-data.idc_current.dicom_all`
WHERE BodyPartExamined LIKE '%BRAIN%'
GROUP BY collection_id HAVING patients > 50 ORDER BY patients DESC;

-- Segmentations joined to source images
SELECT src.collection_id, seg.SeriesInstanceUID seg_series,
       seg.SegmentedPropertyType, src.SeriesInstanceUID source_series, src.Modality
FROM `bigquery-public-data.idc_current.segmentations` seg
JOIN `bigquery-public-data.idc_current.dicom_all` src
  ON seg.segmented_SeriesInstanceUID = src.SeriesInstanceUID
WHERE src.collection_id = 'qin_prostate_repeatability' LIMIT 10;
```

## Private DICOM Elements

Private (vendor-specific) elements often hold acquisition parameters absent from standard tags —
diffusion b-values, gradient directions, scanner settings. They use odd-numbered groups (0019, 0043,
2001, ...); each vendor reserves a block via a Private Creator at `(gggg,0010–00FF)`.

The same parameter may live in both standard and private tags — older scanners populate only private
ones, so check both:

| Parameter | Standard | GE | Siemens | Philips |
|-----------|----------|-----|---------|---------|
| Diffusion b-value | (0018,9087) | (0043,1039) | (0019,100C) | (2001,1003) |
| Private Creator | — | GEMS_PARM_01 | SIEMENS CSA HEADER | Philips Imaging |

In `dicom_all`, private elements sit in the `OtherElements` array of `{Tag, Data}` structs. DICOM
notation `(0043,1039)` becomes BigQuery `Tag_00431039`.

```sql
-- Discover populated private tags in a collection
SELECT oe.Tag, COUNT(*) n,
       ARRAY_AGG(DISTINCT oe.Data[SAFE_OFFSET(0)] IGNORE NULLS LIMIT 5) sample_values
FROM `bigquery-public-data.idc_current.dicom_all`, UNNEST(OtherElements) oe
WHERE collection_id = 'qin_prostate_repeatability' AND Modality = 'MR'
  AND ARRAY_LENGTH(oe.Data) > 0 AND oe.Data[SAFE_OFFSET(0)] NOT IN ('', NULL)
GROUP BY oe.Tag ORDER BY n DESC;

-- Read a specific private element (b-value), aggregated per series
SELECT SeriesInstanceUID, ARRAY_AGG(DISTINCT oe.Data[SAFE_OFFSET(0)]) b_values
FROM `bigquery-public-data.idc_current.dicom_all`, UNNEST(OtherElements) oe
WHERE collection_id = 'qin_prostate_repeatability' AND oe.Tag = 'Tag_00431039'
GROUP BY SeriesInstanceUID;
```

**Workflow:** discover tags → identify `Manufacturer`/`ManufacturerModelName` → find that vendor's
DICOM Conformance Statement → map the tag → query → verify visually in the
[IDC Viewer](https://viewer.imaging.datacommons.cancer.gov/). Caveats: encoding varies (string vs
numeric, odd values like `1000000600`), meanings shift across software versions, and de-identification
may have stripped some tags.

## Clinical Data in BigQuery

Same content as the `idc-index` clinical tables, but queryable with cross-collection joins.
Datasets: `idc_current_clinical` (exploration) and `idc_v{N}_clinical` (reproducibility). ~130 tables
across ~70 collections (clinical data began at IDC v11).

- Table naming: usually `<collection_id>_clinical`; ACRIN collections use several (`acrin_6698_A0`, ...).
- Navigation tables: `table_metadata` (per-table descriptions) and `column_metadata` (per-column labels, types, and observed `values` with descriptions).
- Join key: every clinical table has `dicom_patient_id`, matching the imaging `PatientID`.

```sql
-- Find collections with staging fields
SELECT DISTINCT collection_id, table_name, column, column_label
FROM `bigquery-public-data.idc_current_clinical.column_metadata`
WHERE LOWER(column_label) LIKE '%stage%';

-- Join clinical to imaging
SELECT d.PatientID, d.StudyInstanceUID, d.Modality, c.clinical_stag
FROM `bigquery-public-data.idc_current.dicom_all` d
JOIN `bigquery-public-data.idc_current_clinical.nlst_canc` c
  ON d.PatientID = c.dicom_patient_id
WHERE d.collection_id = 'nlst' AND d.Modality = 'CT' AND c.clinical_stag = '400' LIMIT 20;
```

Clinical schemas vary widely by collection — inspect `INFORMATION_SCHEMA.COLUMNS` first. See
[clinical-data.md](clinical-data.md) for the no-auth `idc-index` path to the same data.

## BigQuery → idc-index Handoff

Query complex criteria in BigQuery, then download with `idc-index` (no GCP auth needed for downloads):

```python
from google.cloud import bigquery
from idc_index import IDCClient
bq = bigquery.Client(project="your-gcp-project-id")
df = bq.query("""SELECT DISTINCT SeriesInstanceUID FROM `bigquery-public-data.idc_current.dicom_all`
                 WHERE collection_id='tcga_luad' AND Manufacturer='GE MEDICAL SYSTEMS' LIMIT 100""").to_dataframe()
IDCClient().download_from_selection(seriesInstanceUID=list(df['SeriesInstanceUID']), downloadDir="./data")
```

## Cost Control

$5/TB scanned (first 1 TB/month free — most users stay free). Select only needed columns, filter
early, `LIMIT` while testing, prefer `dicom_all` over `dicom_metadata`, and use materialized tables
(`table_name`) over views (`table_name_view`). Estimate before running:

```python
job = client.query(query, job_config=bigquery.QueryJobConfig(dry_run=True))
print(f"{job.total_bytes_processed/1e9:.2f} GB")
```

## Common Errors

- **Billing must be enabled** → enable billing on the GCP project, or use the mini-index.
- **Query exceeds resource limits** → tighter `WHERE`, add `LIMIT`, split the query.
- **Column not found** → check `INFORMATION_SCHEMA.COLUMNS`; schemas differ per version and collection.
- **Permission denied** → `gcloud auth application-default login`.

## Links

[BigQuery DICOM schema](https://docs.cloud.google.com/healthcare-api/docs/how-tos/dicom-bigquery-schema) ·
[IDC BigQuery cookbook](https://github.com/ImagingDataCommons/idc-bigquery-cookbook)
