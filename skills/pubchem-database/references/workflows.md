# Workflows and Bioactivity Recipes

End-to-end recipes built on PubChemPy (`references/pubchempy.md`) and raw
PUG-REST (`references/pug-rest-api.md`). All examples assume
`import pubchempy as pcp`.

## 1. Identifier conversion

```python
c = pcp.get_compounds('caffeine', 'name')[0]
ids = {
    'CID': c.cid, 'IUPAC': c.iupac_name, 'SMILES': c.canonical_smiles,
    'InChI': c.inchi, 'InChIKey': c.inchikey, 'Formula': c.molecular_formula,
}
```

## 2. Lipinski Rule-of-Five drug-likeness screen

`None`-safe: not every compound has a computed XLogP.

```python
def lipinski(name):
    c = pcp.get_compounds(name, 'name')[0]
    rules = {
        'MW<=500':  c.molecular_weight is not None and c.molecular_weight <= 500,
        'LogP<=5':  c.xlogp is not None and c.xlogp <= 5,
        'HBD<=5':   c.h_bond_donor_count is not None and c.h_bond_donor_count <= 5,
        'HBA<=10':  c.h_bond_acceptor_count is not None and c.h_bond_acceptor_count <= 10,
    }
    violations = sum(1 for ok in rules.values() if ok is False)
    return rules, violations
```

## 3. Find similar drug candidates, then filter

```python
ref = pcp.get_compounds('imatinib', 'name')[0]
similar = pcp.get_compounds(ref.canonical_smiles, 'smiles',
                            searchtype='similarity', Threshold=85, MaxRecords=20)
candidates = [c for c in similar
              if c.molecular_weight and 200 <= c.molecular_weight <= 600
              and c.xlogp is not None and -1 <= c.xlogp <= 5]
```

## 4. Batch property comparison (tabular)

```python
import pandas as pd
names = ['aspirin', 'ibuprofen', 'naproxen', 'celecoxib']
rows = []
for name in names:
    hits = pcp.get_compounds(name, 'name')
    if not hits:
        continue
    c = hits[0]
    rows.append({'Name': name, 'CID': c.cid, 'Formula': c.molecular_formula,
                 'MW': c.molecular_weight, 'LogP': c.xlogp, 'TPSA': c.tpsa,
                 'HBD': c.h_bond_donor_count, 'HBA': c.h_bond_acceptor_count})
df = pd.DataFrame(rows)
```

For large lists, one `pcp.get_properties([...], name, 'name')` call per name is
cheaper than touching many attributes on a `Compound` object.

## 5. Substructure virtual screening

```python
hits = pcp.get_compounds('S(=O)(=O)N', 'smiles',            # sulfonamide motif
                         searchtype='substructure', MaxRecords=100)
druglike = [c for c in hits if c.molecular_weight and c.molecular_weight < 500]
```

Common SMILES motifs: benzene `c1ccccc1`, pyridine `c1ccncc1`,
phenol `c1ccc(O)cc1`, carboxylic acid `C(=O)O`, sulfonamide `S(=O)(=O)N`.

## Bioactivity helpers (raw PUG-REST)

PubChemPy does not wrap bioassays. These functions use `requests` with a
built-in rate-limit delay. Endpoints are documented in
`references/pug-rest-api.md`.

```python
import time, requests

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
DELAY = 0.21   # ~5 req/s ceiling

def _get(url):
    time.sleep(DELAY)
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

def bioassay_summary(cid):
    return _get(f"{BASE}/compound/cid/{cid}/assaysummary/JSON")

def assay_description(aid):
    return _get(f"{BASE}/assay/aid/{aid}/description/JSON")

def assays_for_target(target, max_results=100):
    data = _get(f"{BASE}/assay/target/{target}/aids/JSON")   # e.g. 'EGFR'
    return data.get('IdentifierList', {}).get('AID', [])[:max_results] if data else []

def active_cids_in_assay(aid, max_results=1000):
    data = _get(f"{BASE}/assay/aid/{aid}/cids/JSON?cids_type=active")
    return data.get('IdentifierList', {}).get('CID', [])[:max_results] if data else []

def compound_annotations(cid, section=None):               # PUG-View
    url = f"{PUG_VIEW}/data/compound/{cid}/JSON"
    if section:
        url += f"?heading={section}"                       # e.g. 'Safety and Hazards'
    return _get(url)
```

### Summarize activity outcomes for a compound

The `assaysummary` payload is a table: `Table.Columns.Column` names the columns,
`Table.Row[i].Cell` holds the values. Bucket by the `Activity Outcome` column.

```python
def summarize_bioactivities(cid):
    data = bioassay_summary(cid)
    counts = {'total': 0, 'active': 0, 'inactive': 0, 'inconclusive': 0, 'other': 0}
    if not data:
        return counts
    table = data.get('Table', {})
    cols = table.get('Columns', {}).get('Column', [])
    outcome_idx = cols.index('Activity Outcome') if 'Activity Outcome' in cols else None
    for row in table.get('Row', []):
        counts['total'] += 1
        if outcome_idx is None:
            continue
        outcome = str(row.get('Cell', [])[outcome_idx]).lower()
        if 'active' in outcome and 'inactive' not in outcome:
            counts['active'] += 1
        elif 'inactive' in outcome:
            counts['inactive'] += 1
        elif 'inconclusive' in outcome:
            counts['inconclusive'] += 1
        else:
            counts['other'] += 1
    return counts
```

### Find compounds active against a target

```python
def compounds_for_target(target, max_compounds=100):
    seen, out = set(), []
    for aid in assays_for_target(target, max_results=10)[:5]:
        for cid in active_cids_in_assay(aid, max_results=max_compounds):
            if cid not in seen:
                seen.add(cid)
                out.append({'cid': cid, 'aid': aid, 'target': target})
            if len(out) >= max_compounds:
                return out
    return out
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Compound not found | Try a synonym or the CID; check name spelling/format. |
| Empty property value (`None`) | Not all properties exist for all compounds; guard before use. |
| Similarity/substructure "hangs" | Async job (15-30 s); lower `MaxRecords`; PubChemPy polls for you. |
| HTTP 503 / `ServerBusy` | Rate limit — add delays, exponential backoff, reuse CIDs. |
| `PUGREST.BadRequest` on a property | Property name drift; check the live PUG-REST property table. |
| Timeout on large batch | Chunk the input; add per-request delay; prefer CIDs over names. |
