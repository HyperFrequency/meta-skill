# ENA API Reference

Endpoint-level reference for the European Nucleotide Archive (ENA, EMBL-EBI)
public REST APIs. All endpoints are unauthenticated and return over HTTPS.
Examples use Python `requests`; the same URLs work with `curl`.

Base hosts:

| API | Base URL | Purpose |
|-----|----------|---------|
| Portal | `https://www.ebi.ac.uk/ena/portal/api` | Metadata search + file-report |
| Browser | `https://www.ebi.ac.uk/ena/browser/api` | Retrieve one record by accession |
| Taxonomy | `https://www.ebi.ac.uk/ena/taxonomy/rest` | Taxon lookups |
| Cross-Reference | `https://www.ebi.ac.uk/ena/xref/rest` | External-DB links |
| CRAM registry | `https://www.ebi.ac.uk/ena/cram` | Reference seqs by checksum |

Official docs: Portal `https://www.ebi.ac.uk/ena/portal/api/doc` ·
Browser `https://www.ebi.ac.uk/ena/browser/api/doc`.

---

## Portal API

### `GET /search`

Advanced metadata search across ENA object types with field selection,
filtering, sorting, and pagination.

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `result` | Yes | Object type to return (one per call) | `sample`, `study`, `read_run`, `read_experiment`, `analysis`, `assembly`, `sequence`, `taxon` |
| `query` | Usually | Filter using ENA query syntax (see below) | `tax_eq(9606)`, `study_accession="PRJNA123456"` |
| `fields` | No | Comma-separated columns to return | `accession,sample_title,scientific_name` |
| `format` | No | `tsv` (default), `json`, or `xml` | `json` |
| `limit` | No | Max rows; **`0` means no cap** (default caps at 100000) | `10`, `0` |
| `offset` | No | Row offset for pagination | `0`, `100` |
| `sortFields` | No | Comma-separated sort columns | `collection_date` |
| `sortOrder` | No | `asc` or `desc` | `desc` |
| `dataPortal` | No | Restrict to a portal | `ena`, `pathogen`, `metagenome` |
| `download` | No | Force a download response | `true` |
| `includeAccessions` | No | Whitelist accessions | `SAMN01,SAMN02` |
| `excludeAccessions` | No | Blacklist accessions | `SAMN03,SAMN04` |

Common `result` values: `study`, `sample`, `read_run`, `read_experiment`,
`analysis`, `assembly`, `sequence`, `taxon`, `coding`, `noncoding`. Field sets
differ per `result` — enumerate with `/returnFields` rather than guessing.

```python
import requests

url = "https://www.ebi.ac.uk/ena/portal/api/search"

# Human samples, selected fields, JSON
requests.get(url, params={
    "result": "sample",
    "query": "tax_eq(9606)",
    "fields": "accession,sample_title,collection_date",
    "format": "json",
    "limit": 100,
})

# RNA-Seq experiments within one study
requests.get(url, params={
    "result": "read_experiment",
    "query": 'study_accession="PRJNA123456" AND library_strategy="RNA-Seq"',
    "format": "tsv",
})

# E. coli (taxon 562) assemblies with contig N50 >= 50 kb, whole clade
requests.get(url, params={
    "result": "assembly",
    "query": "tax_tree(562) AND contig_n50>=50000",
    "format": "json",
})
```

### Query syntax

| Operator | Form | Notes |
|----------|------|-------|
| Equality | `field="value"` / `field=value` | Quote strings with spaces |
| Wildcard | `field="*partial*"` | `*` matches any run of chars |
| Range | `field>=a AND field<=b` | Numeric and ISO dates |
| Boolean | `q1 AND q2`, `q1 OR q2`, `NOT q` | Parenthesise to group |
| Set membership | `study_accession IN (PRJNA1,PRJNA2)` | Comma-separated list |
| Taxon, exact | `tax_eq(taxon_id)` | That taxon only |
| Taxon, subtree | `tax_tree(taxon_id)` | Taxon **plus all descendants** |
| Date range | `collection_date>=2020-01-01 AND collection_date<=2023-12-31` | ISO `YYYY-MM-DD` |

### `GET /returnFields`

List the queryable/returnable fields for a `result` type.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `result` | Yes | Object type, e.g. `sample`, `assembly` |
| `dataPortal` | No | Filter by portal |

```python
requests.get("https://www.ebi.ac.uk/ena/portal/api/returnFields",
             params={"result": "sample"}).json()
```

### `GET /results`

Enumerate the available `result` types.

```python
requests.get("https://www.ebi.ac.uk/ena/portal/api/results")
```

### `GET /filereport`

Resolve data-file URLs and checksums for a run or analysis. This is how you go
from an accession to downloadable FASTQ/BAM.

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `accession` | Yes | Run or analysis accession | `ERR164407` |
| `result` | Yes | `read_run` or `analysis` | `read_run` |
| `format` | No | `tsv` (default) or `json` | `json` |
| `fields` | No | Columns to return | `run_accession,fastq_ftp,fastq_md5` |

Useful `filereport` fields:

| Field | Meaning |
|-------|---------|
| `run_accession` | Run accession |
| `fastq_ftp` | FASTQ URLs, `;`-separated (2 for paired-end) |
| `fastq_aspera` | Aspera paths for the same files |
| `fastq_md5` | MD5 checksums, `;`-separated, aligned to `fastq_ftp` |
| `fastq_bytes` | File sizes in bytes, `;`-separated |
| `submitted_ftp` | Originally submitted files (e.g. BAM) |
| `sra_ftp` | SRA-format copy |

```python
report = requests.get(
    "https://www.ebi.ac.uk/ena/portal/api/filereport",
    params={"accession": "ERR164407", "result": "read_run",
            "format": "json",
            "fields": "run_accession,fastq_ftp,fastq_md5,fastq_bytes"},
).json()[0]

# FTP paths come back host-relative, e.g. ftp.sra.ebi.ac.uk/vol1/fastq/...
# Prefix with https:// (or ftp://) to fetch. MD5-verify every file.
urls = report["fastq_ftp"].split(";")
md5s = report["fastq_md5"].split(";")
```

---

## Browser API

Retrieve a single record by accession. Path accessions accept studies, samples,
runs, assemblies, and sequences as appropriate to the format.

### `GET /xml/{accession}` — metadata as XML

| Parameter | In | Description |
|-----------|----|-------------|
| `accession` | path | e.g. `PRJNA123456`, `SAMEA123456`, `ERR164407` |
| `download` | query | `true` to force download |
| `includeLinks` | query | `true` to embed cross-reference links |

### `GET /text/{accession}` — EMBL flatfile

| Parameter | In | Description |
|-----------|----|-------------|
| `accession` | path | Sequence accession, e.g. `LN847353` |
| `download` | query | `true` to force download |
| `expandDataclasses` | query | Include related data classes |
| `lineLimit` | query | Cap output lines |

### `GET /fasta/{accession}` — FASTA

| Parameter | In | Description |
|-----------|----|-------------|
| `accession` | path | Sequence accession |
| `download` | query | `true` to force download |
| `range` | query | Sub-sequence range, e.g. `1000-2000` |
| `lineLimit` | query | Cap output lines |

### `GET /links/{source}/{accession}` — cross-references

| Parameter | In | Description |
|-----------|----|-------------|
| `source` | path | `sample`, `study`, `sequence`, … |
| `accession` | path | Accession number |
| `target` | query | Restrict to a target DB, e.g. `sra`, `biosample` |

```python
b = "https://www.ebi.ac.uk/ena/browser/api"
requests.get(f"{b}/xml/SAMEA123456", params={"includeLinks": "true"}).text
requests.get(f"{b}/text/LN847353").text
requests.get(f"{b}/fasta/LN847353", params={"range": "1000-2000"}).text
requests.get(f"{b}/links/sample/SAMEA123456").text
```

---

## Taxonomy REST API

Base: `https://www.ebi.ac.uk/ena/taxonomy/rest`. Returns lineage, rank,
scientific/common name, and identifiers.

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /tax-id/{taxon_id}` | Lookup by NCBI taxon ID | `/tax-id/562` → *E. coli* |
| `GET /scientific-name/{name}` | Lookup by name (may be multiple) | `/scientific-name/Escherichia coli` |
| `GET /suggest-for-submission/{partial}` | Autocomplete for submission | `/suggest-for-submission/Escheri` |

```python
requests.get("https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/562").json()
```

Taxon lookups are stable — cache them locally when annotating many records.

---

## Cross-Reference Service

Base: `https://www.ebi.ac.uk/ena/xref/rest`. Find records in external databases
related to an ENA entry.

`GET /json/{source}/{accession}`

| Parameter | In | Description |
|-----------|----|-------------|
| `source` | path | Source DB, e.g. `ena`, `sra` |
| `accession` | path | Accession |

```python
requests.get("https://www.ebi.ac.uk/ena/xref/rest/json/sra/SRR000001").json()
```

---

## CRAM Reference Registry

Base: `https://www.ebi.ac.uk/ena/cram`. Retrieve reference sequences used inside
CRAM files, addressed by content checksum.

`GET /md5/{md5_checksum}` (a `/sha1/{sha1}` variant also exists) returns the
reference sequence.

```python
requests.get("https://www.ebi.ac.uk/ena/cram/md5/7c3f69f0c5f0f0de6d7c34e7c2e25f5c").text
```

---

## Rate Limits and Error Handling

- Documented limit ~**50 requests/second**; exceeding returns HTTP `429`. Stay
  well under it: batch into fewer, larger queries and avoid per-accession loops.

Status codes:

| Code | Meaning | Action |
|------|---------|--------|
| `200 OK` | Success | Process |
| `204 No Content` | Success, empty result | Treat as no match |
| `400 Bad Request` | Invalid params/query | Fix query; **do not retry** |
| `404 Not Found` | Unknown accession | Non-retryable |
| `429 Too Many Requests` | Rate limited | Back off + retry |
| `500/502/503/504` | Server / transient | Back off + retry |

Retrying session (retry transient codes with exponential backoff; leave
`400`/`404` to fail fast):

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def ena_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,                       # 1s, 2s, 4s, ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

session = ena_session()
resp = session.get(url, params=params, timeout=60)
resp.raise_for_status()
```

---

## Bulk Download

Do not iterate the API for many files — transfer directly:

1. **FTP** from `fastq_ftp` / `submitted_ftp` (prefix host-relative paths with
   `https://` or `ftp://`). Base tree: `ftp://ftp.sra.ebi.ac.uk/vol1/fastq/`.
   Verify each file against its `fastq_md5`.
2. **Aspera** for large/high-latency transfers: `era-fasp@fasp.sra.ebi.ac.uk:`
   with the `fastq_aspera` path.
3. **enaBrowserTools** CLI:
   ```bash
   enaDataGet ERR164407     # one run/accession
   enaGroupGet PRJEB1234    # every run in a study
   ```

---

## Query Optimization

1. Pick the narrowest `result` type instead of broad searches.
2. Request only needed columns via `fields` (smaller, faster responses).
3. Paginate large result sets with `limit` + `offset`.
4. Cache taxonomy lookups locally.
5. Prefer `json`/`tsv` over `xml` when you only need tabular metadata.
6. Use `includeAccessions` / `excludeAccessions` to trim big result sets in one
   request rather than filtering client-side across many calls.
