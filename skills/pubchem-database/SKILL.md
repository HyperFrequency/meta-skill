---
name: pubchem-database
version: 0.1.0
description: >-
  Query PubChem — NCBI's open chemical database of 110M+ compounds and 270M+
  bioactivities — from Python via PubChemPy or the raw PUG-REST/PUG-View HTTP
  APIs. Use when you need to look up compounds by name, CID, SMILES, InChI, or
  formula; retrieve computed properties (MW, XLogP, TPSA, H-bond counts,
  InChIKey); run Tanimoto similarity or substructure searches; interconvert
  chemical identifiers; or fetch synonyms, 2D structure images, SDF records,
  bioassay activity, and PUG-View drug/safety annotations; and to batch-screen
  compound sets for drug-likeness. Not for computing descriptors or fingerprints
  locally on your own structures (use RDKit), for protein/gene sequence databases,
  for general web or literature search (use research-lookup), or for other
  structured scientific databases (use database-lookup).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "PubChemPy: MIT"
---

# PubChem Database

## Overview

PubChem (maintained by NCBI) is the largest freely available chemical database:
110M+ validated compound structures, 300M+ deposited substances, and 270M+
bioactivity results from 700+ data sources. It exposes two HTTP interfaces —
**PUG-REST** for structured lookups and searches, and **PUG-View** for full
textual annotations (drug info, toxicity, safety, literature). The Python
library **PubChemPy** wraps PUG-REST and handles the asynchronous polling that
similarity/substructure searches require.

Use PubChemPy for most work; drop to raw `requests` against PUG-REST/PUG-View
only for endpoints PubChemPy does not cover (bioassay summaries, target search,
PUG-View sections).

## When to Use This Skill

- Resolve a compound by name, CID, SMILES, InChI/InChIKey, or molecular formula.
- Retrieve computed molecular properties (formula, MW, XLogP, TPSA, H-bond
  donor/acceptor counts, rotatable bonds, complexity, InChIKey).
- Run **similarity** (Tanimoto) or **substructure**/superstructure searches.
- Convert between chemical identifiers (name ↔ CID ↔ SMILES ↔ InChI).
- Pull synonyms, 2D structure PNGs, or SDF/JSON structure records.
- Access **bioassay** activity outcomes, assay targets, or active-compound lists.
- Fetch PUG-View sections: drug/medication, pharmacology, safety, toxicity.
- Batch-screen a compound list (e.g. Lipinski Rule-of-Five drug-likeness).

## When NOT to Use This Skill

- **Computing descriptors/fingerprints locally** on structures you already have —
  use RDKit; PubChem only returns properties it has precomputed for known CIDs.
- **Protein, gene, or nucleotide sequence** lookups — this is a small-molecule
  database, not UniProt/NCBI Gene/Ensembl.
- **General web or literature search** — use `research-lookup`.
- **Other structured scientific databases** (ChEMBL, UniProt, generic API
  lookups) — use `database-lookup`.
- **Bulk downloads of the entire database** — use PubChem's FTP bulk files, not
  the rate-limited REST API.

## Setup

```bash
uv pip install pubchempy requests   # requests only needed for raw API / bioactivity
uv pip install pandas               # optional, for batch/tabular work
```

No API key is required. PubChem enforces **5 requests/sec, 400/min, 300 s
compute/min** per IP — respect these (see `references/pug-rest-api.md`).

## Core Capabilities

### Search by identifier

```python
import pubchempy as pcp

pcp.get_compounds('aspirin', 'name')                     # -> [Compound, ...]
pcp.Compound.from_cid(2244)                              # aspirin by CID
pcp.get_compounds('CC(=O)OC1=CC=CC=C1C(=O)O', 'smiles')  # by SMILES
pcp.get_compounds('C9H8O4', 'formula')                   # all formula matches
```

`namespace` accepts `name`, `cid`, `smiles`, `inchi`, `inchikey`, `formula`.
Name and formula searches can return many hits — index `[0]` only when you are
sure the query is unambiguous.

### Property retrieval and batch screening

```python
props = pcp.get_properties(
    ['MolecularFormula', 'MolecularWeight', 'XLogP', 'TPSA'],
    'aspirin', 'name')          # -> [ {..}, ... ], one dict per matched CID
```

Compound attributes (`.molecular_weight`, `.xlogp`, `.tpsa`,
`.h_bond_donor_count`, `.inchikey`, …) load lazily. For many compounds, prefer
`get_properties` with an explicit property list — it is one request per call,
not one per attribute. Full property list, attribute-name mapping, and a
**Lipinski batch-screen** example: `references/pubchempy.md` and
`references/workflows.md`.

### Similarity and substructure search

```python
pcp.get_compounds(smiles, 'smiles', searchtype='similarity',
                  Threshold=90, MaxRecords=50)     # Tanimoto, 0-100
pcp.get_compounds('c1ccncc1', 'smiles', searchtype='substructure',
                  MaxRecords=100)                   # compounds containing pyridine
```

These are **asynchronous** server-side jobs (often 15-30 s); PubChemPy polls
automatically. Always set `MaxRecords` to avoid timeouts. The raw async
ListKey protocol is in `references/pug-rest-api.md`.

### Identifier conversion, images, and downloads

```python
c = pcp.get_compounds('caffeine', 'name')[0]
c.cid, c.canonical_smiles, c.inchi, c.inchikey, c.molecular_formula
pcp.download('SDF', 'aspirin', 'name', 'aspirin.sdf', overwrite=True)
pcp.download('PNG', '2244', 'cid', 'aspirin.png', overwrite=True)
```

### Synonyms

```python
pcp.get_synonyms('aspirin', 'name')   # -> [{'CID': 2244, 'Synonym': [...]}]
```

### Bioactivity and PUG-View annotations

Not covered by PubChemPy — use raw HTTP. Endpoints, target search, active-
compound lists, PUG-View section headings, and ready-to-use helper functions
(`get_bioassay_summary`, `search_assays_by_target`, `get_compound_annotations`,
`summarize_bioactivities`) are in `references/workflows.md`.

```python
import requests
cid = 2244
r = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/assaysummary/JSON")
```

## Robustness

Handle the failure modes that bite in production — empty results, missing
property values, rate-limit 503s, async timeouts:

```python
from pubchempy import BadRequestError, NotFoundError, PubChemHTTPError
try:
    hits = pcp.get_compounds(query, 'name')
    compound = hits[0] if hits else None   # get_compounds returns [] , not an error
except NotFoundError:
    compound = None
except (BadRequestError, PubChemHTTPError) as e:
    ...   # bad namespace/property, or rate limit — back off and retry
```

Add ~0.2-0.3 s between raw requests, reuse CIDs for repeat lookups, and guard
against `None` property values (not every compound has an XLogP). Full error
taxonomy, retry/backoff guidance, and the "property renamed" gotcha:
`references/pubchempy.md`.

## Reference Files

- `references/pug-rest-api.md` — PUG-REST URL grammar, full property list,
  structure-search endpoints, the async ListKey pattern, PUG-View sections,
  rate limits.
- `references/pubchempy.md` — PubChemPy classes/methods, attribute-name
  mapping, download formats, error taxonomy, property-deprecation gotchas.
- `references/workflows.md` — end-to-end recipes: identifier conversion,
  Lipinski drug-likeness screening, similar-drug discovery, batch property
  comparison, substructure virtual screening, and the bioactivity helper
  functions.

## Related Skills

- `database-lookup` — generic structured lookups in other named scientific
  databases.
- `research-lookup` — web/scholarly search when you need papers, not structures.
