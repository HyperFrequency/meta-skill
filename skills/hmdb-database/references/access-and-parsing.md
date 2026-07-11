# HMDB Access, Parsing, and Workflows

HMDB exposes **no public REST API**. Everything programmatic runs through bulk
downloads or single-entry XML fetches. This reference covers the download
formats, a memory-safe parsing recipe, the R `hmdbQuery` path, cross-database ID
mapping, and step-by-step workflows.

## Bulk download formats

From `https://www.hmdb.ca/downloads`:

| Format | Contents | Use for |
| --- | --- | --- |
| XML | Complete metabolite / protein / spectra records, all fields | Comprehensive extraction; the authoritative source |
| SDF | Structures + a subset of properties | Cheminformatics via `rdkit` (fingerprints, substructure) |
| CSV/TSV | Flat tabular subset | Fast joins in `polars`/pandas, pipeline ingestion |
| FASTA | Protein and gene sequences | Sequence work |
| TXT | Raw spectral peak lists | Custom spectral matching |

Datasets are also split by specimen (e.g., serum, urine, CSF, saliva, feces,
sweat) and by spectra type (experimental NMR, predicted MS-MS, GC-MS…). Download
the specimen-specific set when you only need one biofluid — it is far smaller
than the full metabolite XML.

Rule of thumb: **download once and parse locally**. Do not fetch per-entry pages
in a loop for large jobs — it is slow, fragile, and discouraged by HMDB.

## Memory-safe XML parsing

The full metabolite XML is multi-GB uncompressed. A DOM load
(`ElementTree.parse`) will exhaust memory. Stream it with `iterparse` and clear
each element after processing:

```python
from lxml import etree

# HMDB elements are namespaced in some releases; strip or match with local-name.
def stream_metabolites(path):
    context = etree.iterparse(path, events=("end",), tag="metabolite")
    for _, elem in context:
        yield elem
        elem.clear()                       # free the parsed subtree
        while elem.getprevious() is not None:
            del elem.getparent()[0]        # drop already-processed siblings

def text(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None else None

for met in stream_metabolites("hmdb_metabolites.xml"):
    row = {
        "accession": text(met, "accession"),
        "name": text(met, "name"),
        "inchikey": text(met, "inchikey"),
        "formula": text(met, "chemical_formula"),
        "mono_mass": text(met, "monoisotopic_molecular_weight"),
    }
    # write row to your store here
```

Notes:
- Some HMDB releases wrap elements in an XML namespace. If `find("accession")`
  returns `None`, match on local name (e.g., an XPath like
  `.//*[local-name()='accession']`) or strip the namespace first.
- Nested repeats (pathways, diseases, concentrations, spectra) are child element
  lists — iterate them within each `<metabolite>` before `elem.clear()`.
- Validate/standardize SMILES and InChI with `rdkit` or `smiles-validation`
  after extraction; HMDB strings are generally clean but predicted entries vary.

## R / Bioconductor: single-entry queries

The `hmdbQuery` package retrieves and parses one metabolite's XML over HTTP —
good for tens of lookups, not bulk harvesting.

```r
BiocManager::install("hmdbQuery")
library(hmdbQuery)

entry <- HmdbEntry(prefix = "http://www.hmdb.ca/metabolites/",
                   id = "HMDB0000001")
store(entry)          # parsed named list of the entry's fields
```

`HmdbEntry()` fetches `https://www.hmdb.ca/metabolites/<id>.xml` and returns a
structured object; `store()` exposes the parsed fields. For many IDs, prefer the
bulk XML download over looping `HmdbEntry()`.

## Cross-database ID mapping

HMDB entries carry direct external IDs (`kegg_id`, `pubchem_compound_id`,
`chebi_id`, `drugbank_id`, `metlin_id`, …) — read them straight from the entry
when present.

When a direct link is missing, bridge on structure:
- Compute or read the **InChIKey** and match across databases (the skeleton —
  first 14 characters — matches stereochemistry-insensitive).
- Resolve InChIKey ↔ external IDs through UniChem or PubChem
  (`pubchem-database`), or bioactivity IDs via `chembl-database`.
- For drugs and toxins, join to `drugbank-database` / T3DB, which share HMDB's
  identifier scheme.

## Workflows

### Untargeted metabolite identification (LC-MS / GC-MS / NMR)
1. From your peak-picked features, take experimental m/z (with adduct), MS-MS
   fragments, or NMR shifts. Do the actual spectral processing in `matchms` /
   `pyopenms`.
2. Match against HMDB reference spectra (web spectral search, or local peak
   lists from the TXT/XML downloads).
3. Shortlist candidates within your mass tolerance (ppm) and formula.
4. Confirm with MS-MS fragmentation, retention behavior, and biofluid
   plausibility (does the candidate normally occur in that specimen?).
5. Cross-check pathway context for biological sanity.

### Biomarker discovery
1. Search HMDB for metabolites associated with the disease of interest.
2. Pull normal vs. abnormal concentrations for the relevant biofluid (units,
   age, sex).
3. Rank by differential abundance / effect size in your data.
4. Read pathway and enzyme context to reason about mechanism.
5. Follow `general_references` PubMed links for evidence.

### Pathway analysis
1. Resolve each metabolite to its HMDB accession.
2. Extract `pathways` (SMPDB/KEGG) and `protein_associations`.
3. Follow SMPDB IDs for pathway diagrams; aggregate to test pathway enrichment.

### Local reference table
1. Bulk-download the metabolite XML (or a specimen-specific CSV).
2. Stream-parse the fields you need (see the recipe above).
3. Key rows on `inchikey`; store external IDs for downstream joins.
4. Record the HMDB version so results are reproducible.

## Gotchas

- **Version drift**: accessions merge between releases; old IDs live on as
  `secondary_accessions`. Pin and report the HMDB version.
- **Predicted vs. experimental**: many properties, concentrations, and spectra
  are computationally predicted — check the flag before treating them as
  measured.
- **Completeness is uneven**: expect nulls for concentrations, disease links,
  and experimental spectra (see `data-fields.md` completeness tiers).
- **Licensing**: free for academic/non-commercial use; commercial use or
  redistribution needs explicit permission, and bulk use obligates citation.
