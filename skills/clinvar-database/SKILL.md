---
name: clinvar-database
version: 0.1.0
description: >-
  Query NCBI ClinVar, the public archive that links human genetic variants to
  clinical significance and disease. Search variants by gene, genomic position,
  condition, or pathogenicity through the E-utilities REST API
  (esearch/esummary/efetch/elink) or Biopython Entrez; interpret ACMG/AMP
  germline classes (Pathogenic → Benign, VUS) plus somatic clinical-impact tiers
  and oncogenicity; weigh review-status star ratings; resolve conflicting
  interpretations; and bulk-download XML/VCF/tab-delimited releases over
  HTTPS/FTP to annotate or filter your own VCFs with bcftools. Use when you need
  clinical-significance annotations, a high-confidence pathogenic variant list,
  or a local ClinVar mirror. NOT for direct clinical diagnosis (always defer to a
  genetics professional), variant-effect prediction or gnomAD population
  frequencies, somatic-tumor pipeline analysis (use `cancer-genomics-analysis`),
  or generic multi-database lookups (use `database-lookup`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# ClinVar Database

## Overview

ClinVar is NCBI's freely accessible archive of assertions about the relationship
between human genetic variants and phenotypes, with supporting evidence. It
aggregates submissions from clinical labs, expert panels, and researchers into
standardized variant classifications used across genomic medicine and research.
Every variant carries both a clinical-significance classification and a
**review status** (star rating) that signals how much evidence backs it.

Reach ClinVar three ways, depending on scale:

| Access path | Best for | Reference |
|-------------|----------|-----------|
| E-utilities REST API / Entrez Direct | Targeted queries, a few hundred records, scripting | `references/eutils-api.md` |
| Bulk FTP download (XML / VCF / tab-delimited) | Whole-database analysis, local mirror, VCF annotation | `references/data-formats.md` |
| Web interface (`ncbi.nlm.nih.gov/clinvar`) | Manual exploration, prototyping a query string | — |

Prototype a query string on the web interface first, then reuse the exact same
`term=` syntax in the API.

## When to Use This Skill

- Searching variants by gene, condition, chromosome position, or pathogenicity.
- Retrieving or interpreting a variant's clinical significance (P / LP / VUS / LB / B).
- Annotating your own VCF with ClinVar `CLNSIG` / `CLNDN` / `CLNREVSTAT` fields.
- Building a high-confidence pathogenic variant list filtered by star rating.
- Resolving or flagging conflicting interpretations across submitters.
- Downloading a monthly release to build a reproducible local ClinVar database.
- Programmatic access via NCBI E-utilities or Biopython `Entrez`.

## When NOT to Use This Skill

- **Direct clinical diagnosis or patient management** — ClinVar assertions are
  submitted evidence, not a diagnosis. Always involve a genetics professional.
- **Variant-effect prediction** (SIFT/PolyPhen/CADD/AlphaMissense) or computing
  population frequencies — ClinVar reports frequencies from other sources but is
  not the primary tool; use dedicated predictors and gnomAD.
- **Somatic-tumor sequencing pipelines** end to end — use `cancer-genomics-analysis`;
  come back here only for the ClinVar somatic-tier / oncogenicity annotation.
- **Reading/writing VCF/BAM records programmatically** — use `pysam`.
- **Generic lookups across many bio databases** — use `database-lookup`; use
  `citation-management` to turn ClinVar's PubMed refs into formatted citations.

## Search and Query

ClinVar's E-utilities use the same field-tagged query syntax as the web search
box. **Clinical significance and conflicts are `[Properties]` filters, not their
own fields**; review status is the `[RVST]` field keyed on the exact aggregate
string. Working tags: `[gene]`, `[DIS]` (disease/phenotype), `[chr]`,
`[variant name]` (HGVS), `"clinsig pathogenic"[Properties]` (also `likely
pathogenic` / `vus` / `likely benign` / `benign`), `"clinsig has
conflicts"[Properties]`, `"reviewed by expert panel"[RVST]`.

There is **no `[CLNSIG]`, `[RVSTAT]`, or `[Assembly]` search field** — Entrez
silently rewrites an unknown tag to a free-text `[All Fields]` match, so
`pathogenic[CLNSIG]` returns every record containing the *word* "pathogenic"
(~3× the real set) instead of filtering on classification. Build (GRCh37 vs
GRCh38) is carried by position and by which VCF you download, not by a term.

```bash
# Search: pathogenic BRCA1 variants, JSON, up to 100 IDs
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=BRCA1%5Bgene%5D+AND+%22clinsig+pathogenic%22%5BProperties%5D&retmode=json&retmax=100"
```

The four operations — `esearch` (find UIDs), `esummary` (compact summaries),
`efetch` (full VCV/RCV XML), `elink` (links to PubMed / Gene / MedGen / dbSNP) —
plus the Entrez Direct CLI, Biopython, rate limits, and error handling are
documented in **`references/eutils-api.md`**. Two rules that bite everyone:

- **Rate limit**: 3 requests/sec without an API key, 10/sec with one. Add
  `&api_key=<KEY>` and back off exponentially on HTTP 429.
- **Large result sets** (>~500 UIDs): pass `usehistory=y` and page through
  `WebEnv`/`query_key` instead of one giant `id=` list. With Biopython set
  `Entrez.email` (required) before any call.

## Interpret Clinical Significance

ClinVar carries three classification tracks: **germline** (ACMG/AMP), **somatic
clinical impact** (AMP/ASCO/CAP Tiers I–IV), and **somatic oncogenicity**
(ClinGen/CGC/VICC). The five core germline terms:

| Term | Abbr | Meaning |
|------|------|---------|
| Pathogenic | P | Causes disease (~99% posterior) |
| Likely Pathogenic | LP | Likely causes disease (~90%) |
| Uncertain Significance | VUS | Insufficient evidence to classify |
| Likely Benign | LB | Likely does not cause disease |
| Benign | B | Does not cause disease |

Never read a classification without its **review status**: ★★★★ practice
guideline, ★★★ expert-panel (e.g. ClinGen), ★★ multiple submitters no conflicts,
★ single submitter with criteria, ☆ no assertion criteria. Prefer ★★★/★★★★ for
any downstream decision; treat VUS as "unknown," not "benign."

Full term glossary (low-penetrance / risk-allele / drug-response terms,
recessive and compound-het rules, somatic tiers, red flags, conflict handling)
is in **`references/clinical-significance.md`**.

### Conflicting interpretations

When submitters disagree, ClinVar reports "Conflicting interpretations of
pathogenicity" and shows every submission. Resolution order: highest star
rating first, then assertion criteria quality, then submission recency, then
population/functional evidence, then any expert-panel (★★★) call. Exclude
conflicts in a query with `... NOT "clinsig has conflicts"[Properties]`. For
clinical use, defer to a genetics professional.

## Bulk Data and VCF Annotation

Bulk releases live under `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/` (HTTPS is
preferred; the `ftp://` host still resolves). Monthly releases drop the first
Thursday of each month and are archived indefinitely — **pin a monthly release
for reproducibility**; weekly updates land each Monday.

- **XML** (`xml/clinvar_variation/`, `xml/RCV/`) — most complete: full
  submissions, evidence, VCV/RCV/SCV accessions. Stream with an iterparse loop
  and `elem.clear()` — releases are multi-GB compressed.
- **VCF** (`vcf_GRCh37/`, `vcf_GRCh38/clinvar.vcf.gz`) — for genomic pipelines.
  Excludes variants >10 kb and complex structural variants. Match your genome
  build.
- **Tab-delimited** (`tab_delimited/variant_summary.txt.gz`) — quick pandas/awk
  filtering and database loading.

```bash
# Download the GRCh38 VCF + its tabix index, then annotate your calls
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi
bcftools annotate -a clinvar.vcf.gz \
  -c INFO/CLNSIG,INFO/CLNDN,INFO/CLNREVSTAT \
  -o annotated.vcf your_variants.vcf
bcftools view -i 'INFO/CLNSIG~"Pathogenic"' annotated.vcf
```

The `.tbi` index must sit beside the bgzipped VCF or `bcftools annotate` fails.
File-format schemas (VCF INFO fields, XML record layout, tab column list),
accession semantics (VCV/RCV/SCV versioning), and pandas/xml.etree/bcftools
processing recipes are in **`references/data-formats.md`**. For VCF I/O in
Python, prefer `pysam` or `cyvcf2` over the unmaintained `PyVCF`.

## Versioning and Reproducibility

Classifications change as evidence accrues (new functional or population data,
revised ACMG guidelines, family segregation). To keep results reproducible:

- Record the **ClinVar release date/version and your access date** in outputs.
- Build pipelines against a **pinned monthly archive**, not `00-latest`.
- Re-check critical variants periodically; reclassification can move either way.
- Keep the genome build (GRCh37 vs GRCh38) consistent across every step.

## Boundaries and Failure Modes

- Submissions carry unequal weight — a ★ single-submitter VUS is not comparable
  to a ★★★ expert-panel Pathogenic call.
- VCF releases silently omit large/complex variants; use XML if completeness
  matters.
- Coverage is uneven across genes and ancestries; absence of a variant is not
  evidence of benignity.
- `Entrez.read` parses XML — do not pass it a `retmode=json` handle; use the
  default XML retmode with Biopython, or `json` only with your own JSON parser.
- Coordinate one genome build end to end; mixing GRCh37 and GRCh38 positions is
  a common silent bug.

## Resources

- `references/eutils-api.md` — E-utilities operations, Entrez Direct, Biopython, rate limits, errors.
- `references/clinical-significance.md` — full classification and review-status glossary, conflict handling.
- `references/data-formats.md` — XML/VCF/tab-delimited schemas, FTP layout, accessions, processing recipes.
- ClinVar docs: https://www.ncbi.nlm.nih.gov/clinvar/docs/
- E-utilities docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- ACMG/AMP guidelines: Richards et al. 2015 (PMID: 25741868); ClinGen: https://clinicalgenome.org/
