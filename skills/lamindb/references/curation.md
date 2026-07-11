# Curation and Validation

Curation makes data both trustworthy and queryable through three steps:
**validate** (does it match the schema?), **standardize** (fix typos, map
synonyms to canonical terms), and **annotate** (link to metadata entities so it
becomes searchable). API names reflect current LaminDB.

## Schema design

A `Schema` binds Features to a data structure and sets how strict validation is.

```python
import lamindb as ln

# Flexible: validate any column that matches a Feature name; allow extras
schema = ln.Schema(name="valid_features", itype=ln.Feature).save()

# Minimal required: require these Features, permit additional columns
schema = ln.Schema(
    name="minimal_immune",
    features=[ln.Feature.get(name="cell_type"), ln.Feature.get(name="tissue")],
    flexible=True,
).save()

# Strict: exactly these Features, nothing else
schema = ln.Schema(
    name="strict_immune",
    features=[ln.Feature.get(name=n) for n in ["cell_type", "tissue", "disease"]],
    flexible=False,
).save()
```

## DataFrame curation workflow

```python
import pandas as pd, lamindb as ln, bionty as bt

df = pd.read_csv("experiment.csv")

# 1. Define Features (and populate controlled vocabularies if used)
ln.Feature(name="cell_type", dtype=str).save()
ln.Feature(name="tissue", dtype=str).save()
ln.Feature(name="gene_count", dtype=int).save()
bt.CellType.import_source(); bt.Tissue.import_source()

# 2. Build a Schema
schema = ln.Schema(
    name="experiment_schema",
    features=[ln.Feature.get(name=n) for n in ["cell_type", "tissue", "gene_count"]],
    flexible=True,
).save()

# 3. Curate and validate
curator = ln.curators.DataFrameCurator(df, schema)
if curator.validate():
    print("validation passed")
else:
    curator.non_validated       # inspect the failing fields/values

# 4. Fix issues (see below), then save with schema linkage
artifact = curator.save_artifact(
    key="experiments/curated.parquet",
    description="Validated and annotated data",
)
artifact.schema                 # the linked Schema
```

## Fixing validation failures

```python
# Standardize categorical values (typos, synonyms → canonical)
curator.cat.standardize("cell_type")

# Map values to an ontology registry
curator.cat.add_ontology("cell_type", bt.CellType)

# Interactive public lookup for unmapped terms
curator.cat.lookup(public=True).cell_type

# Register new valid terms observed in the data
curator.cat.add_new_from("cell_type")

# Rename a column to match a Feature, then re-init the curator
df = df.rename(columns={"celltype": "cell_type"})
curator = ln.curators.DataFrameCurator(df, schema)
```

Three recurring failure classes and their fixes:

- **Column not in schema** → rename the column, or `schema.features.add(feature)`.
- **Invalid values** → `curator.cat.standardize(col)`, `add_new_from(col)`, or
  `add_ontology(col, registry)`.
- **Dtype mismatch** → cast the column (`df[c] = df[c].astype(int)`), or define
  the Feature with `coerce_dtype=True`.

## Composite structures — slot-based curation

AnnData, MuData, SpatialData, and TileDB-SOMA are curated per **slot**. Define a
sub-schema for each slot, then a composite schema with `otype` and `slots`.

### AnnData

```python
obs_schema = ln.Schema(
    name="cell_metadata",
    features=[ln.Feature.get(name=n) for n in ["cell_type", "tissue", "donor_id"]],
).save()
var_schema = ln.Schema(name="gene_ids", features=[ln.Feature.get(name="ensembl_gene_id")]).save()

anndata_schema = ln.Schema(
    name="scrna_schema", otype="AnnData",
    slots={"obs": obs_schema, "var.T": var_schema},   # .T = transpose var
).save()

curator = ln.curators.AnnDataCurator(adata, anndata_schema)
curator.validate()
curator.cat.standardize("obs", "cell_type")
curator.cat.add_ontology("obs", "cell_type", bt.CellType)
artifact = curator.save_artifact(key="scrna/validated.h5ad")
```

### MuData / SpatialData / TileDB-SOMA

Same pattern, different `otype` and slot keys:

```python
# MuData: modality-prefixed slots
ln.Schema(name="mm", otype="MuData",
          slots={"rna:obs": rna_obs, "protein:obs": prot_obs}).save()
# → ln.curators.MuDataCurator(mdata, schema)

# SpatialData: table/attrs slots
ln.Schema(name="sp", otype="SpatialData",
          slots={"tables:cells.obs": cell_schema, "attrs:bio": bio_schema}).save()
# → ln.curators.SpatialDataCurator(sdata, schema)

# TileDB-SOMA: measurement:modality slots
ln.Schema(name="soma", otype="tiledbsoma",
          slots={"obs": obs_schema, "ms:RNA.T": var_schema}).save()
# → ln.curators.TileDBSOMACurator(soma_exp, schema)
```

## Feature-level validation

```python
ln.Feature(name="age", dtype=int).save()
ln.Feature(name="is_treated", dtype=bool).save()
ln.Feature(name="age_str", dtype=int, coerce_dtype=True).save()  # cast strings

# Constrain a Feature to a registry's controlled vocabulary
cell_type = ln.Feature(name="cell_type", dtype=str).save()
cell_type.link_to_registry(bt.CellType)   # values must exist in CellType
```

## Standardization strategies

```python
# Synonyms — register once, standardization maps them thereafter
t_cell = bt.CellType.get(name="T cell")
t_cell.add_synonym("T lymphocyte"); t_cell.add_synonym("T-cell")
curator.cat.standardize("cell_type")     # "T lymphocyte" -> "T cell"

# Public lookup when you don't yet have the term locally
curator.cat.lookup(public=True).cell_type
```

## Schema versioning and querying curated data

```python
schema_v2 = ln.Schema(name="experiment_schema", features=[...], version="2").save()
artifact.schema = schema_v2; artifact.save()

ln.Artifact.filter(is_valid=True).to_dataframe()
ln.Artifact.filter(schema=schema).to_dataframe()
ln.Artifact.filter(cell_type="T cell", tissue="blood").to_dataframe()
```

## Track curation provenance

Wrap curation in `ln.track()`/`ln.finish()` so the standardization and
validation steps are captured as a Transform:

```python
ln.track()
curator = ln.curators.DataFrameCurator(df, schema)
curator.validate(); curator.cat.standardize("cell_type")
artifact = curator.save_artifact(key="curated.parquet")
ln.finish()
artifact.view_lineage()
```

## Best practices

1. Define Features before curating; import ontology sources first.
2. Start with a flexible schema, tighten as the structure stabilizes.
3. Standardize (typos, synonyms) before validating.
4. For composite objects, validate slot by slot; be explicit about `.T`.
5. Enable `coerce_dtype` only when the cast is unambiguously safe.
6. Register domain synonyms once to simplify all future curation.
7. Test on a small subset before curating the full dataset.
