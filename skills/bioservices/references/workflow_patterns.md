# BioServices: Multi-Service Workflows

Runnable, end-to-end pipelines that chain several services. Each is self-
contained; adapt the identifiers to your target. Replace `you@example.com` with
a real address where a service (BLAST) requires it.

---

## 1. Protein Characterization

**Goal:** from a protein name, get its sequence, homologs, pathways,
interactions, and GO annotations. Example: human ZAP70.

```python
from bioservices import UniProt, NCBIblast, KEGG, PSICQUIC, QuickGO
import time

u = UniProt(verbose=False)

# 1. Identify the entry
res = u.search("ZAP70_HUMAN", frmt="tsv",
               columns="accession,gene_names,organism_name,length")
acc = res.strip().split("\n")[1].split("\t")[0]          # e.g. P43403

# 2. Sequence (strip FASTA header for downstream tools)
fasta = u.retrieve(acc, "fasta")
seq = "".join(fasta.split("\n")[1:])

# 3. Remote BLAST (asynchronous: submit -> poll -> fetch)
s = NCBIblast(verbose=False)
job = s.run(program="blastp", sequence=seq, stype="protein",
            database="uniprotkb", email="you@example.com")
while True:
    status = s.getStatus(job)
    if status in ("FINISHED", "ERROR"):
        break
    time.sleep(5)
blast = s.getResult(job, "out") if status == "FINISHED" else None

# 4. KEGG pathways (via UniProt -> KEGG mapping)
k = KEGG()
m = u.mapping(fr="UniProtKB_AC-ID", to="KEGG", query=acc)
pathways = []
if acc in m:
    org, gene = m[acc][0].split(":")
    pathways = k.get_pathway_by_gene(gene, org)

# 5. Interactions (PSICQUIC, PSI-MI TAB output)
interactions = PSICQUIC(verbose=False).query("mint", "ZAP70 AND species:9606")

# 6. GO annotations
go = QuickGO(verbose=False).Annotation(protein=acc, format="tsv")
```

**Outputs:** accession + gene name, FASTA sequence, BLAST hits, KEGG pathway
IDs, interaction partners, GO terms across P/F/C aspects.

---

## 2. Pathway Network Extraction

**Goal:** enumerate an organism's pathways and pull protein-protein networks.

```python
from bioservices import KEGG
k = KEGG(); k.organism = "hsa"

pathway_ids = k.pathwayIds            # ~300 human pathways

kgml = k.parse_kgml_pathway("hsa04660")   # T-cell receptor signaling
entries   = kgml["entries"]               # genes/proteins
relations = kgml["relations"]             # interactions

# Keep only protein-protein relations, tally their types
ppis = [r for r in relations if r.get("link") == "PPrel"]

# SIF edges (activation/inhibition) for Cytoscape / NetworkX
sif = k.pathway2sif("hsa04660")
```

Batch across many pathways to profile network sizes (guard each with
try/except, since some pathways lack KGML):

```python
import pandas as pd
rows = []
for pid in pathway_ids[:50]:
    try:
        g = k.parse_kgml_pathway(pid)
        rows.append({"pathway": pid,
                     "entries":  len(g.get("entries", [])),
                     "relations": len(g.get("relations", []))})
    except Exception:
        pass
df = pd.DataFrame(rows)
```

---

## 3. Compound Cross-Reference

**Goal:** from a compound name, collect KEGG, ChEBI, and ChEMBL IDs plus basic
properties. Example: Geldanamycin.

```python
from bioservices import KEGG, UniChem, ChEBI
k = KEGG()

hits = k.find("compound", "Geldanamycin")            # -> cpd:C11222
kegg_id = hits.strip().split("\n")[0].split("\t")[0].replace("cpd:", "")

# ChEBI ID sits inside the KEGG entry
entry = k.get(f"cpd:{kegg_id}")
chebi_id = next((l.split("ChEBI:")[1].strip().split()[0]
                 for l in entry.split("\n") if "ChEBI:" in l), None)

# ChEMBL via UniChem
chembl_id = UniChem().get_compound_id_from_kegg(kegg_id)

# ChEBI properties
if chebi_id:
    ent = ChEBI().getCompleteEntity(f"CHEBI:{chebi_id}")
    formula, name = ent.Formulae, ent.chebiAsciiName
```

**Outputs:** KEGG ID, ChEBI ID, ChEMBL ID, formula, name, and (via ChEMBL)
structure/weight. For offline property computation on a SMILES you already have,
hand off to `rdkit`.

---

## 4. Batch Identifier Conversion + Export

```python
from bioservices import UniProt
import csv

def batch_convert(ids, from_db, to_db, chunk=50):
    u, out = UniProt(), {}
    for i in range(0, len(ids), chunk):
        block = ids[i:i+chunk]
        try:
            out.update(u.mapping(fr=from_db, to=to_db, query=",".join(block)))
        except Exception as e:
            print(f"chunk {i} failed: {e}")
    return out

def write_csv(mapping, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["source", "targets"])
        for src, tgt in mapping.items():
            w.writerow([src, ";".join(tgt) if tgt else "no mapping"])

ids = ["P43403", "P04637", "P53779", "Q9Y6K9"]
write_csv(batch_convert(ids, "UniProtKB_AC-ID", "KEGG"), "uniprot_to_kegg.csv")
```

See `identifier_mapping.md` for the chunk-with-retry variant.

---

## 5. Interaction Network with NetworkX

```python
from bioservices import PSICQUIC
import networkx as nx

p = PSICQUIC(verbose=False)
G = nx.Graph()

for protein in ["ZAP70", "LCK", "LAT", "SLP76", "PLCg1"]:
    try:
        res = p.query("intact", f"{protein} AND species:9606")
        for line in res.strip().split("\n"):
            f = line.split("\t")
            a = f[4].split(":")[-1]
            b = f[5].split(":")[-1]
            G.add_edge(a, b)
    except Exception:
        pass

nx.write_gml(G, "protein_network.gml")   # open in Cytoscape
```

Column offsets in PSI-MI TAB vary by source database — inspect a few rows before
trusting fixed indices. For graph analysis of the result, see the `networkx`
skill.

---

## Integration Notes

- **pandas** — load tabular UniProt/KEGG output directly:
  `pd.read_csv(StringIO(text), sep="\t")`.
- **biopython** — parse retrieved FASTA:
  `SeqIO.read(StringIO(u.retrieve("P43403", "fasta")), "fasta")`.
- **networkx** — build graphs from PSICQUIC or KEGG SIF/KGML edges.
- **rdkit** — compute descriptors/fingerprints on SMILES fetched from ChEMBL/
  ChEBI (BioServices fetches; RDKit computes).

## Workflow hygiene

Wrap every service call in try/except; validate for empty results before
indexing; report progress on long loops; add `time.sleep` between batches; and
persist intermediate results (JSON/CSV) so a mid-run failure does not lose work.
