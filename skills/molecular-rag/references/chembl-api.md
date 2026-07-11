# ChEMBL Web Services

The ChEMBL REST endpoints this skill uses, plus params, response fields, and the
edge cases that bite in practice. Base URL:

```
https://www.ebi.ac.uk/chembl/api/data
```

All endpoints accept `?format=json`. ChEMBL is a free, shared public service (EBI)
— pace requests and back off on errors. Data is CC BY-SA 3.0.

## Similarity search

Find molecules structurally similar to a query SMILES above a Tanimoto threshold.

```
GET /similarity/{SMILES}/{threshold}.json?limit={n}
```

- `{SMILES}` — the query, **URL-encoded** (see caveat below).
- `{threshold}` — integer Tanimoto **percentage**, minimum **40**, max 100.
- `limit` — page size (default 20; ChEMBL caps a page at 1000, paginate beyond).

Response: `{"molecules": [ ... ], "page_meta": {...}}`. Useful fields per molecule:

| Field | Meaning |
|-------|---------|
| `molecule_chembl_id` | ChEMBL accession, e.g. `CHEMBL25` |
| `pref_name` | preferred/common name (often `null`) |
| `similarity` | server-side Tanimoto **as a string percentage** |
| `molecule_structures.canonical_smiles` | analog SMILES |
| `molecule_properties.full_mwt` | molecular weight |
| `molecule_properties.alogp` | calculated LogP |
| `molecule_properties.hba` / `.hbd` | H-bond acceptors / donors |
| `molecule_properties.psa` | polar surface area |

Prefer re-scoring Tanimoto locally with RDKit ECFP4 rather than trusting the
string `similarity` field, so rankings are consistent across queries.

### SMILES URL-encoding (the #1 gotcha)

SMILES contain characters that are structural in a URL path: `#` (triple bond),
`+` (charge), `/` and `\` (cis/trans), `[`, `]`. A naive f-string URL truncates or
misreads them. Two fixes:

- **Encode** the SMILES: `urllib.parse.quote(smiles, safe='')`.
- **POST** for long/complex SMILES: ChEMBL supports
  `POST /similarity` (and `/substructure`) with the SMILES in the request body,
  avoiding path-length and encoding limits entirely. Use POST for anything with
  charges, isotopes, or > ~100 chars.

### Substructure (alternative)

```
GET /substructure/{SMILES}/json
```

Exact substructure match rather than fuzzy similarity — use when you need every
compound containing a scaffold, not the nearest neighbors.

## Bioactivity

Measured activity records for a molecule.

```
GET /activity.json?molecule_chembl_id={CHEMBL_ID}&limit={n}
```

Response: `{"activities": [ ... ]}`. Useful fields per activity:

| Field | Meaning |
|-------|---------|
| `standard_type` | assay readout, e.g. `IC50`, `Ki`, `EC50`, `Potency` |
| `standard_value` | numeric value |
| `standard_units` | units, e.g. `nM` |
| `standard_relation` | `=`, `>`, `<` — **censored** values are not equalities |
| `pchembl_value` | −log10(molar) normalized potency (compare across assays) |
| `target_chembl_id` | target accession, e.g. `CHEMBL25` |
| `target_pref_name` | human-readable target |
| `assay_chembl_id` | source assay (context: species, conditions) |

Normalize before comparing: filter to one `standard_type` + `standard_units`, or
use `pchembl_value` directly. A `standard_relation` of `>` / `<` means the assay
only bounded the value — treat as a bound, not a point estimate.

### Target-specific activity

To restrict to activity against a given target, filter retrieved activities by
`target_chembl_id`, or query the activity endpoint with both filters:

```
GET /activity.json?molecule_chembl_id={CHEMBL_ID}&target_chembl_id={TARGET}
```

## Pagination

Large result sets page via `page_meta.next` (a relative URL) or explicit
`limit` / `offset`:

```
GET /activity.json?molecule_chembl_id=CHEMBL25&limit=1000&offset=1000
```

Follow `page_meta.next` until it is `null` for a complete set.

## Errors, rate limits, retries

- **HTTP 400** — usually a malformed/under-encoded SMILES or a threshold < 40.
- **HTTP 404** — no results (valid empty answer for a novel query), or a bad ID.
- **HTTP 429 / 5xx** — throttling or transient server error; retry with
  exponential backoff. Space batched activity lookups (~0.2 s between calls) and
  fetch activities only for the top-k analogs, not every hit.
- Set a real `timeout` on every request (30 s is reasonable) so a hung connection
  fails fast instead of stalling a batch.

## Alternative sources

Same fingerprint/Tanimoto retrieval logic ports to other stores; only the endpoint
changes:

- **PubChem PUG-REST** (`https://pubchem.ncbi.nlm.nih.gov/rest/pug`) —
  `.../compound/fastsimilarity_2d/smiles/{SMILES}/cids/JSON` for 2D similarity;
  broadest compound coverage, lighter on assay data than ChEMBL.
- **ZINC** — purchasable / make-on-demand space; good for novelty vs buyable
  chemistry and for expanding an analog set beyond assayed compounds.

For high-volume or client-managed access to any of these, use the `bioservices`
skill (typed ChEMBL/UniChem/PubChem clients) or `database-lookup` rather than
hand-rolling HTTP.
