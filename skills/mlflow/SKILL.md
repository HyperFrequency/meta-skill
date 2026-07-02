---
name: mlflow
version: 1.0.0
description: Framework-agnostic ML lifecycle platform — experiment tracking (params/metrics/artifacts), model registry with versioning + aliases, and model serving/deployment. Use WHEN you need to log and compare training runs, register/version models for promotion, reproduce experiments, or serve a model behind an endpoint, across any framework (sklearn, PyTorch, Lightning, Keras/TF, XGBoost, HuggingFace). Use WHEN-NOT for the actual model training/tuning (use pytorch-lightning, scikit-learn, transformers), for SHAP explainability (use shap), for trading backtests/portfolio analytics (use vectorbt/nautilus), or for pure data orchestration/scheduling pipelines (use a workflow engine, not MLflow).
author: Orchestra Research
license: MIT
tags: [MLOps, MLflow, Experiment Tracking, Model Registry, ML Lifecycle, Deployment, Model Versioning, PyTorch, TensorFlow, Scikit-Learn, HuggingFace]
dependencies: [mlflow, sqlalchemy, boto3]
---

# MLflow: ML Lifecycle Management Platform

Open-source, framework-agnostic platform (Apache 2.0) for the full ML lifecycle:
tracking, model registry, and deployment. This file is a router — deep guides live
in `references/`.

## When to Use

- **Track experiments** — log params, metrics, artifacts; compare runs.
- **Registry** — version models, promote with aliases, govern lifecycle.
- **Deploy / serve** — local server, REST, Docker, SageMaker/Azure ML.
- **Reproduce** — re-run with captured params + environment.

**When NOT:** training/tuning itself (`pytorch-lightning`, `scikit-learn`,
`transformers`), explainability (`shap`), trading backtests (`vectorbt`).

## Install

```bash
pip install mlflow            # core
pip install mlflow[extras]    # + SQLAlchemy, boto3, etc.
mlflow ui                     # local UI at http://localhost:5000
```

## Quick Start

```python
import mlflow

mlflow.set_experiment("my-experiment")
with mlflow.start_run(run_name="baseline"):
    mlflow.log_params({"learning_rate": 0.001, "batch_size": 32})
    model = train_model()
    mlflow.log_metric("val_accuracy", 0.92)
    mlflow.sklearn.log_model(model, "model")
```

### Autologging (zero-boilerplate capture)

```python
mlflow.autolog()              # all supported frameworks
# or per-framework: mlflow.sklearn.autolog(), mlflow.pytorch.autolog(),
#                   mlflow.keras.autolog(), mlflow.xgboost.autolog(),
#                   mlflow.transformers.autolog()
model.fit(X_train, y_train)   # params, metrics, model logged automatically
```

Autolog wraps the framework's `fit`/`train`; for PyTorch use it with Lightning
(plain PyTorch loops still log metrics manually). See `references/tracking.md`.

## Core Concepts (1-minute model)

- **Experiment** — named container for related runs.
- **Run** — one execution; holds params, metrics (can be stepped), artifacts, a model.
- **Artifact** — any file/dir (`log_artifact`/`log_artifacts`); dicts via `log_dict`.
- **Flavor** — framework-specific model logger (`mlflow.<flavor>.log_model`); a
  logged model also carries the generic `pyfunc` flavor for uniform loading.
- **Tracking URI** — where runs are stored (local dir, SQL DB, or remote server).

Step-wise metrics for training curves:

```python
for epoch in range(num_epochs):
    mlflow.log_metric("train_loss", train_loss, step=epoch)
    mlflow.log_metric("val_loss", val_loss, step=epoch)
```

Full param/metric/artifact/model logging reference → `references/tracking.md`.

## Model Registry

Register a model, then promote versions. **Aliases are the modern mechanism**
(`champion`, `challenger`, …); the legacy **stages** API
(`transition_model_version_stage`, `get_latest_versions`, None/Staging/Production/
Archived) is **deprecated since MLflow 2.9** and slated for removal — prefer aliases
+ tags for new work.

```python
import mlflow
from mlflow import MlflowClient

# Register at log time...
mlflow.sklearn.log_model(model, "model", registered_model_name="my-classifier")
# ...or after the fact:
mlflow.register_model(f"runs:/{run_id}/model", "my-classifier")

client = MlflowClient()
# Modern promotion: assign an alias to a version
client.set_registered_model_alias("my-classifier", "champion", version=3)

# Load by alias (or by explicit version)
model = mlflow.pyfunc.load_model("models:/my-classifier@champion")
model = mlflow.pyfunc.load_model("models:/my-classifier/3")
```

Versioning, search (`search_model_versions`), annotations/tags, and the
stages→aliases migration → `references/model-registry.md`.

## Searching Runs

```python
runs = MlflowClient().search_runs(
    experiment_ids=[exp_id],
    filter_string="metrics.accuracy > 0.9 AND params.model = 'ResNet50'",
    order_by=["metrics.accuracy DESC"],
    max_results=10,
)
```

Filter-string grammar and run comparison → `references/tracking.md`.

## Deployment

```bash
# Serve a registered model as a REST endpoint
mlflow models serve -m "models:/my-classifier@champion" -p 5001
# Predict
curl http://127.0.0.1:5001/invocations -H 'Content-Type: application/json' \
  -d '{"inputs": [[1.0, 2.0, 3.0, 4.0]]}'
```

Docker, batch inference, SageMaker/Azure ML, and monitoring →
`references/deployment.md`.

## Configuration

```python
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")   # or env MLFLOW_TRACKING_URI
```

```bash
# Remote tracking server with DB backend + artifact store
mlflow server \
  --backend-store-uri postgresql://user:pass@localhost/mlflow \
  --default-artifact-root s3://my-bucket/mlflow \
  --host 0.0.0.0 --port 5000
```

## Best Practices

- One experiment per task/objective; descriptive `run_name`s, not auto-UUIDs.
- Log full metadata: hyperparams, dataset, framework version, git commit (as tags).
- Reference models for deployment by registry alias, not hard-coded `runs:/<id>`.
- Track lineage by tagging downstream runs with the upstream `run_id`.

## See Also

References (this skill):
- `references/tracking.md` — params/metrics/artifacts/models, autolog, search.
- `references/model-registry.md` — versioning, aliases, stages migration, governance.
- `references/deployment.md` — local/REST/Docker/cloud serving, monitoring.

Sibling skills (MLflow tracks them; it does not replace them):
- `pytorch-lightning`, `scikit-learn`, `transformers` — model training/tuning.
- `shap` — explainability of the models you log here.

Upstream: [docs](https://mlflow.org/docs/latest) ·
[GitHub](https://github.com/mlflow/mlflow) ·
[examples](https://github.com/mlflow/mlflow/tree/master/examples)
