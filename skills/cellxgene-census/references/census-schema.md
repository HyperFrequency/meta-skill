# CELLxGENE Census — Data Schema & Filter Reference

The Census is a versioned single-cell collection built on the TileDB-SOMA
framework. This file documents its object model, the `obs` / `var` metadata
fields you filter on, the value-filter grammar, and the data-inclusion rules
that explain why some cells or genes are (or are not) present.

## Object Model

`open_soma()` returns a `SOMACollection` with two top-level branches.

### `census_info` — catalog and summary

- `summary` — build date, total cell counts, dataset statistics.
- `datasets` — every source dataset from CELLxGENE Discover, with metadata.
- `summary_cell_counts` — cell counts stratified by metadata category.

Read any of these as a DataFrame:

```python
datasets = census["census_info"]["datasets"].read().concat().to_pandas()
covid = datasets[datasets["disease"].str.contains("COVID", na=False)]
```

### `census_data` — per-organism experiments

Keyed `"homo_sapiens"` and `"mus_musculus"`. Each is a `SOMAExperiment`:

- `obs` — cell metadata (`SOMADataFrame`), one row per cell.
- `ms["RNA"]` — the RNA `Measurement`, containing:
  - `X` — data matrices (layers). `raw` holds raw counts; some builds add
    `normalized`.
  - `var` — gene metadata (`SOMADataFrame`).
  - `feature_dataset_presence_matrix` — sparse boolean array marking which genes
    were measured in each dataset.

```python
obs   = census["census_data"]["homo_sapiens"].obs
var   = census["census_data"]["homo_sapiens"].ms["RNA"].var
X_raw = census["census_data"]["homo_sapiens"].ms["RNA"].X["raw"]
```

### SOMA object types you will encounter

- **DataFrame** — tabular (`obs`, `var`).
- **SparseNDArray** — sparse matrices (`X` layers, presence matrix).
- **DenseNDArray** — dense arrays (embeddings, less common).
- **Collection** — container for related objects.
- **Experiment / Measurement** — top-level per-organism / per-modality containers.
- **SOMAScene**, `obs_spatial_presence` — spatial-transcriptomics scenes and
  availability flags (present only for spatial data).

## Cell Metadata Fields (`obs`)

**Identity & dataset**

- `soma_joinid` — unique integer key for joins.
- `dataset_id` — source dataset identifier.
- `is_primary_data` — boolean; `True` = a unique cell, `False` = a duplicate of a
  cell already counted in another dataset. **Filter `== True` in almost every query.**

**Cell type**

- `cell_type`, `cell_type_ontology_term_id` (e.g. `CL:0000236`).

**Tissue**

- `tissue` — specific tissue name.
- `tissue_general` — coarser grouping; prefer for cross-tissue queries.
- `tissue_ontology_term_id`.

**Assay**

- `assay`, `assay_ontology_term_id` — sequencing technology.

**Disease**

- `disease`, `disease_ontology_term_id` (`disease == 'normal'` for healthy).

**Donor & demographics**

- `donor_id`, `sex` (male / female / unknown), `self_reported_ethnicity`,
  `development_stage`, `development_stage_ontology_term_id`.

**Organism & technical**

- `organism`, `organism_ontology_term_id`.
- `suspension_type` — sample prep (cell / nucleus / na).

## Gene Metadata Fields (`var`)

- `soma_joinid` — unique integer key for joins.
- `feature_id` — Ensembl gene ID (e.g. `ENSG00000161798`).
- `feature_name` — gene symbol (e.g. `FOXP2`). Case-sensitive.
- `feature_length` — gene length in base pairs.

## Value-Filter Grammar

Filters are Python-like strings evaluated by TileDB-SOMA. They apply to
`get_obs(value_filter=...)`, `get_var(value_filter=...)`,
`get_anndata(obs_value_filter=..., var_value_filter=...)`, and
`soma.AxisQuery(value_filter=...)`.

**Comparison:** `==`, `!=`, `<`, `>`, `<=`, `>=`
**Membership:** `in` — `feature_id in ['ENSG00000161798', 'ENSG00000188229']`
**Logical:** `and` / `&`, `or` / `|`, grouped with parentheses

```python
# single
"cell_type == 'B cell'"
# multiple AND
"cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True"
# membership
"tissue in ['lung', 'liver', 'kidney']"
# grouped OR
"(cell_type == 'neuron' or cell_type == 'astrocyte') and disease != 'normal'"
# gene filter
"feature_name in ['CD4', 'CD8A', 'CD19']"
```

Ontology term IDs are more reliable than free-text labels across datasets:
`cell_type_ontology_term_id == 'CL:0000236'` beats `cell_type == 'B cell'` when
label spellings vary.

## Data Inclusion Criteria

A cell reaches the Census only if it meets all of:

1. **Species** — *Homo sapiens* or *Mus musculus*.
2. **Technology** — an approved RNA sequencing assay.
3. **Count type** — raw counts (no normalized-only / processed-only data).
4. **Metadata** — standardized to the CELLxGENE schema.
5. Both spatial and non-spatial transcriptomics are included.

This is why a gene or dataset you expect may be absent: it was filtered during
construction, or the gene was not measured in the datasets you queried.

## Count-Type Caveat

The `raw` layer mixes two count semantics:

- **Molecule counts** from UMI-based assays.
- **Full-gene read counts** from non-UMI assays.

They may warrant different normalization. Split by `assay` if this matters for
your analysis.

## Dataset Presence Matrix

Not every gene is measured in every dataset. Before drawing conclusions about a
specific gene, confirm coverage:

```python
presence = census["census_data"]["homo_sapiens"].ms["RNA"]["feature_dataset_presence_matrix"]
```

This sparse boolean matrix (datasets x genes) reveals gene coverage across
datasets, which datasets to include for a gene-specific analysis, and coverage-
driven batch effects. A `cellxgene_census.get_presence_matrix(...)` helper also
exists; confirm its exact signature against your installed version before use.

## Versioning

Releases are date-tagged (e.g. `"2023-12-15"`) plus rolling tags `"stable"` and
`"latest"`. `open_soma()` defaults to `"stable"`, which advances over time — pin
an explicit date for any reproducible analysis:

```python
census = cellxgene_census.open_soma(census_version="2023-12-15")
```

Use the same version across every step of a study, and consult the Census release
notes for schema changes between versions.
