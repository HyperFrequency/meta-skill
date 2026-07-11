# Download and CLI Reference

Ways to pull DICOM series out of IDC: the Python `download_from_selection` method and the three `idc`
CLI commands installed with the package. Downloads pull from IDC's public cloud storage (free egress,
s5cmd internally) and need no authentication.

## Python: `download_from_selection`

```python
from idc_index import IDCClient
client = IDCClient()

# Whole collection (rider_pilot ~1 GB — good for testing)
client.download_from_selection(collection_id="rider_pilot", downloadDir="./data")

# Specific series
uids = client.sql_query("""SELECT SeriesInstanceUID FROM index
                           WHERE Modality='CT' AND BodyPartExamined='CHEST' AND collection_id='nlst' LIMIT 5""")
client.download_from_selection(seriesInstanceUID=list(uids['SeriesInstanceUID']), downloadDir="./data/lung_ct")
```

Accepts `collection_id`, `patientId`, `studyInstanceUID`, `seriesInstanceUID`, and `crdc_series_uuid`
selectors (single value or list), plus `downloadDir` and `dirTemplate`.

### On-disk layout: `dirTemplate`

Default: `%collection_id/%PatientID/%StudyInstanceUID/%Modality_%SeriesInstanceUID`. Variables:
`%collection_id`, `%PatientID`, `%StudyInstanceUID`, `%SeriesInstanceUID`, `%Modality`.

```python
client.download_from_selection(collection_id="tcga_luad", downloadDir="./data",
                               dirTemplate="%collection_id/%PatientID/%Modality")   # → ./data/tcga_luad/<PID>/CT/
client.download_from_selection(seriesInstanceUID=list(uids['SeriesInstanceUID']),
                               downloadDir="./flat", dirTemplate="")                 # → flat: ./flat/*.dcm
```

### Batching large cohorts

Download in chunks to survive network hiccups and keep directories manageable:

```python
results = client.sql_query("""SELECT SeriesInstanceUID FROM index
                              WHERE Modality='CT' AND license_short_name='CC BY 4.0' LIMIT 100""")
results.to_csv('manifest.csv', index=False)     # save for reproducibility
batch = 10
for i in range(0, len(results), batch):
    chunk = results.iloc[i:i+batch]
    client.download_from_selection(seriesInstanceUID=list(chunk['SeriesInstanceUID']),
                                   downloadDir=f"./data/batch_{i//batch}")
```

## CLI Commands

Installed as `idc` after `pip install --upgrade idc-index`.

| Command | Purpose |
|---------|---------|
| `idc download` | General download; auto-detects manifest path vs identifiers |
| `idc download-from-manifest` | Manifest download with validation, progress, resume |
| `idc download-from-selection` | Filter-based download with `--dry-run` size estimation |

### `idc download` (auto-detect)

Interprets the argument as a manifest file path or a comma-separated list of identifiers
(collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID, crdc_series_uuid).

```bash
idc download rider_pilot --download-dir ./data
idc download "1.3.6.1.4.1.9328.50.1.69736" --download-dir ./data
idc download "tcga_luad,tcga_lusc" --download-dir ./data
idc download manifest.txt --download-dir ./data
```

Options: `--download-dir` (default: cwd), `--dir-template` (same variables as `dirTemplate`),
`--log-level` (debug|info|warning|error|critical).

### `idc download-from-selection`

```bash
idc download-from-selection --collection-id nlst --dry-run --download-dir ./data   # size only, no files
idc download-from-selection --collection-id nlst --download-dir ./data \
    --show-progress-bar --use-s5cmd-sync                                           # resumable
```

Filter options: `--collection-id`, `--patient-id`, `--study-instance-uid`, `--series-instance-uid`,
`--crdc-series-uuid` (applied sequentially). Plus `--download-dir` (required), `--dry-run`,
`--show-progress-bar`, `--use-s5cmd-sync`, `--dir-template`.

### `idc download-from-manifest`

```bash
idc download-from-manifest --manifest-file cohort.txt --download-dir ./data \
    --show-progress-bar --use-s5cmd-sync
```

Options: `--manifest-file` (required), `--download-dir` (required), `--validate-manifest` (on by
default), `--show-progress-bar`, `--use-s5cmd-sync` (skips already-downloaded files), `--quiet`,
`--dir-template`, `--log-level`.

## Manifest Files

A manifest is one S3 URL per line. Obtain one by exporting an IDC Portal cohort, receiving one from a
collaborator, or generating it from a query:

```python
results = client.sql_query("""SELECT series_aws_url FROM index
                              WHERE collection_id='rider_pilot' AND Modality='CT'""")
with open('ct_manifest.txt', 'w') as f:
    for url in results['series_aws_url']:
        f.write(url + '\n')
```

```
s3://idc-open-data/cb09464a-c5cc-4428-9339-d7fa87cfe837/*
s3://idc-open-data/88f3990d-bdef-49cd-9b2b-4787767240f2/*
```

> The `idc` manifest format (S3 URLs) differs from the raw `s5cmd run` format (one `cp` command per
> line). Let `idc-index` generate manifests rather than hand-writing s5cmd scripts — see
> [cloud-storage.md](cloud-storage.md).

## Safety Features

The CLI checks free disk space before starting, validates manifests by default, offers a progress
bar, and supports resume via `--use-s5cmd-sync`. Always `--dry-run` (or `SUM(series_size_MB)`) before
large downloads — some collections are terabytes.

## Troubleshooting

- **Interrupted download** → re-run with `--use-s5cmd-sync`; already-downloaded files are skipped.
- **Connection timeout on unstable networks** → split into smaller manifests / batches and download sequentially.
- **Files don't match expected series** → the series was revised in a newer IDC version; pin `crdc_series_uuid` and see [cloud-storage.md](cloud-storage.md) on versioning.
