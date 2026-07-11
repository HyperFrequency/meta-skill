# Biological Ontologies (Bionty)

The `bionty` plugin gives LaminDB registries backed by public biological
ontologies, so metadata uses a controlled, versioned vocabulary. API names
reflect current LaminDB/Bionty.

## Available registries

| Registry | Source | Covers |
| --- | --- | --- |
| `Gene` | Ensembl | genes across organisms |
| `Protein` | UniProt | proteins |
| `CellType` | Cell Ontology (CL) | cell types |
| `CellLine` | Cell Line Ontology (CLO) | cell lines |
| `Tissue` | Uberon | anatomy / tissues |
| `Disease` | Mondo, DOID | diseases |
| `Phenotype` | HPO | phenotypic abnormalities |
| `Pathway` | Gene Ontology (GO) | pathways / processes |
| `ExperimentalFactor` | EFO | experimental variables |
| `DevelopmentalStage` | various | developmental stages |
| `Ethnicity` | HANCESTRO | human ancestry |
| `Drug` | DrugBank | drug compounds |
| `Organism` | NCBItaxon | taxonomy |

## Import a source

Populate a local registry from a public ontology before validating against it:

```python
import bionty as bt

bt.CellType.import_source()
bt.Gene.import_source(organism="human")
bt.Gene.import_source(organism="mouse")
bt.Tissue.import_source()
bt.Disease.import_source(source="mondo")   # or source="doid"
```

## Access records

```python
# Keyword search
bt.CellType.search("T cell").to_dataframe()
bt.Gene.search("CD8").to_dataframe()

# Auto-complete lookup (registries < ~100k records)
cell_types = bt.CellType.lookup()
t_cell = cell_types.t_cell

# Exact field match
bt.CellType.get(ontology_id="CL:0000798")     # gamma-delta T cell
bt.CellType.get(name="T cell")
bt.Gene.get(symbol="CD8A")
bt.Gene.get(ensembl_gene_id="ENSG00000153563")
```

## Hierarchies

```python
gdt = bt.CellType.get(ontology_id="CL:0000798")
gdt.parents.to_dataframe()          # direct parents
gdt.children.to_dataframe()         # direct children
gdt.query_children().to_dataframe() # all descendants (recursive)

gdt.view_parents()                  # visualize
gdt.view_parents(with_children=True)
```

## Validate and standardize

```python
bt.CellType.validate(["T cell", "B cell", "invalid_cell"])  # [True, True, False]
bt.Gene.validate(["CD8A", "TP53", "FAKEGENE"], organism="human")

bt.CellType.standardize(["fat cell", "blood forming stem cell"])
# -> ['adipocyte', 'hematopoietic stem cell']
bt.Gene.standardize(["BRCA-1", "p53"], organism="human")   # -> ['BRCA1', 'TP53']

# Materialize validated records (accepts synonyms)
records = bt.CellType.from_values(["fat cell", "blood forming stem cell"])
genes = bt.Gene.from_values(["CD8A", "CD8B"], organism="human")
```

## Annotate datasets

```python
import lamindb as ln

# AnnData
cell_types = bt.CellType.from_values(adata.obs.cell_type)
artifact = ln.Artifact.from_anndata(adata, key="scrna/annotated.h5ad").save()
artifact.feature_sets.add_ontology(cell_types)

# DataFrame
df["cell_type"] = bt.CellType.standardize(df["cell_type"])
df["tissue"] = bt.Tissue.standardize(df["tissue"])
artifact = ln.Artifact.from_dataframe(df, key="metadata/samples.parquet").save()
artifact.feature_sets.add_ontology(bt.CellType.from_values(df["cell_type"]))
artifact.feature_sets.add_ontology(bt.Tissue.from_values(df["tissue"]))
```

## Custom terms, synonyms, hierarchies

```python
# New term linked into an existing hierarchy
my_type = bt.CellType(name="my_novel_T_cell_subtype").save()
my_type.parents.add(bt.CellType.get(name="T cell"))

# Synonyms and abbreviation feed standardization
hsc = bt.CellType.get(name="hematopoietic stem cell")
hsc.add_synonym("HSC"); hsc.add_synonym("blood stem cell")
hsc.set_abbr("HSC")
bt.CellType.standardize(["HSC"])   # -> ['hematopoietic stem cell']
```

## Multi-organism genes

`Gene` is organism-aware — pass `organism=` or set a global default.

```python
bt.settings.organism = "human"
bt.Gene.validate(["TCF7", "CD8A"], organism="human")
human = bt.Gene.from_values(["CD8A", "TP53"], organism="human")
mouse = bt.Gene.from_values(["Cd8a", "Trp53"], organism="mouse")
```

Note: Bionty does not compute cross-species orthologs. Map orthologs with an
external tool (Ensembl BioMart, homologene), then load each species' symbols.

## Source versioning

```python
bt.Source.filter(currently_used=True).to_dataframe()   # active ontology versions
src = bt.CellType.get(name="hepatocyte").source
src.name, src.version, src.url                          # e.g. "cl", "2023-05-18"
```

## Querying ontology-annotated data

```python
t_cell = bt.CellType.get(name="T cell")
ln.Artifact.filter(feature_sets__cell_types=t_cell).to_dataframe()

# Across the hierarchy: T cell and all its subtypes
subtypes = t_cell.query_children()
ln.Artifact.filter(feature_sets__cell_types__in=subtypes).to_dataframe()
```

## Best practices

1. `import_source()` before validating against a registry.
2. Standardize (synonym mapping) before creating or annotating artifacts.
3. Set the organism context for gene queries.
4. Register domain-specific synonyms to absorb naming variation.
5. Record the ontology source version for reproducibility.
6. Query hierarchically with `query_children()` for comprehensive matches.
