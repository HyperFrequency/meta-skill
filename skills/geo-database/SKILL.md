---
name: geo-database
version: 0.1.0
description: >-
  Retrieve gene-expression and functional-genomics data from NCBI GEO (Gene
  Expression Omnibus). Use to search studies/samples/platforms by keyword,
  organism, platform, or study type (E-utilities via Biopython); download and
  parse a Series into an expression matrix plus per-sample metadata (GEOparse);
  pull SOFT / series-matrix / MINiML / supplementary files by accession
  (GSE/GSM/GPL/GDS) over FTP; or map probe IDs to genes via platform annotation.
  Covers the GSE->GSM->GPL hierarchy, the pivot_samples gotcha, log-transform
  checks, and NCBI rate limits. Not for protein sequences
  or structures (use uniprot-database / pdb-database / alphafold-database), raw
  reads or assemblies (ena-database), germline/somatic variants (clinvar-database),
  literature (pubmed-database), single-cell atlases (cellxgene-census), submitting
  data to GEO, or heavy differential-expression statistics once files are local
  (use statsmodels / scikit-learn) — this skill is read-only GEO retrieval and
  expression-matrix assembly.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: GEOparse BSD-3-Clause; Biopython BSD-derived (Biopython License Agreement)
---

# GEO Database

## Overview

The Gene Expression Omnibus (GEO) is NCBI's public repository for
high-throughput gene-expression and functional-genomics data — hundreds of
thousands of studies spanning both array-based and sequence-based experiments,
each with sample-level metadata and downloadable expression tables.

This skill covers **read-only retrieval** and matrix assembly. Three access
routes do all the work; pick by what you have and what you want:

| Route | Library / protocol | Best for |
|-------|--------------------|----------|
| **GEOparse** | `GEOparse` (pip) | You have an accession and want a parsed Series: metadata, per-sample tables, platform annotation, and an expression matrix in one call. Start here. |
| **E-utilities** | `Bio.Entrez` (Biopython) | You need to *search* — find studies by keyword/organism/platform/date, fetch summaries, or cross-link to PubMed. Returns IDs and metadata, not expression values. |
| **Direct FTP** | `wget` / `curl` / `ftplib` | Bulk downloads, raw supplementary files (CEL/BAM), or when you already know the exact file and want to skip parsing. |

Deep material — the full E-utilities API, search-field qualifiers, SOFT/MINiML
format specs, the FTP directory-naming scheme, advanced GEOparse patterns,
differential-expression example code, troubleshooting, and platform-specific
quirks — lives in **[references/geo-reference.md](references/geo-reference.md)**.
This file is the router; load the reference when you need exact parameters.

## When to Use This Skill

- **Download and parse a study** by accession (`GSE…`) into an expression matrix
  plus sample metadata.
- **Search for datasets** matching a disease, organism, platform, study type
  (RNA-seq / expression profiling by array), author, or date range.
- **Find gene-centric expression profiles** across many studies (GEO Profiles).
- **Retrieve a specific file** — series matrix, family SOFT, MINiML XML, or raw
  supplementary files — for one or many accessions.
- **Map probe IDs to gene symbols** using the platform (`GPL`) annotation table.
- **Assemble a cross-study matrix** for meta-analysis of one gene or signature.

## When NOT to Use This Skill

- **Protein sequences, domains, or 3D structure** — use `uniprot-database`,
  `pdb-database`, or `alphafold-database`.
- **Raw sequencing reads (FASTQ), runs, or genome assemblies** — use
  `ena-database` (or NCBI SRA directly); GEO links to SRA for raw reads but does
  not host them.
- **Germline/somatic variants or clinical significance** — use `clinvar-database`.
- **Curated single-cell atlases** — use `cellxgene-census`; GEO hosts raw
  single-cell submissions but not a harmonized census.
- **Literature / publications** — use `pubmed-database`.
- **Submitting or updating records in GEO** — this skill is retrieval only;
  submission uses NCBI's authenticated GEOsubmit/Webin flows (out of scope).
- **Heavy downstream statistics** once the matrix is local — do differential
  expression, clustering, and modeling with `statsmodels`, `scikit-learn`, or a
  single-cell toolkit; this skill gets you a clean matrix, not the analysis.
- **A one-off "which database has X?" question** — start with `database-lookup`,
  then come here for the actual GEO calls. `bioservices` also wraps GEO/NCBI if
  you need many EBI/NCBI services behind one client.

## Accession and Data Model

GEO is hierarchical. Know which object you are asking for before choosing an
endpoint:

| Object | Prefix | What it is |
|--------|--------|------------|
| **Series** | `GSE` | A complete experiment — the unit you cite. Groups its samples + platforms. |
| **Sample** | `GSM` | One biological sample/replicate: its own data table + metadata (source, characteristics, protocol). |
| **Platform** | `GPL` | The array/sequencer used; carries the probe→gene annotation table. Shared across many series. |
| **DataSet** | `GDS` | A *curated*, reprocessed, comparison-ready subset of Series (a minority of GEO). Ideal for quick comparative analysis. |
| **Profile** | — | Gene-specific expression across studies, queryable by gene name (the `geoprofiles` E-utilities database). |

To get expression values from a study: fetch its `GSE`, which contains its
`GSM` samples (each with a data table) and its `GPL` platform (for gene
annotation). A `GSM` table holds `ID_REF` (probe) + `VALUE` (expression).

## Quick Start

Install: `uv pip install GEOparse biopython` (add `pandas numpy` for analysis).

**Parse a Series and get the expression matrix (GEOparse):**

```python
import GEOparse

# Downloads to destdir and caches; re-runs read the cache
gse = GEOparse.get_GEO(geo="GSE123456", destdir="./data")

print(gse.metadata["title"][0])           # metadata values are lists
print(gse.metadata["summary"][0])

# Fastest matrix: pivots the series-matrix file (probes x samples)
expr = gse.pivot_samples("VALUE")          # -> pandas DataFrame

# Per-sample metadata
for gsm_name, gsm in gse.gsms.items():
    title = gsm.metadata["title"][0]
    chars = gsm.metadata.get("characteristics_ch1", [])
```

**Search for datasets (E-utilities via Biopython):**

```python
from Bio import Entrez
Entrez.email = "you@example.com"           # REQUIRED by NCBI
# Entrez.api_key = "..."                    # optional: 10 req/s vs 3 req/s

handle = Entrez.esearch(
    db="gds",                              # GEO DataSets; use "geoprofiles" for genes
    term="breast cancer[MeSH] AND Homo sapiens[Organism] AND "
         "expression profiling by array[DataSet Type]",
    retmax=20, usehistory="y",
)
results = Entrez.read(handle); handle.close()
print(results["Count"], results["IdList"][:5])
```

Then `Entrez.esummary(db="gds", id=...)` for titles/sample counts, or
`Entrez.efetch(...)` for full records. See the reference for every field
qualifier (`[Organism]`, `[Platform]`, `[Publication Date]`, `[Author]`, …) and
`elink`/`epost`/`einfo`.

## Getting the Expression Matrix (the main gotcha)

`pivot_samples("VALUE")` is the fast path, but it depends on a **series-matrix
file**, which older or some sequence-based submissions lack. When it fails or
returns empty, build the matrix from per-sample tables instead:

```python
import pandas as pd

data = {}
for gsm_name, gsm in gse.gsms.items():
    if hasattr(gsm, "table") and "VALUE" in gsm.table.columns:
        data[gsm_name] = gsm.table.set_index("ID_REF")["VALUE"]
expr = pd.DataFrame(data)                   # aligns on shared probe index
```

Two more checks before analysis:

- **Scale / log-transform**: values may be raw, normalized, or log2. Inspect the
  range; only `log2(x + 1)` if not already log-scaled (large max, positive min).
  Read `Sample_data_processing` in the metadata — do not assume.
- **Probe → gene**: rows are platform probes, not genes. Map via the `GPL`
  annotation table (`gpl.table`, columns like `ID`, `Gene Symbol`, `Gene ID`).
  Multiple probes per gene is normal; collapse deliberately (max, mean, or
  keep-all). Annotation mapping and multi-probe handling are in the reference.

## Direct File and Bulk Download

GEO's FTP layout replaces the last three digits of an accession with `nnn`:
`GSE123456` → `…/geo/series/GSE123nnn/GSE123456/` with `matrix/`, `soft/`,
`miniml/`, and `suppl/` subdirectories. For more than a few files, prefer FTP
over API iteration:

```bash
# Series matrix (expression), then the family SOFT (full metadata + tables)
wget ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE123nnn/GSE123456/matrix/GSE123456_series_matrix.txt.gz
wget ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE123nnn/GSE123456/soft/GSE123456_family.soft.gz
```

GEOparse can also fetch supplementary files:
`gse.download_supplementary_files(directory="./suppl", download_sra=False)`.
Parse an already-downloaded file offline with
`GEOparse.get_GEO(filepath="./GSE123456_family.soft.gz")`.

The full FTP naming scheme (series/sample/platform paths, `.annot.gz` enhanced
platform annotations) is in the reference.

## Rate Limits and Pitfalls

- **NCBI E-utilities**: 3 req/s without an API key, 10 req/s with one. Space
  calls (`time.sleep(0.34)` / `0.1`); retry HTTP `429`/`5xx` with backoff;
  batch with the history server (`usehistory="y"` + `WebEnv`/`QueryKey`) rather
  than many tiny requests. **Always set `Entrez.email`** or NCBI may block you.
- **FTP has no documented rate limit** — the preferred route for bulk transfers.
- **GEOparse caches** in `destdir`; repeat calls reuse the cache. Clear it
  periodically — family SOFT files reach hundreds of MB and CEL bundles are GBs.
- **Data quality is uneven**: user-submitted, mixed normalization, inconsistent
  characteristic formatting, deprecated/renamed genes in old platform
  annotations, and cross-study batch effects. Verify processing methods and
  platform version before trusting values. Cite the original study and
  Barrett et al. (2013, *Nucleic Acids Research*) for GEO itself.

## References

- **[references/geo-reference.md](references/geo-reference.md)** — full
  E-utilities program specs (`esearch`/`esummary`/`efetch`/`elink`/`epost`/
  `einfo`) with parameters and return fields; the complete search-field
  qualifier list and complex-query examples; SOFT and MINiML format
  specifications with a manual SOFT parser; the FTP directory-naming scheme;
  advanced GEOparse (parse modes, platform-annotation mapping, chunked
  large-dataset processing); worked differential-expression and clustering code;
  a troubleshooting guide (failed downloads, missing matrices, probe-ID
  mismatches, rate limiting, memory); and platform-specific notes (Affymetrix,
  Illumina, RNA-seq, two-channel).
- Official docs: GEO `https://www.ncbi.nlm.nih.gov/geo/` · GEOparse
  `https://geoparse.readthedocs.io/` · E-utilities
  `https://www.ncbi.nlm.nih.gov/books/NBK25501/` · GEO2R (web-based DE analysis)
  `https://www.ncbi.nlm.nih.gov/geo/geo2r/`.
