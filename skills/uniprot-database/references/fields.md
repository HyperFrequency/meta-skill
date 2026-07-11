# UniProt Return Fields

The `fields=` parameter (comma-separated, **no spaces**) controls which columns
a search or stream returns. Requesting only what you need is the biggest lever
on response size and parse time.

```
https://rest.uniprot.org/uniprotkb/search?query=insulin&fields=accession,gene_names,organism_name,length&format=tsv
```

Return fields (what comes back) are distinct from *query* fields (what you
search on, see `query-syntax.md`). Get the live list any time:

```bash
curl https://rest.uniprot.org/configure/uniprotkb/result-fields
```

## Identification

| Field | Description |
| --- | --- |
| `accession` | Primary accession (e.g. `P01308`) |
| `id` | Entry name (e.g. `INS_HUMAN`) |
| `reviewed` | `reviewed` (Swiss-Prot) / `unreviewed` (TrEMBL) |
| `protein_name` | Recommended + alternative names |
| `gene_names` | All gene names |
| `gene_primary` | Primary gene name |
| `gene_synonym` | Gene synonyms |

## Organism

| Field | Description |
| --- | --- |
| `organism_name` | Scientific name |
| `organism_id` | NCBI taxonomy id |
| `lineage` | Full taxonomic lineage |
| `virus_hosts` | Host organisms (viral entries) |

## Sequence

| Field | Description |
| --- | --- |
| `sequence` | Amino-acid sequence |
| `length` | Residue count |
| `mass` | Molecular mass (Da) |
| `fragment` | Whether the entry is a fragment |
| `sequence_version` | Sequence version number |

## Function & biology comments (`cc_`)

`cc_function`, `cc_catalytic_activity`, `cc_activity_regulation`, `cc_pathway`,
`cc_cofactor`, `cc_subunit`, `cc_interaction`, `cc_subcellular_location`,
`cc_tissue_specificity`, `cc_developmental_stage`, `cc_induction`,
`cc_disease`, `cc_disruption_phenotype`, `cc_allergen`, `cc_toxic_dose`,
`cc_ptm`, `cc_mass_spectrometry`, `cc_alternative_products` (isoforms),
`cc_polymorphism`, `cc_rna_editing`, `cc_caution`, `cc_similarity`,
`cc_sequence_caution`, `cc_miscellaneous`, `cc_web_resource`.

## Sequence features (`ft_`)

- **Processing:** `ft_signal`, `ft_transit`, `ft_init_met`, `ft_propep`,
  `ft_chain`, `ft_peptide`
- **Regions/sites:** `ft_domain`, `ft_repeat`, `ft_region`, `ft_motif`,
  `ft_coiled`, `ft_zn_fing`, `ft_dna_bind`, `ft_np_bind`, `ft_compbias`
- **Sites/modifications:** `ft_act_site`, `ft_binding`, `ft_site`, `ft_metal`,
  `ft_mod_res`, `ft_lipid`, `ft_carbohyd` (glycosylation), `ft_disulfid`,
  `ft_crosslnk`
- **Structure:** `ft_helix`, `ft_strand`, `ft_turn`, `ft_transmem`,
  `ft_intramem`, `ft_topo_dom`
- **Variation:** `ft_variant`, `ft_var_seq`, `ft_mutagen`, `ft_conflict`,
  `ft_unsure`, `ft_non_ter`, `ft_non_std`

## Gene Ontology

| Field | Description |
| --- | --- |
| `go` | All GO terms |
| `go_p` | Biological process |
| `go_c` | Cellular component |
| `go_f` | Molecular function |
| `go_id` | GO identifiers only |

## Cross-references (`xref_`)

- **Sequence:** `xref_embl`, `xref_refseq`, `xref_ccds`, `xref_pir`
- **Structure:** `xref_pdb`, `xref_alphafolddb`, `xref_smr`, `xref_bmrb`
- **Family/domain:** `xref_interpro`, `xref_pfam`, `xref_prosite`, `xref_smart`,
  `xref_panther`, `xref_supfam`
- **Genome:** `xref_ensembl`, `xref_geneid`, `xref_kegg`, `xref_ucsc`
- **Organism-specific:** `xref_mgi`, `xref_rgd`, `xref_flybase`, `xref_wormbase`,
  `xref_sgd`, `xref_zfin`, `xref_hgnc`
- **Pathway:** `xref_reactome`, `xref_biocyc`, `xref_signor`
- **Disease:** `xref_omim`, `xref_orphanet`, `xref_disgenet`, `xref_malacards`
- **Drug/chemical:** `xref_chembl`, `xref_drugbank`, `xref_guidetopharmacology`
- **Interaction:** `xref_string`, `xref_biogrid`, `xref_intact`, `xref_complexportal`
- **Expression:** `xref_bgee`, `xref_expressionatlas`, `xref_genevisible`
- **Proteomics:** `xref_pride`, `xref_peptideatlas`, `xref_proteomicsdb`

## Metadata

| Field | Description |
| --- | --- |
| `annotation_score` | Annotation score 1–5 |
| `protein_existence` | Evidence level |
| `date_created`, `date_modified`, `date_sequence_modified` | Dates |
| `lit_pubmed_id` | PubMed ids |
| `xref_proteomes` | Proteome id + membership |

## Ready-made combinations

```
# Basic identity table
accession,id,protein_name,gene_names,organism_name,length

# Sequence + structural links
accession,sequence,length,mass,xref_pdb,xref_alphafolddb

# Functional annotation
accession,protein_name,cc_function,cc_catalytic_activity,cc_pathway,go

# Disease view
accession,protein_name,gene_names,cc_disease,xref_omim,xref_malacards
```

## Notes

- **Format matters:** in TSV a missing field is an empty cell; in JSON it is
  omitted. Many JSON fields are arrays of objects, not plain strings.
- **Wildcards:** the TSV/JSON `fields` parameter does not accept `cc_*` — list
  concrete field names. (`cc_*`/`ft_*` wildcards work in *queries*, not in
  `fields`.)
- **Performance:** fewer fields → smaller payload and faster streaming.

## Docs

- Return fields: https://www.uniprot.org/help/return_fields
- Field explorer: https://www.uniprot.org/api-documentation
