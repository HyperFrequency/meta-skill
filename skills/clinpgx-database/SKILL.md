---
name: clinpgx-database
version: 0.1.0
description: >-
  Query ClinPGx, the clinical pharmacogenomics knowledge base that consolidates
  PharmGKB, CPIC, and PharmCAT, over its public REST API. Pull gene-drug pairs,
  CPIC/DPWG clinical guidelines, star-allele function and activity scores,
  population allele frequencies, variant (rsID) annotations, evidence-graded
  clinical annotations (levels 1A-4), regulatory drug labels, and PK/PD pathways
  for pharmacogenes such as CYP2D6, CYP2C19, TPMT, DPYD, SLCO1B1, and HLA-B. Use
  for genotype-guided dosing, building actionable PGx panels, drug-safety and HLA
  screening, mapping a diplotype to a metabolizer phenotype, or comparing allele
  frequencies across populations. NOT for calling genotypes from a VCF or raw
  sequence (run PharmCAT locally), general small-molecule bioactivity or target
  data (use `chembl-database`), germline variant pathogenicity unrelated to drug
  response (use `database-lookup` / ClinVar), or formatting the literature
  references it returns into citations (use `citation-management`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: ClinPGx data is CC BY-SA 4.0
---

# ClinPGx Database

## Overview

ClinPGx is the clinical pharmacogenomics knowledge base that succeeds and
consolidates **PharmGKB**, **CPIC** (Clinical Pharmacogenetics Implementation
Consortium), and **PharmCAT**. It curates how inherited genetic variation
changes drug metabolism, efficacy, and toxicity, and packages that as gene-drug
pairs, evidence-graded clinical annotations, and actionable dosing guidelines.
As of 2025, PharmGKB URLs redirect to ClinPGx.

Drive it over a public, keyless REST API. This skill covers the query surface —
genes, drugs, gene-drug pairs, guidelines, alleles, variants, clinical
annotations, drug labels, and pathways — plus how to read a result
(phenotype/evidence/CPIC grading) and stay inside the rate limit.

> The v1 REST API is in beta: endpoint paths, parameters, and response field
> names may change. Treat the shapes here as representative and confirm against
> the live docs at `https://api.clinpgx.org/`. Exact endpoint and field detail
> lives in [references/api-reference.md](references/api-reference.md).

## When to Use This Skill

- **Genotype-guided dosing**: turn a patient's diplotype (e.g. `CYP2C19 *1/*2`)
  into a phenotype and a CPIC dosing recommendation for a specific drug.
- **Gene-drug interaction lookup**: check whether a drug's response is modified
  by a pharmacogene, and at what evidence/CPIC level.
- **Build an actionable PGx panel**: enumerate gene-drug pairs backed by CPIC
  Level A guidance to decide which genes a clinical assay must cover.
- **Drug-safety / HLA screening**: flag high-risk pairs (e.g. `HLA-B*57:01` +
  abacavir, `DPYD` + fluoropyrimidines) before prescribing.
- **Allele intelligence**: retrieve star-allele function, activity score, and
  defining variants for a pharmacogene.
- **Population pharmacogenomics**: compare allele/phenotype frequencies across
  biogeographic groups.
- **Literature evidence review**: pull curated clinical annotations with PMIDs,
  filtered by evidence level.

## When NOT to Use This Skill

- **Genotype / diplotype calling from sequence** — ClinPGx annotates known
  alleles; it does not call them. Run **PharmCAT** locally on a VCF to go from
  variants to a diplotype, then look the diplotype up here.
- **General chemistry / bioactivity** (IC50, targets, SAR) — use
  `chembl-database`.
- **Germline pathogenicity unrelated to drug response** — use `database-lookup`
  / ClinVar for disease variant interpretation.
- **Citation formatting** — ClinPGx returns PMIDs; format them with
  `citation-management`.
- **Whole-database / bulk analytics** — download the ClinPGx/PharmGKB data
  dumps rather than scanning the rate-limited API pair by pair.
- **Building the patient-facing recommendation UI** — that is the job of a
  decision-support layer (`clinical-decision-support`); this skill is the data
  source underneath it.

## Setup

```bash
uv pip install requests            # add pandas for tabular analysis
```

```python
import requests

BASE_URL = "https://api.clinpgx.org/v1/"   # keyless; ~2 requests/second cap
```

No authentication is required. Data is licensed **CC BY-SA 4.0** — attribute
ClinPGx and share-alike. For substantial or bulk use, notify `api@clinpgx.org`.

## Core Capabilities

Canonical calls below. The full endpoint list, parameters, filter values, and
representative response fields are in
[references/api-reference.md](references/api-reference.md); reusable helpers
(rate-limited request, retry/backoff, caching) and end-to-end clinical/research
workflows are in [references/query-recipes.md](references/query-recipes.md).

```python
# Gene — by symbol, or search
requests.get(f"{BASE_URL}gene/CYP2D6").json()
requests.get(f"{BASE_URL}gene", params={"q": "CYP"}).json()

# Drug / chemical — by ClinPGx ID, or search by name
requests.get(f"{BASE_URL}chemical/PA448515").json()            # warfarin
requests.get(f"{BASE_URL}chemical", params={"name": "warfarin"}).json()

# Gene-drug pair — the core clinical relationship
requests.get(f"{BASE_URL}geneDrugPair",
             params={"gene": "CYP2C19", "drug": "clopidogrel"}).json()
requests.get(f"{BASE_URL}geneDrugPair", params={"cpicLevel": "A"}).json()

# Guideline — CPIC / DPWG dosing guidance
requests.get(f"{BASE_URL}guideline",
             params={"source": "CPIC", "gene": "CYP2C19"}).json()

# Allele — star-allele function, activity score, population frequencies
requests.get(f"{BASE_URL}allele", params={"gene": "CYP2D6"}).json()
requests.get(f"{BASE_URL}allele/CYP2D6*4").json()

# Variant — by rsID
requests.get(f"{BASE_URL}variant/rs4244285").json()            # CYP2C19*2

# Clinical annotation — literature, filterable by evidence level
requests.get(f"{BASE_URL}clinicalAnnotation",
             params={"gene": "TPMT", "drug": "azathioprine",
                     "evidenceLevel": "1A"}).json()

# Drug label — regulatory PGx labeling
requests.get(f"{BASE_URL}drugLabel",
             params={"drug": "warfarin", "source": "FDA"}).json()

# Pathway — PK/PD diagram and involved genes
requests.get(f"{BASE_URL}pathway", params={"drug": "warfarin"}).json()
```

**Key pharmacogenes** to reach for: metabolizing enzymes (`CYP2D6`, `CYP2C19`,
`CYP2C9`, `CYP3A5`, `DPYD`, `TPMT`, `NUDT15`, `UGT1A1`), transporters
(`SLCO1B1`, `ABCG2`), and HLA risk alleles (`HLA-B`, `HLA-A`).

## Interpreting Results

Three grading systems recur across responses — read them before acting:

- **Metabolizer phenotype** (from diplotype → summed allele activity score):
  Ultra-rapid (UM), Normal (NM), Intermediate (IM), Poor (PM). Drives the dosing
  recommendation.
- **Allele function**: normal / decreased / no / increased / uncertain function,
  with a numeric `activityScore` (typically 0.0-2.0+). Two allele scores sum to
  the diplotype phenotype.
- **CPIC level** (`A`-`D`) marks *clinical actionability*; **PharmGKB evidence
  level** (`1A`, `1B`, `2A`, `2B`, `3`, `4`) marks *strength of evidence*. Level
  `1A` / CPIC `A` are the highest-confidence, guideline-backed pairs. See
  [references/api-reference.md](references/api-reference.md) for the full ladder.

## Best Practices and Gotchas

- **Rate limit**: ~2 requests/second. Sleep ~0.5 s between calls; on HTTP `429`
  back off exponentially. A ready-made rate-limited/retrying request wrapper is
  in [references/query-recipes.md](references/query-recipes.md).
- **Cache aggressively**: allele functions and guidelines change slowly — cache
  responses to disk rather than re-fetching in loops.
- **Phenoconversion**: a co-prescribed inhibitor/inducer can shift the *effective*
  phenotype away from the genotype-predicted one (e.g. a strong CYP2D6 inhibitor
  turns a genetic NM into a functional PM). Genotype lookups alone miss this.
- **Population matters**: allele frequencies vary widely across ancestries — a
  phenotype distribution computed for one population does not transfer.
- **Multi-gene and non-genetic factors**: some drugs (warfarin) depend on several
  genes plus age, organ function, and interactions; a single gene-drug pair is
  necessary, not sufficient.
- **Assay coverage**: not every clinically relevant allele is detected by every
  panel; absence of a called allele is not proof of the reference allele.
- **Not a genotype caller**: this API annotates alleles you already have. Pair it
  with PharmCAT for VCF → diplotype calling.
- **Beta API**: pin behavior in tests and watch the ClinPGx blog for breaking
  changes; PharmGKB endpoints now redirect to ClinPGx.

## References

- [references/api-reference.md](references/api-reference.md) — endpoint
  catalogue (gene, chemical, geneDrugPair, guideline, allele, variant,
  clinicalAnnotation, drugLabel, pathway), parameters, representative response
  fields, evidence/CPIC/phenotype grading tables, error responses, licensing.
- [references/query-recipes.md](references/query-recipes.md) — reusable
  rate-limited/retrying/caching request helpers and end-to-end workflows:
  clinical decision support, PGx panel analysis, drug-safety screening,
  population frequency analysis, and literature evidence review.
