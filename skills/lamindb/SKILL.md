---
name: lamindb
version: 0.1.0
description: >-
  LaminDB is an open-source Python data framework for biology that makes
  datasets queryable, traceable, and reproducible. Use it to version data
  artifacts (DataFrame, AnnData, Parquet, Zarr, TileDB-SOMA), auto-capture
  code and run lineage with ln.track()/ln.finish(),
  validate and curate data against typed Feature schemas, and annotate with
  biological ontologies (genes, cell types, tissues, diseases) through the
  Bionty plugin. Reach for it when building a queryable data lakehouse over many
  biological datasets, tracking notebook or pipeline provenance, standardizing
  metadata against ontologies, or wiring lineage into Nextflow/Snakemake and
  MLOps tools (W&B, MLflow, scVI-tools). Do NOT use it for single-cell analysis
  algorithms themselves (normalization, clustering, UMAP — use anndata/scanpy),
  for generic tabular or out-of-core compute (use polars/dask), or as a plain
  object store when you need no metadata, validation, or lineage — LaminDB's
  value is the registry and provenance layer, not raw bytes.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (LaminDB, laminlabs/lamindb)"
---

# LaminDB

## Overview

LaminDB is a Python-first data framework that turns a collection of files and
in-memory objects into a queryable, versioned, lineage-tracked registry. Every
dataset becomes an **Artifact** with a stable key, a content hash, and automatic
version history. Every notebook or script run is captured as a **Run** of a
**Transform**, so you can trace any output back to the exact code, inputs,
parameters, and environment that produced it. **Features** give you typed,
searchable metadata, and the **Bionty** plugin validates that metadata against
public biological ontologies (Ensembl genes, Cell Ontology, Uberon tissues,
Mondo/DOID diseases, and more).

The mental model: LaminDB is a metadata database plus a storage abstraction. The
database (SQLite for dev, PostgreSQL for production) holds registries and
provenance; the storage backend (local, S3, GCS) holds the actual bytes. You
query the database, then lazily fetch or stream the data you need.

This SKILL.md is a **router**. It gives you the object model, a quick-start
path, and a capability map, then delegates deep API surface, examples, and
troubleshooting to `references/`.

## When to Use This Skill

- Building a **queryable data lakehouse**: one filter/search interface across
  many scRNA-seq, spatial, flow-cytometry, bulk, or clinical datasets.
- **Tracking provenance**: capturing which code, inputs, and parameters
  produced a given result, and visualizing the lineage graph.
- **Curating and validating** data: enforcing schemas on DataFrames, AnnData,
  MuData, SpatialData, or TileDB-SOMA before analysis.
- **Standardizing metadata** against biological ontologies (genes, cell types,
  tissues, diseases) so datasets share a controlled vocabulary.
- **Wiring lineage into pipelines** (Nextflow, Snakemake, Redun) or MLOps
  platforms (Weights & Biases, MLflow, HuggingFace, scVI-tools).
- **Versioning datasets** without duplicating keys as data or code evolves.

## When NOT to Use This Skill

- You need the **analysis algorithms themselves** — normalization, PCA,
  neighbors, clustering, UMAP. Those live in scanpy; for the data container and
  `.h5ad`/`.zarr` I/O see `anndata`.
- You want **generic tabular transforms** (`polars`) or **out-of-core array
  compute** (`dask`). LaminDB tracks and stores; it does not compute.
- You need a **plain object store** with no metadata, validation, or lineage
  requirements — the registry overhead buys you nothing there.
- Your entities live in an external system of record (e.g. an ELN/LIMS). For
  Benchling and DNAnexus workflows see `benchling-integration` and
  `dnanexus-integration`; LaminDB can sync with, not replace, them.

## Core Object Model

| Entity | What it is | Key calls |
| --- | --- | --- |
| **Artifact** | A versioned dataset (file or object) with a key + hash | `ln.Artifact(...).save()`, `.load()`, `.cache()`, `.describe()` |
| **Record** | An experimental entity (sample, perturbation, instrument), optionally typed and hierarchical | `ln.Record(name=..., type=...).save()` |
| **Transform** | A reusable analysis step (notebook, script, function) | captured by `ln.track()` / `@ln.tracked()` |
| **Run** | One execution of a Transform, with inputs, outputs, params | `artifact.run`, `run.inputs` |
| **Feature** | A typed metadata field for annotation and querying | `ln.Feature(name=..., dtype=...).save()` |
| **Schema** | A validation contract binding Features to a data structure | `ln.Schema(...).save()` |
| **Collection** | A named group of artifacts | `ln.Collection([...], name=...).save()` |
| **Bionty registries** | Ontology-backed registries (Gene, CellType, Tissue, Disease, ...) | `import bionty as bt` |

## Quick Start

```bash
pip install lamindb            # add extras as needed: 'lamindb[gcp,zarr,fcs]'
lamin login                    # authenticate (metadata only; your data stays private)
lamin init --storage ./mydata --modules bionty   # local SQLite instance
```

```python
import lamindb as ln

ln.track()                                         # begin lineage capture

df = ...                                            # a pandas DataFrame
artifact = ln.Artifact.from_dataframe(
    df, key="experiments/batch1.parquet",
    description="Processed batch 1",
).save()                                            # register + store + version

artifact.features.add_values({"tissue": "PBMC", "condition": "treated"})

# Query the registry, then load only what you need
hits = ln.Artifact.filter(
    key__startswith="experiments/", tissue="PBMC",
).to_dataframe()

ln.finish()                                         # close the run
```

The two habits that make everything else work: call `ln.track()` at the start of
every analysis, and **query metadata before loading bytes**.

## Capability Map

Read the reference that matches your task:

- **`references/core-concepts.md`** — Artifacts, Records, Runs/Transforms,
  Features, versioning, and lineage (`view_lineage()`, `@ln.tracked()`,
  parameter and project tracking). Start here to understand the model.
- **`references/querying.md`** — filtering with `__gt`/`__contains`/`__in`,
  feature and cross-registry queries, `Q` objects (AND/OR/NOT), full-text
  `search()`, lazy QuerySets, streaming large arrays (`backed()`,
  `open()`, iterators), and Collections.
- **`references/curation.md`** — Schema design (flexible / minimal / strict),
  `DataFrameCurator` and `AnnDataCurator`, slot-based curation for MuData /
  SpatialData / TileDB-SOMA, `.cat.standardize()` / `.cat.add_ontology()`, and
  resolving validation errors.
- **`references/ontologies.md`** — the Bionty registries, `import_source()`,
  `validate()` / `standardize()` / `from_values()`, hierarchy navigation,
  custom terms and synonyms, multi-organism gene handling, and source
  versioning.
- **`references/setup-deployment.md`** — installation and extras, `lamin init`
  for SQLite / S3 / GCS / PostgreSQL, `lamin connect`, cache and settings,
  local-to-cloud and multi-region deployment, migrations, and security.
- **`references/integrations.md`** — storage backends, workflow managers
  (Nextflow, Snakemake, Redun), MLOps (W&B, MLflow, HuggingFace, scVI-tools),
  DuckDB / TileDB-SOMA / Vitessce, module plugins (wetlab, clinical), and git
  sync.

## Working Principles

1. **Track everything** — `ln.track()` at the top of every notebook/script.
2. **Validate early** — define Features and a Schema before deep analysis.
3. **Query before you load** — filter the registry, then `.load()` or stream.
4. **Version, don't rename** — reuse the same key so history is preserved.
5. **Standardize with ontologies** — Bionty `standardize()` before annotating.
6. **Structure keys hierarchically** — e.g. `project/experiment/batch/file.h5ad`.
7. **Start local, scale cloud** — SQLite for dev, PostgreSQL + S3/GCS for prod.

## Version and API Notes

LaminDB's API has evolved across releases. Notably, older tutorials use `.df()`
and `Artifact.from_df(...)`, which current versions expose as `.to_dataframe()`
and `Artifact.from_dataframe(...)`. The reference files use the current names.
If a call is rejected, confirm the exact signature for your installed version
against docs.lamin.ai rather than guessing — and pin `lamindb` in reproducible
environments so lineage stays stable.

## External Resources

- Documentation: https://docs.lamin.ai
- API reference: https://docs.lamin.ai/api
- Source: https://github.com/laminlabs/lamindb
- Bionty: https://github.com/laminlabs/bionty
