# BioServices: Service Catalogue

A per-service reference for the classes you will use most. Each service is a
Python class you instantiate once (`s = Service(verbose=False)`) and then call.
Method names and identifier codes occasionally shift between bioservices
releases and upstream API revisions — treat the signatures below as the common
case and confirm against https://bioservices.readthedocs.io when a call
surprises you.

---

## Protein & Gene

### UniProt
Protein sequence and functional annotation.

- `search(query, frmt="tsv", columns=None, limit=None, sort=None)` — flexible
  query syntax (`"gene:TP53 AND organism_id:9606"`). `frmt`: `tsv`, `fasta`,
  `xml`, `txt`, `gff`. `columns`: comma-separated field list. Returns a string
  in the requested format.
- `retrieve(uniprot_id, frmt="txt")` — one entry; `frmt`: `txt`, `fasta`,
  `xml`, `gff`, `rdf`.
- `mapping(fr, to, query)` — ID conversion across databases (see
  `identifier_mapping.md`). Returns a dict `{source_id: [target_ids]}`.

Common column names: `accession`, `id`, `gene_names`, `organism_name`,
`protein_name`, `length`, `sequence`, `go_id`, `ec`. (Column tokens were
renamed when UniProt migrated its REST API; older skills used `id,genes,
organism` — verify against the current UniProt "return fields" docs.)

### KEGG
Genes, pathways, compounds, organisms.

- `list(database)` — enumerate a database: `"organism"`, `"pathway"`,
  `"module"`, `"disease"`, `"drug"`, `"compound"`.
- `find(database, query)` — keyword search; returns matching entries with IDs.
- `get(entry_id)` — raw entry text (gene, pathway, compound, ...).
- `parse(data)` — structured dict from a `get` result.
- `lookfor_organism(name)` / `lookfor_pathway(name)` — search by name.
- `get_pathway_by_gene(gene_id, organism)` — pathways containing a gene.
- `parse_kgml_pathway(pathway_id)` — dict with `entries` and `relations`.
- `pathway2sif(pathway_id)` — Simple Interaction Format edges (activation/
  inhibition), for Cytoscape/NetworkX.
- Attributes: `organism` (set default), `organismIds`, `pathwayIds`.

Organism codes: `hsa` human, `mmu` mouse, `dme` fly, `sce` yeast, `eco` E. coli.

### HGNC
Official human gene nomenclature. `search(query)`, `fetch(format, query)` —
standardize/look up official gene symbols.

### MyGeneInfo
Gene annotation service. `querymany(ids, scopes, fields, species)` for batch
queries; `getgene(geneid)` for a single annotation. Good for bulk gene ID
conversion.

---

## Chemical Compounds

### ChEBI
Curated small-molecule dictionary (SOAP). `getCompleteEntity(chebi_id)` for full
records (formula via `.Formulae`, name via `.chebiAsciiName`),
`getLiteEntity(...)` for basics, `getCompleteEntityByList([...])` for batches.

### ChEMBL
Bioactive, drug-like compounds — molecules, targets, activities, similarity.
BioServices wraps the ChEMBL web resource; exact method names track that client
and its version. Treat ChEMBL access as "query molecules/targets/assays and
similarity" and confirm the precise method against current docs before relying
on a specific signature.

### UniChem
Chemical identifier mapping across databases.

- `get_compound_id_from_kegg(kegg_id)` — convenience KEGG → ChEMBL.
- `get_all_compound_ids(src_compound_id, src_id)` — every known ID for a
  compound.
- `get_src_compound_ids(src_compound_id, from_src_id, to_src_id)` — convert
  between two named sources.

Source IDs: 1 ChEMBL, 2 DrugBank, 3 PDB, 4 IUPHAR, 6 KEGG, 7 ChEBI, 22 PubChem.
(UniChem revised its REST API; source-ID numbering and method names may differ
by release — verify.)

### PubChem
NIH compound database. `get_compounds(identifier, namespace)`,
`get_properties(properties, identifier, namespace)`.

---

## Sequence Analysis

### NCBIblast
Remote similarity search — **asynchronous** (submit → poll → fetch).

- `run(program, sequence, stype, database, email, **params)` — returns a job id.
  `program`: `blastp`, `blastn`, `blastx`, `tblastn`, `tblastx`. `stype`:
  `protein` or `dna`. `database`: `uniprotkb`, `pdb`, `refseq_protein`, ...
  `email` is required by the service.
- `getStatus(jobid)` — `RUNNING` / `FINISHED` / `ERROR`.
- `getResult(jobid, result_type)` — `out` (default), `ids`, `xml`.

Always poll `getStatus` until `FINISHED` before calling `getResult`.

---

## Pathways & Interactions

### Reactome
Curated human-centric pathways. `get_pathway_by_id(pathway_id)`,
`search_pathway(query)`.

### PSICQUIC
Federated protein-interaction query over 30+ databases (MINT, IntAct, BioGRID,
DIP, ...). `query(database, query_string)` returns PSI-MI TAB format; `activeDBs`
lists reachable databases. Query syntax supports `AND`/`OR` and species filters,
e.g. `"ZAP70 AND species:9606"`.

### IntactComplex
Protein complexes. `search(query)`, `details(complex_ac)`.

### OmniPath
Integrated signaling networks. `interactions(datasets, organisms)`,
`ptms(datasets, organisms)` for post-translational modifications.

---

## Ontology, Genomics & Structure

### QuickGO
Gene Ontology. `Term(go_id, frmt="obo")` for a term; `Annotation(protein=...,
goid=..., format="tsv")` for annotations. Aspects: Biological Process (P),
Molecular Function (F), Cellular Component (C).

### BioMart
Genomic data mining. `datasets(dataset)`, `attributes(dataset)`,
`query(query_xml)` — build XML queries for bulk annotations, SNPs, homologs.

### ENA / ArrayExpress
Nucleotide sequences (ENA) and gene-expression experiments (ArrayExpress).
Search-then-retrieve style methods; check current signatures before use.

### PDB
3D structures. `get_file(pdb_id, file_format)` — `pdb`, `cif`, `xml`. Pair the
retrieved IDs with PyMOL or a structural viewer.

### Pfam
Protein families/domains. `searchSequence(sequence)` to find domains,
`getPfamEntry(pfam_id)` for family info.

### BioModels / BiGG / COG
Systems-biology SBML models (`get_model_by_id`), genome-scale metabolic models
(`list_models`, `get_model`), and orthologous-gene clusters, respectively.

---

## Cross-Cutting Patterns

- **Verbosity / timeout:** `Service(verbose=False)`; `service.TIMEOUT = 30`.
- **Caching:** several services cache; where supported, `service.CACHE = True`
  and a `clear_cache()` helper exist.
- **Error handling:** every method can raise on network or parse failure — wrap
  calls and check for empty results.
- **Formats:** `frmt`/`format` args vary per service; common values are `xml`,
  `json`, `tsv`/`tab`, `txt`, `fasta`, `obo`.

Full official docs: https://bioservices.readthedocs.io — source:
https://github.com/cokelaer/bioservices (GPLv3).
