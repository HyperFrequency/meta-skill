# Configuration and Dependencies (dxapp.json)

`dxapp.json` defines an app/applet: identity, inputs, outputs, how it runs, and
what it depends on. It is validated by `dx build`.

## Minimal file

```json
{
  "name": "my-app",
  "title": "My Analysis App",
  "summary": "Performs analysis on input files",
  "dxapi": "1.0.0",
  "version": "1.0.0",
  "inputSpec": [],
  "outputSpec": [],
  "runSpec": {
    "interpreter": "python3",
    "file": "src/my-app.py",
    "distribution": "Ubuntu",
    "release": "24.04"
  }
}
```

`name` is lowercase letters/digits/`-`/`_`. `version` is required for apps
(semantic versioning). `dxapi` is the platform API version.

## inputSpec / outputSpec

Each entry declares one parameter.

```json
"inputSpec": [
  {"name": "reads", "class": "file", "patterns": ["*.fastq", "*.fastq.gz"],
   "label": "Input reads", "help": "Sequencing reads", "optional": false},
  {"name": "quality_threshold", "class": "int", "default": 30, "optional": true},
  {"name": "reference", "class": "file", "patterns": ["*.fa", "*.fasta"],
   "suggestions": [{"name": "GRCh38", "project": "project-XXXX",
                    "path": "/references/GRCh38.fa"}]}
]
```

**Classes:** `file`, `record`, `applet`, `string`, `int`, `float`, `boolean`,
`hash`, and `array:<class>` (e.g. `array:file`).

**Common keys:** `name` + `class` (required), `optional`, `default`, `label`,
`help`, `patterns` (filename globs for files), `choices` (allowed values),
`suggestions` (pre-filled reference data), `group` (UI grouping).

`outputSpec` uses the same shape:

```json
"outputSpec": [
  {"name": "aligned_reads", "class": "file", "patterns": ["*.bam"]},
  {"name": "mapping_stats",  "class": "record"}
]
```

## runSpec

```json
"runSpec": {
  "interpreter": "python3",           // or "bash"
  "file": "src/my-app.py",
  "distribution": "Ubuntu",
  "release": "24.04",
  "execDepends": [{"name": "samtools"}, {"name": "bwa"}],
  "bundledDepends": [
    {"name": "scripts.tar.gz", "id": {"$dnanexus_link": "file-XXXX"}}],
  "assetDepends": [
    {"name": "star-asset", "id": {"$dnanexus_link": "record-XXXX"}}],
  "systemRequirements": {"*": {"instanceType": "mem2_ssd1_v2_x4"}},
  "restartableEntryPoints": ["main"],
  "timeoutPolicy": {"*": {"hours": 8}}
}
```

## Dependencies

### System packages — `execDepends`

Installed with `apt-get` from Ubuntu repos at job start.

```json
"execDepends": [{"name": "samtools"}, {"name": "bwa"},
                {"name": "r-base", "version": "4.0.0"}]
```

### Python packages

Install `python3-pip` via `execDepends`, then either `pip install` explicit
pins in your app, or ship `resources/requirements.txt` and
`pip install -r requirements.txt`. Pin versions for reproducibility.

### Bundled resources

Anything under `resources/` is unpacked onto the worker at build time (rooted at
`/`). Use for small custom tools/scripts. For large/heavy dependencies, prefer
assets.

### Assets — `assetDepends`

Assets are pre-built, shareable dependency bundles (compiled tools, big
reference blobs) mounted at runtime.

```bash
dx build_asset my-asset --destination=project-XXXX:/assets/
```

```json
"assetDepends": [{"name": "bwa-asset", "id": {"$dnanexus_link": "record-XXXX"}}]
```

## Docker

Request `docker.io` and network access, then pull/run images in-app:

```json
"runSpec": {"interpreter": "bash", "file": "src/wrapper.sh",
            "execDepends": [{"name": "docker.io"}]},
"access": {"network": ["*"]}
```

```python
subprocess.check_call(["docker", "pull", "biocontainers/samtools:v1.9"])
subprocess.check_call(["docker", "run", "-v", f"{os.getcwd()}:/data",
                       "biocontainers/samtools:v1.9",
                       "samtools", "view", "/data/input.bam"])
```

## systemRequirements (instance types)

Set per entry point (`"*"` = all). Names follow
`mem{1|2|3}_ssd{n}_v2_x{cores}` — higher `mem` tier means more RAM per core.

```json
"systemRequirements": {
  "main":    {"instanceType": "mem2_ssd1_v2_x8"},
  "process": {"instanceType": "mem3_ssd1_v2_x16"}
}
```

Exact RAM/disk and availability vary by region and change over time — verify
against the current DNAnexus instance-type catalog rather than assuming fixed
specs. Start small and scale up on OOM.

### Cluster (Spark)

```json
"systemRequirements": {"main": {"clusterSpec": {
  "type": "spark", "version": "3.1.2",
  "initialInstanceCount": 3, "instanceType": "mem1_ssd1_v2_x4",
  "bootstrapScript": "bootstrap.sh"}}}
```

## regionalOptions

Per-region instance types and asset IDs for multi-region apps:

```json
"regionalOptions": {
  "aws:us-east-1": {"systemRequirements": {"*": {"instanceType": "mem2_ssd1_v2_x4"}},
                    "assetDepends": [{"id": "record-XXXX"}]},
  "azure:westus":  {"systemRequirements": {"*": {"instanceType": "azure:mem2_ssd1_x4"}}}
}
```

## access

Least-privilege by default; request only what the app needs.

```json
"access": {
  "network": ["*"],           // or specific hosts: ["github.com", "pypi.org"]
  "project": "CONTRIBUTE",     // write to the running project
  "allProjects": "VIEW",       // read other projects
  "developer": true
}
```

## timeoutPolicy

```json
"timeoutPolicy": {"*": {"days": 1, "hours": 12, "minutes": 30}}
```

## Complete example (RNA-seq)

```json
{
  "name": "rna-seq-pipeline",
  "title": "RNA-Seq Analysis Pipeline",
  "summary": "Aligns RNA-seq reads and quantifies gene expression",
  "version": "1.0.0",
  "dxapi": "1.0.0",
  "categories": ["Read Mapping", "RNA-Seq"],
  "inputSpec": [
    {"name": "reads", "class": "array:file", "patterns": ["*.fastq.gz", "*.fq.gz"]},
    {"name": "reference_genome", "class": "file", "patterns": ["*.fa", "*.fasta"]},
    {"name": "gtf_file", "class": "file", "patterns": ["*.gtf", "*.gtf.gz"]}
  ],
  "outputSpec": [
    {"name": "aligned_bam", "class": "file", "patterns": ["*.bam"]},
    {"name": "counts", "class": "file", "patterns": ["*.counts.txt"]},
    {"name": "qc_report", "class": "file", "patterns": ["*.html"]}
  ],
  "runSpec": {
    "interpreter": "python3",
    "file": "src/rna-seq-pipeline.py",
    "distribution": "Ubuntu",
    "release": "24.04",
    "execDepends": [{"name": "python3-pip"}, {"name": "samtools"}, {"name": "subread"}],
    "assetDepends": [{"name": "star-aligner", "id": {"$dnanexus_link": "record-star"}}],
    "systemRequirements": {"main": {"instanceType": "mem3_ssd1_v2_x16"}},
    "timeoutPolicy": {"*": {"hours": 8}}
  },
  "access": {"network": ["*"]},
  "details": {"citations": ["doi:10.1093/bioinformatics/bts635"]}
}
```

## Practices

- Semantic-version apps; document dependencies in `details`.
- Prefer assets for heavy shared deps; bundle only small helpers.
- Request minimal `access` (network hosts, project level).
- Pin package versions for reproducibility.
- Right-size instances: start small, scale on OOM/timeout, don't over-provision (cost).
