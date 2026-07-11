# Resource Configuration

Each Latch task runs on infrastructure you select through its decorator. Pick
the smallest tier that fits, and scale only after a real run tells you it is too
small. Resource specs are **static** — they cannot be computed from an input at
runtime.

## Standard Decorators

| Decorator | Profile | Typical use |
| --- | --- | --- |
| `@small_task` | Minimal CPU/memory | Parsing, QC checks, metadata ops, aggregation |
| `@large_task` | High CPU/memory | Alignment, assembly, heavy statistics, multithreaded steps |
| `@small_gpu_task` | GPU + basic CPU/memory | NN inference, small GPU-accelerated steps |
| `@large_gpu_task` | GPU + max CPU/memory | Model training, AlphaFold-scale prediction |

```python
from latch import small_task, large_gpu_task

@small_task
def validate_inputs():
    ...

@large_gpu_task
def train_model():
    ...
```

## Custom Resources

Use `@custom_task` when the standard tiers do not fit:

```python
from latch import custom_task

@custom_task(cpu=8, memory=32, storage_gib=100, timeout=3600)
def custom_processing():
    ...
```

Parameters (confirm exact names/units against `docs.latch.bio` — they have
shifted across SDK versions):

- `cpu` — CPU cores (int)
- `memory` — memory in GB (int)
- `storage_gib` — ephemeral storage in GiB (int)
- `timeout` — max execution seconds (int)
- `gpu` — number of GPUs (int; 0 for CPU-only)
- `gpu_type` — GPU model string (e.g. `"nvidia-tesla-a100"`)

```python
@custom_task(cpu=16, memory=64, storage_gib=500, timeout=7200,
             gpu=1, gpu_type="nvidia-tesla-a100")
def alphafold_prediction():
    ...
```

## GPU Types

- `nvidia-tesla-k80` — entry-level, for testing.
- `nvidia-tesla-v100` — high-performance training/inference.
- `nvidia-tesla-a100` — top tier, maximum throughput.

Multi-GPU: set `gpu=N` with a `gpu_type`; the task must actually implement
distributed/multi-GPU execution to benefit.

```python
@custom_task(cpu=32, memory=128, gpu=4, gpu_type="nvidia-tesla-v100")
def multi_gpu_training():
    ...
```

## Sizing by Workload

- **Memory-bound** (genome assembly): high memory, moderate CPU —
  `@custom_task(cpu=4, memory=128)`.
- **CPU-bound** (parallel alignment): high CPU, moderate memory —
  `@custom_task(cpu=64, memory=32)`.
- **I/O-bound** (large intermediates): large ephemeral storage —
  `@custom_task(cpu=8, memory=16, storage_gib=1000)`.

Mix tiers across a pipeline so each stage is right-sized:

```python
from latch import workflow, small_task, large_task, large_gpu_task
from latch.types import LatchFile

@small_task
def quality_control(fastq: LatchFile) -> LatchFile: ...
@large_task
def alignment(fastq: LatchFile) -> LatchFile: ...
@large_gpu_task
def variant_calling(bam: LatchFile) -> LatchFile: ...
@small_task
def generate_report(vcf: LatchFile) -> LatchFile: ...

@workflow
def genomics_pipeline(input_fastq: LatchFile) -> LatchFile:
    qc = quality_control(fastq=input_fastq)
    aligned = alignment(fastq=qc)
    variants = variant_calling(bam=aligned)
    return generate_report(vcf=variants)
```

## Timeout and Storage

- **Timeout** — estimate conservatively and add a buffer; adjust from observed
  runtimes. Long jobs need an explicit `timeout` well above the default.
- **Ephemeral storage** — scratch space (commonly under `/tmp`) cleared after
  the task finishes. Raise `storage_gib` for large intermediate files. Use
  `LatchDir` for anything that must persist.

## Static-Resource Workaround

Because decorators cannot read inputs, branch across pre-declared task variants
for different data sizes instead of computing a spec at runtime:

```python
@custom_task(cpu=4,  memory=16)
def process_small(f: LatchFile) -> LatchFile: ...
@custom_task(cpu=16, memory=64)
def process_medium(f: LatchFile) -> LatchFile: ...
@custom_task(cpu=32, memory=128)
def process_large(f: LatchFile) -> LatchFile: ...
```

## Cost and Failure Modes

| Problem | Cause | Fix |
| --- | --- | --- |
| Out of memory (OOM) | `memory` too low | Raise `memory` |
| Task killed at time limit | `timeout` too low | Raise `timeout` |
| No space left on device | `storage_gib` too low | Raise `storage_gib` |
| Surprising bill | Over-provisioned / needless GPU | Right-size; drop GPU unless the algorithm uses it |

Cost discipline: start with standard decorators, profile a real run, prefer
several parallel small tasks over one oversized task, and reserve GPU for steps
that genuinely exploit it.

## Platform Limits

Latch enforces per-task and per-workspace ceilings (max CPU/memory/GPU, max
concurrent executions, storage and runtime quotas). These change over time and
by plan — check current limits in the platform, and request increases through
Latch support if a job exceeds them.
