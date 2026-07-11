# Data Handling and the Registry

Two data layers: **cloud storage** (`LatchFile`/`LatchDir` over `latch:///`
paths) for the bytes, and the **Registry** (Projects -> Tables -> Records) for
structured metadata. Read patterns below are stable; Registry *write* signatures
change across SDK versions — confirm against `docs.latch.bio` before relying on
them (flagged where it matters).

## Cloud Storage: LatchFile and LatchDir

`LatchFile` and `LatchDir` are handles to objects in Latch cloud storage. Inside
a task, an input handle is downloaded to local disk on entry and a returned
handle is uploaded on exit — you work with ordinary local paths in between.

```python
from latch.types import LatchFile, LatchDir

input_file = LatchFile("latch:///data/sample.fastq")
input_file.local_path    # local path available while a task runs
input_file.remote_path   # the latch:/// location

out_dir = LatchDir("latch:///results/experiment_1")
```

### Path scheme

- `latch:///path/to/file` — Latch cloud storage (three slashes; root-relative).
- Local paths are resolved automatically during execution.
- S3 paths can be used directly when the workspace is configured for them.

### Automatic transfer

```python
from latch import small_task
from latch.types import LatchFile

@small_task
def process_file(input_file: LatchFile) -> LatchFile:
    with open(input_file.local_path) as f:   # downloaded already
        data = f.read()
    out = "output.txt"
    with open(out, "w") as f:
        f.write(transform(data))
    # returning the handle uploads it to the given latch:/// path
    return LatchFile(out, "latch:///results/output.txt")
```

### Glob selection

```python
data = LatchDir("latch:///data")
data.glob("**/*.fastq")          # recursive
data.glob("alignments/**/*.bam")
```

## The Registry

Structured metadata store for sample sheets, run tracking, and linking results
to inputs. Hierarchy:

```
Account / Workspace
└── Projects
    └── Tables
        └── Records
```

### Column types

`string`, `number`, `boolean`, `date`, `file` (a `LatchFile`), `directory`
(a `LatchDir`), `link` (a reference to a record in another table), and `enum`
(a value from a fixed option list). Model relationships between tables with
`link` columns — e.g. a Results table whose `sample` column links to the
Samples table.

### Reading (stable API)

```python
from latch.registry.table import Table

table = Table("tbl_456")             # construct a handle by id
for record in table.list_records():  # iterate records
    values = record.get_values()     # dict of column -> value
    record.id                        # record identifier
```

Projects are enumerated from the account/workspace (see below). Column
definitions are available via the table's column accessors.

### Writing (transactional — verify signatures)

The Registry mutates through a **transactional updater context**, not plain
constructors. The pattern is: open an update on the table, stage
column/record upserts, and commit on exit.

```python
# Illustrative — confirm exact method names against docs.latch.bio,
# they differ across SDK versions.
with table.update() as updater:
    updater.upsert_record(
        "S001",
        condition="treated",
        replicate=1,
        fastq_file=LatchFile("latch:///data/S001.fastq"),
    )
    # column mutations (add/rename/retype) are also staged here
```

Do **not** assume `Table.create(...)` / `Record.create(...)` / `record.update(...)`
free-function signatures exist as written in older material — treat the
transactional updater as the source of truth and check the docs for the current
method names before writing production code. Batch multiple record changes in
one `update()` context rather than committing per record.

### Linked records

A `link` column stores the id of a record in a target table; resolving it
returns that record so you can read its values. Use links to keep a Results
record pointed at the Samples record it came from — this is how you preserve
provenance across a pipeline.

### Enum columns

Declare an `enum` column with a fixed option list (e.g. status in
`pending`/`running`/`completed`/`failed`) to constrain values at write time.

## Registry Inside Workflows

The natural pattern is: look up a sample record, process its file, then write
status/results back so the Registry reflects run state.

```python
from latch import workflow, small_task
from latch.registry.table import Table

@small_task
def process_and_track(sample_name: str, table_id: str) -> str:
    table = Table(table_id)
    record = next(r for r in table.list_records()
                  if r.get_values().get("sample_id") == sample_name)
    input_file = record.get_values()["fastq_file"]
    # ... process input_file ...
    with table.update() as updater:           # write status back (verify API)
        updater.upsert_record(sample_name, status="completed")
    return "ok"

@workflow
def registry_workflow(sample_name: str, table_id: str) -> str:
    return process_and_track(sample_name=sample_name, table_id=table_id)
```

Launch plans can watch a folder and auto-launch a workflow when data lands there
— see `authoring-workflows.md` for the LaunchPlan API. The exact
folder-trigger argument is version-specific; confirm in the docs.

## Account and Workspace

```python
from latch.account import Account

account = Account.current()      # active workspace
# team workspaces are enumerated / switched through Account as well;
# confirm the current listing/switching methods in the docs.
```

## Data Utility Functions

`latch.functions` provides helpers used inside tasks: table join operations
(left/inner/outer/right joins on a key), record filtering, and secure secret
retrieval (`get_secret("name")`) for API keys and tokens. Signatures vary — look
them up before use.

## Best Practices

1. Keep a consistent folder layout (`/data`, `/results`, `/logs`).
2. Define the table schema before bulk-loading records.
3. Use `link` columns for provenance, not copied ids.
4. Batch record writes in one `update()` context.
5. Store experimental metadata in the Registry for traceability.
6. Validate column types when writing records.
