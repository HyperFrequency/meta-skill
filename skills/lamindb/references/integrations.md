# Integrations

LaminDB slots into existing pipelines and platforms by being the data-and-
lineage layer beneath them. The recurring pattern: call `ln.track()`, load
inputs from LaminDB, do the external work, save outputs back as Artifacts, and
store the external system's IDs as Features. API names reflect current LaminDB.

## Storage backends

Storage is chosen at `lamin init` (see `setup-deployment.md`); once set, saving
and loading are transparent regardless of backend.

```python
artifact = ln.Artifact("data.csv", key="local/data.csv").save()
data = artifact.load()   # downloads from S3/GCS if not cached

# Read-only remote file (not copied into storage)
ln.Artifact("https://example.com/data.csv", key="remote/data.csv").save()

# HuggingFace dataset -> Artifact
from datasets import load_dataset
ds = load_dataset("squad", split="train")
ln.Artifact.from_dataframe(ds.to_pandas(), key="hf/squad_train.parquet").save()
```

## Workflow managers

### Nextflow / Snakemake

Wrap the process/rule body with `ln.track()` … `ln.finish()`; load inputs and
save outputs as Artifacts keyed by the pipeline's sample IDs.

```python
# Inside a Nextflow process script or a Snakemake `run:` block
import lamindb as ln
ln.track()
data = ln.Artifact.get(key="raw/batch_${batch_id}.csv").load()
result = process(data)
ln.Artifact.from_dataframe(result, key="processed/batch_${batch_id}.csv").save()
ln.finish()
```

### Redun

Stack `@ln.tracked()` under Redun's `@task()` so both track the same call:

```python
from redun import task
import lamindb as ln

@task()
@ln.tracked()
def process_dataset(input_key: str, output_key: str) -> str:
    data = ln.Artifact.get(key=input_key).load()
    ln.Artifact.from_dataframe(transform(data), key=output_key).save()
    return output_key
```

## MLOps platforms

Run both trackers side by side; log parameters to each, save the model to
LaminDB, and cross-reference the external run ID as a Feature.

### Weights & Biases

```python
import wandb, lamindb as ln, joblib
wandb.init(project="drug-response", name="exp-42")
ln.track(params={"model": "rf", "n_estimators": 100})

train = ln.Artifact.get(key="datasets/train.parquet").load()
model = train_model(train)
wandb.log({"accuracy": 0.95})

joblib.dump(model, "model.pkl")
art = ln.Artifact("model.pkl", key="models/exp-42.pkl").save()
art.features.add_values({"wandb_run_id": wandb.run.id})
ln.finish(); wandb.finish()
```

### MLflow / HuggingFace / scVI-tools

Same shape:

```python
# MLflow
import mlflow, lamindb as ln
mlflow.start_run(); ln.track()
mlflow.log_params(params); ln.context.params = params
model_art = ln.Artifact("model.pkl", key=f"models/{mlflow.active_run().info.run_id}.pkl").save()
mlflow.end_run(); ln.finish()

# scVI-tools — save the latent representation as a new Artifact
import scvi, lamindb as ln
ln.track()
adata = ln.Artifact.get(key="scrna/raw.h5ad").load()
scvi.model.SCVI.setup_anndata(adata, layer="counts")
m = scvi.model.SCVI(adata); m.train()
adata.obsm["X_scvi"] = m.get_latent_representation()
ln.Artifact.from_anndata(adata, key="scrna/scvi_latent.h5ad").save()
ln.finish()
```

## Array stores and SQL

### TileDB-SOMA

Register a SOMA experiment URI as an Artifact; read it back with the SOMA API.
Pairs with cellxgene. See `curation.md` for slot-based SOMA validation.

### DuckDB

Query a Parquet Artifact in place — cache the path, hand it to DuckDB, save the
result back:

```python
import duckdb, lamindb as ln
path = ln.Artifact.get(key="datasets/large.parquet").cache()
res = duckdb.query(
    f"SELECT cell_type, COUNT(*) c FROM read_parquet('{path}') GROUP BY cell_type"
).to_df()
ln.Artifact.from_dataframe(res, key="analysis/cell_type_counts.parquet").save()
```

## Visualization — Vitessce

Build a Vitessce config from an AnnData Artifact and register the config JSON as
its own Artifact for sharing/reproducibility.

## Module plugins

```python
# Bionty (ontologies) — see ontologies.md
import bionty as bt
bt.CellType.import_source()

# WetLab entities
import lamindb_wetlab as wetlab
wetlab.Experiment(name="RNA-seq batch 1").save()

# Clinical (OMOP CDM)
import lamindb_clinical as clinical
clinical.Patient(patient_id="P001").save()
```

## Git sync

With a configured sync repo, `ln.track()` captures the git commit hash and
source code, tying Transforms to code versions:

```bash
export LAMINDB_SYNC_GIT_REPO=https://github.com/user/repo.git
lamin settings set dev-dir .
```

```python
transform = ln.Transform.get(name="analysis.py")
transform.source_code   # code at the recorded commit
transform.hash          # git commit hash
```

Commit before tracking so the captured commit reflects the code that ran.

## Custom sources (API, SQL DB)

Fetch from any source, convert to a DataFrame, save as an Artifact, and record
provenance as Features (e.g. `api_url`). Wrap in `ln.track()`/`ln.finish()` so
the fetch itself is part of the lineage.

## Enterprise — Benchling

LaminDB can sync schemas and data from Benchling registries on team/enterprise
plans. For Benchling-native workflows see `benchling-integration`; for DNAnexus
see `dnanexus-integration`.

## Best practices

1. `ln.track()` in every integrated workflow so nothing escapes lineage.
2. Store external IDs (W&B run, MLflow run, API URL) as Features for join-back.
3. Treat LaminDB as the single source of truth for data artifacts.
4. Log parameters to both LaminDB and the ML platform.
5. Keep code (git), data (LaminDB), and experiments (ML platform) versioned in step.
6. Verify each integration on a small dataset, checking `view_lineage()`.
