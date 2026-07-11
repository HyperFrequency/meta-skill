# Querying, Filtering, and Streaming

LaminDB registries are queried with a Django-ORM-style API. QuerySets are lazy —
they hit the database only when evaluated (`.to_dataframe()`, iteration,
`.count()`, `.first()`). API names reflect current LaminDB.

## Browsing registries

```python
import lamindb as ln

ln.view()                        # overview across modules
ln.Artifact.to_dataframe()       # latest artifacts
ln.Transform.to_dataframe()
ln.Run.to_dataframe()
```

## Lookup (auto-complete)

For registries under ~100k records, `lookup()` returns an object with
attribute-style, IDE-autocompletable access:

```python
records = ln.Record.lookup()
sample = records.sample_a

import bionty as bt
cell_types = bt.CellType.lookup()
t_cell = cell_types.t_cell
```

## Single-record retrieval

```python
ln.Artifact.get(key="data/experiment.h5ad")     # exactly one, else error
ln.Artifact.filter(key="data.csv").one()          # exactly one from a QuerySet
ln.Artifact.filter(key="maybe.csv").one_or_none() # one or None (error if >1)
ln.Artifact.filter(suffix=".h5ad").first()        # first match or None
```

## Filtering

`filter()` returns a QuerySet; multiple kwargs are AND-combined. Field lookups
use the `__` suffix operators.

```python
ln.Artifact.filter(suffix=".h5ad", created_by=user)

# Numeric comparison
ln.Artifact.filter(size__gt=1e6).to_dataframe()
ln.Artifact.filter(size__gte=1e6, size__lte=1e9).to_dataframe()

# String matching
ln.Artifact.filter(description__contains="RNA").to_dataframe()   # case-sensitive
ln.Artifact.filter(description__icontains="rna").to_dataframe()  # case-insensitive
ln.Artifact.filter(key__startswith="experiments/").to_dataframe()
ln.Artifact.filter(key__endswith=".csv").to_dataframe()
ln.Artifact.filter(suffix__in=[".h5ad", ".csv"]).to_dataframe()
```

## Feature-based queries

Query artifacts by their annotated Features (see `core-concepts.md`):

```python
ln.Artifact.filter(cell_type="T cell").to_dataframe()
ln.Artifact.filter(treatment="DMSO").to_dataframe(include="features")
ln.Artifact.filter(cell_type__isnull=False).to_dataframe()  # has annotation
ln.Artifact.filter(study_metadata__assay="RNA-seq").to_dataframe()  # nested dict
```

## Traversing related registries

The double-underscore syntax walks foreign keys across tables:

```python
ln.Artifact.filter(created_by__handle="researcher123").to_dataframe()
ln.Artifact.filter(transform__name="preprocess.py").to_dataframe()
ln.Artifact.filter(feature_sets__genes__symbol="CD8A").to_dataframe()
ln.Run.filter(params__downsample=True).to_dataframe()
```

## Logical queries with Q

Import `Q` for OR / NOT / grouped logic:

```python
from lamindb import Q

ln.Artifact.filter(Q(suffix=".jpg") | Q(suffix=".png")).to_dataframe()   # OR
ln.Artifact.filter(~Q(suffix=".tmp")).to_dataframe()                     # NOT

ln.Artifact.filter(
    (Q(suffix=".h5ad") | Q(suffix=".csv"))
    & Q(size__gt=1e6)
    & ~Q(created_by__handle__startswith="test")
).to_dataframe()
```

## Full-text search

```python
ln.Artifact.search("iris").to_dataframe()
bt.CellType.search("T cell").to_dataframe()
bt.Gene.search("CD8").to_dataframe()
```

## QuerySets: ordering, chaining, evaluation

```python
qs = ln.Artifact.filter(suffix=".h5ad")     # no DB hit yet
qs = qs.filter(size__gt=1e6).order_by("-created_at")   # chain, still lazy

qs.to_dataframe()      # -> pandas DataFrame
list(qs)               # -> list of records
qs.count()             # -> int
qs.exists()            # -> bool
qs[:10]                # slicing
for artifact in qs:    # iteration
    ...
```

## Streaming large datasets

Do not `.load()` data that does not fit in memory. Options:

```python
# Byte streaming
with ln.Artifact.get(key="large.csv").open() as f:
    chunk = f.read(10_000)

# Backed arrays (Zarr / HDF5 / AnnData) — slice without loading
adata = ln.Artifact.get(key="large.h5ad").backed()
subset = adata[:1000, :]                    # first 1000 cells
for i in range(0, adata.n_obs, 1000):       # batch iterate
    batch = adata[i:i+1000, :]

# Iterate a collection of files in chunks
for artifact in ln.Artifact.filter(suffix=".fastq.gz").iterator(chunk_size=10):
    path = artifact.cache()
```

## Aggregation

QuerySets expose the underlying Django ORM for aggregation:

```python
ln.Artifact.filter(suffix=".h5ad").count()
ln.Artifact.values_list("suffix", flat=True).distinct()

from django.db.models import Sum, Avg
ln.Artifact.aggregate(Sum("size"))
ln.Artifact.values("suffix").annotate(avg_size=Avg("size"))
```

## Organizing with keys and collections

```python
# Hierarchical keys → browse by prefix
ln.Artifact("data.h5ad", key="scrna/2025/oct/sample_001.h5ad").save()
ln.Artifact.filter(key__startswith="scrna/2025/oct/").to_dataframe()

# Collections group artifacts into a named dataset
collection = ln.Collection(
    [artifact1, artifact2, artifact3],
    name="scRNA-seq batches 1-3",
).save()
for artifact in collection.artifacts:
    ...
```

## Common patterns

```python
ln.Artifact.order_by("-created_at")[:10].to_dataframe()   # most recent

me = ln.setup.settings.user
ln.Artifact.filter(created_by=me).to_dataframe()          # mine

ln.Artifact.filter(created_at__year=2025, created_at__month=10).to_dataframe()

ln.Artifact.filter(
    is_valid=True, cell_type__isnull=False,
).to_dataframe(include="features")                        # validated + annotated
```

## Best practices

1. Filter metadata before loading bytes — cheap query, expensive download.
2. Build queries incrementally; QuerySets are lazy and composable.
3. Use `backed()` / `open()` / `iterator()` for data larger than RAM.
4. Prefer `one_or_none()` / `exists()` over `get()` when a miss is expected.
5. Structure keys hierarchically so `key__startswith` browsing works.
