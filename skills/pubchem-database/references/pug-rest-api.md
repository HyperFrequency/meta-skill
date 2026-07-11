# PUG-REST API Reference

The raw HTTP interface behind PubChemPy. Use it directly for endpoints
PubChemPy does not wrap (bioassay summaries, target search, PUG-View), or when
you want fine control over the async structure-search protocol.

## Database structure

PubChem has three linked sub-databases, each with its own identifier:

- **Compound** — validated unique structures with computed properties. ID = **CID**.
- **Substance** — raw depositor records. ID = **SID**.
- **BioAssay** — biological activity test results. ID = **AID**.

## URL grammar

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/<input>/<operation>/<output>
```

- `<input>`   — e.g. `compound/cid/2244`, `compound/name/aspirin`,
  `compound/smiles/<smiles>`, `assay/aid/1000`.
- `<operation>` — optional: `property/<list>`, `synonyms`, `cids`, `sids`,
  `assaysummary`, `classification`, `description`, `record`.
- `<output>`  — `JSON`, `XML`, `CSV`, `TXT`, `PNG`, `SDF`, `ASNT`.

### Retrieve by identifier

```
GET /rest/pug/compound/cid/{cid}/property/{properties}/JSON
GET /rest/pug/compound/name/{name}/property/{properties}/JSON
GET /rest/pug/compound/smiles/{smiles}/property/{properties}/JSON
GET /rest/pug/compound/inchikey/{inchikey}/cids/JSON
```

Long or special-character inputs (SMILES/InChI with `#`, `/`, `+`) should be
sent by **POST** in the request body rather than URL-encoded in the path.

## Computed properties

Request several at once, comma-separated:
`/property/MolecularFormula,MolecularWeight,XLogP/JSON`

Commonly available: `MolecularFormula`, `MolecularWeight`, `ExactMass`,
`MonoisotopicMass`, `SMILES`, `ConnectivitySMILES`, `InChI`, `InChIKey`,
`IUPACName`, `XLogP`, `TPSA`, `Complexity`, `Charge`, `HBondDonorCount`,
`HBondAcceptorCount`, `RotatableBondCount`, `HeavyAtomCount`, `IsotopeAtomCount`,
`AtomStereoCount`, `BondStereoCount`, `CovalentUnitCount`, `Volume3D`,
`FeatureCount3D`.

> Property names have changed over time. PubChem superseded the older
> `CanonicalSMILES` / `IsomericSMILES` property names; current output uses
> `SMILES` / `ConnectivitySMILES`. If a `property/...` request returns
> `PUGREST.BadRequest` naming an unknown property, consult the live property
> table at https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest — do not assume a
> fixed name across PubChemPy versions.

## Structure searches (asynchronous)

Similarity, substructure, and superstructure searches run as server-side jobs.

```
POST /rest/pug/compound/similarity/smiles/{smiles}/cids/JSON      (param: Threshold, default 90)
POST /rest/pug/compound/substructure/smiles/{smiles}/cids/JSON
POST /rest/pug/compound/superstructure/smiles/{smiles}/cids/JSON
```

### The ListKey polling pattern

```python
import requests, time

# 1. Submit — returns a ListKey while the job runs
sub = requests.post(
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/similarity/smiles/"
    f"{smiles}/cids/JSON", data={"Threshold": 90})
listkey = sub.json()["Waiting"]["ListKey"]

# 2. Poll the ListKey URL until the job finishes (still-running -> "Waiting")
poll_url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/listkey/"
            f"{listkey}/cids/JSON")
for _ in range(30):
    time.sleep(2)
    res = requests.get(poll_url).json()
    if "Waiting" not in res:
        cids = res["IdentifierList"]["CID"]
        break
```

PubChemPy performs this loop for you when you pass `searchtype=`; only handle it
manually if you need custom timeouts or progress reporting.

## Images and downloads

```
GET /rest/pug/compound/cid/{cid}/PNG          (param: image_size=small|large)
GET /rest/pug/compound/cid/{cid}/SDF
GET /rest/pug/compound/cid/{cid}/record/SDF   (3D record variant)
```

## Bioassay endpoints

```
GET /rest/pug/compound/cid/{cid}/assaysummary/JSON
GET /rest/pug/assay/aid/{aid}/description/JSON
GET /rest/pug/assay/aid/{aid}/cids/JSON?cids_type=active
GET /rest/pug/assay/target/{target_name}/aids/JSON
```

## PUG-View (full annotations)

```
GET /rest/pug_view/data/compound/{cid}/JSON
GET /rest/pug_view/data/compound/{cid}/JSON?heading={section}
```

Section headings include: `Chemical and Physical Properties`,
`Drug and Medication Information`, `Pharmacology and Biochemistry`,
`Safety and Hazards`, `Toxicity`, `Literature`, `Patents`,
`Biomolecular Interactions and Pathways`. Spaces in headings must be
URL-encoded.

## Rate limits and etiquette

- **5 requests/sec**, **400 requests/min**, **300 s compute/min** per IP.
- Exceeding limits returns HTTP 503 with a `PUGREST.ServerBusy` code — back off
  (exponential) and retry.
- Prefer CIDs for repeat lookups (cheapest resolution path).
- Batch multiple CIDs into one request where the endpoint allows it.
- For whole-database work, use the FTP bulk files instead of REST.

## Official documentation

- PUG-REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- PUG-REST tutorial: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial
- PUG-View: https://pubchem.ncbi.nlm.nih.gov/docs/pug-view
