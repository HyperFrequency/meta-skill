# DuckDB SQL over `hf://` datasets

Query, sample, transform, join, and export Hugging Face Hub datasets with DuckDB,
without a full download. DuckDB reads the Hub's auto-converted Parquet files
directly through the `hf://` filesystem (provided by the `httpfs` extension).

## Setup

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")   # httpfs provides the hf:// reader
```

For private datasets or to lift anonymous rate limits, register a Hugging Face
secret once per connection:

```python
# Read the token from the environment at query time
con.execute("CREATE SECRET hf (TYPE huggingface, TOKEN getenv('HF_TOKEN'));")
# Or pull it from the local HF cache / login (~/.cache/huggingface/token):
# con.execute("CREATE SECRET hf (TYPE huggingface, PROVIDER credential_chain);")
```

## The `hf://` path format

```
hf://datasets/{repo_id}@{revision}/{config}/{split}/*.parquet
```

- `{repo_id}` — e.g. `cais/mmlu`, `ibm/duorc`.
- `{revision}` — use `~parquet` to hit the **auto-converted Parquet branch**
  (`refs/convert/parquet`), which exists for *every* dataset regardless of its
  native format. Without `~parquet` you would need the raw files in their original
  format.
- `{config}` — the dataset config/subset. Datasets with no named config use
  `default`. Check the dataset card or the `info` call below if unsure.
- `{split}` — `train`, `test`, `validation`, or `*` to glob all splits.

Examples:

```
hf://datasets/cais/mmlu@~parquet/all/test/*.parquet
hf://datasets/ibm/duorc@~parquet/ParaphraseRC/test/*.parquet
hf://datasets/stanfordnlp/imdb@~parquet/plain_text/train/*.parquet
```

If a path errors with "no files found", the `{config}` is usually wrong. List the
real configs/splits with `huggingface_hub` (see `hub-management.md` → inspection) or
browse the dataset's "Files" tab on the Hub and read the Parquet tree.

## Query cookbook

Point `FROM` at the full `hf://` glob. Everything else is ordinary DuckDB SQL.

```sql
-- Filter
SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
WHERE subject = 'nutrition' LIMIT 10;

-- Aggregate / group
SELECT subject, COUNT(*) AS cnt
FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
GROUP BY subject HAVING cnt > 100 ORDER BY cnt DESC;

-- Reshape: extract the correct choice by index (arrays are 1-based in DuckDB)
SELECT question, choices[answer + 1] AS correct_answer, subject
FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet';

-- Regex filter / clean
SELECT regexp_replace(question, '\n', ' ') AS cleaned
FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
WHERE regexp_matches(question, 'nutrition|diet');
```

### Schema

```python
con.execute("""
  DESCRIBE SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
""").fetchall()   # -> [(column_name, column_type, null, key, default, extra), ...]
```

### Random sample (reproducible)

```sql
-- Reservoir sample with a fixed seed
SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
USING SAMPLE 5 (RESERVOIR, 42);
```

### Count with filter

```sql
SELECT COUNT(*) FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
WHERE subject = 'nutrition';
```

### Value distribution / unique values

```sql
-- Top values by frequency (approximate "histogram" for categoricals)
SELECT subject, COUNT(*) AS count
FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
GROUP BY subject ORDER BY count DESC LIMIT 20;

-- Distinct values
SELECT DISTINCT subject
FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet' LIMIT 100;
```

### Join two datasets

Reference each dataset by its full `hf://` glob:

```sql
SELECT a.*, b.summary
FROM 'hf://datasets/org/dataset_a@~parquet/default/train/*.parquet' AS a
INNER JOIN 'hf://datasets/org/dataset_b@~parquet/default/train/*.parquet' AS b
  ON a.id = b.id
LIMIT 100;
```

## Export to local files

```sql
-- Parquet (columnar, preserves types)
COPY (
  SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
  WHERE subject = 'nutrition'
) TO 'nutrition.parquet' (FORMAT PARQUET);

-- JSONL / NDJSON
COPY (
  SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet' LIMIT 100
) TO 'sample.jsonl' (FORMAT JSON);   -- newline-delimited by default

-- CSV
COPY (SELECT question, subject FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet')
TO 'out.csv' (HEADER, DELIMITER ',');
```

## Push a derived subset to the Hub

DuckDB itself does not upload to the Hub. Materialize the query, then hand it to the
`datasets` library (details in `hub-management.md`):

```python
import duckdb
from datasets import Dataset

con = duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
df = con.execute("""
    SELECT * FROM 'hf://datasets/cais/mmlu@~parquet/all/test/*.parquet'
    WHERE subject IN ('nutrition','anatomy','clinical_knowledge')
""").fetchdf()

Dataset.from_pandas(df).push_to_hub("your-username/mmlu-medical", private=True)
```

## Useful DuckDB SQL functions

```sql
-- Strings
length(col)                       -- character length
lower(col), upper(col)
regexp_replace(col, '\n', ' ')    -- regex substitution
regexp_matches(col, 'a|b')        -- boolean regex test
substring(col, 1, 50)

-- Arrays / lists (1-based indexing)
choices[1]                        -- first element
len(choices)                      -- array length
unnest(choices)                   -- explode array into rows
list_contains(tags, 'x')

-- Aggregates
count(*), sum(col), avg(col), min(col), max(col)
approx_count_distinct(col)
GROUP BY col HAVING <cond>

-- Sampling
USING SAMPLE 10                   -- 10 rows
USING SAMPLE 10% (BERNOULLI)      -- 10% of rows
USING SAMPLE 10 (RESERVOIR, 42)   -- fixed-seed reproducible

-- Windows
row_number() OVER (PARTITION BY subject ORDER BY id)
```

## Reusable Python helper

A thin wrapper that centralizes path-building and token setup. Adapt as needed.

```python
import os, duckdb
from typing import Optional

class HubDatasetSQL:
    """Query Hugging Face Hub datasets with DuckDB over the hf:// Parquet branch."""

    def __init__(self, token: Optional[str] = None):
        self.con = duckdb.connect()
        self.con.execute("INSTALL httpfs; LOAD httpfs;")
        token = token or os.environ.get("HF_TOKEN")
        if token:
            self.con.execute(
                "CREATE SECRET hf (TYPE huggingface, TOKEN $t);", {"t": token}
            )

    def path(self, repo_id: str, split: str = "train", config: str = "default") -> str:
        return f"hf://datasets/{repo_id}@~parquet/{config}/{split}/*.parquet"

    def query(self, repo_id, sql_template, split="train", config="default"):
        """SQL uses the literal token 'data' as the table name; it is substituted."""
        src = f"'{self.path(repo_id, split, config)}'"
        return self.con.execute(sql_template.replace("data", src)).fetchdf()

    def describe(self, repo_id, split="train", config="default"):
        return self.con.execute(
            f"DESCRIBE SELECT * FROM '{self.path(repo_id, split, config)}'"
        ).fetchall()

    def sample(self, repo_id, n=5, seed=42, split="train", config="default"):
        p = self.path(repo_id, split, config)
        return self.con.execute(
            f"SELECT * FROM '{p}' USING SAMPLE {n} (RESERVOIR, {seed})"
        ).fetchdf()

    def close(self):
        self.con.close()
```

> Note on the `data` placeholder: the naive `str.replace("data", ...)` above is
> convenient but will also rewrite the substring `data` inside column names. Prefer
> a full `hf://` path in your `FROM` clause for anything non-trivial, or use a
> word-boundary regex if you keep the placeholder convention.
