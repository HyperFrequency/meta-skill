---
name: latchbio-integration
version: 0.1.0
description: >-
  Build and deploy bioinformatics pipelines on the Latch (LatchBio) cloud
  platform with the Latch Python SDK: @workflow/@task decorators, LatchFile/
  LatchDir cloud storage, CPU/GPU resource decorators, the Registry data model
  (Projects/Tables/Records), Nextflow/Snakemake imports, and pre-built verified
  workflows (bulk RNA-seq, DESeq2, AlphaFold, ColabFold, single-cell). Use when
  authoring, registering, or executing Latch workflows, wiring sample metadata
  into the Registry, or invoking Latch's managed pipelines. NOT for local-only
  analysis with no cloud deployment (use biopython, scanpy, or pydeseq2
  directly), NOT for other platforms (see dnanexus-integration,
  benchling-integration), and NOT a substitute for current docs.latch.bio
  API signatures.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT"
---

# Latch (LatchBio) Integration

## Overview

Latch is a cloud platform for building, deploying, and running bioinformatics
pipelines as serverless workflows. You describe computation as ordinary Python
functions decorated with `@task` and compose them inside a `@workflow`; the SDK
containerizes the code with Docker, uploads it, and generates a no-code UI so
non-programmers can launch runs. Data lives in Latch cloud storage behind
`LatchFile`/`LatchDir` handles (the `latch:///` scheme), and structured
metadata lives in the **Registry** (Projects -> Tables -> Records). Latch is
built on top of Flyte, so tasks are typed, versioned, and reproducible.

Use this skill to author workflows from scratch, port existing Nextflow or
Snakemake pipelines, size compute (CPU/GPU/memory/storage), track samples in
the Registry, and call Latch's maintained **verified** pipelines.

This file is a router. Each capability below links to a reference with the
concrete commands, signatures, and worked examples.

## When to Use This Skill

Reach for this skill when the task involves the Latch platform specifically:

- Authoring a workflow with `@workflow` / `@task` decorators, or registering
  one with `latch register`. -> `references/authoring-workflows.md`
- Porting an existing **Nextflow** or **Snakemake** pipeline onto Latch.
- Reading or writing files through `latch:///` paths, `LatchFile`, `LatchDir`,
  or organizing samples/results in the **Registry**.
  -> `references/data-and-registry.md`
- Sizing compute — choosing `@small_task` vs `@large_gpu_task`, requesting a
  specific GPU (V100/A100), setting memory, timeout, or ephemeral storage, or
  cutting cost. -> `references/resource-configuration.md`
- Running a maintained pipeline (bulk RNA-seq, DESeq2, AlphaFold, ColabFold,
  MAFFT, single-cell) via `latch.verified`.
  -> `references/verified-workflows.md`
- Executing a registered workflow from the CLI (`latch execute`) or
  programmatically.

## When NOT to Use This Skill

- **Local-only analysis with no cloud deployment.** If you just need to run
  DESeq2, align reads, or cluster single cells on your own machine, call the
  library directly — `pydeseq2`, `biopython`, `pysam`, `scanpy`, `scvi-tools`,
  `anndata`. Latch's value is managed cloud execution and a shared UI; it is
  overhead for a one-off local script.
- **A different cloud platform.** For DNAnexus use `dnanexus-integration`; for
  Benchling's registry/ELN use `benchling-integration`. The `@task`/Registry
  concepts here do not transfer verbatim.
- **Generic Flyte/Nextflow/Snakemake authoring** unrelated to Latch hosting —
  those tools have their own native tooling.
- **Authoritative API lookup.** The Latch SDK evolves; treat the examples in
  the references as patterns and confirm exact signatures against
  `docs.latch.bio` before relying on them (this is called out where it matters,
  especially for Registry writes).

## Setup and Authentication

```bash
python3 -m pip install latch     # requires Python 3.8+
latch login                      # opens browser auth, caches a token
latch init my-workflow           # scaffold: wf/__init__.py, Dockerfile, version
latch register my-workflow       # build container + serialize + upload + gen UI
```

**Prerequisites:** Docker installed and running locally (registration builds a
container), a Latch account, and network access to the platform. `latch
register --verbose` surfaces build logs when a registration fails.

## Core Mental Model

- **Task** = one containerized step, a typed Python function under a resource
  decorator (`@small_task`, `@large_task`, `@small_gpu_task`,
  `@large_gpu_task`, or `@custom_task(...)`).
- **Workflow** = a `@workflow` function that wires tasks together by passing
  outputs as inputs; its parameter type hints and docstring populate the
  auto-generated UI.
- **Cloud data** = `LatchFile` / `LatchDir` handles over `latch:///` paths;
  inputs are downloaded to the task's local filesystem on entry and returned
  values are uploaded on exit automatically.
- **Registry** = structured metadata store (Projects -> Tables -> Records) for
  sample sheets, run status, and linking results back to inputs.

```python
from latch import workflow, small_task
from latch.types import LatchFile

@small_task
def process(input_file: LatchFile) -> LatchFile:
    """Task docstring becomes UI help text."""
    local = input_file.local_path          # already downloaded here
    # ... produce output on local disk ...
    return LatchFile("output.txt", "latch:///results/output.txt")

@workflow
def my_workflow(input_file: LatchFile) -> LatchFile:
    """Workflow description shown in the generated UI."""
    return process(input_file=input_file)
```

## Capability Reference Map

| Task | Reference |
| --- | --- |
| Define/register/execute workflows, tasks, launch plans, conditional UI, `map_task` parallelism, Nextflow/Snakemake imports | `references/authoring-workflows.md` |
| `LatchFile`/`LatchDir`, `latch:///` paths, glob, transfer semantics, Registry model, column types, linked records, transactions, workspaces | `references/data-and-registry.md` |
| Resource decorators, `@custom_task` params, GPU types, sizing by workload, timeout, storage, cost, monitoring | `references/resource-configuration.md` |
| `latch.verified` managed pipelines and combining them with custom steps | `references/verified-workflows.md` |

## Common Pitfalls

- **Registration fails silently** — 90% of the time Docker is not running or a
  dependency is missing from the `Dockerfile`. Rerun with `--verbose`.
- **Missing type hints** — every workflow/task parameter must be annotated;
  untyped params break UI generation and serialization. Use `LatchFile` /
  `LatchDir` for file and directory inputs, not `str`.
- **Resource decorators are static** — you cannot compute CPU/memory from an
  input at runtime. Define separate task variants (small/medium/large) and
  branch, or use `@custom_task` with a fixed spec. See resource reference.
- **Over-provisioning** — GPU and large tasks cost more; start small and scale
  only after profiling a real run.
- **Registry write API** — creating/mutating Tables, Columns, and Records goes
  through a transactional updater context, not simple constructors. Confirm the
  exact methods in `references/data-and-registry.md` and current docs before
  writing.

## Resources

- Docs: `https://docs.latch.bio`
- SDK source (MIT): `https://github.com/latchbio/latch`
