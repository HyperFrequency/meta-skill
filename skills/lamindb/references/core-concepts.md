# Core Concepts: Artifacts, Records, Runs, Features, Lineage

The building blocks of a LaminDB instance. API names reflect current LaminDB;
verify against docs.lamin.ai for your installed version.

## Artifacts

An Artifact is a versioned dataset — a file or an in-memory object (DataFrame,
AnnData, SpatialData, Parquet, Zarr, etc.). It is identified by a `key`
(a human path) and a content hash (which drives deduplication and versioning).

### Create and save

```python
import lamindb as ln

# From a file on disk
ln.Artifact("sample.fasta", key="sample.fasta").save()

# From a pandas DataFrame
artifact = ln.Artifact.from_dataframe(
    df, key="datasets/processed.parquet",
    description="Processed experimental data",
).save()

# From AnnData
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
artifact = ln.Artifact.from_anndata(
    adata, key="scrna/experiment1.h5ad",
    description="scRNA-seq with QC",
).save()
```

`Artifact(...)` builds an unsaved object; nothing is registered or uploaded
until you call `.save()`.

### Retrieve and access

```python
artifact = ln.Artifact.get(key="datasets/processed.parquet")  # by key
artifact = ln.Artifact.get("aRt1Fact0uid000")                 # by UID
artifact = ln.Artifact.filter(suffix=".h5ad").first()          # by filter

data = artifact.load()          # into memory (DataFrame, AnnData, ...)
path = artifact.cache()         # local cached path (downloads if needed)
with artifact.open() as f:      # stream without full download
    chunk = f.read(1000)
```

### Metadata

```python
artifact.describe()             # full metadata + validation status
artifact.size                   # bytes
artifact.suffix                 # extension
artifact.created_at             # timestamp
artifact.created_by             # User
artifact.run                    # the Run that produced it
artifact.transform              # the Transform (code)
artifact.version                # version string
```

## Records

Records model experimental entities — samples, perturbations, instruments, cell
lines. Use `is_type=True` to define a category, then create instances of it.
Records support parent/child hierarchies.

```python
sample_type = ln.Record(name="Sample", is_type=True).save()
ln.Record(name="P53mutant1", type=sample_type).save()
ln.Record(name="WT-control", type=sample_type).save()

ln.Record.search("p53").to_dataframe()             # full-text
ln.Record.filter(type=sample_type).to_dataframe()  # by field

# Hierarchies
parent = ln.Record.get(name="P53mutant1")
child = ln.Record(name="P53mutant1-rep1", type=sample_type).save()
child.parents.add(parent)
parent.children.to_dataframe()
```

## Runs and Transforms

A **Transform** is a reusable analysis step (a notebook, script, or function).
A **Run** is one execution of it, recording inputs, outputs, parameters, and
environment. This pair is the backbone of lineage.

### Notebook / script tracking

```python
ln.track()                      # at the start — captures code, env, git commit
# ... analysis ...
artifact = ln.Artifact("output.csv", key="output.csv").save()
ln.finish()                     # at the end — closes the run, writes report
```

### Parameters and projects

```python
ln.track(params={"learning_rate": 0.01, "batch_size": 32, "epochs": 100})
ln.Run.filter(params__learning_rate=0.01).to_dataframe()   # query by param

ln.track(project="Cancer Drug Screen 2025")
project = ln.Project.get(name="Cancer Drug Screen 2025")
ln.Artifact.filter(projects=project).to_dataframe()
```

### Function-level tracking

The `@ln.tracked()` decorator records a Transform + Run per call, auto-tracking
loaded and saved artifacts as inputs/outputs:

```python
@ln.tracked()
def preprocess(input_key: str, output_key: str, normalize: bool = True) -> None:
    data = ln.Artifact.get(key=input_key).load()
    if normalize:
        data = (data - data.mean()) / data.std()
    ln.Artifact.from_dataframe(data, key=output_key).save()
```

### Reading lineage

```python
artifact = ln.Artifact.get(key="output.csv")
run = artifact.run
transform = run.transform
run.inputs.to_dataframe()       # input artifacts
run.report                      # execution report
artifact.view_lineage()         # render the provenance graph
```

## Features

Features are typed metadata fields — the schema of your annotations and the axis
you query on.

```python
from datetime import date
ln.Feature(name="gc_content", dtype=float).save()
ln.Feature(name="read_count", dtype=int).save()
ln.Feature(name="experiment_date", dtype=date).save()
ln.Feature(name="cell_type", dtype=str).save()

# Annotate an artifact
artifact.features.add_values({"gc_content": 0.55, "experiment_date": "2025-10-31"})

# Query by feature value / comparison / presence
ln.Artifact.filter(gc_content=0.55).to_dataframe()
ln.Artifact.filter(read_count__gt=1_000_000).to_dataframe()
ln.Artifact.filter(cell_type__isnull=False).to_dataframe(include="features")

# Nested dict features
ln.Artifact.filter(study_metadata__assay__type="RNA-seq").to_dataframe()
```

## Data lineage — what gets captured

On `ln.track()`, LaminDB records: source code and git commit, Python package
versions, input artifacts loaded during the run, output artifacts created,
execution timestamps and user, parameters, and the Transform relationships that
chain runs together.

```python
# Query by provenance
transform = ln.Transform.get(name="preprocessing.py")
ln.Artifact.filter(transform=transform).to_dataframe()      # all outputs of code

input_artifact = ln.Artifact.get(key="raw/data.csv")
runs = ln.Run.filter(inputs=input_artifact)
ln.Artifact.filter(run__in=runs).to_dataframe()             # everything derived
```

## Versioning

Saving to the **same key** with changed content creates a new version rather
than overwriting — history is preserved and queryable.

```python
v1 = ln.Artifact("data.csv", key="experiment/data.csv").save()
# ... modify data.csv ...
v2 = ln.Artifact("data.csv", key="experiment/data.csv").save()  # new version

artifact = ln.Artifact.get(key="experiment/data.csv")   # latest by default
artifact.versions.to_dataframe()                        # full history
first = artifact.versions.filter(version="1").first()   # a specific version
```

## Best practices

1. Use meaningful hierarchical keys (`project/experiment/sample.h5ad`).
2. Add descriptions so future readers understand contents.
3. Call `ln.track()` at the start of every analysis.
4. Define Features up front, with explicit dtypes, before annotating.
5. Reuse keys to version — don't mint a new key for a minor change.
6. Docstring `@ln.tracked()` functions; the docstring becomes Transform docs.
7. Group related work under a project for organization and access control.
8. Use `view_lineage()` to sanity-check provenance before trusting a result.
