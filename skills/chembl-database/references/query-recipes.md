# ChEMBL Query Recipes

Reusable helper functions and end-to-end workflows for the
`chembl_webresource_client`. All snippets assume:

```python
from chembl_webresource_client.new_client import new_client
```

## Helper functions

```python
def molecule_by_id(chembl_id):
    """Full record for one compound, e.g. 'CHEMBL25'."""
    return new_client.molecule.get(chembl_id)


def molecules_by_name(pattern):
    """Compounds whose preferred name contains `pattern` (case-insensitive)."""
    return list(new_client.molecule.filter(pref_name__icontains=pattern))


def molecules_by_properties(max_mw=500, min_logp=None, max_logp=None):
    """Drug-likeness filter over molecule_properties."""
    criteria = {'molecule_properties__mw_freebase__lte': max_mw}
    if min_logp is not None:
        criteria['molecule_properties__alogp__gte'] = min_logp
    if max_logp is not None:
        criteria['molecule_properties__alogp__lte'] = max_logp
    return list(new_client.molecule.filter(**criteria))


def targets_by_name(name):
    """Single-protein targets matching a name/keyword, e.g. 'EGFR', 'kinase'."""
    return list(new_client.target.filter(
        target_type='SINGLE PROTEIN', pref_name__icontains=name))


def clean_bioactivity(target_chembl_id, activity_type='IC50', max_value=100):
    """
    Clean dose-response rows for a target: exact (uncensored) values, in nM,
    below a potency cutoff, with only the fields you usually model on.
    """
    return list(new_client.activity.filter(
        target_chembl_id=target_chembl_id,
        standard_type=activity_type,
        standard_relation='=',
        standard_units='nM',
        standard_value__lte=max_value,
    ).only(['molecule_chembl_id', 'standard_value',
            'standard_units', 'pchembl_value']))


def similar_compounds(smiles, threshold=85):
    """Fingerprint-similarity search; `threshold` is a percentage (40-100)."""
    return list(new_client.similarity.filter(smiles=smiles, similarity=threshold))


def substructure(smiles):
    """Compounds containing the given SMILES substructure."""
    return list(new_client.substructure.filter(smiles=smiles))


def drug_profile(molecule_chembl_id):
    """Approved-drug record plus its mechanisms and indications."""
    try:
        info = new_client.drug.get(molecule_chembl_id)
    except Exception:
        info = None
    mechanisms  = list(new_client.mechanism.filter(
        molecule_chembl_id=molecule_chembl_id))
    indications = list(new_client.drug_indication.filter(
        molecule_chembl_id=molecule_chembl_id))
    return info, mechanisms, indications
```

## Workflow 1 — Target to inhibitors

```python
targets = targets_by_name('EGFR')
target_id = targets[0]['target_chembl_id']

activities = clean_bioactivity(target_id, 'IC50', max_value=100)
compound_ids = sorted({a['molecule_chembl_id'] for a in activities})
compounds = [new_client.molecule.get(cid) for cid in compound_ids[:50]]
```

Resolve the target first, then query `activity` by `target_chembl_id`. Dedupe
compound IDs before fetching full molecule records to avoid redundant calls.

## Workflow 2 — Profile a known drug

```python
info, mechanisms, indications = drug_profile('CHEMBL25')
all_activity = list(new_client.activity.filter(
    molecule_chembl_id='CHEMBL25', pchembl_value__isnull=False))
```

`mechanism.action_type` (INHIBITOR, AGONIST, …) and its `target_chembl_id` tell
you what the drug hits; `drug_indication.max_phase_for_ind` gives clinical stage.

## Workflow 3 — Structure-activity relationship (SAR)

```python
analogs = similar_compounds('CC(=O)Oc1ccccc1C(=O)O', threshold=80)

rows = []
for analog in analogs:
    cid = analog['molecule_chembl_id']
    for act in new_client.activity.filter(
            molecule_chembl_id=cid, pchembl_value__isnull=False):
        rows.append({
            'molecule_chembl_id': cid,
            'target_chembl_id':   act['target_chembl_id'],
            'standard_type':      act['standard_type'],
            'pchembl_value':      act['pchembl_value'],
        })
```

Pair the collected `pchembl_value`s with molecular properties from the analog
records to relate structure to potency.

## Workflow 4 — Mine kinase inhibitors

```python
kinases = new_client.target.filter(
    target_type='SINGLE PROTEIN', pref_name__icontains='kinase')
target_ids = [t['target_chembl_id'] for t in kinases[:10]]  # bound the fan-out

hits = new_client.activity.filter(
    target_chembl_id__in=target_ids,
    standard_type='IC50',
    standard_relation='=',
    standard_units='nM',
    standard_value__lte=50,
)
```

`kinase` is a broad keyword — always cap the target list before an `__in` query so
you don't pull an unbounded activity set.

## Workflow 5 — Virtual screening by properties

```python
candidates = new_client.molecule.filter(
    molecule_properties__mw_freebase__range=[300, 500],
    molecule_properties__alogp__lte=5,
    molecule_properties__hba__lte=10,
    molecule_properties__hbd__lte=5,
    molecule_properties__num_ro5_violations=0,
).only(['molecule_chembl_id', 'pref_name', 'molecule_properties'])
```

## Export to pandas

```python
import pandas as pd

df = pd.DataFrame(clean_bioactivity('CHEMBL203'))
print(df['standard_value'].describe())
print(df.groupby('standard_type').size())
```

Wrap `list(...)` result sets directly in a `DataFrame`. Filter with
`data_validity_comment` null and `potential_duplicate == 0` before any
statistics to keep dirty rows out of your models.
