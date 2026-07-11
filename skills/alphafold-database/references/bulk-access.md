# AlphaFold DB — Bulk Access (Google Cloud Storage + BigQuery)

For anything beyond a few dozen proteins, use Google Cloud rather than looping the
REST API. GCS gives you whole proteomes; BigQuery lets you filter by quality before
downloading a single file.

> **Version note.** The public bulk snapshot is the **`v4`** release (bucket and
> BigQuery table below). The per-entry REST API and website have since advanced to
> `v6`. So bulk files may be an older model than the same accession's live API model.
> If you need the newest per-entry structure, fetch it from the API `*Url` fields
> (see `api-reference.md`); use bulk when you want a consistent whole-proteome dump.

## Google Cloud Storage

Bucket: `gs://public-datasets-deepmind-alphafold-v4`

```
gs://public-datasets-deepmind-alphafold-v4/
├── accession_ids.csv     # index of all entries (~13.5 GB)
├── sequences.fasta       # all sequences (~16.5 GB)
└── proteomes/            # per-species tar archives, grouped by NCBI taxonomy ID
```

Install the client:

```bash
uv pip install gsutil        # or: curl https://sdk.cloud.google.com | bash
```

List and download:

```bash
gsutil ls gs://public-datasets-deepmind-alphafold-v4/

# Whole proteome by NCBI taxonomy ID (9606 = human, 83333 = E. coli K-12)
gsutil -m cp \
  "gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-9606-*_v4.tar" .

# The global index of every entry
gsutil cp gs://public-datasets-deepmind-alphafold-v4/accession_ids.csv .
```

`-m` enables parallel transfers. Proteome archives are large; stage them on disk with
room to extract.

### Scripting proteome downloads safely

Build the `gsutil` argument vector as a **list** and never interpolate untrusted input
into a shell string (`shell=True` invites command injection). Validate the taxonomy ID
as an integer first:

```python
import subprocess

def download_proteome(taxonomy_id: int, output_dir: str = "./proteomes") -> None:
    if not isinstance(taxonomy_id, int):
        raise ValueError("taxonomy_id must be an integer")
    pattern = (
        "gs://public-datasets-deepmind-alphafold-v4/proteomes/"
        f"proteome-tax_id-{taxonomy_id}-*_v4.tar"
    )
    subprocess.run(["gsutil", "-m", "cp", pattern, f"{output_dir}/"], check=True)

download_proteome(83333)   # E. coli
download_proteome(9606)    # human
```

## BigQuery — filter before you download

Dataset: `bigquery-public-data.deepmind_alphafold` · Table: `metadata`

```bash
uv pip install google-cloud-bigquery
```

### Schema (key columns)

| Field                    | Type    | Description                     |
| ------------------------ | ------- | ------------------------------- |
| `entryId`                | STRING  | AlphaFold entry ID              |
| `uniprotAccession`       | STRING  | UniProt accession               |
| `gene`                   | STRING  | Gene symbol                     |
| `organismScientificName` | STRING  | Species scientific name         |
| `taxId`                  | INTEGER | NCBI taxonomy ID                |
| `globalMetricValue`      | FLOAT   | Overall quality metric          |
| `fractionPlddtVeryHigh`  | FLOAT   | Fraction of residues pLDDT ≥ 90 |
| `isReviewed`             | BOOLEAN | Swiss-Prot reviewed status      |
| `sequenceLength`         | INTEGER | Protein length                  |

### Example query

```python
from google.cloud import bigquery

client = bigquery.Client()   # requires GCP auth / project
sql = """
SELECT entryId, uniprotAccession, gene, fractionPlddtVeryHigh
FROM `bigquery-public-data.deepmind_alphafold.metadata`
WHERE taxId = 9606                    -- Homo sapiens
  AND fractionPlddtVeryHigh > 0.8
  AND isReviewed = TRUE
ORDER BY fractionPlddtVeryHigh DESC
LIMIT 100
"""
df = client.query(sql).to_dataframe()
```

Typical pattern: query BigQuery for the high-confidence subset you care about, collect
`entryId`s, then `gsutil cp` only those files (or hit the direct file URLs). BigQuery's
free tier processes 1 TB/month — scope columns and `WHERE` clauses to stay under it.

## Bulk best practices

- Cache aggressively; never re-download a file you already have.
- Use `gsutil -m` for parallelism; the REST API is the wrong tool for bulk.
- Track the database version (`v4`) explicitly in filenames and code.
- For millions of files, work from `accession_ids.csv` rather than enumerating URLs.

## Links

- GCS dataset overview: https://cloud.google.com/datasets/alphafold
- Blog: https://cloud.google.com/blog/products/ai-machine-learning/alphafold-protein-structure-database
