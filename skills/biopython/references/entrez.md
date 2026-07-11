# NCBI Databases — `Bio.Entrez`

`Bio.Entrez` wraps NCBI's E-utilities (search, fetch, link, post) over PubMed,
Nucleotide/GenBank, Protein, Gene, Taxonomy, and dozens of other databases. It
handles URL construction and rate limiting for you.

## Required setup

```python
from Bio import Entrez
Entrez.email = "you@example.com"    # REQUIRED by NCBI — set before any call
Entrez.api_key = "..."              # optional: 3 -> 10 requests/second
```

Biopython enforces NCBI's rate limits internally; do not add manual `sleep()`.

## The E-utilities

Every function returns an open handle. Parse XML handles with `Entrez.read`;
read text handles with `.read()` or pass to `SeqIO`. Always close the handle.

### `einfo` — list databases / describe one

```python
Entrez.read(Entrez.einfo())["DbList"]                    # all db names
info = Entrez.read(Entrez.einfo(db="pubmed"))["DbInfo"]  # counts, fields, links
```

### `esearch` — find record IDs

```python
h = Entrez.esearch(db="pubmed", term="biopython[Title]", retmax=100,
                   sort="relevance", reldate=365, datetype="pdat")
res = Entrez.read(h); h.close()
res["Count"], res["IdList"]
```

Boolean/field syntax works verbatim, e.g.
`"Cypripedioideae[Orgn] AND matK[Gene]"`,
`"(cancer[Title]) AND 2020:2025[PDAT]"`.

### `esummary` — lightweight record summaries

```python
for rec in Entrez.read(Entrez.esummary(db="pubmed", id="19304878,18606172")):
    print(rec["Title"], rec["Source"], rec["AuthorList"])
```

### `efetch` — full records

```python
from Bio import SeqIO
h = Entrez.efetch(db="nucleotide", id="EU490707", rettype="gb", retmode="text")
record = SeqIO.read(h, "genbank"); h.close()
```

`rettype` / `retmode` by database:

| Database | Useful `rettype` | `retmode` |
| --- | --- | --- |
| nucleotide / protein | `fasta`, `gb`/`genbank`, `gp` (GenPept) | `text` |
| pubmed | `medline`, `abstract`, (or none) | `text` or `xml` |
| gene / taxonomy | — | `xml` (parse with `Entrez.read`) |

### `elink` — related records across databases

```python
res = Entrez.read(Entrez.elink(dbfrom="nucleotide", db="protein", id="EU490707"))
for ls in res[0]["LinkSetDb"]:
    ids = [l["Id"] for l in ls["Link"]]
```

### `epost` — stage a big ID list on the server

```python
res = Entrez.read(Entrez.epost(db="pubmed", id="19304878,18606172,16403221"))
qk, we = res["QueryKey"], res["WebEnv"]      # reuse in efetch/esummary
```

### `egquery` / `espell`

```python
Entrez.read(Entrez.egquery(term="biopython"))         # counts across all dbs
Entrez.read(Entrez.espell(db="pubmed", term="biopythn"))  # spelling suggestion
```

## Large batch downloads — use search history

Search with `usehistory="y"`, then page through with `WebEnv` + `query_key`
instead of resending IDs:

```python
res = Entrez.read(Entrez.esearch(db="pubmed", term="crispr", usehistory="y"))
we, qk, count = res["WebEnv"], res["QueryKey"], int(res["Count"])

batch = 200
for start in range(0, count, batch):
    h = Entrez.efetch(db="pubmed", rettype="medline", retmode="text",
                      retstart=start, retmax=batch, webenv=we, query_key=qk)
    data = h.read(); h.close()
    # process/append data
```

For unbounded result sets, first do `esearch(..., retmax=0)` to read `Count`,
then loop `retstart`/`retmax` in batches of a few hundred.

## Parsing XML results

```python
recs = Entrez.read(Entrez.efetch(db="pubmed", id="19304878", retmode="xml"))
article = recs["PubmedArticle"][0]["MedlineCitation"]["Article"]
article["ArticleTitle"], article["Journal"]["Title"]
```

`Entrez.read` returns nested dict/list structures whose shape depends on the
database and record type — inspect before indexing. For streaming very large XML
use `Entrez.parse`.

## Error handling

```python
from urllib.error import HTTPError
try:
    h = Entrez.efetch(db="nucleotide", id="not_a_real_id", rettype="gb")
    h.read(); h.close()
except HTTPError as e:
    print(e.code, e.reason)     # 400 = bad accession; 429 = rate limited
```

## Gotchas & best practices

- Forgetting `Entrez.email` yields `HTTP 400`s from NCBI.
- **Cache locally.** Fetch once, write to disk (`SeqIO.write(record, ...)`), and
  reparse — do not re-hit NCBI on every run.
- `id=` accepts a comma-joined string or a list; joining a long list into one
  `efetch` is far kinder than N separate calls.
- The parsed XML structure varies; guard with `.get()` and check list lengths.
