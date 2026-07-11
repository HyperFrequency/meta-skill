---
name: hugging-face-datasets
version: 0.1.0
description: >-
  Query, transform, create, and publish datasets on the Hugging Face Hub. WHAT:
  run DuckDB SQL directly over any Hub dataset through the hf:// auto-Parquet
  protocol (filter, aggregate, sample, join, reshape) then export locally or push a
  derived subset to a new repo; and initialize dataset repos, stream JSONL row
  chunks without re-uploading, and validate rows against chat/classification/QA/
  completion/tabular templates using huggingface_hub and the datasets library. WHEN:
  building training or eval subsets from existing Hub datasets, inspecting a
  dataset's schema and value distribution without downloading it, or publishing a
  curated dataset. WHEN NOT: not for local-only DataFrame work (use polars, dask, or
  vaex), not for downloading model weights or running inference, and not for dataset
  discovery/search alone (use the Hugging Face MCP server).
license: Apache-2.0
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "DuckDB: MIT; huggingface_hub and datasets: Apache-2.0"
---

# Hugging Face Datasets

## Overview

Operate on datasets hosted on the Hugging Face Hub with two complementary tools:

- **DuckDB over `hf://`** — run SQL against any public (or token-authorized private)
  Hub dataset *in place*, without a full download. The Hub auto-converts every
  dataset to Parquet on a `refs/convert/parquet` branch, and DuckDB reads those
  files directly. Use it to explore schema, sample, aggregate, filter, join, and
  build derived subsets.
- **`huggingface_hub` + `datasets`** — create dataset repositories, stream new rows
  as append-only JSONL chunks, and publish query results or curated rows as a new
  dataset, optionally validated against a fixed row schema.

This skill teaches the underlying libraries directly. It does not require any
vendor CLI wrapper.

## When to Use This Skill

- Carve a training/eval subset out of an existing Hub dataset (filter by column,
  quality threshold, or subject) and push it to a new repo.
- Inspect a dataset's columns, types, row count, and value distribution *before*
  downloading gigabytes.
- Reshape or reformat a dataset with SQL (extract a correct-answer column, join two
  datasets, unnest arrays) and export to Parquet/JSONL or the Hub.
- Stand up a new dataset repo and stream rows to it incrementally from a generation
  or labeling pipeline.
- Enforce a consistent row schema (chat, classification, QA, completion, tabular)
  on data you are about to upload.

## When NOT to Use This Skill

- **Local-only DataFrame work** with no Hub round-trip — use `polars` (in-memory),
  `dask` (larger-than-RAM/cluster), or `vaex` (out-of-core). DuckDB `hf://` shines
  specifically because the data lives on the Hub.
- **Downloading model weights or running inference** — this skill is dataset-only.
- **Discovery / search** ("find me a sentiment dataset") — use the Hugging Face MCP
  server (`hub_repo_search`, `hub_repo_details`, `hf_doc_search`). Pair that for
  *finding* datasets; use this skill for *editing and querying* them.
- **Structured DB lookups** against curated scientific APIs — use `database-lookup`.

## Prerequisites

- `pip install duckdb "huggingface_hub>=0.20" "datasets>=2.14" pandas` (Python
  ≥3.10). DuckDB pulls the `hf://` reader through its `httpfs` extension.
- Set `HF_TOKEN` to a **write**-scoped token for any create/push/private-read
  operation. Read-only queries on public datasets need no token.

```bash
[ -n "$HF_TOKEN" ] && echo "HF_TOKEN set" || echo "HF_TOKEN NOT set"
```

## Capability 1 — Query any Hub dataset with SQL

DuckDB reads the auto-converted Parquet branch through the `hf://` protocol:

```
hf://datasets/{repo_id}@~parquet/{config}/{split}/*.parquet
```

Minimal query (no download of the full dataset):

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
# Private/rate-limited access: register the token once
# con.execute("CREATE SECRET hf (TYPE huggingface, TOKEN getenv('HF_TOKEN'));")

rows = con.execute("""
    SELECT question, subject
    FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
    WHERE subject = 'nutrition'
    LIMIT 10
""").fetchdf()
```

Schema, sampling, distributions, joins, `COPY … TO` exports, and a reusable
`HubDatasetSQL` helper are in **`references/duckdb-sql.md`**. Read it before writing
non-trivial SQL — the `@~parquet` revision, config/split globbing, and reservoir
sampling syntax are easy to get wrong.

## Capability 2 — Create and stream datasets to the Hub

Two publishing paths:

- **Whole result set** — convert query output to a `datasets.Dataset` and
  `push_to_hub`. Best for one-shot derived subsets.
- **Incremental streaming** — `create_repo` once, then append each batch as a new
  timestamped `data/{split}-*.jsonl` file via `HfApi.upload_file`. Best for
  pipelines that emit rows over time without re-uploading prior data.

```python
from datasets import Dataset
ds = Dataset.from_list(rows_as_dicts)          # or from_pandas / from_dict
ds.push_to_hub("your-username/my-subset", private=True)   # needs write HF_TOKEN
```

Repo lifecycle, the streaming-chunk pattern, `config.json`/README card metadata,
multi-config/split layout, inspection (`repo_info`, `list_repo_files`,
`dataset_info`), and failure handling (409 already-exists, missing-repo, token
scope, rate limits, large-file batching) are in **`references/hub-management.md`**.

## Capability 3 — Structured row templates

When you control the row shape, validate it before upload. Six templates with
required/recommended fields, per-field type rules, and example rows are documented
in **`references/dataset-templates.md`**:

| Template | Required fields | Typical use |
|---|---|---|
| `chat` | `messages` (role/content list) | multi-turn dialogue, tool-use traces |
| `classification` | `text`, `label` | sentiment, intent, topic |
| `qa` | `question`, `answer` | reading comprehension, factual QA |
| `completion` | `prompt`, `completion` | LM/code/creative completion |
| `tabular` | `columns`, `data` | structured regression/classification |
| `custom` | (caller-defined) | anything else |

## Reference Map

Load the file that matches your step — do not read everything up front.

| Need | Reference file |
|---|---|
| `hf://` path format, DuckDB secret setup, SQL cookbook (sample/histogram/join/export), reusable Python helper | `references/duckdb-sql.md` |
| Create repos, stream JSONL chunks, `push_to_hub`, config/card metadata, inspection, error handling | `references/hub-management.md` |
| Row schemas, required/recommended fields, validation rules, example rows for the six templates | `references/dataset-templates.md` |

## Related Skills

- `polars`, `dask`, `vaex` — local DataFrame processing once data is downloaded.
- `database-lookup` — structured queries against curated scientific REST APIs.
- Hugging Face MCP server — dataset *discovery* and metadata; complements this
  skill's *editing and querying*.
