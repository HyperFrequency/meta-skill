# BioServices: Identifier Mapping

Biological databases use incompatible ID systems; cross-referencing means
mapping between them. BioServices offers three routes:

1. **UniProt mapping** — the broadest tool for protein/gene IDs.
2. **UniChem** — chemical compound IDs.
3. **KEGG entry cross-refs** — links embedded in KEGG records.

---

## UniProt Mapping

```python
from bioservices import UniProt
u = UniProt()

u.mapping(fr="UniProtKB_AC-ID", to="KEGG", query="P43403")
# -> {'P43403': ['hsa:7535']}
```

`query` accepts a comma-separated list for batch conversion:

```python
u.mapping(fr="UniProtKB_AC-ID", to="KEGG",
          query=",".join(["P43403", "P04637", "P53779"]))
```

Returns a dict `{source_id: [target_ids]}`. A source ID may map to **many**
targets (e.g. one UniProt accession → dozens of PDB entries), so always treat
values as lists.

### Common database codes

`fr`/`to` accept 100+ codes. Frequently used ones:

- **Protein/gene:** `UniProtKB_AC-ID`, `UniProtKB`, `KEGG`, `GeneID` (Entrez),
  `Ensembl`, `Ensembl_Protein`, `Ensembl_Transcript`, `RefSeq_Protein`,
  `RefSeq_Nucleotide`.
- **Nomenclature:** `HGNC`, `MGI`, `RGD`, `SGD`, `FlyBase`, `WormBase`, `ZFIN`.
- **Structure/domain:** `PDB`, `Pfam`, `InterPro`, `SUPFAM`, `PROSITE`.
- **Pathways/networks:** `Reactome`, `BioCyc`, `STRING`, `BioGRID`, `GO`.
- **Expression/proteomics:** `PRIDE`, `ProteomicsDB`, `PaxDb`.

Codes were revised when UniProt migrated its ID-mapping service; if a code is
rejected, check the current UniProt "database list" endpoint.

### Examples

```python
u.mapping(fr="KEGG", to="UniProtKB", query="hsa:7535")   # reverse
u.mapping(fr="UniProtKB_AC-ID", to="Ensembl", query="P43403")
u.mapping(fr="UniProtKB_AC-ID", to="PDB", query="P04637") # -> many PDB IDs
```

### Gene symbol → IDs (search first, then map)

```python
res = u.search("gene:ZAP70 AND organism_id:9606", frmt="tsv", columns="accession")
uniprot_id = res.strip().split("\n")[1]
u.mapping(fr="UniProtKB_AC-ID", to="KEGG", query=uniprot_id)
```

Always constrain by organism (`organism_id:9606` for human) — bare gene symbols
are ambiguous across species.

---

## UniChem Compound Mapping

```python
from bioservices import UniChem
uc = UniChem()

uc.get_compound_id_from_kegg("C11222")               # KEGG -> ChEMBL
uc.get_all_compound_ids("CHEMBL278315", src_id=1)    # every known ID
uc.get_src_compound_ids("C11222", from_src_id=6, to_src_id=1)  # KEGG -> ChEMBL
```

Source IDs: **1** ChEMBL, **2** DrugBank, **3** PDB, **4** IUPHAR, **6** KEGG,
**7** ChEBI, **22** PubChem. UniChem's REST API and this numbering were revised;
verify against current docs if a lookup returns nothing.

---

## KEGG Entry Cross-References

KEGG records embed links to other databases; parse them out of the raw entry:

```python
from bioservices import KEGG
k = KEGG()
entry = k.get("cpd:C11222")

chebi_id = None
for line in entry.split("\n"):
    if "ChEBI:" in line:
        chebi_id = line.split("ChEBI:")[1].strip().split()[0]
        break
```

KEGG gene IDs are `organism:gene`, e.g. `hsa:7535` → split on `:`.

---

## Reusable Patterns

### Gene symbol → many database IDs

```python
def gene_to_ids(symbol, organism_id="9606"):
    u = UniProt()
    res = u.search(f"gene:{symbol} AND organism_id:{organism_id}",
                   frmt="tsv", columns="accession")
    lines = res.strip().split("\n")
    if len(lines) < 2:
        return None
    acc = lines[1]
    return {
        "uniprot": acc,
        "kegg":    u.mapping(fr="UniProtKB_AC-ID", to="KEGG",           query=acc),
        "ensembl": u.mapping(fr="UniProtKB_AC-ID", to="Ensembl",        query=acc),
        "refseq":  u.mapping(fr="UniProtKB_AC-ID", to="RefSeq_Protein", query=acc),
        "pdb":     u.mapping(fr="UniProtKB_AC-ID", to="PDB",            query=acc),
    }
```

### Batch mapping with chunking + fallback

```python
def safe_batch_mapping(ids, from_db, to_db, chunk=100):
    u, out = UniProt(), {}
    for i in range(0, len(ids), chunk):
        block = ids[i:i+chunk]
        try:
            out.update(u.mapping(fr=from_db, to=to_db, query=",".join(block)))
        except Exception:
            for one in block:               # retry individually on chunk failure
                try:
                    out.update(u.mapping(fr=from_db, to=to_db, query=one))
                except Exception:
                    out[one] = None
    return out
```

### Multi-hop: gene symbol → UniProt → KEGG → pathways

```python
def gene_to_pathways(symbol, organism_id="9606"):
    u, k = UniProt(), KEGG()
    res = u.search(f"gene:{symbol} AND organism_id:{organism_id}",
                   frmt="tsv", columns="accession")
    lines = res.strip().split("\n")
    if len(lines) < 2:
        return None
    acc = lines[1]
    m = u.mapping(fr="UniProtKB_AC-ID", to="KEGG", query=acc)
    if acc not in m:
        return None
    org, gene = m[acc][0].split(":")
    return {"uniprot": acc, "kegg": m[acc][0],
            "pathways": k.get_pathway_by_gene(gene, org)}
```

---

## Troubleshooting

- **Empty/None result** — verify the source ID exists (`u.search(id)`), check
  the code spelling, try the reverse direction; not every ID has a mapping in
  every database.
- **Batch times out** — reduce `chunk` to 50; add `time.sleep(0.5)` between
  blocks to respect rate limits.
- **One → many targets** — expected for `PDB`, `GO`, etc.; iterate the list.
- **Organism ambiguity** — always add `AND organism_id:<taxid>` to searches.
- **Deprecated IDs** — retrieve the entry (`u.retrieve(id, "txt")`) and read the
  `AC` line for current primary/secondary accessions.

### Best practices

Validate inputs before batching; handle `None` gracefully; chunk large lists
(50–100); cache repeated queries; specify organism; log failures for retry; add
small delays between big batches to be polite to the APIs.
