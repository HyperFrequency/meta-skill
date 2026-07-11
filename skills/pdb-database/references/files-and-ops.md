# Files, parsing, and operational concerns — reference

Coordinate files come from plain HTTPS URLs; no client library or key is needed.
This file covers formats, download helpers, parsing, rate limiting, error
handling, and a few worked recipes.

## Download URLs

| What | URL template |
| --- | --- |
| mmCIF (modern standard) | `https://files.rcsb.org/download/{ID}.cif` |
| Legacy PDB text | `https://files.rcsb.org/download/{ID}.pdb` |
| Biological assembly N | `https://files.rcsb.org/download/{ID}.pdb{N}` (e.g. `.pdb1`) |
| Structure factors | `https://files.rcsb.org/download/{ID}-sf.cif` |
| FASTA sequence | `https://www.rcsb.org/fasta/entry/{ID}` |
| BinaryCIF (compact binary) | `https://models.rcsb.org/{ID}.bcif` (ModelServer) |

Guidance:

- **Prefer mmCIF.** The legacy fixed-column PDB format cannot represent structures
  with >99,999 atoms or >62 chains; large cryo-EM/ribosome entries exist only as
  mmCIF/BinaryCIF.
- **BinaryCIF** is the most bandwidth-efficient for bulk/programmatic pipelines;
  the ModelServer can also return atom subsets (e.g. a single chain or ligand
  environment) rather than the whole file.
- Downloading a **biological assembly** (`.pdb1`) gives the functional oligomer;
  the plain file is the asymmetric unit, which may be a fraction of the biological
  form.

## Download helper

```python
import requests

def download_structure(pdb_id: str, fmt: str = "cif", out_dir: str = ".") -> str | None:
    """Download an RCSB coordinate file. fmt: 'cif' (preferred) or 'pdb'."""
    url = f"https://files.rcsb.org/download/{pdb_id}.{fmt}"
    resp = requests.get(url, timeout=30)
    if resp.status_code == 200:
        path = f"{out_dir}/{pdb_id}.{fmt}"
        with open(path, "w") as fh:
            fh.write(resp.text)
        return path
    print(f"download failed for {pdb_id}: HTTP {resp.status_code}")
    return None
```

## Parsing (downstream, not this skill)

This skill fetches; analysis belongs to a structure library. Common entry point:

```python
from Bio.PDB import PDBParser, MMCIFParser

structure = MMCIFParser(QUIET=True).get_structure("prot", "4HHB.cif")
for model in structure:
    for chain in model:
        for residue in chain:
            for atom in residue:
                atom.get_coord()   # numpy xyz
```

For heavy per-atom work at scale, prefer Biotite or Gemmi over BioPython.

## Rate limiting and backoff

RCSB endpoints are shared and rate-limited. Exceeding the limit returns **HTTP
429**. Start at a few requests/second and back off on 429:

```python
import time, requests

def fetch_with_retry(url, max_retries=5, initial_delay=1.0):
    delay = initial_delay
    for _ in range(max_retries):
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp
        if resp.status_code == 429:
            time.sleep(delay)
            delay *= 2                 # exponential backoff
            continue
        resp.raise_for_status()
    raise RuntimeError(f"failed after {max_retries} retries: {url}")
```

Batch best practices:

1. Search first to get ids, then fetch — never crawl blindly.
2. Cache downloaded files and metadata locally to avoid re-requesting.
3. Chunk large id lists; add a small delay between chunks.
4. Use `DataQuery`/GraphQL (many ids or fields per call) to minimize request count.

## Error handling

| Symptom | Cause | Action |
| --- | --- | --- |
| HTTP 404 | Id absent, obsolete, or superseded | Verify id (uppercase); check for a replacement entry |
| HTTP 429 | Rate limit exceeded | Exponential backoff; lower concurrency |
| HTTP 500 | Transient server error | Retry after a short delay; check RCSB status |
| Empty search result | Over-restrictive query / wrong attribute path | Loosen operators; validate path against the search schema |
| Missing field in Data response | Field not requested or not applicable to that object | Add the path to `return_data_list`; confirm the object level |

## Worked recipes

### Structures containing a specific ligand

```python
from rcsbapi.search import search_attributes as attrs
q = attrs.rcsb_nonpolymer_entity_instance_container_identifiers.comp_id == "ATP"
atp_bound = list(q())
```

### High-quality X-ray structures (resolution + R-free)

```python
from rcsbapi.search import search_attributes as attrs
q = (attrs.rcsb_entry_info.resolution_combined < 2.0) & (attrs.refine.ls_R_factor_R_free < 0.25)
high_quality = list(q())
```

### Recently released structures

```python
import datetime
from rcsbapi.search import AttributeQuery
lo = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
hi = datetime.date.today().isoformat()
q = AttributeQuery(
    attribute="rcsb_accession_info.initial_release_date",
    operator="range",
    value=(lo, hi),
)
recent = list(q())
```

### Search → metadata pipeline

```python
from rcsbapi.search import search_attributes as attrs
from rcsbapi.data import DataQuery as Query

ids = list((attrs.exptl.method == "ELECTRON MICROSCOPY")
           & (attrs.rcsb_entry_info.resolution_combined < 3.0))
meta = Query(
    input_type="entries",
    input_ids=ids[:200],
    return_data_list=["struct.title", "rcsb_entry_info.resolution_combined"],
).exec()
```

## Links

- Web APIs overview: https://www.rcsb.org/docs/programmatic-access/web-apis-overview
- File download service: https://www.rcsb.org/docs/programmatic-access/file-download-services
- ModelServer / BinaryCIF: https://models.rcsb.org
- `rcsb-api` docs: https://rcsbapi.readthedocs.io
