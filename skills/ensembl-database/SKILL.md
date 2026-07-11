---
name: ensembl-database
version: 0.1.0
description: >-
  Query the Ensembl genome database (EMBL-EBI) for 250+ vertebrate and model
  species through its public REST API (rest.ensembl.org; grch37.rest.ensembl.org
  for GRCh37/hg19). Use to look up genes by symbol or Ensembl ID, fetch
  genomic/cDNA/CDS/protein sequences, predict variant consequences with VEP,
  pull variants by rsID with population frequencies, find orthologs/paralogs and
  gene trees, list features overlapping a region, map coordinates between
  assemblies (GRCh37<->GRCh38), and query regulatory, phenotype, ontology, and
  cross-reference data. Drive it via raw REST endpoints with rate-limit and
  retry handling, or the optional ensembl_rest wrapper; sibling gget and
  biopython skills reach the same source. NOT for bulk whole-genome analytics
  (download the Ensembl MySQL/FASTA/GTF dumps or use BioMart), clinical variant
  curation (use clinvar-database), or protein structures (use alphafold-database
  / pdb-database).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: >-
    Ensembl genomic data and the REST API are released under Apache-2.0; the
    optional ensembl_rest Python wrapper is a separate third-party package (see
    its own repository for its license).
---

# Ensembl Database

## Overview

Ensembl is EMBL-EBI's reference resource for genome annotation across 250+
vertebrate and model species: gene/transcript/protein models, sequences,
variation, regulation, and comparative genomics (orthologs, paralogs, gene
trees). This skill drives Ensembl programmatically through its stateless
**REST API** at `https://rest.ensembl.org`.

Two access styles, in order of preference:

1. **Raw REST + `requests`** — the canonical, fully documented interface. No
   library lock-in; every endpoint is a URL. This skill leads with it.
2. **`ensembl_rest` wrapper** — an optional community Python package whose
   methods are auto-generated from Ensembl's endpoint short-names. Convenient,
   but thin; fall back to raw REST for anything it does not cover.

The releases move (Release 115 was current in Sept 2025). Never hard-code a
release number — read the live one from `GET /info/data`.

## When to Use This Skill

- **Gene lookup** — resolve a symbol (`BRCA2`) or Ensembl ID (`ENSG00000139618`)
  to coordinates, biotype, transcripts, and external cross-references.
- **Sequence retrieval** — genomic, cDNA, CDS, or protein sequence for an ID or
  a `chr:start-end` region, as JSON or FASTA.
- **Variant analysis** — look up a variant by rsID (with population
  frequencies), or predict functional consequences with **VEP** from HGVS,
  rsID, or region+allele.
- **Comparative genomics** — orthologs/paralogs across species and gene trees.
- **Region analysis** — every gene, transcript, regulatory feature, or variant
  overlapping an interval.
- **Assembly mapping** — convert coordinates between assemblies (GRCh37 ↔
  GRCh38) or between cDNA/CDS/protein and genomic space.
- **Metadata** — available species, assembly build, biotypes, ontology terms,
  phenotype and cross-reference lookups.

## When NOT to Use This Skill

- **Bulk / whole-genome analytics** — do not scrape thousands of records over
  REST. Download the Ensembl **MySQL, FASTA, or GTF dumps** from the FTP site,
  or use **BioMart** for tabular bulk export, and query locally.
- **Clinical variant interpretation / curation** — use `clinvar-database` for
  ClinVar significance and review status; Ensembl VEP predicts consequences, it
  does not adjudicate pathogenicity.
- **Protein 3D structure** — use `alphafold-database` or `pdb-database`.
- **Cross-database convenience lookups** — for a one-shot lookup that spans
  many resources, `gget` (which wraps Ensembl for `ref`/`search`/`seq`/`info`)
  or `biopython` may be lighter than hand-rolling REST calls.
- **Non-vertebrate clades outside Ensembl's core** — plants, fungi, protists,
  bacteria live on the sister **Ensembl Genomes** servers (e.g.
  `rest.ensemblgenomes.org`), not `rest.ensembl.org`.

## Access

```bash
uv pip install requests                 # raw REST — all you need
uv pip install ensembl_rest             # optional convenience wrapper
```

Base URLs and the default JSON header:

```python
import requests

SERVER = "https://rest.ensembl.org"           # current assemblies (GRCh38)
GRCH37 = "https://grch37.rest.ensembl.org"     # human GRCh37/hg19 only
HEADERS = {"Content-Type": "application/json"}
```

**Pick the server by assembly.** GRCh37/hg19 human coordinates *must* go to the
`grch37.` host; everything else uses `rest.ensembl.org`.

## Core Capabilities

Canonical one-liners below. The full endpoint catalogue (all 16 categories,
every parameter, batch POST bodies, response formats, error codes) lives in
[references/rest-api.md](references/rest-api.md). A reusable rate-limited client
and end-to-end workflows live in
[references/query-helper.md](references/query-helper.md).

### Gene / object lookup

```python
# By symbol (expand=1 to include transcripts)
requests.get(f"{SERVER}/lookup/symbol/homo_sapiens/BRCA2",
             params={"expand": 1}, headers=HEADERS).json()

# By Ensembl ID
requests.get(f"{SERVER}/lookup/id/ENSG00000139618",
             params={"expand": 1}, headers=HEADERS).json()
```

### Sequence

```python
# By ID; type ∈ {genomic, cds, cdna, protein}
requests.get(f"{SERVER}/sequence/id/ENSG00000139618",
             params={"type": "protein"}, headers=HEADERS).json()

# By region, as FASTA (note the FASTA content-type)
requests.get(f"{SERVER}/sequence/region/human/7:140424943..140624564",
             headers={"Content-Type": "text/x-fasta"}).text
```

### Variants and VEP

```python
# Variant record with population frequencies
requests.get(f"{SERVER}/variation/human/rs699",
             params={"pops": 1}, headers=HEADERS).json()

# Predict consequences from HGVS
requests.get(f"{SERVER}/vep/human/hgvs/ENST00000366667:c.803C>T",
             headers=HEADERS).json()
```

### Comparative genomics

```python
# Orthologs in a target species
requests.get(f"{SERVER}/homology/id/ENSG00000139618",
             params={"target_species": "mouse", "type": "orthologues"},
             headers=HEADERS).json()
```

### Region overlap

```python
# Every gene overlapping an interval (feature ∈ gene/transcript/variation/regulatory/…)
requests.get(f"{SERVER}/overlap/region/human/7:140424943..140624564",
             params={"feature": "gene"}, headers=HEADERS).json()
```

### Assembly mapping

```python
# GRCh37 → GRCh38 coordinate lift
requests.get(f"{SERVER}/map/human/GRCh37/7:140453136..140453136/GRCh38",
             headers=HEADERS).json()
```

## Batch, Rate Limits, and Robustness

- **Batch with POST.** `POST /lookup/id`, `/sequence/id`, `/vep/:species/id`,
  `/vep/:species/hgvs`, `/variation/:species`, and the mapping endpoints accept
  a JSON array (e.g. `{"ids": [...]}`, `{"hgvs_notations": [...]}`) — always
  prefer these to a loop of GETs. Details in
  [references/rest-api.md](references/rest-api.md).
- **Rate limits.** Anonymous clients get ~15 requests/second. On HTTP **429**,
  honor the `Retry-After` header and back off — do not hammer.
- **Handle 400/404/429/5xx.** A missing ID returns 404; malformed params 400.
  The ready-made client in
  [references/query-helper.md](references/query-helper.md) enforces the rate
  limit and retries with exponential backoff.
- **Cache** frequently reused lookups locally; the data changes only per
  release.

## Optional: the `ensembl_rest` wrapper

Its methods mirror Ensembl endpoint short-names, taking path/query fields as
keyword arguments — e.g. `client.symbol_lookup(species='human', symbol='BRCA2')`
maps to `GET /lookup/symbol/...`, and `client.sequence_region(species='human',
region='7:140424943-140624564')` to `GET /sequence/region/...`. It is a thin
convenience layer; the raw REST endpoints above are the source of truth. See the
package's own documentation for its exact method list, and fall back to raw REST
for endpoints it does not expose.

## References

- [references/rest-api.md](references/rest-api.md) — full endpoint catalogue
  (all 16 categories: archive, comparative genomics, xrefs, info, LD, lookup,
  mapping, ontology/taxonomy, overlap, phenotype, regulation, sequence,
  transcript haplotypes, VEP, variation, GA4GH), batch POST bodies, response
  formats, shared parameters, and error codes.
- [references/query-helper.md](references/query-helper.md) — a reusable,
  rate-limited Python client with retry/back-off and a small CLI, plus
  worked gene-annotation, variant-analysis, and comparative-genomics workflows.
