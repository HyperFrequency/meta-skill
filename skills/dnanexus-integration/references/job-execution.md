# Job Execution and Workflows

Every run of an app/applet creates a **job** (`job-XXXX`) on an isolated worker.
A **workflow** run creates an **analysis** (`analysis-XXXX`) grouping many jobs.

## Running an executable

```python
job = dxpy.DXApplet("applet-XXXX").run({
    "reads": dxpy.dxlink("file-YYYY"),      # inputs are LINKS
    "quality_threshold": 30,
})
print(job.get_id())

app_job = dxpy.DXApp(name="my-app").run({"reads": dxpy.dxlink("file-XXXX")})
```

CLI equivalent:

```bash
dx run applet-XXXX -i reads=file-YYYY -i quality_threshold=30
```

### Run parameters

`.run()` accepts (beyond the input hash):

- `project`, `folder` — where outputs land.
- `name` — human-readable job name.
- `instance_type` — override the dxapp.json default, e.g. `"mem3_ssd1_v2_x8"`.
- `priority` — `"low" | "normal" | "high"`.
- `tags`, `properties` — for later discovery via `find_jobs`.
- `depends_on` — force ordering on jobs/objects.

```python
job = dxpy.DXApplet("applet-XXXX").run(
    {"input_file": dxpy.dxlink("file-YYYY")},
    project="project-ZZZZ", folder="/results", name="Alignment",
    instance_type="mem2_ssd1_v2_x4", priority="high",
    tags=["exp001"], properties={"sample": "S1"},
)
```

To override the runtime limit, set `runSpec.timeoutPolicy` in `dxapp.json`
(see `references/configuration.md`) rather than a per-call argument.

## Monitoring

```python
job = dxpy.DXJob("job-XXXX")
job.describe()["state"]     # idle|waiting_on_input|runnable|running|done|failed|terminated
job.wait_on_done()          # block until terminal; raises if it failed
out = job.describe()["output"]
dxpy.download_dxfile(out["result_file"]["$dnanexus_link"], "result.txt")
```

CLI live view (state + streamed logs):

```bash
dx watch job-XXXX
dx watch job-XXXX --get-streams   # full stdout/stderr
```

Programmatic log access is not a stable one-call helper; prefer `dx watch
--get-streams`, or read `failureReason` / `failureMessage` from `describe()` for
post-mortem on failures.

## Chaining by output reference

`get_output_ref(field)` yields a placeholder link that resolves when the
producing job finishes — you can wire a pipeline without blocking between stages.

```python
qc      = qc_applet.run({"reads": dxpy.dxlink("file-YYYY")})
align   = align_applet.run({"reads": qc.get_output_ref("filtered_reads")})
variant = variant_applet.run({"bam":  align.get_output_ref("aligned_bam")})
variant.wait_on_done()      # wait once, at the end
```

## Parallelism: subjobs and scatter-gather

Inside an app, `dxpy.new_dxjob(fn_input=..., fn_name=...)` launches a subjob on
its own worker.

```python
# scatter
scatter = [dxpy.new_dxjob(fn_input={"item": it}, fn_name="process_item")
           for it in items]
# gather
gather = dxpy.new_dxjob(
    fn_input={"parts": [j.get_output_ref("result") for j in scatter]},
    fn_name="combine",
)
```

`fn_name` must match a declared `@dxpy.entry_point('...')` in the same app.

## Workflows

Build a reusable multi-stage pipeline once; run it many times.

```python
wf = dxpy.new_dxworkflow(name="RNA-seq pipeline", project="project-XXXX")

s1 = wf.add_stage(dxpy.DXApplet("applet-qc"),    name="QC",        folder="/qc")
s2 = wf.add_stage(dxpy.DXApplet("applet-align"), name="Alignment", folder="/align")
s2.set_input("reads", s1.get_output_ref("filtered_reads"))   # wire stage 1 -> 2
wf.close()

analysis = wf.run({f"{s1.get_id()}.reads": dxpy.dxlink("file-YYYY")})
analysis.wait_on_done()
analysis.describe()["output"]
```

CLI: `dx run workflow-XXXX -i <stage-id>.reads=file-YYYY`.

## Failure handling and retries

```python
job = dxpy.DXJob("job-XXXX"); job.wait_on_done()
d = job.describe()
if d["state"] == "failed":
    print(d.get("failureReason"), d.get("failureMessage"))
    # resubmit the same executable with the original input
    dxpy.DXApplet(d["applet"]).run(d["originalInput"], project=d["project"])

dxpy.DXJob("job-XXXX").terminate()      # or: dx terminate job-XXXX
```

Declare entry points in `runSpec.restartableEntryPoints` (see
`references/configuration.md`) to let the platform auto-retry transient
worker/spot failures.

## Execution context and requirements

- Jobs run in a temporary **workspace** with input data cloned in; you need `CONTRIBUTE` there and `VIEW` on source projects.
- A job stays in `waiting_on_input` until **every input object is closed** — the single most common stall.
- **Cost accrues to the originating project.** Match instance type to the workload; oversizing is the usual budget leak.

## Instance types

Names follow `mem{1|2|3}_ssd{n}_v2_x{cores}` (higher `mem` tier = more RAM per
core; `x{cores}` = vCPU count), e.g. `mem1_ssd1_v2_x4`, `mem2_ssd1_v2_x8`,
`mem3_ssd1_v2_x16`. Exact RAM/disk per type and region-specific availability
change over time — confirm against the current DNAnexus instance-type catalog
rather than hard-coding assumptions.

## Finding jobs

```python
for j in dxpy.find_jobs(project="project-XXXX", tags=["exp001"],
                        state="failed", describe=True):
    print(j["describe"]["name"], j["id"])
```

## Debugging checklist

1. `dx watch --get-streams` for the actual error.
2. Confirm inputs are **closed** and reachable.
3. Reproduce logic locally on a small input.
4. If OOM/disk, bump instance type; if slow, parallelize with subjobs.
