# Cloud Storage Reference (S3 / GCS)

IDC mirrors every DICOM file across public AWS S3 and Google Cloud Storage buckets with identical
paths. Reach for direct bucket access when you need maximum parallel throughput, cloud-native
pipelines, or specific historical file versions. For most work `idc-index` is simpler — it uses
s5cmd against these same buckets and resolves UUIDs for you.

## Buckets

All buckets are anonymous-readable with free egress (AWS Open Data / Google Public Data programs).
AWS buckets live in `us-east-1`.

| Purpose | AWS S3 | GCS | License | Share |
|---------|--------|-----|---------|-------|
| Primary | `idc-open-data` | `idc-open-data` | No commercial restriction | >90% |
| Possible head scans | `idc-open-data-two` | `idc-open-idc1` | No commercial restriction | small |
| Commercial-restricted | `idc-open-data-cr` | `idc-open-cr` | CC BY-NC | ~4% |

> **Do not infer license from bucket name.** Query `license_short_name` in `idc-index` for the
> authoritative license. Head-scan and commercial-restricted separation exist for policy isolation,
> not as a reliable license signal. Pre-v19 GCS used `public-datasets-idc` (now `idc-open-data`).

## File Layout — CRDC UUIDs, not DICOM UIDs

Files are keyed by CRDC UUIDs so that content revisions get new paths (enabling versioning):

```
<bucket>/<crdc_series_uuid>/<crdc_instance_uuid>.dcm
s3://idc-open-data/7a6b2389-.../0d73f84e-...dcm     # folder = series UUID, file = instance UUID
```

| Identifier | Format | Changes when | Use for |
|------------|--------|--------------|---------|
| DICOM UID (`SeriesInstanceUID`) | `1.3.6.1.4...` | never | Clinical identity, DICOMweb queries |
| CRDC UUID (`crdc_series_uuid`) | `e127d258-...` | content changes | File paths, versioning, reproducibility |

A single `SeriesInstanceUID` can map to several `crdc_series_uuid`s across IDC versions if its content
changed. The CRDC UUID uniquely pins one immutable version.

## Resolving DICOM UIDs to File URLs

```python
from idc_index import IDCClient
client = IDCClient()

urls = client.get_series_file_URLs(seriesInstanceUID="1.3.6.1.4.1.14519.5.2.1.6450.9002.2174...")
# → s3://idc-open-data/<crdc_series_uuid>/<crdc_instance_uuid>.dcm

# Or read the series-folder URL straight from the index
client.sql_query("""SELECT SeriesInstanceUID, series_aws_url FROM index
                    WHERE collection_id='rider_pilot' AND Modality='CT' LIMIT 3""")
```

`series_aws_url` looks like `s3://idc-open-data/<uuid>/*`. GCS uses the identical path — swap `s3://`
for `gs://`.

## Access Commands

### AWS S3 (no account)

```bash
aws s3 ls  --no-sign-request s3://idc-open-data/<series_uuid>/
aws s3 cp  --no-sign-request --recursive s3://idc-open-data/<series_uuid>/ ./series_folder/
```

### s5cmd (fast bulk; used internally by idc-index)

```bash
s5cmd --no-sign-request cp 's3://idc-open-data/<series_uuid>/*' ./local/
s5cmd --no-sign-request run manifest.txt
```

`s5cmd run` expects one command per line (not bare URLs) — this differs from the `idc` manifest format:

```
cp s3://idc-open-data/uuid1/instance1.dcm ./local/
cp s3://idc-open-data/uuid2/instance3.dcm ./local/
```

### GCS

```bash
gsutil -m cp -r gs://idc-open-data/<series_uuid>/ ./local/
gcloud storage cp -r gs://idc-open-data/<series_uuid>/ ./local/     # newer CLI
```

### Python (s3fs / gcsfs, anonymous)

```python
import s3fs, gcsfs
series_path = client.sql_query("SELECT series_aws_url FROM index WHERE collection_id='rider_pilot' LIMIT 1") \
                    ['series_aws_url'].iloc[0].replace('s3://', '').rstrip('/*')

s3 = s3fs.S3FileSystem(anon=True);            files = s3.ls(series_path)
gcs = gcsfs.GCSFileSystem(token='anon');      files = gcs.ls(series_path)   # same path
```

## Versioning and Reproducibility

IDC releases a new version every 2–4 months; each is a complete snapshot and old CRDC UUIDs remain
accessible. The robust way to reproduce a dataset is to record `crdc_series_uuid` values at analysis
time — they pin immutable files.

```python
import json
sel = client.sql_query("""SELECT crdc_series_uuid FROM index
                          WHERE collection_id='tcga_luad' AND Modality='CT' LIMIT 10""")
uuids = list(sel['crdc_series_uuid'])
json.dump({"crdc_series_uuids": uuids, "idc_version": client.get_idc_version()},
          open("analysis_manifest.json", "w"), indent=2)
# Later: client.download_from_selection(crdc_series_uuid=uuids, downloadDir="./repro")
```

Use `index` for current data; use `prior_versions_index` only when reproducing a specific older
release. In rare cases (data-owner request, PHI incident) data may be fully withdrawn, including from
history.

## Coverage vs Other Access Methods

| Method | Buckets | Coverage | Versions |
|--------|---------|----------|----------|
| Direct bucket access | all 3 | 100% | all historical |
| `idc-index` download | all 3 | 100% | current + prior_versions_index |
| IDC Portal / DICOMweb public proxy | all 3 | 100% | current |
| Google Healthcare DICOM store | `idc-open-data` only | ~96% | current |

The Google Healthcare endpoint replicates only `idc-open-data` — the ~4% in `idc-open-data-cr` and
`idc-open-data-two` is missing there (see [dicomweb.md](dicomweb.md)).

## Troubleshooting

- **Access Denied** → use `--no-sign-request` (CLI) or `anon=True` / `token='anon'` (Python).
- **File not found at expected path** → you used a DICOM UID instead of a CRDC UUID, or the data changed version; re-query `series_aws_url`, or check `prior_versions_index`.
- **Downloaded files don't match** → series revised in a newer version; compare `crdc_series_uuid`.

## Links

[Files & metadata](https://learn.canceridc.dev/data/organization-of-data/files-and-metadata) ·
[Data versioning](https://learn.canceridc.dev/data/data-versioning) ·
[NCI IDC on AWS Open Data](https://registry.opendata.aws/nci-imaging-data-commons/) ·
[s5cmd](https://github.com/peak/s5cmd)
