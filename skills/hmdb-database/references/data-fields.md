# HMDB Metabolite Field Catalogue

Each HMDB 5.0 metabolite entry carries 130+ fields. Field names below use the
XML element / bulk-export naming you will encounter when parsing downloads.
Not every field is populated for every entry — see **Field Completeness** at the
end.

## Chemical fields

**Identification**
- `accession` — primary HMDB ID (e.g., `HMDB0000001`).
- `secondary_accessions` — prior IDs retained after entry merges.
- `name`, `synonyms` — primary name and alternative/common names.
- `chemical_formula` — molecular formula (e.g., `C6H12O6`).
- `average_molecular_weight`, `monoisotopic_molecular_weight` — in Daltons.

**Structure representations**
- `smiles` — SMILES string.
- `inchi`, `inchikey` — InChI and its hashed key (use the key for fast,
  structure-based joins and deduplication).
- `iupac_name`, `traditional_iupac` — systematic and traditional names.

**Predicted physicochemical properties**
- `state`, `charge`.
- `logp` — octanol–water partition coefficient (experimental or predicted).
- `pka_strongest_acidic`, `pka_strongest_basic`.
- `polar_surface_area` (TPSA), `refractivity`, `polarizability`.
- `rotatable_bond_count`, `acceptor_count`, `donor_count`.

**Chemical taxonomy (ClassyFire)**
- `kingdom`, `super_class`, `class`, `sub_class`.
- `direct_parent`, `alternative_parents`, `substituents`.
- `description` — free-text summary of the compound.

## Biological fields

**Origin and localization**
- `origin` — endogenous, exogenous, drug metabolite, or food component.
- `biofluid_locations` — blood, urine, saliva, CSF, feces, sweat, etc.
- `tissue_locations` — liver, kidney, brain, muscle, etc.
- `cellular_locations` — cytoplasm, mitochondria, membrane, etc.

**Biospecimen detection**
- `biospecimen`, `status` (detected / expected / predicted).
- `concentration`, `concentration_references`.

**Normal / abnormal concentrations** — per biofluid, each with value and range,
units (µM, mg/L, …), age and sex context, and clinical significance. Abnormal
concentrations carry the associated condition.

## Pathway and enzyme fields

- `pathways` — each with pathway `name`, `smpdb_id`, `kegg_map_id`, and category.
- `protein_associations` — enzymes/transporters with protein `name`, gene name,
  `uniprot_id`, `genbank_id`, protein type, reactions, and kinetics (Km).
- `reactions`, `reaction_enzymes`, `cofactors`, `inhibitors`.

## Disease and biomarker fields

- `diseases` — disease `name`, `omim_id`, category, references/evidence.
- `biomarker_status`, `biomarker_applications`, `biomarker_for`.

## Spectroscopic fields

**NMR** (`nmr_spectra`) — spectrum type (1D ¹H, ¹³C, 2D COSY/HSQC…), spectrometer
frequency (MHz), solvent, temperature, pH, peak list (shifts + multiplicities),
and FID files.

**Mass spectrometry** (`ms_spectra`) — type (MS, MS-MS, LC-MS, GC-MS), ionization
mode, collision energy, instrument, peak list (m/z, intensity, annotation), and a
predicted-vs-experimental flag.

**Chromatography** (`chromatography`) — retention time, column, mobile phase,
method details.

## External cross-references

- Small molecules: `kegg_id`, `pubchem_compound_id`, `pubchem_substance_id`,
  `chebi_id`, `chemspider_id`, `drugbank_id`, `foodb_id`, `knapsack_id`,
  `metacyc_id`, `bigg_id`, `wikipedia_id`, `metlin_id`, `vmh_id`, `fbonto_id`.
- Proteins: `uniprot_id`, `genbank_id`, `pdb_id`.

## Literature, ontology, provenance

- `general_references` (PubMed ID + citation), `synthesis_reference`,
  `protein_references`, `pathway_references`.
- `ontology_terms` — term name, source ontology (ChEBI, MeSH…), ID, definition.
- `creation_date`, `update_date`, `version`, `status`, `evidence`.

## XML entry shape

Bulk XML entries follow this nested pattern (abridged):

```xml
<metabolite>
  <accession>HMDB0000001</accession>
  <name>1-Methylhistidine</name>
  <chemical_formula>C7H11N3O2</chemical_formula>
  <average_molecular_weight>169.1811</average_molecular_weight>
  <monoisotopic_molecular_weight>169.085126436</monoisotopic_molecular_weight>
  <smiles>CN1C=NC(CC(=O)O)=C1</smiles>
  <inchikey>BRMWTNUJHUMWMS-UHFFFAOYSA-N</inchikey>
  <biospecimen_locations>
    <biospecimen>Blood</biospecimen>
    <biospecimen>Urine</biospecimen>
  </biospecimen_locations>
  <pathways>
    <pathway>
      <name>Histidine Metabolism</name>
      <smpdb_id>SMP0000044</smpdb_id>
      <kegg_map_id>map00340</kegg_map_id>
    </pathway>
  </pathways>
  <diseases>
    <disease><name>Carnosinemia</name><omim_id>212200</omim_id></disease>
  </diseases>
  <normal_concentrations>
    <concentration>
      <biospecimen>Blood</biospecimen>
      <concentration_value>3.8</concentration_value>
      <concentration_units>uM</concentration_units>
    </concentration>
  </normal_concentrations>
</metabolite>
```

The bulk metabolite XML is a single large file whose root contains many
`<metabolite>` children — parse it as a stream (see
`access-and-parsing.md`), not with a DOM load.

## Which fields to query per task

- **Identification** — `accession`, `name`, `synonyms`, `inchi`, `smiles`.
- **Structure similarity** — `smiles`, `inchi`, `inchikey`,
  `average_molecular_weight`, `chemical_formula`.
- **Biomarker discovery** — `diseases`, `biomarker_status`,
  `normal_concentrations`, `abnormal_concentrations`.
- **Pathway analysis** — `pathways`, `protein_associations`, `reactions`.
- **Spectral matching** — `nmr_spectra`, `ms_spectra` peak lists.
- **Cross-database joins** — the external ID fields above; prefer `inchikey`
  when no direct ID link exists.

## Field completeness

- **Near-universal (>90%)**: `accession`, `name`, `chemical_formula`,
  molecular weight, `smiles`, `inchi`.
- **Moderate (50–90%)**: `biospecimen_locations`, `tissue_locations`,
  `pathways`.
- **Variable (10–50%)**: concentrations, disease associations, protein
  associations.
- **Sparse (<10%)**: experimental NMR/MS spectra, detailed kinetics.

Predicted/computational values (e.g., predicted MS spectra, predicted
concentrations) fill in where experimental data is missing — always check the
predicted-vs-experimental flag before treating a value as measured.
