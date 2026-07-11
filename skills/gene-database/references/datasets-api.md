# NCBI Datasets v2 — Gene

The NCBI Datasets service delivers structured gene **reports** and sequence
**packages** with less parsing than raw E-utilities XML. Two front ends: a REST
API and the `datasets` / `dataformat` command-line tools. Both draw on the same
backend.

REST base:

```
https://api.ncbi.nlm.nih.gov/datasets/v2/gene
```

Authenticate for the higher rate limit with an `api-key: YOUR_KEY` request
header. This skill uses **v2**; an older `v2alpha` still responds but uses a
different response wrapper (`genes[].gene` vs v2's `reports[].gene`) — pin one.

## REST endpoints

### Gene report by ID

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/672"
# batch: comma-separate
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/672,7157,5594"
```

Response wrapper:

```json
{
  "reports": [
    { "gene": {
        "gene_id": "672",
        "symbol": "BRCA1",
        "description": "BRCA1 DNA repair associated",
        "tax_id": "9606",
        "taxname": "Homo sapiens",
        "common_name": "human",
        "type": "PROTEIN_CODING",
        "chromosomes": ["17"],
        "orientation": "minus",
        "nomenclature_authority": { "authority": "HGNC", "identifier": "HGNC:1100" },
        "swiss_prot_accessions": ["P38398"]
    } }
  ],
  "total_count": 1
}
```

Deeper reports also expose `genomic_ranges` (accession + begin/end/orientation),
`transcripts` (RefSeq accession, length, exons, protein product), `synonyms`,
`ensembl_gene_ids`, and reference-standard genomic regions.

### Gene report by symbol + taxon

`{taxon}` accepts a taxon ID (`9606`) or a name (`human`, `Homo sapiens`).

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/BRCA1/taxon/9606"
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/TP53/taxon/human"
```

### Gene report by RefSeq accession

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/accession/NM_007294.4"
```

### Sequence / data packages

Datasets can also assemble downloadable packages (gene FASTA for transcript,
protein, and genomic sequence, plus a metadata report) as a zip stream. The
report endpoints above give metadata; for sequence bundles prefer the `datasets`
CLI (below), which handles the zip and rehydration cleanly.

## Command-line tools

Install once (conda or the standalone binaries NCBI ships for Linux/macOS/Windows):

```bash
conda install -c conda-forge ncbi-datasets-cli   # provides `datasets` + `dataformat`
```

Fetch and inspect metadata without downloading a package:

```bash
# Print a gene report to stdout (JSON Lines)
datasets summary gene gene-id 672 7157 5594
datasets summary gene symbol BRCA1 --taxon human
```

Download a sequence + metadata package, then flatten to a table:

```bash
datasets download gene gene-id 672 --include gene,rna,protein,cds --filename brca1.zip
unzip brca1.zip -d brca1/
# turn the JSONL report into TSV columns
dataformat tsv gene --inputfile brca1/ncbi_dataset/data/data_report.jsonl \
  --fields gene-id,symbol,description,tax-name,chromosomes,gene-type
```

`--include` selects sequence FASTA types (`gene`, `rna`/transcript, `protein`,
`cds`, `5p-utr`, `3p-utr`). `dataformat tsv gene --help` lists every extractable
field.

## When Datasets vs E-utilities

- **Datasets** — you want a clean, typed gene report, RefSeq/transcript listings,
  Ensembl cross-IDs, or bulk sequence FASTA for a set of genes. Less XML wrangling.
- **E-utilities** (`references/eutils-api.md`) — you need free-text *search*
  (Datasets fetches known IDs/symbols, it is not a search engine), cross-database
  `elink` (PubMed, ClinVar, dbSNP), or `usehistory` paging over large result sets.

A common pattern: `esearch` to discover Gene IDs, then Datasets to pull their
structured reports.

## Rate limits and errors

- **5 req/s** anonymous, **10 req/s** with an `api-key` header.
- HTTP `200` success, `400` bad request, `404` gene/symbol not found, `429` rate
  limit (back off), `5xx` transient (retry). An empty `reports` array with
  `total_count: 0` means "found nothing", not an error.

## Docs

- Datasets v2 API + CLI: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/
- CLI reference: https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/datasets/
