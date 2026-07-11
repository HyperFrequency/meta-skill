# DICOMweb Reference

IDC exposes DICOMweb (DICOM PS3.18 web services) through Google Cloud Healthcare API DICOM stores.
Use it to integrate with PACS/DICOMweb clients (OHIF, dicomweb-client), stream metadata without
downloading full files, or build custom viewers. For plain discovery and downloads, `idc-index` is
simpler.

## Endpoints

### Public proxy — no auth, 100% coverage

```
https://proxy.imaging.datacommons.cancer.gov/current/viewer-only-no-downloads-see-tinyurl-dot-com-slash-3j3d9jyp/dicomWeb
```

Contains all IDC data from every bucket, tracks the latest version immediately, read-only, per-IP
daily quota (fine for testing and moderate use). The "viewer-only-no-downloads" text is legacy naming
with no functional effect. Quota increases: support@canceridc.dev.

### Google Healthcare API — auth required, ~96% coverage

```
https://healthcare.googleapis.com/v1/projects/nci-idc-data/locations/us-central1/datasets/idc/dicomStores/idc-store-v{VERSION}/dicomWeb
```

Replace `{VERSION}` with the release number (`client.get_idc_version()`). Higher quotas and better
performance, but it replicates **only the `idc-open-data` bucket** — the ~4% in `idc-open-data-cr` and
`idc-open-data-two` is absent — and lags 1–2 weeks after each new release. See
[cloud-storage.md](cloud-storage.md).

**Choosing:** use the public proxy for complete/latest coverage and no setup; use Google Healthcare
when the missing ~4% is irrelevant and you need higher quotas. Check whether your collection is
affected:

```python
client.sql_query("""SELECT series_aws_url, COUNT(*) n FROM index
                    WHERE collection_id='your_collection' GROUP BY series_aws_url""")
# URLs containing 'idc-open-data-cr' or 'idc-open-data-two' are missing from Google Healthcare
```

## Supported Operations

| Service | Supported | Notes |
|---------|-----------|-------|
| QIDO-RS (search) | yes | Exact match only, except `StudyDate` (range) and `PatientName` (fuzzy) |
| WADO-RS (retrieve) | yes | Objects and metadata |
| STOW-RS (store) | no | IDC is read-only |

Searchable tags: Study level — `StudyInstanceUID`, `PatientName`, `PatientID`, `AccessionNumber`,
`ReferringPhysicianName`, `StudyDate`; Series adds `SeriesInstanceUID`, `Modality`; Instance adds
`SOPInstanceUID`. Limits: 5,000 results for study/series searches, 50,000 for instances, max offset
1,000,000; DICOM sequences >~1 MB are returned as `BulkDataURI`, not inline.

## Code Examples (public proxy)

Discover UIDs with `idc-index`, then query DICOMweb:

```python
import requests
from idc_index import IDCClient
client = IDCClient()
r = client.sql_query("""SELECT StudyInstanceUID, SeriesInstanceUID FROM index
                        WHERE collection_id='tcga_luad' AND Modality='CT' LIMIT 1""")
study, series = r.iloc[0]['StudyInstanceUID'], r.iloc[0]['SeriesInstanceUID']

base = "https://proxy.imaging.datacommons.cancer.gov/current/viewer-only-no-downloads-see-tinyurl-dot-com-slash-3j3d9jyp/dicomWeb"
hdr = {"Accept": "application/dicom+json"}

# QIDO-RS: list series in a study
resp = requests.get(f"{base}/studies/{study}/series", headers=hdr)
for s in resp.json():
    modality = s.get("00080060", {}).get("Value", [None])[0]      # tags are hex codes
    desc     = s.get("0008103E", {}).get("Value", [""])[0]

# WADO-RS: retrieve series metadata without downloading pixel files
meta = requests.get(f"{base}/studies/{study}/series/{series}/metadata", headers=hdr).json()
inst = meta[0]
rows, cols = inst.get("00280010", {}).get("Value", [None])[0], inst.get("00280011", {}).get("Value", [None])[0]
```

Common tags: `00080018` SOPInstanceUID · `00080060` Modality · `0008103E` SeriesDescription ·
`00100020` PatientID · `0020000D` StudyInstanceUID · `0020000E` SeriesInstanceUID · `00280010` Rows ·
`00280011` Columns.

## Authenticated Access (Google Healthcare)

```python
from google.auth import default
from google.auth.transport.requests import Request
import requests
creds, _ = default(); creds.refresh(Request())
base = "https://healthcare.googleapis.com/v1/projects/nci-idc-data/locations/us-central1/datasets/idc/dicomStores/idc-store-v23/dicomWeb"
resp = requests.get(f"{base}/studies", params={"limit": 5},
                    headers={"Authorization": f"Bearer {creds.token}", "Accept": "application/dicom+json"})
```

Prerequisites: `gcloud` installed, `gcloud auth application-default login`, and account access to
public Google Cloud datasets.

## Troubleshooting

- **400 Bad Request on search** → unsupported search parameter; DICOMweb here only filters specific tags. Discover UIDs with `idc-index`, then query by UID.
- **403 Forbidden (Google Healthcare)** → missing/insufficient auth; re-run `gcloud auth application-default login`.
- **429 Too Many Requests** → back off, lower `limit`, or switch to the authenticated endpoint.
- **204 No Content for a valid UID** → data may be in a bucket Google Healthcare doesn't replicate, or from an older version; use the public proxy for 100% coverage.
- **Missing attributes in response** → sequences >~1 MB are excluded; retrieve the full instance via WADO-RS.

## Links

[IDC DICOMweb access](https://learn.canceridc.dev/data/downloading-data/dicomweb-access) ·
[IDC proxy policy](https://learn.canceridc.dev/portal/proxy-policy) ·
[DICOMweb standard](https://www.dicomstandard.org/using/dicomweb) ·
[dicomweb-client](https://dicomweb-client.readthedocs.io/)
