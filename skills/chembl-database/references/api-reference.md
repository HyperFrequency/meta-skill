# ChEMBL Web Services — API Reference

Deep reference for the `chembl_webresource_client` Python client. The client
wraps the ChEMBL REST API (`https://www.ebi.ac.uk/chembl/api/data/`) with lazy,
Django-style query objects.

## Endpoints

Access each as an attribute of `new_client`. All expose `.get(id)` and
`.filter(**criteria)`.

| Endpoint                     | Contents                                             |
| ---------------------------- | ---------------------------------------------------- |
| `molecule`                   | Compound structures, properties, synonyms            |
| `molecule_form`              | Parent/salt/child form relationships                 |
| `target`                     | Protein and non-protein biological targets           |
| `target_component`           | Sequence/component details of a target               |
| `activity`                   | Individual bioassay measurement results              |
| `assay`                      | Experimental assay descriptions and confidence       |
| `drug`                       | Approved-drug records                                |
| `drug_indication`            | Disease indications + max phase per drug             |
| `mechanism`                  | Drug mechanism of action (action_type, target)       |
| `document`                   | Source literature / patents                          |
| `cell_line`                  | Cell-line metadata                                   |
| `tissue`                     | Tissue types                                         |
| `protein_class`             | Protein classification hierarchy                     |
| `compound_structural_alert`  | Structural (tox) alerts on a compound                |
| `similarity`                 | Fingerprint similarity search (query: `smiles`)      |
| `substructure`               | Substructure search (query: `smiles`)                |
| `image`                      | SVG/PNG depiction of a structure                     |

ChEMBL exposes 30+ endpoints total; the above are the ones you reach for most.

## Query methods

- `.get(chembl_id)` — single record as a dict. Raises on a missing ID.
- `.filter(**criteria)` — lazy result set; criteria AND together.
- `.only([fields])` — restrict returned fields; big payload savings on large sets.
- `.order_by('field')` / `.order_by('-field')` — server-side sort.
- `.set_format('json' | 'xml' | 'yaml')` — response format (JSON default).
- Result sets support `len()`, slicing (`qs[:100]`), and iteration; each
  triggers network I/O and transparent pagination.

## Filter operators

Django-style suffixes, appended to any (possibly nested) field:

| Operator                          | Meaning                       |
| --------------------------------- | ----------------------------- |
| `__exact` / `__iexact`            | Exact / case-insensitive match |
| `__contains` / `__icontains`      | Substring / case-insensitive   |
| `__startswith` / `__endswith`     | Prefix / suffix                |
| `__gt` `__gte` `__lt` `__lte`     | Numeric comparisons            |
| `__range`                         | Value in `[low, high]`         |
| `__in`                            | Value in a list                |
| `__isnull`                        | `True`/`False` null test       |
| `__regex`                         | Regular-expression match       |
| `__search`                        | Full-text search               |

Nested access uses the double-underscore path, e.g.
`molecule_properties__mw_freebase__lte=300` or
`target_components__accession='P00533'`.

## Molecular property fields (`molecule_properties__*`)

| Field                  | Meaning                                   |
| ---------------------- | ----------------------------------------- |
| `mw_freebase`          | Molecular weight of the free base         |
| `full_mwt`             | Full molecular weight (incl. salt)        |
| `alogp`                | Calculated LogP                           |
| `hba`                  | H-bond acceptors                          |
| `hbd`                  | H-bond donors                             |
| `psa`                  | Polar surface area                        |
| `rtb`                  | Rotatable bonds                           |
| `aromatic_rings`       | Aromatic ring count                       |
| `num_ro5_violations`   | Lipinski Rule-of-5 violations             |
| `ro3_pass`             | Rule-of-3 (fragment) compliance (Y/N)     |
| `cx_most_apka`         | Most acidic pKa                           |
| `cx_most_bpka`         | Most basic pKa                            |
| `molecular_species`    | ACID / BASE / NEUTRAL / ZWITTERION        |
| `qed_weighted`         | QED drug-likeness score                   |

Structure fields live under `molecule_structures__*`, e.g.
`canonical_smiles`, `standard_inchi`, `standard_inchi_key`.

## Bioactivity fields (`activity`)

| Field                    | Meaning                                          |
| ------------------------ | ------------------------------------------------ |
| `standard_type`          | Normalized measurement type (IC50, Ki, Kd, EC50) |
| `standard_value`         | Normalized numeric value                         |
| `standard_units`         | Normalized units (nM, uM, %)                     |
| `standard_relation`      | `'='`, `'>'`, `'<'`, `'>='`, `'<='` (censoring)  |
| `pchembl_value`          | -log10(molar) normalized potency                 |
| `activity_comment`       | Free-text annotation                             |
| `data_validity_comment`  | Curation flag (non-null ⇒ suspect row)           |
| `potential_duplicate`    | Duplicate flag                                    |
| `assay_chembl_id`        | Source assay                                      |
| `target_chembl_id`       | Target                                            |
| `molecule_chembl_id`     | Compound                                          |

Prefer the `standard_*` fields over the raw `type`/`value`/`units`, which are not
harmonized across source documents.

## Target fields (`target`)

| Field                | Meaning                                     |
| -------------------- | ------------------------------------------- |
| `target_chembl_id`   | Target identifier                           |
| `pref_name`          | Preferred name                              |
| `target_type`        | `SINGLE PROTEIN`, `ORGANISM`, `CELL-LINE`…  |
| `organism`           | Source organism                             |
| `tax_id`             | NCBI taxonomy ID                            |
| `target_components`  | Component list (UniProt accessions, etc.)   |

## Configuration (`Settings`)

```python
from chembl_webresource_client.settings import Settings
s = Settings.Instance()
s.CACHING       = True     # local response cache (default on)
s.CACHE_EXPIRE  = 86400    # cache TTL in seconds (default 24h)
s.TIMEOUT       = 30       # per-request timeout (s)
s.TOTAL_RETRIES = 3        # automatic retry count on failure
```

Disabling the cache (`s.CACHING = False`) forces every query to hit the network —
use only when freshness is critical, since it also raises rate-limit pressure.

## Image endpoint

```python
svg = new_client.image.get('CHEMBL25')   # SVG depiction of the structure
```

## Response formats

JSON (default), XML, and YAML via `.set_format(...)`. JSON is recommended for
Python consumption.

## Error handling and rate limits

- `404` — resource not found (bad ChEMBL ID).
- `503` — service temporarily unavailable; the client retries per `TOTAL_RETRIES`.
- Timeouts are governed by `TIMEOUT`.
- EBI enforces fair-use: cache aggressively, avoid tight request loops, and use
  the downloadable ChEMBL SQL dump for bulk work.

## Official resources

- REST API docs: https://www.ebi.ac.uk/chembl/api/data/docs
- Python client: https://github.com/chembl/chembl_webresource_client
- Interface documentation: https://chembl.gitbook.io/chembl-interface-documentation/
- Example notebooks: https://github.com/chembl/notebooks
- Downloads (SQL dumps): https://www.ebi.ac.uk/chembl/downloads
