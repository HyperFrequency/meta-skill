# Creating, streaming, and publishing Hub datasets

Repo lifecycle and upload patterns using `huggingface_hub` (repo + file operations)
and `datasets` (typed dataset objects). All write operations need a **write**-scoped
`HF_TOKEN`.

## Authentication

```bash
export HF_TOKEN="hf_..."          # write scope for create/push/private
# or interactively:
huggingface-cli login             # stores token in ~/.cache/huggingface/token
```

Every function below accepts `token=...`; when omitted, `huggingface_hub` falls back
to the cached login or `HF_TOKEN`.

## Create a dataset repository

```python
from huggingface_hub import create_repo
from huggingface_hub.utils import HfHubHTTPError

try:
    create_repo("your-username/my-dataset", repo_type="dataset", private=True)
except HfHubHTTPError as e:
    if "409" in str(e):
        print("Repo already exists — continuing.")   # idempotent create
    else:
        raise
```

Seed a dataset card (`README.md`) so the dataset renders on the Hub:

```python
from huggingface_hub import HfApi
api = HfApi()
card = """---
license: mit
---

# my-dataset

Curated subset built with SQL over the Hub.
"""
api.upload_file(
    path_or_fileobj=card.encode(),
    path_in_repo="README.md",
    repo_id="your-username/my-dataset",
    repo_type="dataset",
    commit_message="Add dataset card",
)
```

## Path A — publish a whole result set (`datasets.push_to_hub`)

Best when you have the full rows in memory (e.g. a DuckDB query result).

```python
from datasets import Dataset

ds = Dataset.from_list(rows)          # rows: list[dict], one dict per example
# ds = Dataset.from_pandas(df)        # from a pandas DataFrame
# ds = Dataset.from_dict({"text": [...], "label": [...]})

ds.push_to_hub(
    "your-username/my-dataset",
    split="train",                    # target split name
    private=True,
    config_name="default",            # optional: name a config/subset
    commit_message="Add train split",
)
# -> https://huggingface.co/datasets/your-username/my-dataset
```

`push_to_hub` writes Parquet shards and updates the dataset card's config metadata,
so the result is immediately queryable via `hf://...@~parquet/...`.

## Path B — incremental streaming (append-only JSONL chunks)

Best for pipelines that emit rows over time. `create_repo` once, then append each
batch as a **new** timestamped file — no need to download or rewrite prior data.

```python
import json, time
from huggingface_hub import HfApi
api = HfApi()

def append_rows(repo_id, rows, split="train"):
    if not rows:
        return
    body = "\n".join(json.dumps(r) for r in rows).encode()
    fname = f"data/{split}-{int(time.time() * 1000)}.jsonl"   # unique per batch
    api.upload_file(
        path_or_fileobj=body,
        path_in_repo=fname,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Append {len(rows)} rows to {split}",
    )
```

The Hub concatenates all `data/train-*.jsonl` files into the `train` split at load
time. To read the accumulated split back:

```python
from datasets import load_dataset
ds = load_dataset("your-username/my-dataset", split="train")             # eager
it = load_dataset("your-username/my-dataset", split="train", streaming=True)  # lazy
```

Store a `config.json` alongside the data for run metadata or a generation system
prompt:

```python
cfg = {"version": "1.0", "created_at": time.time(), "system_prompt": "..."}
api.upload_file(
    path_or_fileobj=json.dumps(cfg, indent=2).encode(),
    path_in_repo="config.json", repo_id=repo_id, repo_type="dataset",
    commit_message="Store dataset config",
)
```

## Multiple configs and splits

- **Splits** — target with `split=` in `push_to_hub`, or with the `{split}` segment
  in streamed filenames (`data/test-*.jsonl`).
- **Configs (subsets)** — pass `config_name=` to `push_to_hub`. Each config is a
  named group of splits (mirrors `cais/mmlu`'s per-subject configs). The dataset
  card's `configs:` YAML block records the mapping; `push_to_hub` maintains it.

## Inspecting a dataset

```python
from huggingface_hub import HfApi
api = HfApi()

info = api.dataset_info("cais/mmlu")          # author, tags, downloads, card_data, ...
files = api.list_repo_files("cais/mmlu", repo_type="dataset")
data_files = [f for f in files if f.startswith("data/")]

repo = api.repo_info("your-username/my-dataset", repo_type="dataset")
print(repo.private, repo.last_modified)
```

Config/split names for building `hf://` paths live in `info.card_data` (the
`configs` key) or can be read straight off the Parquet tree under
`refs/convert/parquet` in `list_repo_files`.

## Failure modes and handling

| Symptom | Cause | Handling |
|---|---|---|
| `HfHubHTTPError` with `409` on create | Repo already exists | Catch and continue (create is idempotent as shown above). |
| `RepositoryNotFoundError` on upload/read | Repo missing, or private repo without a valid token | Verify `repo_id` spelling and that `HF_TOKEN` can see it. |
| `401` / `403` on push | Token missing write scope | Regenerate a **write** token at hf.co/settings/tokens. |
| `429` / rate limited | Too many requests (esp. anonymous) | Register a token; back off and retry with jitter. |
| Slow / failed push of many rows | One giant commit | Batch into shards; `push_to_hub` shards automatically, or stream in chunks. |
| Many small files bloating a repo | One `upload_file` per row | Accumulate rows and append per batch, not per row. |
| Uploading a large local tree | Single-call limits | Use `api.upload_folder(...)` / `upload_large_folder(...)` for many/large files. |

## Validation before upload

If you control the row shape, validate against a fixed schema before pushing to
avoid a mixed-schema dataset that fails to load. See `dataset-templates.md` for the
six template schemas and their required/recommended fields. A minimal check:

```python
def valid_rows(rows, required):
    return all(isinstance(r, dict) and required <= set(r) for r in rows)

assert valid_rows(rows, {"question", "answer"})   # e.g. the qa template
```
