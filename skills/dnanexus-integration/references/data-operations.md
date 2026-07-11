# Data Operations

Manage files, records, projects, and folders via `dxpy` (Python) or `dx` (CLI).

## Object types

- **File** (`file-XXXX`) — binary or text blob.
- **Record** (`record-XXXX`) — structured JSON `details` plus metadata; use for sample sheets, run manifests, computed stats.
- **Applet / App / Workflow** — executables (see `app-development.md`, `job-execution.md`).

## Open → closed lifecycle

Files and records are created **open** (mutable) and must be **closed** to become
immutable and usable as job inputs.

```python
f = dxpy.new_dxfile(project="project-XXXX", name="output.txt")
f.write("line 1\n"); f.write("line 2\n")
f.close()                       # REQUIRED — until closed, the file is unusable

rec = dxpy.new_dxrecord(details={...}, close=True)   # create-and-close in one call
```

Forgetting `.close()` is the top cause of jobs that never leave
`waiting_on_input`.

## Files

### Upload

```python
f = dxpy.upload_local_file("data.txt", project="project-XXXX")   # closes on completion

f = dxpy.upload_local_file(
    "data.txt", name="my_data", project="project-XXXX", folder="/results",
    properties={"sample": "S1", "type": "raw"}, tags=["batch2"],
)

s = dxpy.upload_string("hello", project="project-XXXX", name="note.txt")
```

For generated/streamed content use `new_dxfile()` + `.write()` + `.close()`.

### Download and read

```python
dxpy.download_dxfile("file-XXXX", "local.txt")            # by ID

f = dxpy.DXFile("file-XXXX")
with f.open_file() as fh:                                  # stream without a temp file
    contents = fh.read()
```

### Metadata

```python
d = dxpy.DXFile("file-XXXX").describe()
d["name"], d["size"], d["state"], d["created"]

f = dxpy.DXFile("file-XXXX")
f.set_properties({"experiment": "exp1", "version": "v2"})
f.add_tags(["validated"])
f.rename("new_name.txt")
```

## Records

```python
rec = dxpy.new_dxrecord(
    name="sample_metadata", types=["SampleMetadata"],
    details={"sample_id": "S001", "tissue": "blood", "age": 45},
    project="project-XXXX", close=True,
)

rec = dxpy.DXRecord("record-XXXX")
details = rec.get_details()                # read JSON payload
# to edit, the record must be open:
details["processed"] = True
rec.set_details(details); rec.close()
```

## Search

`dxpy.find_data_objects(...)` returns a generator of `{"id": ..., "project": ...,
"describe": {...}}` dicts (`describe` present when `describe=True`).

```python
for r in dxpy.find_data_objects(name="*.fastq", classname="file",
                                project="project-XXXX", folder="/raw",
                                describe=True):
    print(r["describe"]["name"], r["id"])

# by property
dxpy.find_data_objects(classname="file",
                       properties={"sample": "S1", "type": "processed"},
                       project="project-XXXX")

# by record type / by state
dxpy.find_data_objects(classname="record", typename="SampleMetadata")
dxpy.find_data_objects(classname="file", state="closed", project="project-XXXX")
```

`name` matches globs by default; pass `name_mode="regexp"` for regex. Omit
`project` to search every project you can access (slower).

## Clone / copy across projects

```python
dxpy.DXFile("file-XXXX").clone(project="project-YYYY", folder="/imported")

for r in dxpy.find_data_objects(classname="file", project="project-XXXX", folder="/results"):
    dxpy.DXFile(r["id"]).clone(project="project-YYYY", folder="/backup")
```

## Projects and folders

```python
proj = dxpy.api.project_new({"name": "RNA-seq analysis"})   # -> {"id": "project-..."}

dxpy.api.project_invite("project-XXXX",
    {"invitee": "user-YYYY", "level": "CONTRIBUTE"})         # VIEW|UPLOAD|CONTRIBUTE|ADMINISTER

for p in dxpy.find_projects(describe=True):
    print(p["describe"]["name"], p["id"])

dxpy.api.project_new_folder("project-XXXX",
    {"folder": "/analysis/batch1/results", "parents": True})

dxpy.DXFile("file-XXXX", project="project-XXXX").move("/new_location")
```

### Removal

`project_remove_objects` unlinks an object from a project (it may survive
elsewhere); `.remove()` on a handler permanently deletes it.

```python
dxpy.api.project_remove_objects("project-XXXX", {"objects": ["file-XXXX"]})
dxpy.DXFile("file-XXXX").remove()          # permanent
```

## Archival

Archived data moves to cheaper cold storage and must be unarchived (which takes
time) before reuse. Archival is a project-level operation.

```python
dxpy.api.project_archive("project-XXXX", {"files": ["file-XXXX"]})
dxpy.api.project_unarchive("project-XXXX", {"files": ["file-XXXX"]})
```

## Batch patterns

```python
import os
for fn in os.listdir("./data"):
    p = os.path.join("./data", fn)
    if os.path.isfile(p):
        dxpy.upload_local_file(p, project="project-XXXX", folder="/batch")

for r in dxpy.find_data_objects(classname="file", project="project-XXXX", folder="/results"):
    name = dxpy.DXFile(r["id"]).describe()["name"]
    dxpy.download_dxfile(r["id"], f"./downloads/{name}")
```

## Practices

- **Close before use.** Any writable object must be closed to become a valid input.
- **Tag with properties** for durable, searchable organization instead of relying on names.
- **Prefer high-level helpers** (`upload_local_file`, `download_dxfile`) over manual `new_dxfile` unless you are streaming.
- **Verify project context** before destructive ops; `remove()` is irreversible.
- **Archive cold data** to cut storage cost, but budget unarchive latency before you need it.
