---
name: imaging-data-commons
version: 0.1.0
description: >-
  Query and download public cancer imaging data (CT, MR, PET radiology and slide-microscopy
  pathology) from the NCI Imaging Data Commons (IDC) using the idc-index Python package and idc
  CLI — no authentication. Use to find DICOM series by metadata (modality, body part, cancer type,
  manufacturer, license), assemble a reproducible cohort for AI training or research, download from
  IDC cloud storage, check CC-BY vs CC-BY-NC licensing, generate attribution citations, or view
  images in a browser without a local viewer. Also routes to advanced access — BigQuery (full DICOM
  tags, private vendor elements, clinical joins), DICOMweb (QIDO/WADO), direct S3/GCS buckets, and
  clinical/tabular data. NOT for de-identifying or reading pixel data from already-downloaded DICOM
  files (use pydicom), whole-slide tiling/analysis (histolab, pathml), non-IDC or private imaging
  datasets, or clinical decision-making on patient scans.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: idc-index MIT; IDC data per-collection CC BY 4.0 / CC BY-NC 4.0
---

# Imaging Data Commons

## Overview

The NCI Imaging Data Commons (IDC) is a public, cloud-hosted repository of de-identified cancer
imaging — radiology (CT, MR, PET, and more) and digital pathology (slide microscopy) — plus
AI/expert-derived annotations and segmentations, all stored as DICOM. Access is free and requires
no authentication.

The primary tool is the **`idc-index`** Python package, which ships a local "mini-index" (metadata
for every current series) queried with SQL, plus methods to download, visualize, and cite data. It
also installs an `idc` command-line tool.

The core loop is three steps:

1. **Query metadata** → `client.sql_query("SELECT ... FROM index WHERE ...")` returns a pandas DataFrame.
2. **Download DICOM** → `client.download_from_selection(seriesInstanceUID=[...], downloadDir=...)`.
3. **Visualize in browser** → `client.get_viewer_URL(seriesInstanceUID=...)` (OHIF for radiology, SLIM for pathology).

```python
from idc_index import IDCClient
client = IDCClient()
print(client.get_idc_version())          # data release, e.g. "v23"
df = client.sql_query("SELECT * FROM index WHERE Modality = 'CT' LIMIT 10")
```

## When to Use This Skill

- Finding publicly available radiology or pathology images for AI training, benchmarking, or research.
- Selecting image subsets by cancer type, modality, anatomical site, manufacturer, or other metadata.
- Assembling a **reproducible** cohort and downloading its DICOM series from IDC cloud storage.
- Checking data licenses (CC BY vs CC BY-NC) before research or commercial use, and generating attribution citations.
- Previewing medical images in a browser without installing a DICOM viewer.
- Finding segmentations / RTSTRUCT / SR annotations and linking them to their source images.
- Reaching for advanced access: full DICOM tags or private vendor elements (BigQuery), DICOMweb (QIDO/WADO), or raw bucket files (S3/GCS).

## When NOT to Use This Skill

- **Reading or manipulating already-downloaded DICOM files** (pixel data, headers, anonymization, format conversion) — use `pydicom` or SimpleITK.
- **Whole-slide image analysis** (tiling, tissue detection, nucleus segmentation, ML on pathology) — use `histolab` or `pathml`.
- **Clinical / EHR-style patient reporting or decision support** on scans — see `clinical-imaging` and `clinical-decision-support`.
- **Non-IDC or private imaging data** — IDC contains only public, de-identified cancer imaging.
- **Plotting query results** — hand the returned DataFrame to `matplotlib`, `seaborn`, or `exploratory-data-analysis`.

## Setup

```bash
pip install --upgrade idc-index      # always --upgrade: each IDC release ships a new pinned version
pip install pandas numpy pydicom     # optional, for downstream analysis
```

Each new IDC data release triggers a new `idc-index` version. Pin an older version only when reproducing
a prior analysis. Developed against `idc-index` 0.11.x (IDC data v23); verify against your installed version.

## Data Model

IDC layers two grouping levels above the standard DICOM hierarchy (Patient → Study → Series → Instance):

- **`collection_id`** — groups patients by disease/modality/project (e.g. `nlst`, `tcga_luad`). A patient belongs to exactly one collection. Use it to find original imaging.
- **`analysis_result_id`** — identifies derived objects (segmentations, annotations, radiomics) spanning one or more source collections. Use it to find AI-generated or expert annotations.

Key query identifiers: `collection_id`, `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID` (the last is what you pass to downloads and the viewer). Columns whose names match DICOM attributes (`Modality`,
`BodyPartExamined`, `Manufacturer`, `StudyDate`, `PatientSex`, ...) carry standard DICOM values.

## Querying Metadata

`idc-index` exposes several metadata tables. `index` and `prior_versions_index` load automatically;
the rest need `client.fetch_index("<name>")` before use. Query them by SQL (recommended) or as pandas
attributes (`client.index`, `client.sm_index`, ...).

```python
# Discover valid filter values before filtering — do not guess enum values
client.sql_query("SELECT DISTINCT Modality, COUNT(*) n FROM index GROUP BY Modality ORDER BY n DESC")

# Filter with validated values
client.sql_query("""
    SELECT collection_id, PatientID, SeriesInstanceUID, SeriesDescription, license_short_name
    FROM index WHERE Modality = 'MR' AND BodyPartExamined = 'BREAST' LIMIT 20
""")
```

**Cancer type lives in `collections_index`, not `index`** — join on `collection_id`. Segmentations
carry a `segmented_SeriesInstanceUID` back-reference to their source image. For the full table
catalogue, join keys, `indices_overview` schema-discovery pattern, key `index` columns, and copy-paste
SQL recipes (segmentations, slide microscopy, size estimation, clinical linking), see
[references/querying-and-schema.md](references/querying-and-schema.md).

> Always consult `client.indices_overview` (or `client.get_index_schema("index")`) for the authoritative
> column list of your installed version rather than assuming column names.

## Downloading

```python
# Whole collection (rider_pilot is ~1 GB, good for testing)
client.download_from_selection(collection_id="rider_pilot", downloadDir="./data")

# Specific series, with a custom on-disk layout
uids = client.sql_query("SELECT SeriesInstanceUID FROM index WHERE collection_id='nlst' AND Modality='CT' LIMIT 5")
client.download_from_selection(
    seriesInstanceUID=list(uids['SeriesInstanceUID']),
    downloadDir="./data",
    dirTemplate="%collection_id/%PatientID/%Modality",   # default nests %StudyInstanceUID; "" = flat
)
```

The `idc` CLI mirrors this without Python (`idc download`, `idc download-from-selection --dry-run`,
`idc download-from-manifest --use-s5cmd-sync`). For CLI options, manifest formats, `--dry-run` size
estimation, resumable downloads, and batching large cohorts, see
[references/download-and-cli.md](references/download-and-cli.md).

## Visualizing

```python
r = client.sql_query("SELECT SeriesInstanceUID, StudyInstanceUID FROM index WHERE collection_id='rider_pilot' LIMIT 1")
client.get_viewer_URL(seriesInstanceUID=r.iloc[0]['SeriesInstanceUID'])   # one series
client.get_viewer_URL(studyInstanceUID=r.iloc[0]['StudyInstanceUID'])     # whole study (e.g. T1/T2/DWI)
```

Open the returned URL in a browser. The viewer is auto-selected (OHIF v3 for radiology, SLIM for slide microscopy).

## Licensing and Citations — Read Before Publishing or Commercial Use

Every series is tagged with `license_short_name`. Roughly 97% of IDC is **CC BY** (commercial use OK
with attribution) and ~3% is **CC BY-NC** (non-commercial only); a few collections have custom terms.
Filter on the license before committing to a use case, and **do not infer license from bucket name.**

```python
client.sql_query("""
    SELECT collection_id, license_short_name, COUNT(DISTINCT SeriesInstanceUID) n
    FROM index GROUP BY collection_id, license_short_name
""")

# Attribution citations derived from the source_DOI column
cites = client.citations_from_selection(collection_id="rider_pilot")                 # APA (default)
bib   = client.citations_from_selection(collection_id="tcga_luad",
                                        citation_format=IDCClient.CITATION_FORMAT_BIBTEX)
```

`citation_format` also accepts `CITATION_FORMAT_JSON` (CSL) and `CITATION_FORMAT_TURTLE`. Include the
generated citations in any publication using IDC data.

## Access Options Beyond idc-index

| Method | Auth | Best for |
|--------|------|----------|
| `idc-index` | No | Metadata queries and downloads — the default |
| [IDC Portal](https://portal.imaging.datacommons.cancer.gov/) | No | Interactive cohort building, manual export |
| BigQuery | Yes (GCP) | Full DICOM tags, private vendor elements, complex clinical joins — [references/bigquery.md](references/bigquery.md) |
| DICOMweb | Proxy: no / Google Healthcare: yes | PACS/QIDO/WADO integration, streaming metadata — [references/dicomweb.md](references/dicomweb.md) |
| Direct S3 / GCS | No | Bulk/parallel raw file access, cloud-native pipelines, versioning — [references/cloud-storage.md](references/cloud-storage.md) |

Clinical/tabular data (staging, outcomes) joins to imaging on `PatientID`; see
[references/clinical-data.md](references/clinical-data.md).

## Best Practices and Gotchas

- Explore with `LIMIT` and estimate size (`SUM(series_size_MB)` or CLI `--dry-run`) before large downloads — some collections are terabytes.
- Save Series UIDs or `crdc_series_uuid` (an immutable version pin) as a manifest/CSV for reproducibility; respect `license_short_name` and attach citations when publishing.
- No rows / UID not found → the UID may be deprecated (check `prior_versions_index`) or the column name wrong (check `indices_overview`); test with `LIMIT 5`.
- Download timeout → smaller batches, or CLI `--use-s5cmd-sync` to resume. `ModuleNotFoundError: idc_index` → `pip install --upgrade idc-index`.
- A downloaded SEG/RTSTRUCT/SR won't open in a plain viewer — those object types need specialized tools; validate with `pydicom.dcmread(f, force=True)`.

## References

- [querying-and-schema.md](references/querying-and-schema.md) — table catalogue, join keys, `indices_overview` schema discovery, key columns, SQL recipes.
- [download-and-cli.md](references/download-and-cli.md) — `idc` CLI, `dirTemplate`, manifests, dry-run, resumable + batched downloads.
- [cloud-storage.md](references/cloud-storage.md) — S3/GCS buckets, CRDC UUIDs, s5cmd/aws/gsutil access, versioning and reproducibility.
- [bigquery.md](references/bigquery.md) — full DICOM metadata, private vendor elements, clinical tables, cost control.
- [dicomweb.md](references/dicomweb.md) — public proxy vs Google Healthcare endpoints, QIDO/WADO, coverage caveats.
- [clinical-data.md](references/clinical-data.md) — clinical index, `get_clinical_table`, value mapping, joining to imaging.

**Official:** [Docs](https://learn.canceridc.dev/) · [idc-index GitHub](https://github.com/ImagingDataCommons/idc-index) · [Forum](https://discourse.canceridc.dev/). Cite: Fedorov A. et al., "NCI Imaging Data Commons," *RadioGraphics* 43(12), 2023, https://doi.org/10.1148/rg.230180.

## Related Skills

- `pydicom` — read/write/anonymize downloaded DICOM files and extract pixel data.
- `histolab`, `pathml` — whole-slide preprocessing and computational pathology on IDC slide microscopy.
- `clinical-imaging` — clinical radiology imaging workflows downstream of IDC data.
- `matplotlib`, `seaborn`, `exploratory-data-analysis` — summarize and explore returned metadata.
