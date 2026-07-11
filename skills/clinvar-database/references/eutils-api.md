# ClinVar Programmatic Access — E-utilities, Entrez Direct, Biopython

ClinVar exposes no bespoke REST API of its own; you reach it through NCBI's
shared **E-utilities** using `db=clinvar`. This reference covers the four
operations you need, the command-line and Python wrappers, rate limits, and
error handling.

## E-utilities base

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

The query language in `term=` is identical to the web search box. **Clinical
significance and conflicts are `[Properties]` filters, not their own fields**;
review status is the `[RVST]` field keyed on the exact aggregate string.

| Tag / filter | Matches |
|-----|---------|
| `[gene]` | Gene symbol (e.g. `BRCA1[gene]`) |
| `[DIS]` | Condition / disease / phenotype name |
| `[variant name]` | HGVS expression or variant name |
| `[chr]` | Chromosome number |
| `"clinsig pathogenic"[Properties]` | Clinical significance — also `likely pathogenic`, `vus`, `likely benign`, `benign` |
| `"clinsig has conflicts"[Properties]` | Records with conflicting classifications (negate with `NOT`) |
| `"reviewed by expert panel"[RVST]` | Review status — also `"practice guideline"`, `"criteria provided, single submitter"`, `"criteria provided, multiple submitters, no conflicts"`, `"criteria provided, conflicting classifications"`, `"no assertion criteria provided"` |

There is **no `[CLNSIG]`, `[RVSTAT]`, or `[Assembly]` search field**. Entrez
silently rewrites an unknown tag to a free-text `[All Fields]` match — so
`pathogenic[CLNSIG]` matches every record containing the *word* "pathogenic"
(~3× the real pathogenic set), not the classification, and `conflicting[RVSTAT]`
matches the word "conflicting" across the whole archive. Always confirm your
tags resolve by inspecting `querytranslation` in the esearch response. Assembly
build is carried by position (`[chr]` + base position) and by which VCF you
download, not by a term filter.

URL-encode brackets and spaces (`[` → `%5B`, `]` → `%5D`, space → `+`).

## The four operations

### esearch — resolve a query to UIDs

```
esearch.fcgi?db=clinvar&term=<query>&retmode=json&retmax=<N>
```

- `retmax` default 20; raise it or page with `retstart`.
- `usehistory=y` stores results server-side and returns `WebEnv` + `query_key`;
  use it for large sets rather than a giant `id=` list downstream.

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=CFTR%5Bgene%5D+AND+%22clinsig+pathogenic%22%5BProperties%5D&retmode=json&retmax=200&usehistory=y"
```

### esummary — compact record summaries

```
esummary.fcgi?db=clinvar&id=<UID,UID,...>&retmode=json&version=2.0
```

Pass `version=2.0` for the modern JSON structure. A summary typically includes:
accession (VCV/RCV), clinical significance, review status, gene symbol(s),
variant type, GRCh37 and GRCh38 locations, associated conditions, and allele
origin (germline/somatic).

### efetch — full XML records

```
efetch.fcgi?db=clinvar&id=<UID,...>&rettype=vcv
```

`rettype=vcv` returns the variant-centric VariationArchive XML; `rettype=rcv`
returns variant–condition records; `rettype=docsum` returns document summaries
(handy in Entrez Direct pipelines). Parse the XML with a streaming iterparse
loop for large batches.

### elink — cross-database links

```
elink.fcgi?dbfrom=clinvar&db=<target>&id=<UID>
```

Useful link names: `clinvar_pubmed` (citations), `clinvar_gene`,
`clinvar_medgen` (conditions), `clinvar_snp` (dbSNP).

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=clinvar&db=pubmed&id=12345"
```

### Typical chain

```
esearch (term → UID list, ideally with usehistory)
  → esummary (UIDs → triage on significance + review status)
  → efetch   (UIDs → full evidence for the ones you keep)
  → elink    (UIDs → PubMed / Gene / MedGen as needed)
```

## Entrez Direct (command line)

Install once:

```bash
sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"
```

Pipeline example — search, keep reviewed records, print accession + title:

```bash
esearch -db clinvar -query 'TP53[gene] AND "clinsig pathogenic"[Properties]' \
  | efetch -format docsum \
  | xtract -pattern DocumentSummary -element AccessionVersion Title
```

`efilter -status reviewed` narrows a pipeline to reviewed submissions before
fetching.

## Biopython (`Bio.Entrez`)

Set `Entrez.email` before any call — NCBI requires it and will throttle or block
anonymous traffic. `Entrez.read` parses **XML**, so use the default XML retmode
(do not hand it a JSON handle).

```python
from Bio import Entrez

Entrez.email = "you@example.com"          # required by NCBI
# Entrez.api_key = "..."                   # optional, raises limit to 10 req/s

def search_clinvar(query, retmax=100):
    handle = Entrez.esearch(db="clinvar", term=query, retmax=retmax)
    record = Entrez.read(handle)           # XML → dict
    handle.close()
    return record["IdList"]

def summaries(id_list):
    handle = Entrez.esummary(db="clinvar", id=",".join(id_list))  # default XML
    record = Entrez.read(handle)
    handle.close()
    return record

ids = search_clinvar('BRCA2[gene] AND "clinsig pathogenic"[Properties]')
print(summaries(ids))
```

If you specifically want JSON, call the REST endpoint directly (e.g. via
`requests`) with `retmode=json` and parse it yourself — do not route JSON
through `Entrez.read`.

## Rate limits and etiquette

- **3 requests/second** without an API key; **10/second** with one.
- Get a key: register at https://www.ncbi.nlm.nih.gov/account/ and add
  `&api_key=<KEY>` to every request (or set `Entrez.api_key`).
- Back off exponentially on HTTP 429; batch UIDs instead of firing one request
  per variant; avoid large jobs during US business hours.

## Error handling

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | — |
| 400 | Bad request | Check `term=` syntax / field tags |
| 429 | Rate limited | Exponential backoff; add an API key |
| 500 | Server error | Retry with backoff |

An empty search returns an error body rather than an HTTP failure, e.g.
`<ERROR>Empty id list - nothing to do</ERROR>` — check for it before chaining
into `esummary`/`efetch`.

## Submitting to ClinVar (brief)

Organizations can submit variant interpretations via the web portal
(`submit.ncbi.nlm.nih.gov/subs/clinvar/`), an Excel batch template, or the
submission API (requires an NCBI organizational service account). Submissions
need documented assertion criteria (preferably ACMG/AMP) and supporting
evidence. Contact `clinvar@ncbi.nlm.nih.gov` to set up an account. This is a
data-contribution workflow, separate from the read/query paths above.

## References

- E-utilities manual: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- Entrez Direct cookbook: https://www.ncbi.nlm.nih.gov/books/NBK179288/
- ClinVar maintenance & use: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
