# Persisting Results

**The job container is destroyed when the job ends. Any file on local disk is
lost.** If a job produces something you need, it must leave the container before
completion. There are three durable paths: push to the Hub, mount a bucket/
volume, or send to external storage.

## 1. Push to the Hugging Face Hub

Requires `secrets={"HF_TOKEN": "$HF_TOKEN"}` on the job and a write-scoped token.

```python
# Models
model.push_to_hub("username/model-name")        # token auto-detected from env
tokenizer.push_to_hub("username/model-name")

# Datasets
dataset.push_to_hub("username/dataset-name")

# Arbitrary files / artifacts
from huggingface_hub import HfApi
api = HfApi()                                    # auto-detects HF_TOKEN
api.upload_file(
    path_or_fileobj="results.json",
    path_in_repo="results.json",
    repo_id="username/results",
    repo_type="dataset",
)
```

Repos are auto-created on first push if the token has write access; or create
explicitly with `api.create_repo("username/name", repo_type="dataset", private=True)`.
Use `JOB_ID` in the repo name for unique, collision-free outputs.

Wrap pushes so a failure is loud, not silent:

```python
try:
    dataset.push_to_hub("username/dataset")
    print("push ok")
except Exception as e:
    print(f"push failed: {e}")
    raise
```

## 2. Mount a volume or storage bucket

Volumes let a job read/write a repo or a Storage Bucket as a normal directory —
useful for large inputs (no download) and for durable, mutable outputs like
training checkpoints.

```python
from huggingface_hub import run_uv_job, Volume

# Read a dataset repo directly (no full download)
run_uv_job(
    "process.py",
    volumes=[Volume(type="dataset", source="HuggingFaceFW/fineweb", mount_path="/data")],
)

# Write checkpoints to a bucket (read+write by default)
ckpt = Volume(type="bucket", source="username/my-bucket", mount_path="/out")
run_uv_job("train.py", script_args=["--output_dir", "/out/run-v3"], volumes=[ckpt])
```

Volume types: `model`, `dataset`, `space`, `bucket`. Buckets are read+write by
default; pass `read_only=True` for read-only. In the CLI, use `-v`:
`hf jobs uv run -v ./pdfs:/input -v ./md-out:/output:rw ocr.py`.

### Syncing local data in and out

`sync_job_volume(local_dir, mount_path)` uploads a local directory to your
`jobs-artifacts` bucket (created if needed) and returns a ready-to-mount
`Volume`; re-running only uploads changed files. To retrieve outputs, mount a
read-write volume and pull it back with `sync_bucket` after the job finishes.

```python
from huggingface_hub import run_uv_job, sync_job_volume, sync_bucket

data = sync_job_volume("./training-data", "/data")            # read-only by default
outputs = sync_job_volume("./outputs", "/outputs", read_only=False)
job = run_uv_job("train.py", volumes=[data, outputs])
# ...after completion:
sync_bucket(f"hf://buckets/{outputs.source}/{outputs.path}", "./outputs")
```

## 3. External storage / API

```python
import boto3
boto3.client("s3").upload_file("results.json", "my-bucket", "results.json")

import requests
requests.post("https://your-api.com/results", json=results)
```

## Pre-submission checklist

- [ ] A persistence method (push, bucket, or external) is actually in the script.
- [ ] `secrets={"HF_TOKEN": "$HF_TOKEN"}` set if pushing to the Hub.
- [ ] Script asserts the token exists before Hub calls (`assert "HF_TOKEN" in os.environ`).
- [ ] Target repo/namespace is writable by the token owner.
- [ ] Push/upload is wrapped in error handling so failures surface in logs.
