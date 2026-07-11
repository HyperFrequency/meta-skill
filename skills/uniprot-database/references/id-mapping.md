# UniProt ID Mapping

ID mapping translates identifiers between UniProt and ~100 external databases,
in either direction. It is an **asynchronous job**: submit, poll, then fetch.

## The three-step contract

```
1. POST /idmapping/run        form: from={db}&to={db}&ids={csv}   -> { "jobId": "..." }
2. GET  /idmapping/status/{jobId}   poll until not RUNNING
3. GET  /idmapping/results/{jobId}  (paginated via the Link header)
```

- When the **target is `UniProtKB`**, fetch full entries (with a `fields=`
  selector and any `format`) from
  `GET /idmapping/uniprotkb/results/{jobId}` instead of the plain results path.
- The status endpoint returns `{"jobStatus":"RUNNING"}` while working; on
  completion the body carries `results` and/or `failedIds`. It may also
  `303`-redirect straight to the results URL — follow redirects.
- **Limits:** max **100,000 IDs** per job; results retained ~7 days.
- **Case-sensitive:** database names must match exactly.
- **Many-to-many:** one input can map to several targets; unmatched inputs are
  listed under `failedIds`.

Fetch the authoritative, current database list programmatically:

```bash
curl https://rest.uniprot.org/configure/idmapping/fields
```

## Frequently used database names

### UniProt
`UniProtKB_AC-ID`, `UniProtKB`, `UniProtKB-Swiss-Prot`, `UniRef50`, `UniRef90`,
`UniRef100`, `UniParc`

### Genes & genomes
`GeneID` (Entrez), `Gene_Name`, `Ensembl`, `Ensembl_PRO`, `Ensembl_TRS`,
`EnsemblGenomes`, `KEGG`, `UCSC`, `HGNC`, `MGI`, `RGD`, `FlyBase`, `WormBase`,
`SGD`, `PomBase`, `TAIR`, `ZFIN`, `Xenbase`

### Sequence
`EMBL`, `EMBL-CDS`, `RefSeq_Protein`, `RefSeq_Nucleotide`, `CCDS`, `PIR`

### Structure
`PDB`, `AlphaFoldDB`, `SMR`, `PDBsum`, `BMRB`, `SASBDB`

### Family / domain
`InterPro`, `Pfam`, `PROSITE`, `SMART`, `CDD`, `PANTHER`, `SUPFAM`, `TIGRFAMs`,
`HAMAP`, `PRINTS`

### Pathways, enzymes, disease, drugs
`Reactome`, `BioCyc`, `SIGNOR`, `EC`, `BRENDA`, `SABIO-RK`, `OMIM`, `Orphanet`,
`DisGeNET`, `MalaCards`, `CTD`, `OpenTargets`, `ChEMBL`, `DrugBank`,
`GuidetoPHARMACOLOGY`

### Interaction, expression, proteomics, orthology
`STRING`, `BioGRID`, `IntAct`, `MINT`, `ComplexPortal`, `Bgee`,
`ExpressionAtlas`, `PRIDE`, `PeptideAtlas`, `ProteomicsDB`, `eggNOG`, `OMA`,
`OrthoDB`, `TreeFam`, `GeneTree`, `KO`

## Common scenarios

```python
# Gene symbols -> reviewed UniProt entries (returns full records)
from_db, to_db, ids = "Gene_Name", "UniProtKB-Swiss-Prot", ["BRCA1", "TP53", "INS"]

# UniProt -> PDB structures
from_db, to_db, ids = "UniProtKB_AC-ID", "PDB", ["P01308", "P04637"]

# RefSeq protein -> UniProt
from_db, to_db, ids = "RefSeq_Protein", "UniProtKB", ["NP_000198.1"]

# UniProt -> Ensembl gene/transcript
from_db, to_db, ids = "UniProtKB_AC-ID", "Ensembl", ["P12345"]
```

See `python-client.md` for a `map_ids(...)` helper that runs the full poll loop,
and `api-examples.md` for curl/JS equivalents.

## Docs

- Tool: https://www.uniprot.org/id-mapping
- Programmatic guide: https://www.uniprot.org/help/id_mapping
- API reference: https://www.uniprot.org/help/api_idmapping
