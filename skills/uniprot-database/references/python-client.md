# A Reusable UniProt Python Client

A dependency-light client (`requests` only) that wraps the operations described
in `SKILL.md`: search, single-entry retrieval, correct `Link`-header cursor
pagination, streaming, and the full async ID-mapping poll loop. Copy the whole
module or lift individual functions.

For production use, prefer the maintained `Unipressed` (typed UniProt REST
client) or the `bioservices` package. This module is here so you can read the
exact HTTP contract and drop it into a script with no extra install.

```python
#!/usr/bin/env python3
"""Minimal UniProt REST client (requests-only)."""

import json
import sys
import time
from typing import Iterator, Optional

import requests

BASE = "https://rest.uniprot.org"
POLL_SECONDS = 3
SESSION = requests.Session()


def _get(url: str, **kwargs) -> requests.Response:
    """GET with retry on HTTP 429 (respecting Retry-After)."""
    for attempt in range(5):
        resp = SESSION.get(url, **kwargs)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def search(query: str, fmt: str = "json",
           fields: Optional[list[str]] = None, size: int = 25):
    """Single page of results (up to `size`, max 500)."""
    params = {"query": query, "format": fmt, "size": size}
    if fields:
        params["fields"] = ",".join(fields)
    resp = _get(f"{BASE}/uniprotkb/search", params=params)
    return resp.json() if fmt == "json" else resp.text


def search_all(query: str, fields: Optional[list[str]] = None,
               size: int = 500) -> Iterator[dict]:
    """Every JSON result, walking the Link-header cursor."""
    url = f"{BASE}/uniprotkb/search"
    params = {"query": query, "format": "json", "size": size}
    if fields:
        params["fields"] = ",".join(fields)
    while url:
        resp = _get(url, params=params)
        yield from resp.json()["results"]
        params = None  # cursor is embedded in the next URL
        url = resp.links.get("next", {}).get("url")


def get_entry(accession: str, fmt: str = "json"):
    """One entry by accession. fmt: json, fasta, txt, xml, gff, rdf."""
    resp = _get(f"{BASE}/uniprotkb/{accession}.{fmt}")
    return resp.json() if fmt == "json" else resp.text


def stream_to_file(query: str, path: str, fmt: str = "fasta",
                   compressed: bool = False) -> None:
    """Download an entire result set to disk (no pagination)."""
    params = {"query": query, "format": fmt}
    if compressed:
        params["compressed"] = "true"
    with SESSION.get(f"{BASE}/uniprotkb/stream", params=params,
                     stream=True) as resp:
        resp.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)


def map_ids(ids: list[str], from_db: str, to_db: str) -> dict:
    """Async ID mapping: submit -> poll -> results. Max 100,000 ids."""
    if len(ids) > 100_000:
        raise ValueError("UniProt allows at most 100,000 ids per job")

    run = SESSION.post(f"{BASE}/idmapping/run",
                       data={"from": from_db, "to": to_db,
                             "ids": ",".join(ids)})
    run.raise_for_status()
    job_id = run.json()["jobId"]

    status_url = f"{BASE}/idmapping/status/{job_id}"
    while True:
        body = _get(status_url).json()
        if body.get("jobStatus") != "RUNNING":
            break
        if "results" in body or "failedIds" in body:
            break
        time.sleep(POLL_SECONDS)

    # UniProtKB targets return full entries from a dedicated path
    results_path = ("idmapping/uniprotkb/results" if to_db.startswith("UniProtKB")
                    else "idmapping/results")
    return _get(f"{BASE}/{results_path}/{job_id}").json()


def list_return_fields() -> list:
    return _get(f"{BASE}/configure/uniprotkb/result-fields").json()


def list_mapping_databases() -> dict:
    return _get(f"{BASE}/configure/idmapping/fields").json()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Query UniProt over REST")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--search")
    g.add_argument("--get", metavar="ACCESSION")
    g.add_argument("--map", metavar="ID1,ID2,...")
    g.add_argument("--stream", metavar="QUERY")
    p.add_argument("--format", default="json")
    p.add_argument("--fields")
    p.add_argument("--size", type=int, default=25)
    p.add_argument("--from", dest="from_db")
    p.add_argument("--to", dest="to_db")
    p.add_argument("--out", default="uniprot_stream.out")
    a = p.parse_args()

    fields = a.fields.split(",") if a.fields else None
    try:
        if a.search:
            out = search(a.search, a.format, fields, a.size)
            print(json.dumps(out, indent=2) if a.format == "json" else out)
        elif a.get:
            out = get_entry(a.get, a.format)
            print(json.dumps(out, indent=2) if a.format == "json" else out)
        elif a.map:
            if not (a.from_db and a.to_db):
                p.error("--map requires --from and --to")
            print(json.dumps(map_ids(a.map.split(","), a.from_db, a.to_db), indent=2))
        elif a.stream:
            stream_to_file(a.stream, a.out, a.format)
            print(f"wrote {a.out}")
    except Exception as exc:  # noqa: BLE001 - CLI top level
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
```

## CLI usage

```bash
python uniprot_client.py --search "insulin AND organism_id:9606" --format json --size 5
python uniprot_client.py --get P01308 --format fasta
python uniprot_client.py --map P01308,P04637 --from UniProtKB_AC-ID --to PDB
python uniprot_client.py --stream "organism_id:9606 AND reviewed:true" --format fasta --out human.fasta
```

## Notes

- `search_all` is the correct paginator — it follows the `Link` header rather
  than a nonexistent JSON `next` key.
- `map_ids` routes UniProtKB targets to `/idmapping/uniprotkb/results/{job}` so
  you get full records, and checks both the `jobStatus` field and the presence
  of `results`/`failedIds` before fetching.
- `_get` retries HTTP 429 with exponential backoff, honoring `Retry-After`.
- Reuse of one `Session` keeps connections warm across many calls.
