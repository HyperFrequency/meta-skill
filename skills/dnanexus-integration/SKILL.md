---
name: dnanexus-integration
version: 0.1.0
description: >-
  Orchestrate genomics work on the DNAnexus cloud platform through the dxpy
  Python SDK and dx CLI. Use when you need to build/deploy apps or applets,
  manage platform data objects (upload/download files and records, search,
  clone, organize projects and folders), launch and monitor jobs, chain
  multi-stage workflows, or author dxapp.json with dependencies (execDepends,
  bundled resources, assets, Docker) for bioinformatics pipelines over
  FASTQ/BAM/VCF. Requires a DNAnexus account and an authenticated dx session.
  NOT a bioinformatics toolkit itself — it does not align reads, call variants,
  or parse genomic formats; it orchestrates tools you supply. NOT for other
  execution backends (AWS Batch, GCP, Terra/Cromwell, Nextflow, Snakemake) or
  for local pipelines with no DNAnexus platform involved.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (dxpy / dx-toolkit)"
---

# DNAnexus Integration

## Overview

DNAnexus is a cloud platform for biomedical and genomics data analysis. Work
happens against three things: **projects** (containers that hold data and
accrue cost), **data objects** (files, records, applets, workflows — each with
an immutable ID like `file-XXXX`), and **jobs** (executions of an app/applet on
an isolated Linux worker with API access).

This skill is a **router**. It gives you the setup path, the mental model, and
the failure modes, then delegates deep API surface and long examples to
`references/`. Two libraries do the work: the `dxpy` Python SDK for
programmatic control, and the `dx` command-line tool for interactive and
shell-script use.

## When to Use This Skill

Use this skill when you are:

- Building, deploying, or debugging DNAnexus **apps/applets** (`dx build`, entry points).
- Managing **data**: uploading sequencing data, downloading results, searching by name/property/type, cloning across projects, organizing folders.
- Running and monitoring **jobs**, or chaining them into **workflows** with output references.
- Writing **automation scripts** with `dxpy` (batch processing, data migration).
- Authoring **dxapp.json**: input/output specs, dependencies, Docker, instance types, timeouts.

## When NOT to Use This Skill

- **You need the actual science, not the platform.** Aligning reads, calling variants, parsing/QC-ing FASTQ/BAM/VCF — DNAnexus *runs* those tools but does not implement them. Supply the tool; this skill orchestrates it.
- **A different execution backend.** AWS Batch, GCP, Azure Batch, Terra/Cromwell, Nextflow Tower, or a local Snakemake run have their own APIs — this skill does not apply.
- **No DNAnexus account or platform data.** Every operation here needs an authenticated session and platform-resident object IDs.
- **Pure local file wrangling.** If nothing touches `project-XXXX` / `file-XXXX` objects, use ordinary Python/shell.

## Core Mental Model

- **Everything is an ID.** `file-`, `record-`, `applet-`, `app-`, `workflow-`, `job-`, `analysis-`, `project-`, `user-`, `org-`. You pass IDs, not paths.
- **Links, not IDs, connect objects.** A data object referenced as input is wrapped as `{"$dnanexus_link": "file-XXXX"}`; build these with `dxpy.dxlink(...)`. This is the single most common source of confusion.
- **Open → closed lifecycle.** Files and records start *open* (writable), then must be *closed* to become immutable and usable. A job will not start until every input object is closed. Forgetting to `.close()` is the most common hang.
- **Jobs run remotely.** Inside a job, input files must be `download`ed to the local worker before you can read them, and outputs must be `upload`ed and returned as links — the worker filesystem is ephemeral.

## Setup and Authentication

```bash
uv pip install dxpy          # provides both the dxpy library and the dx CLI
dx login                     # interactive auth; stores a session token
dx --version && dx whoami    # verify install and identity
dx select project-XXXX       # set the working project context
```

For non-interactive contexts (CI, apps), authenticate with a token instead of
`dx login` — see `references/python-sdk.md` (Authentication).

## Capability Map

Load the reference for the task at hand — do not read all five up front.

| You need to…                                             | Reference |
| -------------------------------------------------------- | --------- |
| Create/build/deploy an app or applet; entry points; test | [`references/app-development.md`](references/app-development.md) |
| Upload/download/search/clone files & records; folders; projects; archival | [`references/data-operations.md`](references/data-operations.md) |
| Run jobs, monitor state, parallel subjobs, workflows, retries | [`references/job-execution.md`](references/job-execution.md) |
| dxpy class/function reference, auth, error handling, patterns | [`references/python-sdk.md`](references/python-sdk.md) |
| dxapp.json spec, dependencies, Docker, instance types, timeouts | [`references/configuration.md`](references/configuration.md) |

Most real tasks combine two: app development + configuration, or data
operations + job execution.

## Quick Start

Upload input, run an applet, wait, download the result:

```python
import dxpy

reads = dxpy.upload_local_file("sample.fastq", project="project-XXXX")

job = dxpy.DXApplet("applet-XXXX").run({
    "reads": dxpy.dxlink(reads.get_id()),   # wrap the input as a link
    "quality_threshold": 30,
})
job.wait_on_done()

aligned = job.describe()["output"]["aligned_reads"]["$dnanexus_link"]
dxpy.download_dxfile(aligned, "aligned.bam")
```

Chain two applets by reference (no need to wait between stages):

```python
qc    = qc_applet.run({"reads": dxpy.dxlink(reads.get_id())})
align = align_applet.run({"reads": qc.get_output_ref("filtered_reads")})
```

## Common Failure Modes

- **`wait_on_done` hangs forever.** An input object is still *open*. Close every file/record before running (`f.close()`), or create them closed.
- **`ResourceNotFound` / permission errors.** The object lives in a project you have not selected, or you lack the level (VIEW/UPLOAD/CONTRIBUTE/ADMINISTER). Check `dx select` and project membership.
- **Input rejected as wrong type.** You passed a raw ID string where a link is expected. Wrap it: `dxpy.dxlink("file-XXXX")` → `{"$dnanexus_link": "file-XXXX"}`.
- **App can't find its input file.** Inside a job you must `dxpy.download_dxfile(...)` before opening the path; the ID is not a local file.
- **Job fails on memory/disk.** Raise the instance type in `dxapp.json` `systemRequirements` (see `references/configuration.md`), or split into subjobs.
- **Unexpected cost.** Charges accrue to the *originating project* and archived data still incurs storage. Pick modest instance types first, then scale.

## Debugging a Job

```bash
dx watch job-XXXX                 # live state + streamed logs
dx watch job-XXXX --get-streams   # full stdout/stderr streams
dx describe job-XXXX              # failureReason / failureMessage on failure
dx terminate job-XXXX            # stop a runaway job
```

Job states: `idle → waiting_on_input → runnable → running → done | failed | terminated`.

## References

- [`references/app-development.md`](references/app-development.md) — applets vs apps, `dx-app-wizard`, Python/Bash entry points, I/O handling, local vs platform testing.
- [`references/data-operations.md`](references/data-operations.md) — file & record CRUD, metadata/properties/tags, search, cloning, projects, folders, archival, batch ops.
- [`references/job-execution.md`](references/job-execution.md) — running executables, monitoring, output references, subjobs/scatter-gather, workflows, retries, resources.
- [`references/python-sdk.md`](references/python-sdk.md) — dxpy handler classes, high-level functions, `dxpy.api.*`, links, error handling, patterns.
- [`references/configuration.md`](references/configuration.md) — full dxapp.json spec, execDepends/assets/Docker, instance types, regional options, access, timeouts.

## Getting Help

- Documentation: https://documentation.dnanexus.com/
- API reference: https://autodoc.dnanexus.com/
- dx-toolkit source: https://github.com/dnanexus/dx-toolkit
