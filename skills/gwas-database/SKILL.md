---
name: gwas-database
version: 0.1.0
description: >-
  Query the NHGRI-EBI GWAS Catalog, the curated repository of published
  genome-wide association studies, for SNP-trait associations and full summary
  statistics. Look up variants by rs ID, search by disease/trait (EFO term) or
  gene, and retrieve p-values, effect sizes (odds ratio / beta), risk alleles,
  study metadata, and ancestry through the two open REST APIs (Catalog API +
  Summary Statistics API) or FTP bulk downloads. Use for genetic-epidemiology
  literature synthesis, pleiotropy scans, assembling polygenic-risk-score
  variant lists, or producing inputs for fine-mapping / colocalization. NOT for
  clinical variant interpretation or pathogenicity (use `clinvar-database`),
  variant consequence annotation or population allele frequencies (use
  `ensembl-database`), pharmacogenomics (use `clinpgx-database`), somatic cancer
  mutations (use `cosmic-database`), or generic multi-database routing (use
  `database-lookup`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# GWAS Catalog Database

## Overview

The NHGRI-EBI GWAS Catalog is a manually curated, freely available collection of
published genome-wide association studies, maintained jointly by the National
Human Genome Research Institute (NHGRI) and the European Bioinformatics Institute
(EBI). It captures SNP-trait associations extracted from thousands of GWAS
papers — the reported variant, the associated trait, the p-value, the effect
size, and the study it came from — and additionally hosts full summary
statistics (every tested variant, not only the genome-wide hits) for a large and
growing subset of studies.

Access is entirely open: a web interface, two REST APIs (no key, no
registration), and an FTP tree for bulk downloads. This skill covers all three,
plus how to interpret the returned fields and cross-reference them with other
resources.

## When to Use This Skill

Use this skill when a task involves published human genetic-association evidence:

- Finding SNPs associated with a **disease or trait** and their statistics.
- Looking up **one variant** (rs ID) and every trait it is associated with
  (pleiotropy).
- Finding variants **in or near a gene**, or in a **chromosomal region**.
- Retrieving **study metadata** — PMID, first author, sample size, ancestry,
  discovery vs. replication.
- Accessing **full summary statistics** for fine-mapping, colocalization, LD
  score regression, or Mendelian randomization inputs.
- Assembling a candidate-variant list for a **polygenic risk score** (then
  hand off to the PGS Catalog for pre-built scores).
- **Systematic review / meta-analysis** of the genetic evidence for a phenotype.

## When NOT to Use This Skill

- **Clinical pathogenicity / ACMG classification of a variant** — use
  `clinvar-database`. The GWAS Catalog reports statistical association, not
  clinical significance.
- **Variant consequence annotation, VEP, or gnomAD population frequencies** —
  use `ensembl-database`.
- **Pharmacogenomics (drug-gene-response)** — use `clinpgx-database` (PharmGKB).
- **Somatic mutations in cancer** — use `cosmic-database`.
- **Target-disease evidence aggregation across many data types** — Open Targets
  builds on GWAS Catalog plus much more; query it directly for that.
- **Deciding which biomedical database to hit at all** — use `database-lookup`.

## Core Concepts

The catalog is organized around four linked entities, each with a canonical
identifier. Get these right and every query follows.

| Entity | What it is | Identifier | Example |
|--------|-----------|-----------|---------|
| Study | A GWAS publication / analysis | `GCST` accession | `GCST001795` |
| Association | One SNP-trait statistical result | numeric ID | — |
| Variant | A SNP | `rs` number | `rs7903146` |
| Trait | A phenotype/disease, mapped to EFO | EFO term | `EFO_0001360` (type 2 diabetes) |

Genes are referenced by HGNC symbol (e.g. `TCF7L2`, `APOE`). The
genome-wide-significance convention is **p ≤ 5×10⁻⁸**; associations below that
threshold are the default "hits."

## The Two APIs

The GWAS Catalog exposes two distinct REST services — pick by what you need:

- **Catalog REST API** — `https://www.ebi.ac.uk/gwas/rest/api`
  Curated associations, studies, variants, traits, genes, publications. JSON in
  HAL format (`_embedded` payload, `_links` for navigation, `page` metadata).
  This is the one you want for "what SNPs are associated with trait X."
- **Summary Statistics API** — `https://www.ebi.ac.uk/gwas/summary-statistics/api`
  Every tested variant for deposited studies, filterable by chromosome,
  position, and p-value. This is the one you want for genome-wide sweeps and
  region extraction.

Version note: the Catalog REST API was re-versioned (v2) in 2024, adding
publications/genes/genomic-context/ancestry endpoints and richer study metadata.
The endpoint paths shown here are the long-standing patterns; treat the live
**interactive docs at `https://www.ebi.ac.uk/gwas/rest/docs/api` as the
authoritative current schema** before hard-coding a path in production, and
confirm response field names against a real response.

## Quick Start

Find genome-wide-significant SNPs for a disease (by EFO term):

```python
import requests

TRAIT = "EFO_0001360"  # type 2 diabetes
url = f"https://www.ebi.ac.uk/gwas/rest/api/efoTraits/{TRAIT}/associations"
r = requests.get(url, params={"size": 100, "page": 0},
                 headers={"Content-Type": "application/json"})
r.raise_for_status()
for a in r.json().get("_embedded", {}).get("associations", []):
    print(a.get("rsId"), a.get("pvalue"), a.get("strongestAllele"))
```

Look up one variant and all its trait associations (pleiotropy):

```python
rs = "rs7903146"
base = "https://www.ebi.ac.uk/gwas/rest/api"
info  = requests.get(f"{base}/singleNucleotidePolymorphisms/{rs}").json()
assoc = requests.get(f"{base}/singleNucleotidePolymorphisms/{rs}/associations",
                     params={"projection": "associationBySnp"}).json()
```

Pull summary statistics for a region below a p-value cutoff:

```python
ss = "https://www.ebi.ac.uk/gwas/summary-statistics/api"
r = requests.get(f"{ss}/chromosomes/10/associations",
                 params={"start": 114000000, "end": 115000000,
                         "p_upper": "0.00000005", "size": 1000})
```

## Common Workflows

Each of these is written up step-by-step, with complete paginated code, in
[references/workflows.md](references/workflows.md):

- **Disease → variant list** — resolve the EFO term, page through all
  associations, filter by p-value, extract rs IDs / alleles / effect sizes,
  cross-reference to Ensembl and gnomAD.
- **Variant → pleiotropy** — collect every trait a SNP hits and its genomic
  context / nearby genes.
- **Gene-centric** — find variants in a gene region (extend boundaries for
  promoter/regulatory), analyze association patterns.
- **Systematic review** — comprehensive extraction with quality assessment
  (sample size, ancestry diversity, replication, heterogeneity) and export.
- **Summary statistics** — locate deposited studies, download harmonised
  files via FTP, or query variant/region slices via the Summary Statistics API.

## Key Fields (cheat sheet)

Catalog association records commonly carry: `rsId`, `strongestAllele` (risk/
effect allele), `pvalue` / `pvalueMantissa` / `pvalueExponent`, `orPerCopyNum`
(odds ratio) or `betaNum` + `betaUnit` (quantitative), `range` (CI),
`standardError`, `efoTrait`, `mappedLabel`, and the source `studyId`. Summary
Statistics records use snake_case: `variant_id`, `chromosome`,
`base_pair_location`, `effect_allele` / `other_allele`,
`effect_allele_frequency`, `beta`, `standard_error`, `p_value`, `odds_ratio`,
`study_accession`. Full field tables and response layouts are in
[references/api_reference.md](references/api_reference.md).

## Best Practices and Gotchas

- **Resolve the EFO term first.** Free-text disease names are ambiguous; find the
  `EFO_xxxxxxx` ID (web interface or the `efoTraits` search endpoints) before
  querying associations, or you will silently miss or over-collect results.
- **Always paginate.** List endpoints default to 20 items/page. Loop on `page`
  until `_embedded` is empty; do not assume the first page is complete.
- **Two APIs, two field vocabularies.** Catalog uses camelCase (`pvalue`,
  `rsId`); Summary Statistics uses snake_case (`p_value`, `variant_id`). Don't
  mix them.
- **Curated ≠ complete.** The Catalog holds *published* associations that met
  curation criteria — it is not every GWAS ever run, and effect sizes are stored
  as reported (may need harmonisation before combining across studies). Beware
  winner's-curse inflation of discovery effect sizes.
- **Prefer FTP for genome-wide work.** For whole-genome summary statistics use
  the FTP tree, not thousands of API calls; reserve the API for targeted slices.
- **Be a good citizen.** No auth or hard rate limit is published, but add a small
  delay (0.1–0.5 s) between calls, cache responses, and handle 404/500 with
  retries. See error handling in [references/api_reference.md](references/api_reference.md).
- **Check ancestry.** Historically European-biased; confirm the discovery/
  replication ancestry before generalizing an association or building a PRS for a
  different population.
- **Data updates continuously.** Re-run queries and record the access date for
  reproducibility.

## Citation

Cite the resource paper when you use GWAS Catalog data, and cite the original
study for any specific finding:

> Sollis E, et al. (2023). The NHGRI-EBI GWAS Catalog: knowledgebase and
> deposition resource. *Nucleic Acids Research*. PMID: 37953337.

## References

- [references/api_reference.md](references/api_reference.md) — full endpoint
  specifications for both APIs, query parameters, response field tables, HAL /
  pagination structure, error handling, and advanced/cross-API query patterns.
- [references/workflows.md](references/workflows.md) — end-to-end recipes with
  complete paginated Python (including a reusable query class and FTP download
  helper) for the five common workflows above.

External resources:

- Web interface — https://www.ebi.ac.uk/gwas/
- Interactive API docs — https://www.ebi.ac.uk/gwas/rest/docs/api
- Summary Statistics API docs — https://www.ebi.ac.uk/gwas/summary-statistics/docs/
- FTP (bulk / summary stats) — http://ftp.ebi.ac.uk/pub/databases/gwas/
- Workshop materials — https://github.com/EBISPOT/GWAS_Catalog-workshop
- `gwasrapidd` R package — https://cran.r-project.org/package=gwasrapidd
- PGS Catalog (pre-built polygenic scores) — https://www.pgscatalog.org/
