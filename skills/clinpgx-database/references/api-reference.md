# ClinPGx REST API Reference

Endpoint-level reference for the ClinPGx v1 REST API. ClinPGx succeeds and
consolidates PharmGKB, CPIC, and PharmCAT; PharmGKB URLs now redirect to
ClinPGx.

> **Stability note.** The v1 API is beta. Endpoint paths, query parameters, and
> response field names below reflect the documented v1 surface and are
> *representative* — confirm exact spellings against a live response and the
> official docs before hard-coding against them. Do not assume a field exists;
> read the JSON you actually get back.

## Base URL, auth, format

- **Base URL**: `https://api.clinpgx.org/v1/`
- **Authentication**: none for public access.
- **Format**: JSON. `200` success, `404` not found, `429` rate limited, `5xx`
  server error.
- **Rate limit**: ~2 requests/second; exceeding it returns `429`. Use ~500 ms
  spacing and exponential backoff.
- **Data license**: CC BY-SA 4.0 + ClinPGx Data Usage Policy.
- **Bulk use**: email `api@clinpgx.org`; prefer the downloadable data dumps over
  scraping the API.

## Endpoints

| Resource | By ID | Search / filter |
| --- | --- | --- |
| Gene | `GET /gene/{symbol}` | `GET /gene?q={term}` |
| Chemical (drug) | `GET /chemical/{id}` | `GET /chemical?name={name}` |
| Gene-drug pair | — | `GET /geneDrugPair?gene=&drug=&cpicLevel=` |
| Guideline | `GET /guideline/{id}` | `GET /guideline?source=&gene=&drug=` |
| Allele | `GET /allele/{name}` | `GET /allele?gene={symbol}` |
| Variant | `GET /variant/{rsid}` | `GET /variant?chromosome=&position=` |
| Clinical annotation | `GET /clinicalAnnotation/{id}` | `GET /clinicalAnnotation?gene=&drug=&evidenceLevel=&phenotype=` |
| Drug label | — | `GET /drugLabel?drug=&source=` |
| Pathway | `GET /pathway/{id}` | `GET /pathway?drug=&gene=` |

ClinPGx accession IDs use the `PA######` scheme (e.g. gene `PA126`, drug
`PA448515` = warfarin, guideline `PA166104939`, pathway `PA146123006`).

### Gene

`GET /gene/{symbol}` — e.g. `CYP2D6`. `GET /gene?q=CYP` searches by symbol/name.

Representative fields: `id`, `symbol`, `name`, `chromosome`,
`chromosomeLocation`, `function`, `description`, and counts/links to related
clinical annotations and drugs.

### Chemical (drug)

`GET /chemical/{id}` by ClinPGx ID; `GET /chemical?name={name}` searches (returns
a list — take the best match, don't assume index 0).

Representative fields: `id`, `name`, `genericNames`, `tradeNames`,
`drugClasses`, `indication`, `relatedGenes`.

### Gene-drug pair

`GET /geneDrugPair` with any of `gene`, `drug`, `cpicLevel` (`A`/`B`/`C`/`D`).
Omitting `gene`/`drug` and passing `cpicLevel=A` enumerates all Level-A
actionable pairs — the basis for a PGx panel.

Representative fields: `gene`, `drug`, `sources` (`["CPIC","FDA","DPWG"]`),
`cpicLevel`, `evidenceLevel`, `clinicalAnnotationCount`, `hasGuideline`,
`guidelineUrl`.

### Guideline

`GET /guideline/{id}`, or filter by `source` (`CPIC`/`DPWG`/`FDA`), `gene`,
`drug`.

Representative fields: `id`, `name`, `source`, `genes`, `drugs`,
`recommendationLevel`, `lastUpdated`, `summary`, `recommendations` (per
phenotype), `pdfUrl`, `pmid`.

### Allele

`GET /allele?gene={symbol}` lists all star alleles; `GET /allele/{name}` (e.g.
`CYP2D6*4`) fetches one.

Representative fields: `name`, `gene`, `function`, `activityScore`,
`frequencies` (map of population → frequency), `definingVariants` (rsIDs),
`pharmVarId`.

### Variant

`GET /variant/{rsid}` (e.g. `rs4244285`); or `GET /variant?chromosome=&position=`
(coordinates are GRCh38 — confirm the assembly for any position query).

Representative fields: `rsid`, `chromosome`, `position`, `gene`, `alleles`,
`consequence`, `clinicalSignificance`, `frequencies`, `references`.

### Clinical annotation

`GET /clinicalAnnotation` filterable by `gene`, `drug`, `evidenceLevel`,
`phenotype`. These are the curated literature summaries formerly branded as
PharmGKB clinical annotations.

Representative fields: `id`, `gene`, `drug`, `phenotype`, `evidenceLevel`,
`annotation`, `pmid`, `studyType`, `population`, `sources`.

### Drug label

`GET /drugLabel?drug={name}` with optional `source`
(`FDA`/`EMA`/`PMDA`/`Health Canada`).

Representative fields: `id`, `drug`, `source`, `sections`
(`testing`/`dosing`/`warnings`), `biomarkers`, `testingRecommended`, `labelUrl`,
`lastUpdated`.

### Pathway

`GET /pathway/{id}` or `GET /pathway?drug=&gene=`.

Representative fields: `id`, `name`, `drugs`, `genes`, `description`,
`diagramUrl`, `steps` (ordered PK/PD steps with the genes acting at each).

## Grading systems

### Metabolizer phenotype

A diplotype's two allele activity scores sum to a phenotype:

| Phenotype | Abbrev | Enzyme activity |
| --- | --- | --- |
| Ultra-rapid metabolizer | UM | Increased |
| Normal metabolizer | NM | Normal |
| Intermediate metabolizer | IM | Reduced |
| Poor metabolizer | PM | Little / none |

Exact activity-score cutoffs are gene-specific (defined by CPIC/PharmVar); read
them from the gene's guideline rather than assuming a universal threshold.

### Allele function

`normal function`, `decreased function`, `no function`, `increased function`,
`uncertain function`, plus a numeric `activityScore` (commonly 0.0-2.0+).

### CPIC level vs. PharmGKB evidence level

Two independent axes — don't conflate them:

- **CPIC level** = *clinical actionability*: `A` (prescribing action
  recommended) → `D` (no action).
- **PharmGKB evidence level** = *strength of evidence*:

| Level | Meaning |
| --- | --- |
| 1A | High-quality evidence; in a CPIC/FDA/DPWG guideline |
| 1B | High-quality evidence; not yet in a guideline |
| 2A | Moderate evidence, well-designed studies, variant in a very important pharmacogene |
| 2B | Moderate evidence, some limitations |
| 3 | Limited or conflicting evidence |
| 4 | Case reports / weak evidence |

## Error responses

```json
// 404
{ "error": "Resource not found", "message": "Gene 'INVALID' does not exist" }

// 429
{ "error": "Rate limit exceeded", "message": "Maximum 2 requests per second allowed" }
```

Handle `429` with exponential backoff, treat `404` as an empty result (not a
crash), and set a request `timeout`. A robust wrapper is in
[query-recipes.md](query-recipes.md).

## Related tools and data sources

- **PharmCAT** — genotype/diplotype calling from a VCF (the step *before* these
  lookups). Run locally.
- **PharmVar** — the authoritative star-allele nomenclature ClinPGx allele IDs
  reference.
- **CPIC** — the guideline body whose recommendations ClinPGx serves.
- **DPWG** — Dutch Pharmacogenetics Working Group guidelines.
- **ClinPGx decision-support web app** — an interactive phenoconversion / custom
  genotype interpreter on the ClinPGx site for point-of-care use (separate from
  this API).

## Migration from PharmGKB

- Old host `https://api.pharmgkb.org/` → new host `https://api.clinpgx.org/`.
- PharmGKB web URLs redirect to the corresponding ClinPGx pages.
- Watch `https://blog.clinpgx.org/` for API changes; pin behavior for production.
