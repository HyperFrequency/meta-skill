# gget Module Reference

Parameter tables, defaults, and return schemas for every `gget` module. Flags are
shown as `-short/--long`. Unless noted, `-o/--out` saves output and `-q/--quiet`
suppresses progress; `-csv` (CLI) switches JSON to CSV. In Python, `save=True`
writes to the working directory and `json=True` returns JSON where supported.

---

## Gene & Reference Lookup

### `ref` — Ensembl reference genome links
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `species` | str | `Genus_species` or shortcut (`human`, `mouse`) | required |
| `-w/--which` | str | file types: `gtf`, `cdna`, `dna`, `cds`, `cdrna`, `pep` | all |
| `-r/--release` | int | Ensembl release number | latest |
| `-od/--out_dir` | str | download directory | cwd |
| `-l/--list_species` | flag | list vertebrate species | false |
| `-liv/--list_iv_species` | flag | list invertebrate species | false |
| `-ftp` | flag | return only FTP URLs | false |
| `-d/--download` | flag | download files (needs `curl`) | false |

Returns JSON: FTP links, release number, release date, file sizes.

### `search` — find genes by name/description
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `searchwords` | str/list | terms (case-insensitive) | required |
| `-s/--species` | str | species or Ensembl core DB name | required |
| `-r/--release` | int | Ensembl release | latest |
| `-t/--id_type` | str | `gene` or `transcript` | `gene` |
| `-ao/--andor` | str | `or` (any term) / `and` (all terms) | `or` |
| `-l/--limit` | int | max results | none |

Returns: `ensembl_id`, `gene_name`, `ensembl_description`, `ext_ref_description`,
`biotype`, `url`.

### `info` — merged gene/transcript metadata
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `ens_ids` | str/list | Ensembl IDs (also WormBase/FlyBase) | required |
| `-n/--ncbi` | bool | disable NCBI retrieval | false |
| `-u/--uniprot` | bool | disable UniProt retrieval | false |
| `-pdb` | flag | include PDB IDs (slower) | false |

Python extras: `wrap_text=True`. **Limit: ~1000 IDs per call.** Returns UniProt
ID, NCBI gene ID, primary name, synonyms, protein names, descriptions, biotype,
canonical transcript.

### `seq` — sequences as FASTA
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `ens_ids` | str/list | Ensembl IDs | required |
| `-t/--translate` | flag | amino-acid instead of nucleotide | false |
| `-iso/--isoforms` | flag | all transcript variants (gene IDs only) | false |

Nucleotide from Ensembl; amino-acid from UniProt.

---

## Sequence Alignment & Similarity

### `blast` — NCBI BLAST
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `sequence` | str | sequence or FASTA/.txt path | required |
| `-p/--program` | str | `blastn`/`blastp`/`blastx`/`tblastn`/`tblastx` | auto |
| `-db/--database` | str | nt, refseq_rna, pdbnt / nr, swissprot, pdbaa, refseq_protein | nt or nr |
| `-l/--limit` | int | max hits | 50 |
| `-e/--expect` | float | E-value cutoff | 10.0 |
| `-lcf/--low_comp_filt` | flag | low-complexity filter | false |
| `-mbo/--megablast_off` | flag | disable MegaBLAST (blastn) | false |

Returns: Description, Scientific/Common Name, Taxid, Max/Total Score, Query
Coverage, E-value, Per. Ident, Accession.

### `blat` — UCSC BLAT genomic position
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `sequence` | str | sequence or FASTA/.txt path | required |
| `-st/--seqtype` | str | `DNA`, `protein`, `translated%20RNA`, `translated%20DNA` | auto |
| `-a/--assembly` | str | assembly (`human`/hg38, `mouse`/mm39, taeGut2, …) | hg38 |

Returns: genome, query size, alignment start/end, matches, mismatches, %.

### `muscle` — multiple sequence alignment (Muscle5)
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `fasta` | str/list | sequences or FASTA path | required |
| `-s5/--super5` | flag | Super5 algorithm (faster on large sets) | false |

Returns ClustalW-format alignment or `.afa`.

### `diamond` — fast local protein/translated-DNA alignment
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `query` | str/list | sequences or FASTA path | required |
| `--reference` | str/list | reference sequences or FASTA path | required |
| `--sensitivity` | str | fast … very-sensitive … ultra-sensitive | very-sensitive |
| `--threads` | int | CPU threads | 1 |
| `--diamond_db` | str | save built DB for reuse | none |
| `--translated` | flag | nucleotide→amino-acid alignment | false |

Returns: identity %, sequence lengths, match positions, gap openings, E-values,
bit scores.

---

## Structure & Motifs

### `pdb` — RCSB Protein Data Bank
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `pdb_id` | str | PDB identifier (e.g. `7S7U`) | required |
| `-r/--resource` | str | `pdb`, `entry`, `pubmed`, `assembly`, entity types | `pdb` |
| `-i/--identifier` | str | assembly/entity/chain ID | none |

Returns PDB file (structures) or JSON (metadata).

### `alphafold` — AlphaFold2 structure prediction
Setup: `uv pip install openmm` then `gget setup alphafold` (~4GB).
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `sequence` | str/list | amino-acid seq(s) or FASTA; multiple → multimer | required |
| `-mr/--multimer_recycles` | int | recycling iterations (≈20 for accuracy) | 3 |
| `-mfm/--multimer_for_monomer` | flag | apply multimer model to a monomer | false |
| `-r/--relax` | flag | AMBER relaxation of top model | false |

Python-only: `plot=True` (interactive 3D), `show_sidechains=True`. Returns a PDB
file, JSON predicted-alignment-error data, and optional plot.

### `elm` — Eukaryotic Linear Motifs
Setup: `gget setup elm`.
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `sequence` | str | amino-acid seq or UniProt accession | required |
| `-u/--uniprot` | flag | input is a UniProt accession | false |
| `-e/--expand` | flag | add protein names/organisms/references | false |
| `-s/--sensitivity` | str | DIAMOND sensitivity | very-sensitive |
| `-t/--threads` | int | threads | 1 |

Returns **two** objects: `ortholog_df` (motifs from orthologous proteins) and
`regex_df` (motifs matched directly in the input).

---

## Expression & Disease

### `archs4` — correlation / tissue expression
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `gene` | str | symbol or Ensembl ID | required |
| `-w/--which` | str | `correlation` (top 100 genes) or `tissue` | `correlation` |
| `-s/--species` | str | `human` or `mouse` (tissue only) | `human` |
| `-e/--ensembl` | flag | input is an Ensembl ID | false |

Correlation → gene symbols + Pearson r. Tissue → tissue IDs + min/Q1/median/Q3/max.

### `cellxgene` — CZ CELLxGENE single-cell
Setup: `gget setup cellxgene`. **Gene symbols case-sensitive.**
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `--gene` (`-g`) | list | gene names or Ensembl IDs | required |
| `--tissue` | list | tissue type(s) | none |
| `--cell_type` | list | cell type(s) | none |
| `--species` (`-s`) | str | `homo_sapiens` / `mus_musculus` | homo_sapiens |
| `--census_version` (`-cv`) | str | `stable`, `latest`, or dated | stable |
| `--ensembl` (`-e`) | flag | inputs are Ensembl IDs | false |
| `--meta_only` (`-mo`) | flag | return metadata only | false |

Extra filters: `disease`, `development_stage`, `sex`, `assay`, `dataset_id`,
`donor_id`, `ethnicity`, `suspension_type`. Returns an AnnData object (or
metadata DataFrame). CLI requires `-o`.

### `enrichr` — ontology/pathway enrichment
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `genes` | list | symbols or Ensembl IDs | required |
| `-db/--database` | str | library or shortcut | required |
| `-s/--species` | str | human, mouse, fly, yeast, worm, fish | human |
| `-bkg_l/--background_list` | list | background genes | none |
| `-ko/--kegg_out` | str | dir for KEGG pathway images | none |

Python-only: `plot=True`. Shortcuts: `pathway`→KEGG_2021_Human,
`transcription`→ChEA_2016, `ontology`→GO_Biological_Process_2021,
`diseases_drugs`→GWAS_Catalog_2019, `celltypes`→PanglaoDB_Augmented_2021.
Returns term, adjusted p-value, overlapping genes.

### `bgee` — orthologs / expression across species
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `ens_id` | str/list | Ensembl or NCBI gene ID | required |
| `-t/--type` | str | `orthologs` or `expression` | `orthologs` |

Multiple IDs allowed when `type=expression`.

### `opentargets` — disease/drug associations
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `ens_id` | str | Ensembl gene ID | required |
| `-r/--resource` | str | diseases, drugs, tractability, pharmacogenetics, expression, depmap, interactions | diseases |
| `-l/--limit` | int | cap results | none |

Resource-specific filters: `--filter_disease` (drugs); `--filter_drug`
(pharmacogenetics); `--filter_tissue`/`--filter_anat_sys`/`--filter_organ`
(expression, depmap); `--filter_protein_a`/`--filter_protein_b`/`--filter_gene_b`
(interactions).

### `cbio` — cBioPortal cancer heatmaps
Two subcommands. **search**: `gget cbio search <keywords…>` → study IDs.
**plot** parameters:
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `-s/--study_ids` | list | cBioPortal study IDs | required |
| `-g/--genes` | list | gene names or Ensembl IDs | required |
| `-st/--stratification` | str | tissue, cancer_type, cancer_type_detailed, study_id, sample | none |
| `-vt/--variation_type` | str | mutation_occurrences, cna_nonbinary, sv_occurrences, cna_occurrences, Consequence | none |
| `-f/--filter` | str | `column:value` filter | none |
| `-dd/--data_dir` | str | cache dir | ./gget_cbio_cache |
| `-fd/--figure_dir` | str | figure dir | ./gget_cbio_figures |
| `-dpi` | int | resolution | 100 |
| `-nc/--no_confirm` | flag | skip download prompts | false |
| `-sh/--show` | flag | display window | false |

Python: `gget.cbio_search(...)`, `gget.cbio_plot(...)`. Returns a PNG heatmap.

### `cosmic` — COSMIC somatic mutations
**Account + one-time DB download required; commercial use is licensed.**
Query: `searchterm` (gene/Ensembl/mutation/sample), `-ctp/--cosmic_tsv_path`
(required), `-l/--limit` (100). Download mode: `-d/--download_cosmic`,
`-gm/--gget_mutate`, `-cp/--cosmic_project` (cancer, census, cell_line,
resistance, genome_screen, targeted_screen), `-cv/--cosmic_version`,
`-gv/--grch_version` (37/38), `--email`, `--password`.

---

## Utilities

### `mutate` — generate mutated sequences
| Param | Type | Meaning | Default |
|-------|------|---------|---------|
| `sequences` | str/list | FASTA path or sequence(s) | required |
| `-m/--mutations` | str/df | CSV/TSV or DataFrame of mutations | required |
| `-mc/--mut_column` | str | mutation column | `mutation` |
| `-sic/--seq_id_column` | str | sequence-ID column | `seq_ID` |
| `-mic/--mut_id_column` | str | mutation-ID column | none |
| `-k/--k` | int | flanking length (nt) | 30 |

Mutations use HGVS-style notation (e.g. `c.4G>T`). Returns FASTA.

### `setup` — install per-module dependencies
`gget setup <module>` for `alphafold` (~4GB params), `cellxgene`
(cellxgene-census), `elm` (local DB; `-o` sets its dir), `gpt` (OpenAI config).

### `gpt` — OpenAI text generation
Peripheral to the bioinformatics core; needs `gget setup gpt` and an API key.
Params: `prompt`, `api_key`, `model` (default gpt-3.5-turbo), plus standard
sampling knobs (`temperature`, `top_p`, `max_tokens`, `frequency_penalty`,
`presence_penalty`). For LLM work, prefer a dedicated client over this module.
