# Python SDK (dxpy)

`dxpy` provides Python bindings to the DNAnexus API. The same library runs both
in external scripts (accessing the platform remotely) and inside apps (running
on a worker). Requires Python 3.8+.

```bash
uv pip install dxpy        # or: pip install dxpy / conda install -c bioconda dxpy
```

## Authentication

Interactive: `dx login` stores a session the library reads automatically.

Non-interactive (CI, apps, servers) — set a token, do **not** hard-code it:

```python
import os, dxpy
dxpy.set_security_context({
    "auth_token_type": "Bearer",
    "auth_token": os.environ["DX_API_TOKEN"],
})
```

or via environment before the process starts:

```bash
export DX_SECURITY_CONTEXT='{"auth_token_type":"Bearer","auth_token":"<token>"}'
```

## Handler classes

Each platform object class has a handler you construct from an ID. Handlers are
lazy — construction does not hit the API; `.describe()` does.

| Class | Object | Key methods |
| ----- | ------ | ----------- |
| `DXFile` | `file-` | `describe`, `open_file`, `set_properties`, `add_tags`, `rename`, `clone`, `move`, `close`, `remove` |
| `DXRecord` | `record-` | `describe`, `get_details`, `set_details`, `close` |
| `DXApplet` | `applet-` | `describe`, `run` |
| `DXApp` | `app-` | `describe`, `run` (also `DXApp(name=...)`) |
| `DXWorkflow` | `workflow-` | `add_stage`, `run`, `close` |
| `DXJob` | `job-` | `describe`, `wait_on_done`, `get_output_ref`, `terminate` |
| `DXProject` | `project-` | `describe`, `list_folder`, `new_folder` |

```python
f = dxpy.DXFile("file-XXXX")
d = f.describe(); d["name"], d["size"], d["state"]
with f.open_file() as fh: data = fh.read()

proj = dxpy.DXProject("project-XXXX")
contents = proj.list_folder("/data")     # -> {"objects": [...], "folders": [...]}
```

## High-level functions

```python
# files
f = dxpy.upload_local_file("local.txt", project="project-XXXX", folder="/data")
dxpy.download_dxfile("file-XXXX", "out.txt")
s = dxpy.upload_string("hello", project="project-XXXX")

# create objects
f = dxpy.new_dxfile(project="project-XXXX", name="o.txt"); f.write("x"); f.close()
r = dxpy.new_dxrecord(name="meta", details={"k": "v"}, project="project-XXXX")

# search (generators)
dxpy.find_data_objects(classname="file", name="*.fastq",
                       project="project-XXXX", describe=True)
dxpy.find_projects(name="*analysis*", describe=True)
dxpy.find_jobs(project="project-XXXX", state="failed", created_after="2025-01-01")
dxpy.find_apps(category="Read Mapping")

# introspection
dxpy.describe("file-XXXX")                          # any object
dxpy.describe("file-XXXX", fields={"name": True})   # narrow fields = less latency
h = dxpy.get_handler("file-XXXX")                   # returns the right handler class
```

## Links and references

A data object used as job input must be a link, not a bare ID:

```python
dxpy.dxlink("file-XXXX")                 # -> {"$dnanexus_link": "file-XXXX"}
dxpy.dxlink("file-XXXX", "project-YYYY") # link scoped to a project
job.get_output_ref("output_name")        # forward reference to a not-yet-finished output
```

## Direct API calls (`dxpy.api.*`)

`dxpy.api.<route>` methods map 1:1 onto REST routes for operations without a
high-level wrapper. The naming is `<class>_<verb>`.

```python
dxpy.api.project_new({"name": "New Project"})
dxpy.api.project_new_folder("project-XXXX", {"folder": "/f"})
dxpy.api.project_invite("project-XXXX", {"invitee": "user-YYYY", "level": "VIEW"})
dxpy.api.file_describe("file-XXXX")
dxpy.api.system_find_data_objects({
    "class": "file", "project": "project-XXXX",
    "name": {"regexp": r".*\.bam$"},
})
```

Use `dxpy.api.*` when a high-level helper does not exist; prefer the helpers
otherwise.

## Error handling

```python
from dxpy.exceptions import DXError, DXAPIError
try:
    dxpy.DXFile("file-XXXX").describe()
except DXAPIError as e:      # API rejected the request (has .code)
    print("API error", getattr(e, "code", None), e)
except DXError as e:         # general dxpy error
    print("dxpy error", e)
```

Common conditions: object not found, insufficient permission, invalid input,
object in wrong state (e.g. open when a closed object is required).

## Session/project context

```python
dxpy.set_workspace_id("project-XXXX")    # default project for subsequent ops
dxpy.WORKSPACE_ID                        # current default project
```

To point the SDK at a non-default API server or region, configure the
`DX_APISERVER_HOST` / `DX_APISERVER_PORT` / `DX_APISERVER_PROTOCOL` environment
variables (or `dx select --region ...` at the CLI) before creating handlers,
rather than mutating server state mid-script.

## Reusable patterns

Upload → run → collect:

```python
inp = dxpy.upload_local_file("data.txt", project="project-XXXX")
job = dxpy.DXApplet("applet-XXXX").run({"input": dxpy.dxlink(inp.get_id())})
job.wait_on_done()
oid = job.describe()["output"]["result"]["$dnanexus_link"]
dxpy.download_dxfile(oid, "result.txt")
```

Batch fan-out:

```python
jobs = [dxpy.DXApplet("applet-XXXX").run({"input": dxpy.dxlink(r["id"])})
        for r in dxpy.find_data_objects(classname="file", name="*.fastq",
                                         project="project-XXXX")]
for j in jobs:
    j.wait_on_done()
```

## Practices

- Prefer high-level helpers; drop to `dxpy.api.*` only when needed.
- Request narrow `describe` `fields` to cut latency on hot loops.
- Wrap API calls in `try/except DXAPIError` at boundaries.
- Never hard-code tokens; read from the environment.
- Always `dxlink()` inputs — bare IDs are the most common input error.
