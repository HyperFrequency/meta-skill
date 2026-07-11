# Reactome Content Service — Reference

Base URL: `https://reactome.org/ContentService`

The Content Service retrieves curated Reactome objects. Responses are JSON unless
the requested attribute is a scalar (then plain text). No authentication. The
interactive Swagger at `https://reactome.org/ContentService/` is authoritative —
use it to confirm any signature below.

## Database information

| Method | Path | Returns |
| ------ | ---- | ------- |
| GET | `/data/database/version` | Version number as plain text (e.g. `94`) |
| GET | `/data/database/name` | Database name as plain text |

```python
import requests
CONTENT = "https://reactome.org/ContentService"
version = requests.get(f"{CONTENT}/data/database/version").text.strip()
```

## Entity queries by stable ID

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/data/query/{id}` | Full object for a stable ID or dbId |
| GET | `/data/query/{id}/{attributeName}` | A single attribute of that object |
| GET | `/data/query/enhanced/{id}` | Object enriched with extra derived fields |
| POST | `/data/query/ids` | Batch: body is a comma/newline-separated ID list |

`{id}` accepts a Reactome stable identifier (`R-HSA-69278`) or a numeric dbId.

```python
obj = requests.get(f"{CONTENT}/data/query/R-HSA-69278").json()
print(obj["stId"], obj["displayName"], obj["schemaClass"])
print(obj["species"][0]["displayName"])

# Just one attribute
name = requests.get(f"{CONTENT}/data/query/R-HSA-69278/displayName").text
```

### Common object fields

Returned objects share a core shape (type-specific fields vary):

```json
{
  "stId": "R-HSA-69278",
  "dbId": 69278,
  "displayName": "Cell Cycle, Mitotic",
  "schemaClass": "Pathway",
  "species": [{ "dbId": 48887, "displayName": "Homo sapiens", "taxId": "9606" }],
  "isInDisease": false,
  "summation": [{ "text": "Description of the pathway ..." }]
}
```

`schemaClass` values you will encounter include `Pathway`, `TopLevelPathway`,
`Reaction`, `BlackBoxEvent`, `Complex`, `EntityWithAccessionedSequence` (proteins),
`SimpleEntity` (small molecules), and `DefinedSet`.

## Pathway / event structure

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/data/event/{id}/participatingPhysicalEntities` | Molecules taking part in an event |
| GET | `/data/pathway/{id}/containedEvents` | Sub-events (reactions, subpathways) |
| GET | `/data/pathway/{id}/containedEvents/{attributeName}` | One attribute of each contained event |
| GET | `/data/eventsHierarchy/{species}` | Full event tree for a species (e.g. `9606`) |
| GET | `/data/complex/{id}/subunits` | Subunits of a complex |

```python
parts = requests.get(
    f"{CONTENT}/data/event/R-HSA-69278/participatingPhysicalEntities"
).json()
by_type = {}
for e in parts:
    by_type.setdefault(e["schemaClass"], []).append(e["displayName"])
```

## Free-text search

Use the search controller (not `/data/query`, which requires a resolvable ID).

| Method | Path | Key params |
| ------ | ---- | ---------- |
| GET | `/search/query` | `query` (term), `species`, `types`, `cluster`, `start`, `rows` |
| GET | `/search/facet` | Faceting metadata for a query |
| GET | `/search/suggest` | Autocomplete suggestions for `query` |

```python
hits = requests.get(
    f"{CONTENT}/search/query",
    params={"query": "glycolysis", "species": "Homo sapiens", "types": "Pathway"},
).json()
```

The search response wraps results under `results` → grouped by `typeName`, each with
`entries` carrying `stId`, `name`, `species`, and `exactType`. Confirm the exact
envelope against the Swagger UI, as it is richer than the flat lists returned by the
`/data/*` endpoints.

## Mapping identifiers to pathways

Resolve an external identifier to the pathways containing it.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/data/mapping/{resource}/{identifier}/pathways` | Pathways containing an identifier |
| GET | `/data/mapping/{resource}/{identifier}/reactions` | Reactions containing an identifier |
| GET | `/data/pathways/low/entity/{id}` | Lowest-level pathways for a physical entity |
| GET | `/data/pathways/low/diagram/entity/{id}` | Lowest-level pathways that have a diagram |

`{resource}` is a namespace such as `UniProt`, `Ensembl`, `ChEBI`, or `NCBI Gene`.
Add `?species=9606` to constrain. Verify the exact resource spelling in Swagger;
namespace labels are case- and space-sensitive.

## Output formats

Most endpoints return JSON. Some list endpoints can emit TSV when you send
`Accept: text/tab-separated-values`, e.g.:

```
stId          displayName            schemaClass
R-HSA-69278   Cell Cycle, Mitotic    Pathway
R-HSA-69306   DNA Replication        Pathway
```

## Error handling

| Status | Meaning |
| ------ | ------- |
| 200 | Success |
| 400 | Bad request (malformed parameters) |
| 404 | Not found (unknown stable ID / dbId) |
| 415 | Unsupported media type |
| 500 | Server error |

Error bodies are JSON:

```json
{ "code": 404, "reason": "NOT_FOUND", "messages": ["Entity R-HSA-INVALID not found"] }
```

```python
resp = requests.get(f"{CONTENT}/data/query/R-HSA-INVALID")
if resp.status_code == 404:
    print("Unknown identifier")
else:
    resp.raise_for_status()
    data = resp.json()
```
