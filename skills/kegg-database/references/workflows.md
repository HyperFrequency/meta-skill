# KEGG Analysis Workflows and Integration

Recipes below assume the `kegg(...)` helper from `SKILL.md` (or the named
helpers in `references/rest-api.md`) and `parse_tsv` for tab-delimited output.

## Workflow 1 — Gene → pathway mapping

Find pathways associated with a gene of interest (pathway-enrichment context).

```python
# 1. Resolve a name to a KEGG gene id (inspect the search rows).
hits = parse_tsv(kegg("find", "genes", "p53", encode=0))

# 2. Link the gene to its pathways (TP53 = hsa:7157).
pathway_rows = parse_tsv(kegg("link", "pathway", "hsa:7157"))

# 3. Pull details for each pathway (strip the "path:" prefix).
for gene_id, path_id in pathway_rows:
    entry = kegg("get", path_id.replace("path:", ""))
```

## Workflow 2 — Enrichment context (all genes per pathway)

Build the pathway → gene-set membership needed for over-representation tests.

```python
pathways = parse_tsv(kegg("list", "pathway", "hsa"))   # (path_id, name)
gene_sets = {}
for path_id, name in pathways:
    members = parse_tsv(kegg("link", "genes", path_id))  # (path_id, gene_id)
    gene_sets[path_id] = [gene for _, gene in members]
# Feed gene_sets + your foreground list into a hypergeometric / Fisher test.
```

Throttle this loop and cache — it issues one request per pathway (hundreds).

## Workflow 3 — Compound → reaction → pathway

Trace which metabolic pathways involve a metabolite.

```python
comp = parse_tsv(kegg("find", "compound", "glucose", encode=0))  # -> cpd:C00031
reactions = parse_tsv(kegg("link", "reaction", "cpd:C00031"))
for _, rxn in reactions:
    paths = parse_tsv(kegg("link", "pathway", rxn))   # rxn like rn:R00299
glyco = kegg("get", "map00010")   # reference glycolysis entry
```

## Workflow 4 — Cross-database integration

Map KEGG ids onto UniProt / NCBI / PubChem for joins with other datasets.

```python
uniprot = parse_tsv(kegg("conv", "uniprot", "hsa"))       # (kegg_gene, up:XXXX)
ncbi    = parse_tsv(kegg("conv", "ncbi-geneid", "hsa"))   # (kegg_gene, ncbi:NN)
seq     = kegg("get", "hsa:10458", encode=None)           # then /aaseq for FASTA
```

## Workflow 5 — Cross-organism comparison

Compare the same reference pathway across species.

```python
ref   = kegg("get", "map00010")     # organism-agnostic reference
human = kegg("get", "hsa00010")
mouse = kegg("get", "mmu00010")
yeast = kegg("get", "sce00010")
# Diff the GENE / ORTHOLOGY blocks, or pull KGML for graph-level comparison.
```

## Pathway classification (7 categories)

Pathway ids follow the reference numbering; the leading digits encode category.

1. **Metabolism** — `map00010` Glycolysis/Gluconeogenesis, `map00020` TCA cycle,
   `map00190` Oxidative phosphorylation.
2. **Genetic Information Processing** — `map03010` Ribosome, `map03020` RNA
   polymerase, `map03040` Spliceosome.
3. **Environmental Information Processing** — `map02010` ABC transporters,
   `map04010` MAPK signaling.
4. **Cellular Processes** — `map04140` Autophagy, `map04210` Apoptosis.
5. **Organismal Systems** — `map04610` Complement/coagulation cascades,
   `map04910` Insulin signaling.
6. **Human Diseases** — `map05200` Pathways in cancer, `map05010` Alzheimer disease.
7. **Drug Development** — chronological and target-based drug classifications.

Swap the `map` prefix for an organism code (`hsa04010`) to get the species map.

## Library alternatives to raw REST

When you are already in Python/R and want parsing, caching, and multi-database
convenience, prefer a wrapper over hand-rolled HTTP:

**Biopython — `Bio.KEGG.REST`** (Python). Thin wrappers mirroring the operations:
`kegg_info`, `kegg_list`, `kegg_find`, `kegg_get`, `kegg_conv`, `kegg_link`;
each returns a file-like handle you `.read()`. Biopython also ships parsers under
`Bio.KEGG` (e.g. compound and KGML pathway parsers).

```python
from Bio.KEGG import REST
pathways = REST.kegg_list("pathway", "hsa").read()
```

**KEGGREST** (R / Bioconductor). Functions `keggList`, `keggGet`, `keggFind`,
`keggConv`, `keggLink`, `keggInfo` return parsed R structures.

```r
library(KEGGREST)
pathways <- keggList("pathway", "hsa")
entry    <- keggGet("hsa00010")
```

**bioservices** (Python). A `KEGG` class covering the full API plus dozens of
other bioinformatics services with a uniform interface and caching — the best
fit when a workflow spans KEGG *and* UniProt/ChEBI/etc. Use raw REST (this
skill) only when you need HTTP-level control or want zero dependencies.

## Related web tools (not part of the REST API)

- **KEGG Mapper** (https://www.kegg.jp/kegg/mapper/) — paste id/expression lists
  onto pathway maps interactively.
- **BlastKOALA / GhostKOALA** — automated KO annotation for genomes and
  metagenomes/metatranscriptomes respectively.
- **KEGG Modules** and **BRITE** browsers for the `module`/`brite` hierarchies.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `404` | unknown entry or database | verify id spelling and organism code |
| `400` | malformed request | check operation syntax; encode `find` text |
| status 200, empty body | valid query, no matches | broaden keyword / check organism |
| garbled bytes from `get` | requested `image` (PNG) and decoded as text | read as bytes, write to `.png` |
| only first entry returned for `image`/`kgml`/`json` | those formats are single-entry | loop one id at a time |
| slow / throttled bulk loop | too many rapid requests | batch with `+` (≤10), cache locally |
