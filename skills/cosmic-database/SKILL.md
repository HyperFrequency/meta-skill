---
name: cosmic-database
version: 0.1.0
description: >-
  Programmatic access to COSMIC (Catalogue of Somatic Mutations in Cancer), the
  Sanger Institute's curated catalogue of somatic cancer mutations — millions
  of SNVs/indels, the ~700-gene Cancer Gene Census, SBS/DBS/ID signature
  profiles, gene fusions, structural variants,
  copy-number, expression, and drug-resistance mutations across GRCh37/GRCh38.
  Use to authenticate and bulk-download COSMIC files (TSV/CSV/VCF), pick the
  right file for a data type and assembly, and load/filter them with pandas or
  pysam for cancer-genomics and precision-oncology pipelines. Requires a
  registered COSMIC account (free for academic use; commercial license via
  QIAGEN). Do NOT use for downstream analysis — somatic calling, CNV/SV
  profiling, TMB, signature deconvolution (use `cancer-genomics-analysis`);
  germline/clinical variant interpretation (ClinVar via `database-lookup`);
  drug/bioactivity databases (`chembl-database`); or general gene lookups
  (`gget`, `bioservices`). COSMIC ships whole-file dumps, not a per-variant
  query API.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "COSMIC data: free for academic/non-commercial use with registration; commercial license via QIAGEN"
---

# COSMIC Database

## Overview

COSMIC (Catalogue of Somatic Mutations in Cancer), maintained by the Wellcome
Sanger Institute, is the largest curated catalogue of somatic mutations in human
cancer — millions of mutations across thousands of tumor types, plus curated gene
lists, mutational-signature reference profiles, and clinical annotations.

COSMIC is distributed as **whole-file dumps** (TSV, CSV, VCF; gzip-compressed)
grouped by genome assembly and release. There is no fine-grained public query
API — you authenticate, download the file for the data type you need, then load
and filter it locally. This skill covers authentication, choosing the right file,
the two-step download protocol, and the standard pandas/pysam load patterns.

Deep material lives in the references:
- [references/data-products.md](references/data-products.md) — full file
  catalogue, field dictionaries, formats, assemblies, versioning caveats,
  downstream tools, and citation.
- [references/download-and-recipes.md](references/download-and-recipes.md) — the
  full download helper, data-type shortcut table, load/filter recipes, and
  troubleshooting.

## When to Use This Skill

- Bulk-download cancer mutation data (coding/non-coding SNVs and indels).
- Pull the **Cancer Gene Census** to identify known cancer genes or prioritize
  variants by cancer relevance.
- Retrieve **SBS/DBS/ID mutational-signature** reference profiles to fit against.
- Fetch structural variants, gene fusions, copy-number, or expression files.
- Access drug-resistance mutations with clinical annotations.
- Work with cancer cell-line genomics files.
- Feed COSMIC files into a bioinformatics or ML cancer-genomics pipeline.

## When NOT to Use This Skill

- **Downstream analysis** — somatic mutation calling, VCF annotation, CNV/SV
  profiling, tumor mutational burden, or signature deconvolution: use
  `cancer-genomics-analysis` (this skill only *retrieves* the data).
- **Germline / clinical variant interpretation** — use ClinVar via
  `database-lookup`; COSMIC catalogues somatic cancer mutations.
- **Bioactivity or drug databases** — use `chembl-database`.
- **General gene/genome/ID lookups** — use `gget` or `bioservices`.
- **Interactive, per-variant queries** — COSMIC has no public REST query API for
  arbitrary variants; use the web interface for exploratory point lookups, or
  download the file and query it locally.

## Access and Authentication

COSMIC requires a registered account for downloads:

- **Academic / non-commercial**: free with registration at
  https://cancer.sanger.ac.uk/cosmic/register.
- **Commercial**: license required through QIAGEN
  (`cosmic-translation@sanger.ac.uk`).

Store credentials outside your code (env var or `getpass`); never commit a
password.

## Setup

```bash
uv pip install requests pandas   # add pysam to read VCF files
```

## Download Workflow

COSMIC downloads are a **two-step** protocol: an authenticated request returns a
short-lived **signed URL**, then you stream the file from that URL. Minimal form:

```python
import os, requests

def download_cosmic_file(email, password, filepath, output=None):
    endpoint = "https://cancer.sanger.ac.uk/cosmic/file_download/"
    output = output or os.path.basename(filepath)
    # Step 1: credentials + path -> signed, short-lived download URL (JSON).
    meta = requests.get(endpoint + filepath, auth=(email, password), timeout=30)
    meta.raise_for_status()
    signed_url = meta.json()["url"]
    # Step 2: stream the bytes from the signed URL (no auth on this leg).
    with requests.get(signed_url, stream=True, timeout=300) as r, open(output, "wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=1 << 16):
            f.write(chunk)
    return output

download_cosmic_file(
    "you@institution.edu", os.environ["COSMIC_PASSWORD"],
    "GRCh38/cosmic/latest/CosmicMutantExport.tsv.gz",
)
```

Legacy path pattern: `{assembly}/cosmic/{version}/{filename}`. Use `latest` for
the newest release or pin a version (e.g. `v102`) for reproducibility. The full
helper with progress, error handling, and a data-type shortcut table is in
[references/download-and-recipes.md](references/download-and-recipes.md).

> **Filenames change between releases.** Older releases use flat names like
> `CosmicMutantExport.tsv.gz`; recent ones use `Cosmic_<Product>_v<NN>_<Assembly>`.
> Confirm the exact path against the current download page before scripting it.

## Core Data Products

| Data type | File (legacy name) | Use |
|---|---|---|
| Coding mutations | `CosmicMutantExport.tsv.gz` | SNVs/indels, annotations, tumor type |
| Mutations (Census only) | `CosmicMutantExportCensus.tsv.gz` | smaller, cancer-gene subset |
| Mutations (VCF) | `CosmicCodingMuts.vcf.gz` | annotation/region queries |
| Cancer Gene Census | `cancer_gene_census.csv` | ~700+ curated cancer genes |
| Signatures | `signatures/signatures.tsv` | SBS/DBS/ID reference profiles (v3.4) |
| Structural variants | `CosmicStructExport.tsv.gz` | breakpoints, rearrangements |
| Gene fusions | `CosmicFusionExport.tsv.gz` | curated fusion events |
| Copy number | `CosmicCompleteCNA.tsv.gz` | gains/losses, amplifications |
| Expression | `CosmicCompleteGeneExpression.tsv.gz` | over/under-expression Z-scores |
| Resistance mutations | `CosmicResistanceMutations.tsv.gz` | therapy-resistance variants |
| Sample metadata | `CosmicSample.tsv.gz` | tumor site/histology, study refs |

Field dictionaries and the full catalogue are in
[references/data-products.md](references/data-products.md).

## Common Analysis Patterns

```python
import pandas as pd

mutations   = pd.read_csv("CosmicMutantExport.tsv.gz", sep="\t", compression="gzip")
gene_census = pd.read_csv("cancer_gene_census.csv")

# Mutations in one gene
tp53 = mutations[mutations["Gene name"] == "TP53"]

# Cancer genes by role
oncogenes = gene_census[gene_census["Role in Cancer"].str.contains("oncogene", na=False)]

# Prioritize a variant table: keep only known cancer genes
known = set(gene_census["Gene Symbol"])
prioritized = mutations[mutations["Gene name"].isin(known)]
```

Core files run to several GB — stream downloads to disk and filter huge TSVs in
chunks (`pd.read_csv(..., chunksize=...)`). VCF region queries need the tabix
`.tbi` index and `pysam`. See
[references/download-and-recipes.md](references/download-and-recipes.md) for
chunked filtering, VCF `fetch`, and troubleshooting (401/404, expired signed
URLs, HTML responses).

## Assemblies and Versioning

- **GRCh38** (hg38) — current standard, recommended.
- **GRCh37** (hg19) — legacy; keep the assembly consistent across a pipeline.
- COSMIC releases periodically (a few per year). As of the source material the
  current release was v102 (May 2025) — treat as a snapshot and check the release
  notes for the live version.

## Related Skills

- `cancer-genomics-analysis` — the analysis layer over COSMIC files (calling,
  CNV/SV, TMB, signatures).
- `database-lookup` — ClinVar and other biomedical databases.
- `chembl-database`, `gget`, `bioservices` — sibling data-access skills.

## Citation

Tate JG, Bamford S, Jubb HC, et al. *COSMIC: the Catalogue Of Somatic Mutations
In Cancer.* Nucleic Acids Research. 2019;47(D1):D941–D947.
