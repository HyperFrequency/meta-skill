# Metabolomics Workbench REST API — Reference

Deep reference for the seven contexts, the two positional grammars
(`metstat`, `moverz`), response handling, and worked recipes. The router lives
in `../SKILL.md`; this file is the lookup table.

## Base URL and grammar

```
https://www.metabolomicsworkbench.org/rest/
```

Standard path grammar (contexts `compound`, `study`, `refmet`, `gene`,
`protein`):

```
/<context>/<input_item>/<input_value>/<output_item>/<format>
```

- `format` is `json` (default when omitted) or `txt` (tab-delimited).
- URL-encode values containing spaces or slashes (`Fatty%20Acids`, `PC(34:1)`).
- `moverz` and `metstat` do **not** follow this grammar — see their sections.

Interactive URL builder: https://www.metabolomicsworkbench.org/tools/mw_rest.php
Official spec (v1.1 PDF): https://www.metabolomicsworkbench.org/tools/MWRestAPIv1.1.pdf

## Context: compound

Metabolite structure and identifier data; cross-referencing between databases.

### Input items

| input_item | Meaning | Example value |
| --- | --- | --- |
| `regno` | MW internal registry number | `11` |
| `pubchem_cid` | PubChem Compound ID | `5281365` |
| `inchi_key` | InChIKey | `WQZGKKKJIJFFOK-GASJEMHNSA-N` |
| `formula` | Molecular formula | `C6H12O6` |
| `lm_id` | LIPID MAPS ID | `LMFA01010001` |
| `hmdb_id` | Human Metabolome Database ID | `HMDB0000122` |
| `kegg_id` | KEGG Compound ID | `C00031` |
| `chebi_id` | ChEBI ID | `17234` |

### Output items

`all`, `classification`, `regno`, `formula`, `exactmass`, `inchi_key`, `name`,
`sys_name`, `smiles`, `lm_id`, `pubchem_cid`, `hmdb_id`, `kegg_id`, `chebi_id`,
`metacyc_id`, `molfile`, `png`.

- `png` returns image **bytes**; `molfile` returns MOL **text**. Do not call
  `.json()` on these.

```bash
curl "https://www.metabolomicsworkbench.org/rest/compound/pubchem_cid/5281365/all/json"
curl "https://www.metabolomicsworkbench.org/rest/compound/regno/11/name/json"
curl "https://www.metabolomicsworkbench.org/rest/compound/kegg_id/C00031/all/json"
curl "https://www.metabolomicsworkbench.org/rest/compound/chebi_id/17234/all/json"
curl "https://www.metabolomicsworkbench.org/rest/compound/formula/C6H12O6/all/json"
curl "https://www.metabolomicsworkbench.org/rest/compound/regno/11/png" -o structure.png
```

## Context: study

Study metadata and experimental results.

### Input items

| input_item | Meaning | Example |
| --- | --- | --- |
| `study_id` | Study identifier | `ST000001` |
| `analysis_id` | Analysis identifier | `AN000001` |
| `study_title` | Keyword(s) in title | `diabetes` |
| `institute` | Institute name | `UCSD` |
| `last_name` | Investigator surname | `Smith` |
| `metabolite_id` | Metabolite registry number | `11` |
| `refmet_name` | RefMet standardized name | `Glucose` |
| `kegg_id` | KEGG compound ID | `C00031` |

### Output items

`summary`, `factors`, `analysis`, `metabolites`, `data`, `mwtab`,
`number_of_metabolites`, `species`, `disease`, `source`, `untarg_studies`,
`untarg_factors`, `untarg_data`, `datatable`, `available`.

- To list all public studies, use input `study_id/ST` with output `available`.
- `mwtab` is the full study record (mwTab format); request it as `txt` for the
  canonical flat file.

```bash
# List all public studies
curl "https://www.metabolomicsworkbench.org/rest/study/study_id/ST/available/json"
# Metadata and data
curl "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/summary/json"
curl "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/factors/json"
curl "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/data/json"
# Search
curl "https://www.metabolomicsworkbench.org/rest/study/refmet_name/Tyrosine/summary/json"
curl "https://www.metabolomicsworkbench.org/rest/study/last_name/Smith/summary/json"
# Full study in mwTab
curl "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/mwtab/txt"
```

## Context: refmet

Standardized nomenclature with a four-level classification hierarchy.

### Input items

| input_item | Meaning | Example |
| --- | --- | --- |
| `match` | Fuzzy-match a common name → standardized name | `citrate` |
| `name` | Exact RefMet name | `Glucose` |
| `inchi_key` | InChIKey | `WQZGKKKJIJFFOK-GASJEMHNSA-N` |
| `pubchem_cid` | PubChem CID | `5793` |
| `exactmass` | Exact mass | `180.0634` |
| `formula` | Molecular formula | `C6H12O6` |
| `super_class` | Super class name | `Organic compounds` |
| `main_class` | Main class name | `Carbohydrates` |
| `sub_class` | Sub class name | `Monosaccharides` |
| `refmet_id` | RefMet identifier | `12345` |
| `all` | Retrieve entire RefMet table (no value) | — |

### Output items

`all`, `name`, `inchi_key`, `pubchem_cid`, `exactmass`, `formula`, `sys_name`,
`super_class`, `main_class`, `sub_class`, `refmet_id`.

### Classification hierarchy (broad → specific)

1. **Super Class** — e.g. `Organic compounds`, `Lipids`
2. **Main Class** — e.g. `Fatty Acids`, `Carbohydrates`
3. **Sub Class** — e.g. `Monosaccharides`, `Amino acids`
4. **Individual metabolite** — the standardized name

```bash
curl "https://www.metabolomicsworkbench.org/rest/refmet/match/citrate/name/json"
curl "https://www.metabolomicsworkbench.org/rest/refmet/name/Glucose/all/json"
curl "https://www.metabolomicsworkbench.org/rest/refmet/formula/C6H12O6/all/json"
curl "https://www.metabolomicsworkbench.org/rest/refmet/exactmass/180.0634/all/json"
curl "https://www.metabolomicsworkbench.org/rest/refmet/main_class/Fatty%20Acids/all/json"
curl "https://www.metabolomicsworkbench.org/rest/refmet/all/json"          # full table — cache it
```

## Context: metstat (positional filter)

Filter studies by analytical and biological parameters. Eight semicolon-delimited
positions; leave a position empty (consecutive `;`) to skip it; all optional.

```
/metstat/ANALYSIS;POLARITY;CHROMATOGRAPHY;SPECIES;SAMPLE_SOURCE;DISEASE;KEGG_ID;REFMET_NAME/<format>
```

| Position | Parameter | Example options |
| --- | --- | --- |
| 1 | Analysis type | `LCMS`, `GCMS`, `NMR`, `MS`, `ICPMS` |
| 2 | Polarity | `POSITIVE`, `NEGATIVE` |
| 3 | Chromatography | `HILIC`, `RP` (reverse phase), `GC`, `IC` |
| 4 | Species | `Human`, `Mouse`, `Rat`, ... |
| 5 | Sample source | `Blood`, `Plasma`, `Serum`, `Urine`, `Liver`, ... |
| 6 | Disease | `Diabetes`, `Cancer`, `Alzheimer`, ... |
| 7 | KEGG ID | `C00031`, ... |
| 8 | RefMet name | `Glucose`, `Tyrosine`, ... |

```bash
curl "https://www.metabolomicsworkbench.org/rest/metstat/LCMS;POSITIVE;HILIC;Human;Blood;Diabetes/json"
curl "https://www.metabolomicsworkbench.org/rest/metstat/;;;Human;Blood;;;Tyrosine/json"
curl "https://www.metabolomicsworkbench.org/rest/metstat/GCMS;;;;;;/json"
curl "https://www.metabolomicsworkbench.org/rest/metstat/;;;Mouse;Liver;;/json"
curl "https://www.metabolomicsworkbench.org/rest/metstat/;;;;;;;Glucose/json"
```

## Context: moverz (m/z search)

Two positional grammars — a database search and an exact-mass calculation.

### Precursor m/z search

```
/moverz/DATABASE/mass/adduct/tolerance/<format>
```

- `DATABASE` — `MB` (Metabolomics Workbench), `LIPIDS`, `REFMET`
- `mass` — observed m/z (e.g. `635.52`)
- `adduct` — ion adduct (tables below)
- `tolerance` — mass window in Daltons (`0.5` low-res, `0.01` high-res)

### Exact-mass calculation for a known metabolite

```
/moverz/exactmass/metabolite_name/adduct/<format>
```

### Ion adducts

Positive mode:

| Adduct | Meaning | Typical use |
| --- | --- | --- |
| `M+H` | Protonated | Default positive ESI |
| `M+Na` | Sodium | Common in ESI |
| `M+K` | Potassium | Less common |
| `M+NH4` | Ammonium | Ammonium-salt buffers |
| `M+2H` | Doubly protonated | Multiply charged |
| `M+H-H2O` | Protonated, water loss | In-source dehydration |
| `M+2Na-H` | Disodium minus H | Multiple sodium |
| `M+CH3OH+H` | Methanol adduct | MeOH mobile phase |
| `M+ACN+H` | Acetonitrile adduct | ACN mobile phase |
| `M+ACN+Na` | ACN + sodium | ACN + Na |

Negative mode:

| Adduct | Meaning | Typical use |
| --- | --- | --- |
| `M-H` | Deprotonated | Default negative ESI |
| `M+Cl` | Chloride | Chlorinated phases |
| `M+FA-H` | Formate | Formic-acid phase |
| `M+HAc-H` | Acetate | Acetic-acid phase |
| `M-H-H2O` | Deprotonated, water loss | In-source dehydration |
| `M-2H` | Doubly deprotonated | Multiply charged |
| `M+Na-2H` | Sodium minus two H | Mixed charge states |

Uncharged: `M` (neutral molecule; direct-ionization methods).

```bash
curl "https://www.metabolomicsworkbench.org/rest/moverz/MB/635.52/M+H/0.5/json"
curl "https://www.metabolomicsworkbench.org/rest/moverz/REFMET/200.15/M-H/0.3/json"
curl "https://www.metabolomicsworkbench.org/rest/moverz/LIPIDS/760.59/M+Na/0.5/json"
curl "https://www.metabolomicsworkbench.org/rest/moverz/exactmass/PC(34:1)/M+H/json"
curl "https://www.metabolomicsworkbench.org/rest/moverz/MB/180.0634/M+H/0.01/json"
```

## Context: gene

Metabolome Gene/Protein (MGP) gene records.

Input items: `mgp_id`, `gene_id` (NCBI), `gene_name`, `gene_symbol`, `taxid`
(e.g. `9606` = human).

Output items: `all`, `mgp_id`, `gene_id`, `gene_name`, `gene_symbol`,
`gene_synonyms`, `alt_names`, `chromosome`, `map_location`, `summary`, `taxid`,
`species`, `species_long`.

```bash
curl "https://www.metabolomicsworkbench.org/rest/gene/gene_symbol/ACACA/all/json"
curl "https://www.metabolomicsworkbench.org/rest/gene/gene_id/31/all/json"
curl "https://www.metabolomicsworkbench.org/rest/gene/gene_name/carboxylase/summary/json"
```

## Context: protein

MGP protein records and sequences.

Input items: `mgp_id`, `gene_id`, `gene_name`, `gene_symbol`, `taxid`,
`mrna_id`, `refseq_id`, `protein_gi`, `uniprot_id`, `protein_entry`,
`protein_name`.

Output items: `all`, `mgp_id`, `gene_id`, `gene_name`, `gene_symbol`, `taxid`,
`species`, `species_long`, `mrna_id`, `refseq_id`, `protein_gi`, `uniprot_id`,
`protein_entry`, `protein_name`, `seqlength`, `seq`, `is_identical_to`.

```bash
curl "https://www.metabolomicsworkbench.org/rest/protein/uniprot_id/Q13085/all/json"
curl "https://www.metabolomicsworkbench.org/rest/protein/gene_symbol/ACACA/all/json"
curl "https://www.metabolomicsworkbench.org/rest/protein/uniprot_id/Q13085/seq/json"
curl "https://www.metabolomicsworkbench.org/rest/protein/refseq_id/NP_001084/all/json"
```

MW mirrors identifiers only — for the authoritative protein sequence/structure,
follow the `uniprot_id` out to UniProt or the corresponding PDB entry.

## Output formats, errors, and rate limits

- **Formats.** `json` (machine-readable, default) or `txt` (tab-delimited).
- **HTTP status.** `200` success, `400` malformed request, `404` not found,
  `500` server error. **A no-match query usually returns an empty `[]`/`{}` with
  status 200** — test for emptiness, do not rely on `raise_for_status()` alone.
- **Rate limits.** No strict enforcement for reasonable use (as of the current
  API). Still: add small delays in bulk loops, cache large reference pulls
  (`/refmet/all`, `/study/.../available`), and keep batch sizes modest.

## Response-shape normalization

Multi-row endpoints frequently return a JSON **object keyed by row-number
strings** rather than a JSON array. Normalize before iterating:

```python
def rows(payload):
    """Yield records whether the API returned a list or a row-number-keyed dict."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        keys = list(payload.keys())
        if keys and all(k.isdigit() for k in keys):   # {"1": {...}, "2": {...}}
            return list(payload.values())
        return [payload]                                # single flat record
    return []
```

## Worked recipes

### 1. Metabolite → studies → data

```python
import requests
BASE = "https://www.metabolomicsworkbench.org/rest"

std = requests.get(f"{BASE}/refmet/match/citrate/name/json", timeout=30).json()
name = std["name"]                                     # standardized RefMet name
studies = rows(requests.get(f"{BASE}/study/refmet_name/{name}/summary/json").json())
sid = studies[0]["study_id"]
data = requests.get(f"{BASE}/study/study_id/{sid}/data/json", timeout=60).json()
```

### 2. m/z peak → candidate → structure image

```python
hits = rows(requests.get(f"{BASE}/moverz/MB/180.0634/M+H/0.01/json").json())
regno = hits[0]["regno"]
info = requests.get(f"{BASE}/compound/regno/{regno}/all/json").json()
png = requests.get(f"{BASE}/compound/regno/{regno}/png").content   # bytes
open("candidate.png", "wb").write(png)
```

### 3. Batch identifier resolution (with throttle + cache)

```python
import time, functools

@functools.lru_cache(maxsize=None)
def compound_by_cid(cid):
    time.sleep(0.2)                                    # be polite in bulk
    return requests.get(f"{BASE}/compound/pubchem_cid/{cid}/all/json").json()
```

### 4. Enumerate a RefMet class

```python
lipids = rows(requests.get(f"{BASE}/refmet/main_class/Fatty%20Acids/all/json").json())
```

## Client libraries and cross-references

- **Python** — `mwtab` (parse/validate mwTab files).
- **R / Bioconductor** — `metabolomicsWorkbenchR`.
- **Julia** — `MetabolomicsWorkbenchAPI.jl`.
- **Cheminformatics on returned MOL/SMILES** — `rdkit`, `datamol`.
- **Federated multi-database access** (KEGG, ChEBI, UniProt, ...) —
  `bioservices`.
- **Downstream pathway/flux modeling** — `cobrapy`.
- **Study literature references → citations** — `citation-management`.
