# Reactome Analysis Service — Reference

Base URL: `https://reactome.org/AnalysisService`

The Analysis Service runs pathway overrepresentation (enrichment) and expression
analysis. You submit a set of identifiers (or a value matrix), get a JSON summary
plus a reusable token (valid 7 days), and later retrieve, filter, or download
results by that token. No authentication. Authoritative signatures live in the
Swagger UI at `https://reactome.org/AnalysisService/`.

## Submitting an analysis

| Method | Path | Body / content |
| ------ | ---- | -------------- |
| POST | `/identifiers/` | Plain-text identifier list or `#`-headed TSV |
| POST | `/identifiers/projection/` | Same, but project orthologs onto human pathways |
| POST | `/identifiers/form/` | `multipart/form-data`, field `file` |
| POST | `/identifiers/url/` | Form field `url` pointing to a data file |

All raw-body submissions require `Content-Type: text/plain`. Omitting it returns
`415 Unsupported Media Type`.

### Overrepresentation (list) input

One identifier per line — types may be mixed and are auto-detected:

```
TP53
BRCA1
EGFR
MYC
```

```python
import requests
ANALYSIS = "https://reactome.org/AnalysisService"

genes = ["TP53", "BRCA1", "EGFR", "MYC", "CDK1"]
result = requests.post(
    f"{ANALYSIS}/identifiers/",
    headers={"Content-Type": "text/plain"},
    data="\n".join(genes),
).json()
token = result["summary"]["token"]
```

### Expression input

A TSV whose header row starts with `#`. Column 1 is the identifier; later columns
are numeric values (period as decimal separator). The service colors the Pathway
Browser diagram by these values.

```
#Gene	Sample1	Sample2	Sample3
TP53	2.5	3.1	2.8
BRCA1	1.2	1.5	1.3
EGFR	4.5	4.2	4.8
```

```python
with open("expression.tsv") as f:
    result = requests.post(
        f"{ANALYSIS}/identifiers/",
        headers={"Content-Type": "text/plain"},
        data=f.read(),
    ).json()
```

### Species projection

For non-human input, POST to the `projection/` variant to map orthologs onto human
pathways instead of the input organism's:

```python
result = requests.post(
    f"{ANALYSIS}/identifiers/projection/",
    headers={"Content-Type": "text/plain"},
    data="\n".join(mouse_genes),
).json()
```

## Response schema

```json
{
  "summary": {
    "token": "MzUxODM3NTQzMDAwMDA1ODI4MA==",
    "type": "OVERREPRESENTATION",
    "species": "9606",
    "text": true
  },
  "pathways": [
    {
      "stId": "R-HSA-69278",
      "name": "Cell Cycle, Mitotic",
      "species": { "name": "Homo sapiens", "taxId": "9606" },
      "entities": {
        "found": 15, "total": 450,
        "pValue": 0.0000234, "fdr": 0.00156
      },
      "reactions": { "found": 12, "total": 342 }
    }
  ],
  "resourceSummary": [{ "resource": "TOTAL", "pathways": 25 }]
}
```

- `summary.token` — retrieve/filter/download later; expires after 7 days.
- `summary.type` — `OVERREPRESENTATION` or `EXPRESSION`.
- `pathways[].entities` — `found`/`total` counts, `pValue`, and Benjamini-Hochberg
  `fdr`. Filter to `fdr < 0.05` for significance.
- `pathways[].reactions` — reaction-level coverage.

## Retrieving, filtering, downloading

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/token/{token}` | Re-fetch results without recomputation |
| GET | `/token/{token}/projection/` | Re-fetch with species projection |
| GET | `/token/{token}/filter/pathways` | Filter (e.g. `?resource=UNIPROT`) |
| GET | `/download/{token}/pathways/{resource}/result.csv` | Pathway table as CSV |
| GET | `/download/{token}/entities/found/{resource}/mapping.tsv` | Identifier to entity mapping |

`{resource}` is typically `TOTAL`, or a namespace such as `UNIPROT`, `ENSEMBL`,
`CHEBI`. Confirm the exact download paths in Swagger before scripting them.

```python
results = requests.get(f"{ANALYSIS}/token/{token}").json()
```

## Supported identifiers

The service auto-detects the namespace, so a mixed list is fine.

- Proteins / genes: UniProt (`P04637`), gene symbol (`TP53`),
  Ensembl (`ENSG00000141510`), EntrezGene (`7157`), RefSeq (`NM_000546`),
  OMIM (`191170`).
- Small molecules: ChEBI (`CHEBI:15377`), KEGG Compound (`C00031`),
  PubChem (`702`).
- Other: miRBase (`hsa-miR-21`), InterPro (`IPR011616`).

## Visualizing in the Pathway Browser

Deep-link the browser with the token to overlay the analysis on a diagram:

```python
st_id = result["pathways"][0]["stId"]
url = f"https://reactome.org/PathwayBrowser/#{st_id}&DTAB=AN&ANALYSIS={token}"
```

## Reusable client

A small, dependency-light client covering the common calls. Adapt as needed.

```python
import requests

class ReactomeClient:
    CONTENT  = "https://reactome.org/ContentService"
    ANALYSIS = "https://reactome.org/AnalysisService"

    def version(self) -> str:
        r = requests.get(f"{self.CONTENT}/data/database/version")
        r.raise_for_status()
        return r.text.strip()

    def query(self, stable_id: str) -> dict:
        r = requests.get(f"{self.CONTENT}/data/query/{stable_id}")
        r.raise_for_status()
        return r.json()

    def participants(self, event_id: str) -> list:
        r = requests.get(
            f"{self.CONTENT}/data/event/{event_id}/participatingPhysicalEntities"
        )
        r.raise_for_status()
        return r.json()

    def search(self, term: str, **params) -> dict:
        r = requests.get(f"{self.CONTENT}/search/query",
                         params={"query": term, **params})
        r.raise_for_status()
        return r.json()

    def enrich(self, identifiers: list, project: bool = False) -> dict:
        path = "identifiers/projection/" if project else "identifiers/"
        r = requests.post(
            f"{self.ANALYSIS}/{path}",
            headers={"Content-Type": "text/plain"},
            data="\n".join(identifiers),
        )
        r.raise_for_status()
        return r.json()

    def results_by_token(self, token: str) -> dict:
        r = requests.get(f"{self.ANALYSIS}/token/{token}")
        r.raise_for_status()
        return r.json()
```

## End-to-end enrichment workflow

```python
import json

def analyze_gene_list(genes, out_path="analysis_results.json"):
    client = ReactomeClient()
    result = client.enrich(genes)
    token = result["summary"]["token"]

    significant = [p for p in result["pathways"] if p["entities"]["fdr"] < 0.05]

    with open(out_path, "w") as f:
        json.dump({
            "token": token,
            "total_pathways": len(result["pathways"]),
            "significant_pathways": len(significant),
            "pathways": significant,
        }, f, indent=2)

    if significant:
        top = significant[0]["stId"]
        print(f"View: https://reactome.org/PathwayBrowser/#{top}&DTAB=AN&ANALYSIS={token}")
    return result

analyze_gene_list(["TP53", "BRCA1", "BRCA2", "CDK1", "CDK2"])
```

## Best practices

- Batch, do not loop. Submit every identifier in one POST; never analyze one gene
  per request.
- Persist tokens. Store the token to re-fetch results within the 7-day window
  instead of resubmitting.
- Filter early. Reduce to `fdr < 0.05` (or your threshold) before reporting.
- Project deliberately. Use `projection/` only when you actually want orthology
  mapping onto human pathways; it changes the result set.
- Be polite. No hard rate limit exists, but space out large batches and cache where
  possible.
