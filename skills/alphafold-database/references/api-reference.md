# AlphaFold DB — REST API and File Access Reference

Programmatic access to the AlphaFold Protein Structure Database. All endpoints and
files are public and require no authentication.

## REST API

Base URL: `https://alphafold.ebi.ac.uk/api/`

### Get prediction by UniProt accession

```
GET /prediction/{uniprot_id}
```

- `uniprot_id` (required) — UniProt accession, e.g. `P00520`.
- Returns a JSON **array** (one object per fragment; usually length 1).
- `404` if no prediction exists for that accession.

```bash
curl https://alphafold.ebi.ac.uk/api/prediction/P00520
```

Representative response object:

```json
{
  "entryId": "AF-P00520-F1",
  "gene": "ABL1",
  "uniprotAccession": "P00520",
  "uniprotId": "ABL1_HUMAN",
  "uniprotDescription": "Tyrosine-protein kinase ABL1",
  "taxId": 9606,
  "organismScientificName": "Homo sapiens",
  "uniprotStart": 1,
  "uniprotEnd": 1130,
  "uniprotSequence": "MLEICLKL...",
  "modelCreatedDate": "2025-08-01",
  "latestVersion": 6,
  "allVersions": [1, 2, 3, 4, 5, 6],
  "cifUrl":       "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-model_v6.cif",
  "bcifUrl":      "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-model_v6.bcif",
  "pdbUrl":       "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-model_v6.pdb",
  "plddtDocUrl":  "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-confidence_v6.json",
  "paeImageUrl":  "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-predicted_aligned_error_v6.png",
  "paeDocUrl":    "https://alphafold.ebi.ac.uk/files/AF-P00520-F1-predicted_aligned_error_v6.json"
}
```

**Always prefer the `*Url` fields from this response** over hand-built URLs — they
resolve to the current version and correct fragment naming automatically.

Key fields: `entryId` (AF entry ID), `uniprotAccession`, `gene`,
`organismScientificName`, `taxId`, `uniprotStart`/`uniprotEnd` (residue range
covered by this fragment), `uniprotSequence`, `latestVersion`, `allVersions`,
and the file links `cifUrl`/`bcifUrl`/`pdbUrl`, `plddtDocUrl` (per-residue pLDDT
JSON), `paeDocUrl` (PAE JSON), `paeImageUrl`, `msaUrl`.

### 3D-Beacons federated access

AlphaFold is one provider inside the 3D-Beacons network, which aggregates predicted
and experimental structures for a UniProt entry:

```python
import requests

acc = "P00520"
url = f"https://www.ebi.ac.uk/pdbe/pdbe-kb/3dbeacons/api/uniprot/summary/{acc}.json"
data = requests.get(url).json()

alphafold = [s for s in data["structures"] if s["summary"]["provider"] == "AlphaFold DB"]
```

Use 3D-Beacons when you want AlphaFold *alongside* experimental and other predicted
models in one call; use the direct AlphaFold API when you only want AlphaFold.

## File Access Patterns

Deterministic URL (use only when you already hold the entry ID and version):

```
https://alphafold.ebi.ac.uk/files/{entry_id}-{file_type}_{version}.{ext}
```

- `{entry_id}` — e.g. `AF-P00520-F1`
- `{version}`  — e.g. `v6` (current); read `latestVersion` from the API rather than assuming

### File types

| Purpose             | file_type / ext                        | Notes |
| ------------------- | -------------------------------------- | ----- |
| Coordinates (mmCIF) | `model_v6.cif`                         | Recommended; full metadata; no atom cap |
| Coordinates (bCIF)  | `model_v6.bcif`                        | Binary mmCIF, ~70% smaller, needs binary parser |
| Coordinates (PDB)   | `model_v6.pdb`                         | Legacy text; 99,999-atom limit |
| Per-residue pLDDT   | `confidence_v6.json`                   | Reached via `plddtDocUrl`; see schema below |
| PAE matrix          | `predicted_aligned_error_v6.json`      | Reached via `paeDocUrl`; see schema below |
| PAE heatmap image   | `predicted_aligned_error_v6.png`       | Pre-rendered, quick visual check |

`v6` is the current release (as of 2025-08); older versions stay reachable at their
own suffix. Prefer the API's `*Url` fields so the version is always correct.

```python
import requests
entry, ver = "AF-P00520-F1", "v6"
base = f"https://alphafold.ebi.ac.uk/files/{entry}"
cif  = requests.get(f"{base}-model_{ver}.cif").content
conf = requests.get(f"{base}-confidence_{ver}.json").json()
pae  = requests.get(f"{base}-predicted_aligned_error_{ver}.json").json()
```

## Data Schemas

### Coordinate mmCIF — where the confidence lives

Standard mmCIF categories (`_entry`, `_struct`, `_entity`, `_atom_site`,
`_pdbx_struct_assembly`). In `_atom_site`, `B_iso_or_equiv` holds the **per-residue
pLDDT**, not a crystallographic B-factor — so viewers color by confidence for free.
Useful columns: `label_atom_id`, `label_comp_id`, `label_seq_id`, `Cartn_x/y/z`.

### confidence JSON

A single top-level JSON **object** (not a list):

```json
{
  "residueNumber":      [1, 2, 3],
  "confidenceScore":    [87.5, 91.2, 93.8],
  "confidenceCategory": ["high", "very_high", "very_high"]
}
```

- `residueNumber` — 1-based residue index, parallel to the score arrays.
- `confidenceScore` — pLDDT (0–100) per residue, in sequence order.
- `confidenceCategory` — `very_low` (≤50), `low` (50–70), `high` (70–90),
  `very_high` (>90).

### predicted_aligned_error JSON

The response is a JSON **array containing one object** — you must index `[0]` before
reading the matrix:

```json
[
  {
    "predicted_aligned_error": [[0, 2, 4], [2, 0, 3], [4, 3, 0]],
    "max_predicted_aligned_error": 31.75
  }
]
```

- `predicted_aligned_error[i][j]` — expected position error (Å) of residue *j* when
  predicted and true structures are aligned on residue *i*. Values are integer-rounded
  Ångströms (0-based row/column, residue *i+1* / *j+1*).
- **Not symmetric** in general: `pae[i][j] != pae[j][i]`. Diagonal is 0.
- Lower = more confident relative placement.
- **Parse it as `resp[0]["predicted_aligned_error"]`.** A common bug is treating the
  response as a top-level object or reading a `distance` key — both fail on current
  files. The legacy v1 format did use flat `residue1`/`residue2`/`distance` arrays;
  v4+ (including v6) uses the 2-D `predicted_aligned_error` shown above.

## Error Handling and Rate Limiting

| Code | Meaning             | Action                                    |
| ---- | ------------------- | ----------------------------------------- |
| 200  | OK                  | Process response                          |
| 404  | Not Found           | No AlphaFold model for this accession     |
| 429  | Too Many Requests   | Back off, retry with exponential delay    |
| 500  | Server Error        | Retry with backoff                        |
| 503  | Service Unavailable | Wait and retry later                      |

Recommendations: keep to ~10 concurrent REST requests, add ~100–200 ms between
sequential calls, cache everything locally, and move any large job to Google Cloud
(see `bulk-access.md`).

## Version History

- v1 (Jul 2021) ~350K structures (initial model-organism proteomes + human) ·
  v2–v3 (2021–2022) incremental proteome expansions · v4 (Jul 2022) the 200M+
  expansion · v5–v6 (through 2025-08) current release. `latestVersion`/`allVersions`
  in the API response are authoritative; don't hard-code a version — read it back.
- **The bulk GCS/BigQuery snapshot lags the API.** The public Google Cloud dataset
  is still the `-v4` bucket (see `bulk-access.md`); the per-entry REST API and website
  now serve `v6`. For the newest per-entry model, use the API `*Url` fields, not bulk.

## Links

- API docs: https://alphafold.ebi.ac.uk/api-docs
- 3D-Beacons: https://www.ebi.ac.uk/pdbe/pdbe-kb/3dbeacons/
- Biopython `Bio.PDB.alphafold_db`: https://biopython.org/docs/dev/api/Bio.PDB.alphafold_db.html
