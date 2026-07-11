# UniProt API Examples

Runnable snippets in Python, curl, R, and JavaScript. Base URL throughout:
`https://rest.uniprot.org`. No API key required.

## curl

```bash
# Search (5 human reviewed insulin hits, JSON)
curl "https://rest.uniprot.org/uniprotkb/search?query=insulin+AND+organism_id:9606+AND+reviewed:true&format=json&size=5"

# Single entry as FASTA
curl "https://rest.uniprot.org/uniprotkb/P01308.fasta"

# Selected columns as TSV
curl "https://rest.uniprot.org/uniprotkb/search?query=gene:BRCA1+AND+reviewed:true&format=tsv&fields=accession,gene_names,length"

# ID mapping: submit, then fetch (substitute the returned JOB_ID)
curl -X POST "https://rest.uniprot.org/idmapping/run" \
  -d "from=UniProtKB_AC-ID&to=PDB&ids=P01308,P04637"
curl "https://rest.uniprot.org/idmapping/results/JOB_ID"

# Stream a whole proteome, gzip-compressed, to disk
curl "https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true&format=fasta&compressed=true" \
  -o human_proteome.fasta.gz
```

Use `--data-urlencode "query=..."` (with `-G`) instead of manual `+`/`%20`
escaping for complex queries.

## Python (`requests`)

```python
import requests

BASE = "https://rest.uniprot.org"

# Search with field selection
r = requests.get(f"{BASE}/uniprotkb/search", params={
    "query": "gene:BRCA1 AND reviewed:true",
    "format": "tsv",
    "fields": "accession,gene_names,organism_name,length,cc_function",
})
r.raise_for_status()
print(r.text)

# Parse a JSON search result
r = requests.get(f"{BASE}/uniprotkb/search", params={
    "query": "insulin AND organism_id:9606 AND reviewed:true",
    "format": "json", "size": 10,
})
for entry in r.json()["results"]:
    acc = entry["primaryAccession"]
    name = entry["proteinDescription"]["recommendedName"]["fullName"]["value"]
    print(acc, name)
```

### Cursor pagination (the correct way)

UniProt paginates via the HTTP `Link` header, not a JSON key.

```python
def iter_all(query, fields=None, size=500):
    url = f"{BASE}/uniprotkb/search"
    params = {"query": query, "format": "json", "size": size}
    if fields:
        params["fields"] = ",".join(fields)
    while url:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        yield from resp.json()["results"]
        # after the first page the cursor is baked into the next URL
        params = None
        url = resp.links.get("next", {}).get("url")

count = sum(1 for _ in iter_all(
    "protein_name:kinase AND organism_id:9606 AND reviewed:true",
    fields=["accession", "gene_names"]))
print(count, "proteins")
```

`resp.headers["x-total-results"]` gives the full match count up front.

### Streaming a large download with a progress bar

```python
from tqdm import tqdm

def download(query, out, fmt="fasta"):
    with requests.get(f"{BASE}/uniprotkb/stream",
                      params={"query": query, "format": fmt},
                      stream=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(out, "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

download("organism_id:9606 AND reviewed:true", "human_proteome.fasta")
```

## R (`httr`)

```r
library(httr); library(readr)

resp <- GET("https://rest.uniprot.org/uniprotkb/search",
            query = list(query = "gene:BRCA1 AND reviewed:true",
                         format = "tsv",
                         fields = "accession,gene_names,organism_name,length"))
df <- read_tsv(content(resp, "text"))
print(df)

# Single sequence
cat(content(GET("https://rest.uniprot.org/uniprotkb/P01308.fasta"), "text"))
```

## JavaScript (fetch)

```javascript
const BASE = "https://rest.uniprot.org";

async function search(query) {
  const url = `${BASE}/uniprotkb/search?query=${encodeURIComponent(query)}&format=json&size=10`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return (await res.json()).results;
}

async function mapIds(ids, fromDb, toDb) {
  const run = await fetch(`${BASE}/idmapping/run`, {
    method: "POST",
    body: new URLSearchParams({ from: fromDb, to: toDb, ids: ids.join(",") }),
  });
  const { jobId } = await run.json();
  for (;;) {
    const s = await (await fetch(`${BASE}/idmapping/status/${jobId}`)).json();
    if (s.results || s.failedIds) break;
    await new Promise(r => setTimeout(r, 3000));
  }
  return (await fetch(`${BASE}/idmapping/results/${jobId}`)).json();
}
```

## Handling failures

- **429 Too Many Requests** — back off and retry after `Retry-After` seconds.
- **400 Bad Request** — the body names the bad `query`/`fields` token; validate
  against the `/configure/...` endpoints.
- **Empty search** — HTTP 200 with `results: []`, not a 404.
- **Obsolete accession** — a `303` redirect to the current entry; follow it.
