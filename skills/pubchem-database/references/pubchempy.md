# PubChemPy Guide

PubChemPy is an MIT-licensed Python wrapper over PUG-REST. It resolves
identifiers, exposes compounds as objects with lazily loaded property
attributes, and handles the async polling for structure searches.

Docs: https://pubchempy.readthedocs.io/ — Source: https://github.com/mcs07/PubChemPy

## Core functions

| Call | Returns |
| --- | --- |
| `pcp.get_compounds(query, namespace, **kw)` | `list[Compound]` (empty list if no match) |
| `pcp.Compound.from_cid(cid)` | one `Compound` |
| `pcp.get_properties(props, query, namespace)` | `list[dict]`, one per matched CID |
| `pcp.get_synonyms(query, namespace)` | `list[dict]` with `CID` + `Synonym` list |
| `pcp.download(fmt, query, namespace, path, overwrite=)` | writes file (SDF/JSON/PNG/CSV) |
| `pcp.get_cids(query, namespace)` | `list[int]` of CIDs |

`namespace` ∈ `{name, cid, smiles, inchi, inchikey, formula}`.

### Structure-search keyword args

Pass to `get_compounds` / `get_cids`:

- `searchtype='similarity'` with `Threshold=<0-100>` (Tanimoto) — default 90.
- `searchtype='substructure'` / `'superstructure'`.
- `MaxRecords=<int>` — cap results; always set it to avoid server timeouts.

## Compound attributes

Attributes are fetched on first access (one network call per attribute unless
already cached), so for many compounds prefer `get_properties` with an explicit
list. Attribute name → PUG-REST property:

| Attribute | Property |
| --- | --- |
| `.cid` | CID |
| `.molecular_formula` | MolecularFormula |
| `.molecular_weight` | MolecularWeight |
| `.iupac_name` | IUPACName |
| `.canonical_smiles` | SMILES |
| `.isomeric_smiles` | ConnectivitySMILES |
| `.inchi` / `.inchikey` | InChI / InChIKey |
| `.xlogp` | XLogP |
| `.tpsa` | TPSA |
| `.h_bond_donor_count` | HBondDonorCount |
| `.h_bond_acceptor_count` | HBondAcceptorCount |
| `.rotatable_bond_count` | RotatableBondCount |
| `.exact_mass` / `.monoisotopic_mass` | ExactMass / MonoisotopicMass |
| `.charge` / `.complexity` | Charge / Complexity |

> Property-name drift: PubChem renamed the SMILES property set
> (`CanonicalSMILES`→`SMILES`, `IsomericSMILES`→`ConnectivitySMILES`). The
> PubChemPy attribute names above still work, but if you pass raw property
> strings to `get_properties` and get `PUGREST.BadRequest`, upgrade PubChemPy
> or switch to the current property name. Verify against the live property
> table rather than hard-coding.

## Error taxonomy

```python
from pubchempy import (
    BadRequestError,   # malformed query / unknown property / bad namespace
    NotFoundError,     # identifier resolved to nothing (some ops raise this)
    TimeoutError,      # async search exceeded the polling window
    PubChemHTTPError,  # base for HTTP errors incl. 503 ServerBusy (rate limit)
)
```

Key behavior nuances:

- `get_compounds` / `get_properties` return an **empty list** when nothing
  matches — they do not always raise `NotFoundError`. Guard with
  `hits[0] if hits else None`.
- Property values can be `None` even for a valid compound (e.g. no computed
  XLogP for salts/mixtures). Check before arithmetic:
  `if c.xlogp is not None:`.
- A 503 `ServerBusy` means you hit the rate limit — sleep and retry with
  exponential backoff; it is transient, not a bad request.

## Robust retrieval pattern

```python
import time
import pubchempy as pcp
from pubchempy import PubChemHTTPError

def resolve(query, namespace='name', retries=3):
    for attempt in range(retries):
        try:
            hits = pcp.get_compounds(query, namespace)
            return hits[0] if hits else None
        except PubChemHTTPError:           # rate limit / transient server error
            time.sleep(0.5 * 2 ** attempt) # 0.5s, 1s, 2s backoff
    return None
```

## Downloads

```python
pcp.download('SDF',  'aspirin', 'name', 'aspirin.sdf', overwrite=True)
pcp.download('JSON', '2244',    'cid',  'aspirin.json', overwrite=True)
pcp.download('PNG',  '2244',    'cid',  'aspirin.png',  overwrite=True)
```
