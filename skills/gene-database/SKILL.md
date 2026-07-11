---
name: gene-database
version: 0.1.0
description: >-
  Query NCBI Gene, the cross-species catalogue of gene nomenclature, RefSeq
  transcripts/proteins, chromosomal locations, Gene Ontology, phenotypes, and
  cross-references, through two public APIs: E-utilities
  (esearch/esummary/efetch/elink/einfo) and the NCBI Datasets v2 REST API/CLI,
  plus Biopython Entrez. Use to resolve a gene symbol or Gene ID, batch-annotate
  gene lists, pull RefSeqs and genomic coordinates, find orthologs and linked
  PubMed/ClinVar/protein records, and search by disease, GO term, or chromosome
  with the CORRECT field tags (Entrez silently rewrites unknown tags to a
  free-text match). NOT for clinical variant interpretation (use
  clinvar-database), genome-scale sequence retrieval or annotation (use
  ensembl-database or bulk RefSeq downloads), protein 3D structure (use
  alphafold-database), or a one-shot cross-database convenience lookup (use gget
  or database-lookup).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# NCBI Gene Database

## Overview

NCBI Gene is the reference catalogue of genes across all sequenced organisms. Each
record ties together official nomenclature and aliases, RefSeq transcripts and
proteins, genomic coordinates and map location, Gene Ontology annotations,
associated phenotypes/diseases, and cross-references to dbSNP, ClinVar, PubMed,
HGNC, and the protein/nucleotide databases. Records are keyed by a stable integer
**Gene ID** (e.g. `672` = human BRCA1).

Reach it two ways, chosen by task:

| Access path | Best for | Reference |
|-------------|----------|-----------|
| **E-utilities** REST (esearch/esummary/efetch/elink/einfo) | Text search, cross-database links, scripting, batch summaries | `references/eutils-api.md` |
| **NCBI Datasets v2** REST API + `datasets`/`dataformat` CLI | Structured gene reports, RefSeqs, orthologs, sequence downloads | `references/datasets-api.md` |

Rule of thumb: **search** and **link** with E-utilities; pull a rich, structured
**gene report** or sequence package with Datasets. They are complementary, not
redundant.

## When to Use This Skill

- Resolve a gene **symbol → Gene ID** (or the reverse) for a given organism.
- Retrieve a gene's nomenclature, aliases, description, type, and chromosomal location.
- Fetch **RefSeq** transcript/protein accessions and genomic coordinate ranges.
- **Batch-annotate** a list of symbols or IDs into a table.
- Search by **disease/phenotype, GO term, chromosome, or gene type** — using the correct field tags.
- Find **orthologs** across species, or **link** a gene to its PubMed, ClinVar, dbSNP, or protein records.
- Access programmatically via raw REST, `curl`, or **Biopython `Entrez`**.

## When NOT to Use This Skill

- **Clinical variant interpretation** — pathogenicity, ACMG classes, review-status
  stars. Use `clinvar-database`; from here, `elink` a gene *to* ClinVar.
- **Genome-scale sequence retrieval / annotation** — bulk exons, whole-region
  FASTA, VEP, assembly mapping. Use `ensembl-database`, or download RefSeq/GTF
  dumps and query locally; do not scrape thousands of records over these APIs.
- **Protein 3D structure** — use `alphafold-database` (or a PDB skill).
- **One-shot cross-database convenience** — a single lookup that spans many
  resources is often lighter with `gget` (wraps NCBI/Ensembl), `bioservices`, or
  `database-lookup`.
- **Turning PubMed refs into formatted citations** — `elink` gets the PMIDs; hand
  them to `citation-management`.
- **Somatic-tumor pipelines end to end** — use `cancer-genomics-analysis`.

## Query Syntax — Use Real Field Tags

Gene search uses field-tagged terms, exactly like the web search box. **Entrez
silently rewrites an unknown tag to a free-text `[All Fields]` match**, so a wrong
tag returns plausible-looking garbage instead of erroring. These tags are real
(verified against `einfo.fcgi?db=gene`):

| Intent | Correct tag | Example |
|--------|-------------|---------|
| Gene symbol | `[Gene Name]` (or `[Preferred Symbol]`) | `BRCA1[Gene Name]` |
| Organism | `[Organism]` (or `[Taxonomy ID]`) | `human[Organism]` / `9606[Taxonomy ID]` |
| Chromosome | `[Chromosome]` | `17[Chromosome]` |
| Disease / phenotype | `[Disease/Phenotype]` | `diabetes[Disease/Phenotype]` |
| GO annotation (**by term name, not GO ID**) | `[Gene Ontology]` | `apoptosis[Gene Ontology]` |
| Gene type / properties | `[Properties]` | `genetype protein coding[Properties]` |
| Other | `[EC/RN Number]`, `[MIM ID]`, `[PubMed ID]`, `[Text Word]`, `[Nucleotide/Protein Accession]`, `[Expression/Tissues]` | |

**Common traps (all silently rewritten to `[All Fields]`):** `[disease]`,
`[phenotype]`, `[pathway]`, `[biological process]`, `[gene type]`, and
`GO:0006915[...]` (the GO field is indexed by term *name*, so query `apoptosis`,
not the GO ID). NCBI Gene has **no pathway field** — search pathway member genes
by `[Text Word]` or use a pathway resource. Confirm any tag live with
`einfo.fcgi?db=gene`, or prototype the query on the Gene web UI and reuse the
exact `term=`. Full tag list and property/filter values: `references/eutils-api.md`.

## Core Capabilities

Canonical calls below; every parameter, response field, and the Biopython
equivalents live in the references. Base URLs:

```
E-utilities: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Datasets v2: https://api.ncbi.nlm.nih.gov/datasets/v2/gene
```

### Search → Gene IDs (esearch)

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&retmode=json&retmax=20&term=BRCA1%5BGene%20Name%5D+AND+human%5BOrganism%5D"
# -> esearchresult.idlist = ["672"]
```

### Compact summaries (esummary) — the reliable batch path

```bash
# Up to ~500 IDs per call; returns result.uids + a dict keyed by UID
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&retmode=json&id=672,7157,5594"
# each entry: name, description, organism.scientificname, chromosome, maplocation
```

### Full records (efetch) and links (elink)

```bash
# Detailed XML record (nomenclature, locations, transcripts, GO, xrefs, pubs)
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=gene&id=672&retmode=xml"

# Link a gene to related records in another DB (pubmed, clinvar, homologene, protein, snp)
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gene&db=pubmed&id=672&retmode=json"
```

### Structured gene report (Datasets v2)

```bash
# By Gene ID (comma-separate for a batch); by symbol+taxon; by RefSeq accession
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/672,7157,5594"
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/BRCA1/taxon/human"
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/accession/NM_007294.4"
# -> { "reports": [ { "gene": { gene_id, symbol, description, tax_id, taxname,
#      type, chromosomes, nomenclature_authority, swiss_prot_accessions, ... } } ] }
```

Worked, end-to-end recipes (disease-gene discovery, annotation pipeline,
cross-species orthologs via HomoloGene, GO/function search, variant linkage to
ClinVar, publication mining) are in `references/workflows.md`.

## Batch, Rate Limits, and Robustness

- **Rate limits:** without an API key, **3 req/s** for E-utilities and **5 req/s**
  for Datasets; **10 req/s** with a key. Register a free key at
  ncbi.nlm.nih.gov/account and pass `&api_key=<KEY>` (E-utilities) or the
  `api-key:` header (Datasets). Add `&email=you@example.com` &
  `&tool=<name>` to E-utilities calls — NCBI asks for it and contacts you before
  blocking. Back off exponentially on HTTP **429**.
- **Batch, don't loop.** For many IDs, one `esummary` call (up to ~500 IDs; use
  `POST` and `usehistory=y` for larger sets) or one comma-separated Datasets GET
  beats a request per gene.
- **Always filter by organism** when searching by symbol — the same symbol names
  different genes across species (`TP53[Gene Name]` alone spans dozens of taxa).
- **Handle errors:** 400 = malformed term/params, 404 = ID/symbol not found,
  429 = rate limit, 5xx = retry with backoff. E-utilities also return in-body
  `<ERROR>…</ERROR>` (XML) or `{"error": …}` (JSON) with HTTP 200 — check the body.
- **Cache** stable lookups locally; annotations change only as the database is
  reannotated.

## Boundaries and Failure Modes

- A wrong field tag does **not** error — it free-text matches and inflates the
  hit count. Verify the `querytranslation` field in the esearch JSON response.
- Gene symbols are ambiguous across species and change over time; prefer the
  integer **Gene ID** for anything downstream, and record it in outputs.
- Datasets JSON keys differ slightly between `v2` (`reports[].gene`) and the older
  `v2alpha` (`genes[].gene`) — pin one version. This skill uses `v2`.
- `efetch` on Gene returns XML/ASN.1/text, not FASTA — for sequence, follow the
  RefSeq accessions into `nuccore`/`protein` (or use Datasets sequence downloads).
- Coverage and annotation depth are uneven across organisms; absence of a
  record is not evidence a gene does not exist.

## References

- `references/eutils-api.md` — E-utilities endpoints (esearch/esummary/efetch/elink/einfo),
  the full gene-db field-tag and property list, common taxon IDs, Biopython `Entrez`,
  rate limits, error handling, and retry/back-off.
- `references/datasets-api.md` — NCBI Datasets v2 REST endpoints, the gene-report
  JSON schema, and the `datasets` / `dataformat` command-line tools.
- `references/workflows.md` — worked recipes: disease-gene discovery, annotation
  pipeline, cross-species orthologs, GO/function search, variant linkage, publication mining.
- NCBI Gene: https://www.ncbi.nlm.nih.gov/gene/ · E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/ · Datasets: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/
