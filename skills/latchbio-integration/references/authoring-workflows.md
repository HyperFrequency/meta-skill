# Authoring, Registering, and Executing Workflows

How to define Latch workflows, deploy them, and run them from the CLI or Python.
Signatures reflect the public Latch SDK; verify exact argument names against
`docs.latch.bio` when a call fails.

## Scaffolding

```bash
latch init my-workflow
```

Generates a workflow directory:

- `wf/__init__.py` — workflow and task definitions
- `Dockerfile` — the container image the tasks run in
- `version` — a version string bumped per registration

Add third-party tools (samtools, STAR, R packages, etc.) to the `Dockerfile`.
Everything a task imports or shells out to must be installed in that image.

## Tasks and Workflows

A **task** is a typed Python function under a resource decorator. A **workflow**
composes tasks; its signature and docstring drive the auto-generated UI.

```python
from latch import workflow, small_task, large_task
from latch.types import LatchFile, LatchDir

@small_task
def quality_control(input_file: LatchFile) -> LatchFile:
    """Run FastQC."""
    return qc_output

@large_task
def alignment(qc_file: LatchFile, genome: str) -> LatchFile:
    """STAR alignment."""
    return bam_output

@workflow
def rnaseq_pipeline(input_fastq: LatchFile, genome: str) -> LatchFile:
    """RNA-seq analysis pipeline.

    Args:
        input_fastq: Raw reads (this text appears in the UI).
        genome: Reference genome identifier.
    """
    qc = quality_control(input_file=input_fastq)
    return alignment(qc_file=qc, genome=genome)
```

Rules that bite people:

- **Every parameter needs a type annotation.** Untyped params break
  serialization and UI generation.
- **Wire tasks by keyword.** Pass one task's return value as the next task's
  keyword argument; the SDK builds the dependency graph from that.
- **Docstrings are documentation, not decoration.** The workflow docstring and
  `Args:` entries become UI labels and help text.

### Resource decorators (summary)

`@small_task`, `@large_task`, `@small_gpu_task`, `@large_gpu_task`, and
`@custom_task(...)`. Full details, GPU types, and sizing guidance live in
`resource-configuration.md`.

## Registering

```bash
latch register my-workflow            # add --verbose for build logs
```

Registration builds the Docker image, serializes the workflow graph, uploads
the container, generates the no-code UI, and makes the workflow launchable.
Docker must be running locally.

## Parallelism with `map_task`

Fan a task across a list of inputs:

```python
from typing import List
from latch import workflow, small_task, map_task
from latch.types import LatchFile

@small_task
def process_sample(sample: LatchFile) -> LatchFile:
    return processed

@workflow
def batch_pipeline(samples: List[LatchFile]) -> List[LatchFile]:
    return map_task(process_sample)(sample=samples)
```

## Launch Plans (preset inputs)

Launch plans bundle default parameter values so users can start a run in one
click:

```python
from latch.resources.launch_plan import LaunchPlan

LaunchPlan(
    rnaseq_pipeline,               # the workflow object
    "default_config",              # launch plan name
    {
        "input_fastq": LatchFile("latch:///data/sample.fastq"),
        "genome": "hg38",
    },
)
```

## Conditional UI Sections

Show or hide parameters based on other inputs so the generated form stays clean.
This is configured through `LatchMetadata`/`LatchParameter` and conditional
section helpers in `latch.resources`. The exact constructor arguments differ
across SDK versions — check `docs.latch.bio` for the current
`LatchParameter` / conditional-section API before wiring one up.

## Importing Nextflow and Snakemake Pipelines

Latch can host existing pipelines without a full Python rewrite:

```bash
latch register --nextflow  <nextflow-directory>
latch register --snakemake <snakemake-directory>
```

The imported pipeline gets the same containerization, versioning, and generated
UI as a native SDK workflow. Use this to lift an established community pipeline
onto Latch rather than re-implementing it.

## Executing a Registered Workflow

### From the CLI

```bash
latch execute rnaseq_pipeline --input_fastq latch:///data/s.fastq --genome hg38
```

### Programmatically

The SDK exposes account and execution objects for launching runs from Python
(e.g. `latch.account.Account`, execution helpers under `latch.executions`).
Signatures vary by SDK version; confirm the current entrypoint in the docs. The
shape is: identify the workflow by name/version, supply a parameter dict, and
receive an execution handle you can poll.

## Local Development

`latch develop <workflow-directory>` opens an interactive environment inside the
task container so you can iterate on code against the real image before paying
for a full `register` cycle. This is the fastest debug loop — you catch missing
`Dockerfile` dependencies and type errors without re-registering each time.

## Troubleshooting Registration

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Registration hangs or errors immediately | Docker daemon not running | Start Docker |
| Auth / 401 errors | Stale token | `latch login` |
| Build fails on `import` or CLI tool | Missing from `Dockerfile` | Add the dependency, rebuild |
| Type/serialization error | Missing/incorrect annotation | Annotate every param; use `LatchFile`/`LatchDir` |
| Opaque failure | — | Rerun with `latch register --verbose` |

## Best Practices

1. Type-annotate everything; use `LatchFile`/`LatchDir` for I/O.
2. Write real docstrings — they are the user-facing UI.
3. Keep tasks modular and single-purpose; compose in the workflow.
4. Start with standard resource decorators; scale only after profiling.
5. Iterate with `latch develop` before `latch register`.
6. Version workflows deliberately (the `version` file) for reproducibility.
