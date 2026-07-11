---
name: chembl-database
version: 0.1.0
description: >-
  Query ChEMBL, the EBI-curated database of bioactive molecules (2M+ compounds,
  ~20M bioactivity measurements, 15k+ drug targets, approved-drug data), through
  the official chembl_webresource_client Python client. Use to find
  inhibitors/ligands for a target, pull IC50/Ki/EC50/pChEMBL bioactivity for QSAR
  or ML datasets, run SAR over analogs, filter compounds by drug-likeness (MW,
  LogP, HBA/HBD, Lipinski), look up a drug's mechanism and indications, or run
  SMILES similarity/substructure searches. Not for local descriptor/fingerprint
  computation (use datamol or deepchem), docking (molecular-docking), de-novo
  generation (denovo-design), ADMET model predictions (admet-prediction), or
  other databases like PubChem/UniProt/PDB (use database-lookup and their
  dedicated skills); for whole-database analytics, download the ChEMBL SQL dump
  rather than hammering the REST API.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Apache-2.0 (chembl_webresource_client); ChEMBL data is CC BY-SA 3.0
---

# ChEMBL Database

## Overview

ChEMBL is a manually curated database of bioactive molecules with drug-like
properties, maintained by the European Bioinformatics Institute (EBI). It holds
over 2 million distinct compounds, ~20 million bioactivity measurements, 15,000+
biological targets, and curated data on approved drugs and clinical candidates.

Drive it programmatically through the official `chembl_webresource_client`
Python package. The client is a thin, **lazily evaluated** wrapper over the
ChEMBL REST API: you build Django-style query objects that only hit the network
when you iterate, slice, or `len()` them. This skill covers compound/target/
activity retrieval, drug-likeness filtering, drug/mechanism/indication lookup,
and structure (similarity + substructure) searches.

## When to Use This Skill

- **Find binders for a target**: inhibitors, agonists, or antagonists of a named
  protein, pulled with a potency cutoff.
- **Build a bioactivity dataset**: gather IC50/Ki/Kd/EC50/`pchembl_value` records
  for a target or compound set to feed QSAR or ML models.
- **SAR studies**: collect analogs of a lead compound and their activities.
- **Drug-likeness filtering**: slice compound space by MW, LogP, HBA/HBD, PSA,
  rotatable bonds, or Lipinski Rule-of-5 violations.
- **Drug intelligence**: look up an approved drug's mechanism of action,
  indications, and max clinical phase.
- **Structure search**: SMILES similarity or substructure queries.

## When NOT to Use This Skill

- **Local descriptor / fingerprint computation** — compute in-process with
  `datamol`, `deepchem`, or `molfeat`; don't round-trip to the API for cheminfo.
- **Docking / pose prediction** — use `molecular-docking`.
- **De-novo molecule generation** — use `denovo-design` or `drug-design`.
- **ADMET model predictions** — use `admet-prediction`; ChEMBL stores measured
  bioactivity, not predicted ADMET.
- **Other databases** (PubChem, UniProt, PDB, DrugBank) — use `database-lookup`,
  `bioservices`, or their dedicated `*-database` skills.
- **Whole-database analytics / joins over millions of rows** — download the
  ChEMBL SQLite or PostgreSQL dump and query locally; the REST API is for
  targeted lookups, not bulk scans.

## Setup

```bash
uv pip install chembl_webresource_client   # add pandas for tabular analysis
```

```python
from chembl_webresource_client.new_client import new_client

molecule = new_client.molecule   # each attribute is a queryable endpoint
target   = new_client.target
activity = new_client.activity
```

Every endpoint exposes two entry points: `.get(chembl_id)` for a single record
and `.filter(**criteria)` for a lazy result set.

## Core Capabilities

Concise, canonical examples below. Full endpoint list, all filterable fields,
and configuration knobs live in
[references/api-reference.md](references/api-reference.md). Reusable helper
functions and multi-step workflows live in
[references/query-recipes.md](references/query-recipes.md).

### Retrieve a compound

```python
aspirin = new_client.molecule.get('CHEMBL25')          # by ChEMBL ID
hits    = new_client.molecule.filter(pref_name__icontains='aspirin')
```

### Filter by drug-likeness

```python
leads = new_client.molecule.filter(
    molecule_properties__mw_freebase__range=[300, 500],
    molecule_properties__alogp__lte=5,
    molecule_properties__hbd__lte=5,
    molecule_properties__num_ro5_violations=0,
)
```

### Bioactivity for a target

```python
potent = new_client.activity.filter(
    target_chembl_id='CHEMBL203',   # EGFR
    standard_type='IC50',
    standard_relation='=',          # keep exact values, drop censored '>' / '<'
    standard_units='nM',
    standard_value__lte=100,
).only(['molecule_chembl_id', 'standard_value', 'pchembl_value'])
```

`.only([...])` restricts returned fields and sharply cuts payload size on large
result sets — prefer it whenever you don't need the full record.

### Structure search

```python
similar = new_client.similarity.filter(
    smiles='CC(=O)Oc1ccccc1C(=O)O', similarity=85)   # similarity is % (40-100)
sub     = new_client.substructure.filter(smiles='c1ccccc1')
```

### Drug, mechanism, indication

```python
drug_info   = new_client.drug.get('CHEMBL25')
mechanisms  = new_client.mechanism.filter(molecule_chembl_id='CHEMBL25')
indications = new_client.drug_indication.filter(molecule_chembl_id='CHEMBL25')
```

## Filter Operators

Django-style suffixes on any field: `__exact`, `__iexact`, `__icontains`,
`__startswith`, `__endswith`, `__gt`/`__gte`/`__lt`/`__lte`, `__range`, `__in`,
`__isnull`, `__regex`. Chain multiple criteria in one `.filter(...)` call (they
AND together) and reach into nested objects with the double-underscore path,
e.g. `molecule_properties__mw_freebase__lte`. See
[references/api-reference.md](references/api-reference.md) for the full field
catalogue.

## Data Hygiene and Gotchas

Bioactivity data is heterogeneous and merged from many papers — filter defensively:

- **Standardize on `standard_type` / `standard_units` / `standard_value`**, not
  the raw `type`/`value` fields, which are un-normalized across sources.
- **Check `standard_relation`**: a row with relation `'>'` or `'<'` is a censored
  (out-of-range) measurement, not an equality. Filter to `'='` for clean modeling.
- **Prefer `pchembl_value`** (= -log10 of molar potency) for cross-assay
  comparison; it is null for non-dose-response endpoints.
- **Drop dirty rows**: skip records where `data_validity_comment` is non-null and
  deduplicate on `potential_duplicate`.
- **Lazy + paginated**: nothing executes until you iterate. Iterating a large
  `.filter()` transparently pages the API — bound it with slicing (`[:1000]`) or
  a tight filter to avoid pulling tens of thousands of rows.
- **Caching**: the client caches responses ~24h on local disk. Tune or disable
  via `Settings.Instance()` (see references) when data freshness matters.
- **Rate limits**: respect EBI fair-use — lean on the cache, avoid tight request
  loops, and use the SQL dump for large jobs.
- **Licensing**: ChEMBL *data* is CC BY-SA 3.0 (attribute and share-alike); the
  `chembl_webresource_client` code is Apache-2.0.

## References

- [references/api-reference.md](references/api-reference.md) — endpoint
  catalogue, full filter operators, molecular-property / bioactivity / target
  field lists, client configuration (`Settings`), response formats, image
  endpoint, error handling.
- [references/query-recipes.md](references/query-recipes.md) — reusable helper
  functions and end-to-end workflows: target → inhibitors, drug profiling, SAR,
  kinase-inhibitor mining, virtual screening, and pandas export.
