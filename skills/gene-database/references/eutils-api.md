# E-utilities API for NCBI Gene

E-utilities (Entrez Programming Utilities) are NCBI's stable REST interface to
every Entrez database, including `gene`. All calls share the base URL:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

Shared parameters worth setting on every request:

| Param | Purpose |
|-------|---------|
| `db=gene` | Target the Gene database |
| `retmode` | `json`, `xml`, or `text` (default `xml`; Gene efetch has no JSON) |
| `retmax` / `retstart` | Page size / offset (default retmax 20; cap 10000 per call) |
| `api_key` | Raises the rate limit to 10 req/s |
| `email`, `tool` | Contact + client name — NCBI emails you before blocking |
| `usehistory=y` | Store UIDs server-side (`WebEnv` + `query_key`) for large sets |

## esearch — text query → Gene IDs

`esearch.fcgi` returns `esearchresult.idlist` (a list of Gene IDs) plus `count`
and, crucially, **`querytranslation`** — always inspect it to confirm your field
tags were honoured and not rewritten to `[All Fields]`.

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&retmode=json&retmax=50&term=BRCA1%5BGene%20Name%5D+AND+human%5BOrganism%5D"
```

```json
{"esearchresult": {"count": "1", "idlist": ["672"],
  "querytranslation": "BRCA1[Gene Name] AND \"Homo sapiens\"[Organism]"}}
```

## esummary — compact document summaries

`esummary.fcgi` accepts up to ~500 comma-separated IDs and returns
`result.uids` plus one object per UID. Use `POST` (body `id=...`) for larger
sets, or `usehistory` paging.

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&retmode=json&id=672,7157,5594"
```

Useful summary fields: `name` (symbol), `description`, `organism`
(`.scientificname`, `.commonname`, `.taxid`), `chromosome`, `maplocation`,
`otheraliases`, `nomenclaturesymbol`, `nomenclaturename`, `genomicinfo`
(chraccver/chrstart/chrstop).

## efetch — full records

`efetch.fcgi` returns the complete gene record. Gene supports `retmode` of `xml`
(default, richest), `text`, and `asn.1`, plus `rettype=gene_table`. There is **no
JSON efetch for Gene** and **no FASTA** — for sequence, take the RefSeq
accessions and fetch from `db=nuccore` / `db=protein`, or use Datasets.

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=gene&id=672&retmode=xml"
```

The XML carries nomenclature, `Gene-commentary` sequence locations, transcript
variants and protein products, GO terms, cross-references, and linked
publications.

## elink — related records in other databases

`elink.fcgi` (`dbfrom=gene`, `db=<target>`) is the bridge from a gene to the rest
of Entrez. Common targets:

| `db=` | Gives you |
|-------|-----------|
| `pubmed` | Linked publications (PMIDs) — hand to `citation-management` |
| `clinvar` | Clinical variants — interpret with `clinvar-database` |
| `snp` | dbSNP variants |
| `homologene` | Ortholog group across species |
| `protein` / `nuccore` | Protein / nucleotide sequence records |
| `omim` | OMIM phenotype entries |

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gene&db=pubmed&id=672&retmode=json"
# PMIDs at: linksets[0].linksetdbs[*].links
```

## einfo — authoritative field and link list

`einfo.fcgi?db=gene&retmode=json` returns the live `fieldlist` (search fields) and
`linklist` (valid elink targets). Run it whenever you are unsure a tag exists —
it is the source of truth, not memory.

## Gene search fields (from einfo, db=gene)

Query as `value[Full Name]` or `value[ABBR]`. Both forms resolve.

| Abbr | Full name | Notes |
|------|-----------|-------|
| GENE | Gene Name | Gene symbol(s) / aliases |
| PREF | Preferred Symbol | Official symbol only |
| GFN  | Gene Full Name | Full descriptive name |
| ORGN | Organism | Scientific or common name |
| TID  | Taxonomy ID | e.g. `9606` |
| CHR  | Chromosome | Number, `mitochondrial`, or `unknown` |
| MV   | Default Map Location | Cytoband, e.g. `17q21.31` |
| CPOS | Base Position | Chromosome coordinate |
| DIS  | Disease/Phenotype | Associated disease names |
| GO   | Gene Ontology | **By GO term name, not GO ID** (`apoptosis[Gene Ontology]`) |
| PROP | Properties | Gene type / source, e.g. `genetype protein coding[Properties]` |
| FILT | Filter | Predefined limits (see below) |
| ECNO | EC/RN Number | Enzyme EC / CAS number |
| MIM  | MIM ID | OMIM number |
| PMID | PubMed ID | Linked publications |
| ACCN | Nucleotide/Protein Accession | Any linked accession |
| NCAC / PACC | Nucleotide / Protein Accession | Specific sequence accessions |
| EXPR | Expression/Tissues | Expression annotation |
| WORD | Text Word | Free-text token |
| TITL | Gene/Protein Name | Name index |

### Property and filter values

`[Properties]` and `[Filter]` take controlled strings, e.g.
`genetype protein coding[Properties]`, `genetype pseudo[Properties]`,
`genetype ncrna[Properties]`, `source_refseq[Properties]`. List the current
values from the einfo `linklist`/`fieldlist` or the Gene web UI's Advanced
Search builder rather than guessing — invented values silently mismatch.

### The silent-rewrite trap

Entrez maps an **unknown** tag to `[All Fields]` and returns hits for the literal
words. Verified failures to avoid:

| Wrong (rewrites to `[All Fields]`) | Correct |
|------------------------------------|---------|
| `diabetes[disease]` (~15k hits) | `diabetes[Disease/Phenotype]` |
| `...[phenotype]` | `...[Disease/Phenotype]` |
| `...[pathway]` (no such field) | `...[Text Word]` or a pathway resource |
| `GO:0006915[biological process]` | `apoptosis[Gene Ontology]` |
| `protein coding[gene type]` | `genetype protein coding[Properties]` |

Always read back `querytranslation` from the esearch response to confirm.

## Common taxon IDs

| Organism | Scientific name | Taxon ID |
|----------|-----------------|----------|
| Human | Homo sapiens | 9606 |
| Mouse | Mus musculus | 10090 |
| Rat | Rattus norvegicus | 10116 |
| Zebrafish | Danio rerio | 7955 |
| Fruit fly | Drosophila melanogaster | 7227 |
| C. elegans | Caenorhabditis elegans | 6239 |
| Yeast | Saccharomyces cerevisiae | 4932 |
| Arabidopsis | Arabidopsis thaliana | 3702 |
| E. coli | Escherichia coli | 562 |

`[Organism]` accepts names too (`human[Organism]`), so the ID table is mainly for
Datasets `taxon/{taxon}` paths and disambiguation.

## Biopython Entrez

Biopython wraps E-utilities. `Entrez.email` is **required** before any call;
set `Entrez.api_key` for the higher rate limit.

```python
from Bio import Entrez
Entrez.email = "you@example.com"
Entrez.api_key = "YOUR_KEY"        # optional, 10 req/s

ids = Entrez.read(Entrez.esearch(db="gene",
        term="BRCA1[Gene Name] AND human[Organism]"))["IdList"]
summary = Entrez.read(Entrez.esummary(db="gene", id=",".join(ids)))
record = Entrez.read(Entrez.efetch(db="gene", id="672", retmode="xml"))
```

`Entrez.read` parses XML — do not hand it a `retmode="json"` handle; use
`json.load` on the raw handle for JSON, or the default XML retmode with
`Entrez.read`.

## Rate limits and error handling

- **3 req/s** anonymous, **10 req/s** with `api_key`. Serialize requests with a
  small delay (~0.34 s without a key, ~0.1 s with one).
- HTTP status: `200` OK (still check the body for `<ERROR>`/`error`), `400`
  malformed, `404` not found, `429` rate limit, `5xx` transient.
- Retry transient failures (`429`, `5xx`, timeouts) with exponential back-off:

```python
import time, urllib.request
def get(url, attempts=4):
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode()
        except Exception:
            if i == attempts - 1: raise
            time.sleep(2 ** i)   # 1s, 2s, 4s
```

- For result sets beyond a few hundred UIDs, prefer `usehistory=y` and page with
  `WebEnv` + `query_key` rather than one enormous `id=` list.

## Docs

- E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- Entrez Direct (`efetch`/`esearch` CLI): https://www.ncbi.nlm.nih.gov/books/NBK179288/
- API keys: https://www.ncbi.nlm.nih.gov/account/
