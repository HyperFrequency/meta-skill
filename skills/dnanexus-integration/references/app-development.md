# App Development

Apps and applets are executable programs that run on DNAnexus workers. Both are
authored identically; they differ only at build time.

## Applets vs Apps

- **Applet** (`applet-XXXX`) — a data object that lives *inside a project*. Fast to iterate; ideal for development and internal use.
- **App** (`app-XXXX`) — a versioned, shareable executable that does *not* live in a project and can be published for others. Requires a `version` in `dxapp.json`.

Develop as an applet, then promote to an app when stable.

## Scaffolding

```bash
dx-app-wizard          # interactive: prompts for name, inputs, outputs, language
```

Produces:

```
my-app/
├── dxapp.json         # metadata, I/O spec, run spec (see configuration.md)
├── src/
│   └── my-app.py      # or my-app.sh
├── resources/         # files copied into the worker at / (bundled deps)
└── test/
```

## Building

```bash
dx build                     # build/overwrite an applet in the current project
dx build --app               # build a versioned app
dx build -f                  # force-overwrite an existing applet
```

The build validates `dxapp.json`, bundles `src/` and `resources/`, uploads, and
returns the new `applet-`/`app-` ID.

## Python entry points

A Python app declares entry points with `@dxpy.entry_point('<name>')` and ends
with `dxpy.run()`, which dispatches to the entry point the platform invokes
(`main` for the top-level job, other names for subjobs).

```python
import dxpy, subprocess

@dxpy.entry_point('main')
def main(reads, quality_threshold=30):
    # `reads` arrives as a link dict, e.g. {"$dnanexus_link": "file-XXXX"}
    dxpy.download_dxfile(reads["$dnanexus_link"], "reads.fastq")

    subprocess.check_call(
        ["quality_filter", "--in", "reads.fastq",
         "--out", "filtered.fastq", "--q", str(quality_threshold)]
    )

    out = dxpy.upload_local_file("filtered.fastq")   # upload result
    return {"filtered_reads": dxpy.dxlink(out)}       # return as a link

dxpy.run()
```

Rules that trip people up:

- **Inputs are links, not paths.** Download before reading.
- **File outputs must be uploaded and returned via `dxpy.dxlink(...)`.** Scalars (int/float/string/boolean/hash) are returned directly.
- **The worker filesystem is ephemeral.** Nothing persists unless uploaded.

## Bash entry points

```bash
#!/bin/bash
set -e -x -o pipefail

main() {
    dx download "$reads" -o reads.fastq            # inputs are shell vars
    process_reads reads.fastq > output.fastq
    trimmed=$(dx upload output.fastq --brief)      # --brief prints just the ID
    dx-jobutil-add-output filtered_reads "$trimmed" --class=file
}
```

`dx-jobutil-add-output <name> <value> --class=<class>` is how a Bash app emits
each declared output.

## Parallel processing with subjobs

An entry point can spawn subjobs that run on their own workers. Reference their
outputs before they finish; the platform resolves the dependency graph.

```python
@dxpy.entry_point('main')
def main(input_files):
    subjobs = [
        dxpy.new_dxjob(fn_input={"file": f}, fn_name="process_file")
        for f in input_files
    ]
    return {"results": [j.get_output_ref("processed") for j in subjobs]}

@dxpy.entry_point('process_file')
def process_file(file):
    ...
    return {"processed": dxpy.dxlink(out)}
```

See `references/job-execution.md` for the scatter-gather pattern.

## Execution environment

Workers are isolated Linux VMs (Ubuntu; pin the release in `dxapp.json`
`runSpec.release`) with root, a scratch directory under `/home/dnanexus`, DNAnexus
API access, and internet only if `access.network` is requested. Instance type is
chosen in `dxapp.json` `systemRequirements` (see `references/configuration.md`).

## Testing

```bash
# Logic-level: exercise pure functions locally before deploying.
python src/my-app.py            # only works for code with no platform I/O

# Platform: run the built applet with real inputs.
dx run applet-XXXX -i reads=file-YYYY -i quality_threshold=30
dx watch job-ZZZZ               # stream state + logs
dx watch job-ZZZZ --get-streams # full stdout/stderr
```

## Common issues

| Symptom | Cause / fix |
| ------- | ----------- |
| `FileNotFoundError` on an input path | Download it first: `dxpy.download_dxfile(id, path)`. |
| Output missing after job `done` | You returned a raw ID or local path instead of `dxpy.dxlink(uploaded)`. |
| Killed / OOM | Raise instance type in `systemRequirements`, or split into subjobs. |
| Timeout | Set `runSpec.timeoutPolicy` in `dxapp.json`, or shard the work. |
| Network calls blocked | Add `"access": {"network": ["*"]}` (or specific hosts). |
