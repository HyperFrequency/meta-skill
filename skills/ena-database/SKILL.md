---
name: ena-database
version: 0.1.0
description: >-
  Retrieve nucleotide data from the European Nucleotide Archive (ENA, at EMBL-EBI)
  over its public REST APIs and FTP: DNA/RNA sequences, raw sequencing reads
  (FASTQ), genome/transcriptome assemblies, run/experiment/sample/study metadata,
  and NCBI-compatible taxonomy. Use to fetch a record by accession (ERR/SRR/DRR,
  PRJ*, SAM*, assembly IDs), run Portal-API metadata searches (by taxon, study,
  library strategy, collection date), resolve FASTQ/BAM download URLs plus MD5
  checksums for a run, pull EMBL-flatfile or FASTA sequence text, or bulk-download
  via FTP/Aspera/enaBrowserTools. Not for protein sequences or 3D structures (use
  uniprot-database / pdb-database / alphafold-database), gene models or variants
  (ensembl / gwas-database), literature (pubmed-database), submitting/uploading
  data to ENA, or local parsing and alignment of downloaded files (use biopython)
  — this skill is read-only retrieval from ENA.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# ENA Database

## Overview

The European Nucleotide Archive (ENA), hosted at EMBL-EBI, is a public,
open-access repository for nucleotide sequence data: raw reads, assemblies,
annotated sequences, and their metadata. It is one of the three INSDC partners
(with NCBI's GenBank/SRA and DDBJ), so records submitted to any partner
propagate to ENA and accessions are cross-resolvable.

This skill covers **read-only retrieval** over ENA's public HTTP APIs — no
authentication, no client library required, just `requests` (or `curl`) against
documented endpoints. Two APIs do most of the work:

- **Portal API** (`/ena/portal/api`) — advanced metadata *search* across all
  object types, plus the `filereport` endpoint that resolves FASTQ/BAM download
  URLs and checksums for a run.
- **Browser API** (`/ena/browser/api`) — direct *retrieval* of a single record
  by accession as XML, EMBL flatfile, or FASTA.

Deep endpoint tables, every query operator, the full field lists, and worked
error-handling code live in `references/api-reference.md`. This file is the
router — read it first, then load the reference when you need exact parameters.

## When to Use This Skill

- **Fetch a record by accession**: reads (`ERR`/`SRR`/`DRR`…), studies (`PRJEB`/
  `PRJNA`/`PRJDB`), samples (`SAM*`), experiments, analyses, assemblies, or
  sequences (`LN847353`).
- **Metadata search at scale**: find all samples in a study, all `RNA-Seq`
  experiments for a taxon, or assemblies for a clade — filtered by taxonomy,
  date, library strategy, platform, or any indexed field.
- **Resolve download URLs for raw reads**: get FASTQ/BAM/CRAM FTP + Aspera URLs,
  byte sizes, and MD5s for a run via `filereport`, then download and verify.
- **Pull sequence text**: EMBL flatfile or FASTA for an assembled/annotated
  sequence, optionally a sub-range.
- **Taxonomy lookups**: resolve an NCBI taxon ID or scientific name to lineage
  and rank.
- **Bulk downloads**: stage many runs or a whole study via FTP, Aspera, or
  `enaBrowserTools`.
- **Cross-references**: find related records in external databases (BioSamples,
  SRA, etc.).

## When NOT to Use This Skill

- **Protein sequences, domains, or 3D structure** — use `uniprot-database`,
  `pdb-database`, or `alphafold-database`.
- **Gene models, transcripts, or germline/somatic variants** — use an
  Ensembl-oriented skill or `gwas-database`; ENA stores sequence, not curated
  gene annotation or variant calls.
- **Literature / publications** — use `pubmed-database`.
- **Submitting, uploading, or updating records in ENA** — this skill is
  retrieval only; ENA submission uses the authenticated Webin service (out of
  scope).
- **Parsing, QC, trimming, or aligning downloaded reads/sequences** — use
  `biopython` or dedicated bioinformatics tools once files are local.
- **A one-off "which database has X?" question** — start with `database-lookup`,
  then come here for the actual ENA calls.

If you need many INSDC databases behind one client, `bioservices` and `gget`
also wrap ENA/EBI services and may be more convenient for mixed workflows.

## Accession and Object Model

ENA data is hierarchical. Know which object you are asking for before you pick
an endpoint:

| Object | Accession prefixes | What it is |
|--------|--------------------|------------|
| Study / Project | `PRJEB`, `PRJNA`, `PRJDB` (alias `ERP`/`SRP`/`DRP`) | Top-level grouping; the unit you cite in papers |
| Sample | `SAMEA`, `SAMN`, `SAMD` (alias `ERS`/`SRS`/`DRS`) | Biomaterial a library was made from |
| Experiment | `ERX`, `SRX`, `DRX` | Library-prep + instrument metadata |
| Run | `ERR`, `SRR`, `DRR` | The actual raw-read data files (FASTQ/BAM) |
| Analysis | `ERZ` | Derived results (e.g. variant calls, assemblies) |
| Assembly | `GCA_*` | Genome/transcriptome/metagenome assembly |
| Sequence | e.g. `LN847353`, `A00145` | Assembled + annotated EMBL entry |

Reads come as **run** files; a run belongs to an experiment, which belongs to a
sample and a study. To go from "a study" to "FASTQ files" you search for its
runs (Portal API), then call `filereport` per run to get file URLs.

## Quick Start

Search the Portal API for all samples in a study:

```python
import requests

resp = requests.get(
    "https://www.ebi.ac.uk/ena/portal/api/search",
    params={
        "result": "sample",                       # object type to return
        "query": 'study_accession="PRJEB1234"',   # ENA query syntax
        "fields": "sample_accession,scientific_name,collection_date",
        "format": "json",
        "limit": 0,                               # 0 = no cap; default caps at 100000
    },
    timeout=60,
)
resp.raise_for_status()
samples = resp.json()
```

Resolve FASTQ download URLs + checksums for one run, then verify a download:

```python
import hashlib, requests

report = requests.get(
    "https://www.ebi.ac.uk/ena/portal/api/filereport",
    params={
        "accession": "ERR164407",
        "result": "read_run",
        "fields": "run_accession,fastq_ftp,fastq_md5,fastq_bytes",
        "format": "json",
    },
    timeout=60,
).json()[0]

ftp_urls = report["fastq_ftp"].split(";")     # semicolon-separated (paired-end -> 2 URLs)
md5s     = report["fastq_md5"].split(";")
# FTP paths come back host-relative; prefix with https:// to fetch over HTTP
```

Fetch a single record directly by accession (Browser API):

```python
# EMBL flatfile for an annotated sequence
embl = requests.get("https://www.ebi.ac.uk/ena/browser/api/text/LN847353").text
# FASTA, sub-range 1000-2000
fa   = requests.get("https://www.ebi.ac.uk/ena/browser/api/fasta/LN847353",
                    params={"range": "1000-2000"}).text
# XML metadata for a sample, including cross-reference links
xml  = requests.get("https://www.ebi.ac.uk/ena/browser/api/xml/SAMEA123456",
                    params={"includeLinks": "true"}).text
```

## Query Syntax (essentials)

Portal-API `query` uses a small operator language. Full grammar and every
result type are in `references/api-reference.md`; the core:

- Equality: `field="value"` or `field=value`; wildcard with `*`.
- Boolean: `AND`, `OR`, `NOT`; parenthesise for grouping.
- Ranges: `collection_date>=2020-01-01 AND collection_date<=2023-12-31`.
- Taxonomy: `tax_eq(9606)` (exact taxon) vs `tax_tree(562)` (taxon **and all
  descendants**) — use `tax_tree` for a clade, `tax_eq` for one species.
- Discover fields with the `returnFields` endpoint before guessing names; each
  `result` type has a different field set.

## Bulk Download

For more than a handful of files, do not iterate the API — use file transfer:

- **FTP** from the URLs in `fastq_ftp` / `submitted_ftp` (prefix host-relative
  paths with `https://` or `ftp://`), verifying every file against its MD5.
- **Aspera** (`fastq_aspera`, `era-fasp@fasp.sra.ebi.ac.uk:`) for large,
  high-latency transfers.
- **enaBrowserTools** CLI: `enaDataGet ERR164407` for one accession,
  `enaGroupGet PRJEB1234` to pull every run in a study.

## Rate Limits and Robustness

- ENA documents a limit around **50 requests/second**; exceeding it returns
  HTTP `429`. Be conservative — space calls, batch queries, and prefer one
  large `search`/`filereport` over many tiny per-accession calls.
- Retry `429`, `500`, `502`, `503`, `504` with **exponential backoff**;
  treat `404` (unknown accession) and `400` (bad query) as non-retryable.
- Parse XML with a real XML parser, never regex. Handle pagination
  (`limit`/`offset`) for large result sets, and always MD5-verify downloads.

A ready-to-use retrying `requests.Session` and the full status-code table are in
`references/api-reference.md`.

## References

- **[references/api-reference.md](references/api-reference.md)** — every
  endpoint (Portal `search` / `returnFields` / `results` / `filereport`, Browser
  `xml` / `text` / `fasta` / `links`, Taxonomy REST, Cross-Reference, CRAM
  registry), full parameter tables, `filereport` field list, the complete query
  operator grammar, the retrying-session pattern, and query-optimization tips.
- Official docs: Portal API `https://www.ebi.ac.uk/ena/portal/api/doc` ·
  Browser API `https://www.ebi.ac.uk/ena/browser/api/doc`.
