---
name: uniprot-database
version: 0.1.0
description: >-
  Query the UniProt REST API directly over HTTP for protein data: search UniProtKB
  by gene, accession, organism, GO term, or sequence; retrieve entries as
  FASTA/JSON/TSV/XML; map identifiers across ~100 databases (Ensembl, RefSeq, PDB,
  KEGG); stream whole proteomes; and select exactly which return fields you need.
  Use when you need protein sequences, Swiss-Prot/TrEMBL annotations, or
  cross-database ID mapping and want direct REST control or a language-agnostic
  curl/HTTP workflow. Do NOT use for multi-database Python pipelines spanning many
  bioinformatics services (prefer the bioservices or Unipressed clients), for
  nucleotide/genome sequence retrieval (use NCBI Entrez or Ensembl), for 3D
  structures beyond a cross-reference lookup (use the RCSB PDB API), or for
  small-molecule/compound data (use PubChem or ChEMBL).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# UniProt Database

## Overview

UniProt is the reference resource for protein sequence and functional annotation.
Every capability is reachable through one public REST service at
`https://rest.uniprot.org` — no API key, no SDK required. This skill covers the
four operations you actually need: **search** UniProtKB, **retrieve** a single
entry, **map IDs** to/from other databases, and **stream** large result sets. It
works from `curl`, any HTTP client, or the small Python helper linked below.

Two data quality tiers matter throughout:
- **Swiss-Prot** (`reviewed:true`) — manually curated, high-confidence entries.
- **TrEMBL** (`reviewed:false`) — automatic annotation, computational predictions.
Filter with `reviewed:true` whenever you want trustworthy annotations.

## When to Use This Skill

- Search for proteins by gene symbol, accession, organism, GO term, keyword, or
  sequence properties (length, mass).
- Retrieve a sequence in FASTA (or an entry in JSON/TSV/XML/GFF/TXT).
- Map identifiers between UniProt and Ensembl, RefSeq, PDB, KEGG, HGNC, and ~90
  other databases.
- Pull a whole proteome or any large query set as a single streamed download.
- Restrict responses to specific fields to cut bandwidth and parsing cost.
- Work at the HTTP layer directly (curl / shell / non-Python) or need
  UniProt-specific control that a wrapper library hides.

## When NOT to Use This Skill

- **Building a Python pipeline across many bio services** — the `bioservices` or
  `Unipressed` libraries give a typed, unified interface; use those instead of
  hand-rolling requests.
- **Nucleotide or genome sequences** — UniProt is protein-only; use NCBI Entrez,
  ENA, or Ensembl.
- **3D structures** — UniProt gives you PDB/AlphaFold *cross-references*, not
  coordinates; fetch structures from the RCSB PDB or AlphaFold APIs.
- **Small molecules, drugs, assays** — use PubChem or ChEMBL.
- **Deciding which scientific database fits a question** — route through
  `database-lookup` first, then come here for the UniProt-specific work.

## Endpoints at a Glance

| Operation | Method + URL |
| --- | --- |
| Search | `GET /uniprotkb/search?query={q}&format={fmt}&fields={f}&size={n}` |
| Retrieve one entry | `GET /uniprotkb/{accession}.{fmt}` |
| Stream (no pagination) | `GET /uniprotkb/stream?query={q}&format={fmt}` |
| Submit ID-mapping job | `POST /idmapping/run` (form: `from`, `to`, `ids`) |
| Poll job status | `GET /idmapping/status/{jobId}` |
| ID-mapping results | `GET /idmapping/results/{jobId}` |
| List query fields | `GET /configure/uniprotkb/result-fields` |
| List mapping databases | `GET /configure/idmapping/fields` |

Base URL for all rows: `https://rest.uniprot.org`. Other datasets swap the path
prefix — `uniref`, `uniparc`, `proteomes`, `taxonomy` all expose `/search` and
`/stream` the same way.

## Searching UniProtKB

Build queries from field terms joined by `AND` / `OR` / `NOT`, grouped with
parentheses. Quote multi-word values.

```bash
curl "https://rest.uniprot.org/uniprotkb/search?query=gene:BRCA1+AND+reviewed:true&format=json&size=5"
```

Common field terms: `gene:`, `accession:`, `organism_id:` (NCBI taxon, e.g. 9606
for human), `organism_name:"Homo sapiens"`, `protein_name:`, `go:0005515`,
`length:[100 TO 500]`, `keyword:`, `xref:pdb`, `reviewed:true`. Wildcards (`*`,
`?`) and range syntax `[min TO max]` are supported. The full grammar, existence
queries (`cc_function:*`), and worked patterns are in
[references/query-syntax.md](references/query-syntax.md).

**Formats:** `json`, `tsv`, `fasta`, `xml`, `txt`, `gff`, `list` (accessions
only), `rdf`, `xlsx`. Pick TSV for tables, FASTA for sequences, JSON for parsing.

## Retrieving a Single Entry

```bash
curl "https://rest.uniprot.org/uniprotkb/P01308.fasta"    # human insulin
```

Accessions are 6 characters (`P12345`) or 10 for newer entries (`A0A022YWF9`).
Entry retrieval supports `json`, `txt`, `xml`, `fasta`, `gff`, and `rdf`. To
"batch retrieve" several accessions, OR them in one search query
(`accession:P01308 OR accession:P04637`) rather than issuing N single requests.

## Selecting Return Fields

Add `fields=` (comma-separated, no spaces) to any search/stream request to return
only what you need:

```
fields=accession,id,gene_names,organism_name,length,cc_function,xref_pdb
```

Field families: `cc_*` (comments: function, disease, subcellular location),
`ft_*` (features: domains, signal peptides, variants), `go_*` (Gene Ontology),
`xref_*` (cross-references). The complete field catalogue, common combinations,
and the live `/configure/uniprotkb/result-fields` endpoint are documented in
[references/fields.md](references/fields.md).

## ID Mapping Across Databases

Mapping is a three-step async job:

1. `POST /idmapping/run` with form fields `from`, `to`, `ids` → returns `{jobId}`.
2. Poll `GET /idmapping/status/{jobId}` until it is no longer `RUNNING`.
3. Fetch `GET /idmapping/results/{jobId}` (paginated). When the **target is
   UniProtKB**, use `/idmapping/uniprotkb/results/{jobId}` to get full entries and
   a `fields=` selector.

```bash
curl -X POST "https://rest.uniprot.org/idmapping/run" \
  -d "from=UniProtKB_AC-ID&to=PDB&ids=P01308,P04637"
```

Database names are **case-sensitive** (`UniProtKB_AC-ID`, `Gene_Name`, `Ensembl`,
`RefSeq_Protein`, `PDB`, `KEGG`, …). Mapping is many-to-many; unmapped inputs come
back under `failedIds`. Limits: **100,000 IDs per job**, results retained ~7 days.
The full database list, direction notes, and the polling contract are in
[references/id-mapping.md](references/id-mapping.md).

## Streaming Large Result Sets

For anything bigger than a page or two, skip pagination and stream:

```bash
curl "https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true&format=fasta" \
  -o human_proteome.fasta
```

Add `compressed=true` to receive a gzip stream (much faster for whole proteomes).
`stream` returns the complete result in one response — do not combine it with
`size` or cursor pagination.

## Pagination, Rate Limits, and Failure Modes

- **Pagination is cursor-based via the HTTP `Link` header**, not a JSON key.
  Follow `response.links["next"]["url"]` (requests) until it is absent. `size`
  caps at **500** per page. The total count is in the `X-Total-Results` header.
- **Rate limiting:** the service throttles heavy clients and returns **HTTP 429**
  with a `Retry-After` header — honor it and back off. Serialize large batch jobs;
  do not fan out hundreds of concurrent requests.
- **Empty results** return `200` with an empty `results` array (JSON) — not a 404.
- **A bad field name** in `query=` or `fields=` returns `400` with a message
  naming the offending field; validate against the `/configure` endpoints.
- **Retrieving an obsolete/merged accession** may `303`-redirect to the current
  entry — follow redirects.

## Python Client

A small, dependency-light client (`requests` only) wrapping search, single-entry
retrieval, correct `Link`-header pagination, streaming, and the full ID-mapping
poll loop — plus a `curl`-equivalent CLI — is provided in
[references/python-client.md](references/python-client.md). Copy it into a project
or lift individual functions. For production Python, prefer the maintained
`Unipressed` (typed UniProt client) or `bioservices` packages.

## References

- [references/query-syntax.md](references/query-syntax.md) — full query grammar,
  fields, operators, ranges, wildcards, and worked search patterns.
- [references/fields.md](references/fields.md) — complete return-field catalogue
  (`cc_*`, `ft_*`, `go_*`, `xref_*`) and useful field combinations.
- [references/id-mapping.md](references/id-mapping.md) — supported mapping
  databases, the async job contract, and common mapping scenarios.
- [references/api-examples.md](references/api-examples.md) — runnable examples in
  Python, curl, R, and JavaScript, including batch + rate-limited patterns.
- [references/python-client.md](references/python-client.md) — the reusable Python
  client and CLI.

**Official UniProt docs:** REST tutorial
`https://www.uniprot.org/help/uniprot_rest_tutorial`, query fields
`https://www.uniprot.org/help/query-fields`, ID mapping
`https://www.uniprot.org/help/id_mapping`, programmatic pagination
`https://www.uniprot.org/help/pagination`, SPARQL endpoint
`https://sparql.uniprot.org/` (for graph-style queries).
