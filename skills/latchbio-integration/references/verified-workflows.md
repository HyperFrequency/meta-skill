# Verified Workflows

`latch.verified` exposes maintained, production-ready pipelines you call like
functions instead of re-implementing. Import the ones you need and pass
`LatchFile`/`LatchDir` inputs plus an output location. Parameter names below are
representative — confirm the current signature and defaults for any workflow
against `docs.latch.bio` before a production run, and pin a version when
reproducibility matters.

```python
from latch.verified import (
    bulk_rnaseq, deseq2, mafft, trim_galore, alphafold, colabfold,
)
```

## Bulk RNA-seq and Differential Expression

```python
from latch.verified import bulk_rnaseq, deseq2
from latch.types import LatchFile

rnaseq = bulk_rnaseq(
    fastq_r1=LatchFile("latch:///data/sample_R1.fastq.gz"),
    fastq_r2=LatchFile("latch:///data/sample_R2.fastq.gz"),
    reference_genome="hg38",
    output_dir="latch:///results/rnaseq",
)

deg = deseq2(
    count_matrix=LatchFile("latch:///data/counts.csv"),
    sample_metadata=LatchFile("latch:///data/metadata.csv"),
    design_formula="~ condition",
    output_dir="latch:///results/deseq2",
)
```

- **bulk_rnaseq** — FastQC, adapter trimming, STAR/HISAT2 alignment,
  featureCounts quantification, MultiQC report.
- **deseq2** — normalization/variance stabilization, DE testing, MA and volcano
  plots, PCA, annotated results tables. (For local DESeq2, run the `pydeseq2`
  library directly.)

## Pathway Enrichment

```python
from latch.verified import pathway_enrichment

pathway_enrichment(
    gene_list=LatchFile("latch:///data/deg_list.txt"),
    organism="human",
    databases=["GO_Biological_Process", "KEGG", "Reactome"],
    output_dir="latch:///results/pathways",
)
```

Databases include GO, KEGG, Reactome, WikiPathways, and MSigDB collections.

## Sequence Alignment and Trimming

- **mafft** — multiple sequence alignment; algorithms FFT-NS-1/2, G-INS-i,
  L-INS-i, or `auto`; multiple output formats.
- **trim_galore** — automatic adapter detection, quality trimming, FastQC
  integration, single- and paired-end.

```python
from latch.verified import mafft
aligned = mafft(
    input_fasta=LatchFile("latch:///data/sequences.fasta"),
    algorithm="auto",
    output_format="fasta",
)
```

## Protein Structure Prediction

```python
from latch.verified import alphafold, colabfold
from latch.types import LatchFile

structure = alphafold(
    sequence_fasta=LatchFile("latch:///data/protein.fasta"),
    model_preset="monomer",          # monomer | monomer_ptm | multimer | monomer_casp14
    use_templates=True,
    output_dir="latch:///results/alphafold",
)

fast = colabfold(
    sequence_fasta=LatchFile("latch:///data/protein.fasta"),
    num_models=5,
    use_amber_relax=True,
    output_dir="latch:///results/colabfold",
)
```

- **alphafold** — monomer/multimer, optional templates, MSA generation, pLDDT
  and PAE confidence, PDB output.
- **colabfold** — MMseqs2-based MSA (much faster than the standard MSA step),
  multiple model predictions, Amber relaxation, confidence ranking; lower cost
  at similar accuracy. Both are GPU-heavy — see `resource-configuration.md`.

## Single-Cell

- **archr** — scATAC-seq: arrow files, QC, dimensionality reduction, clustering,
  peak calling, motif enrichment.
- **scvelo** — RNA velocity: spliced/unspliced quantification, dynamical
  modeling, trajectory inference.
- **emptydrops** — distinguishes real cells from empty droplets by FDR
  threshold; removes ambient RNA (10x-compatible).

```python
from latch.verified import scvelo
scvelo(
    adata_file=LatchFile("latch:///data/adata.h5ad"),
    mode="dynamical",
    output_dir="latch:///results/scvelo",
)
```

For local single-cell analysis outside Latch, use the `anndata` skill together
with libraries like `scanpy` and `scvi-tools`.

## Gene Editing and Phylogenetics

- **crispresso2** — CRISPR editing assessment: indel quantification, base and
  prime editing analysis, HDR quantification, allele-frequency plots.
- **phylogenetics** — tree construction (e.g. maximum likelihood), bootstrap
  support, model selection, tree visualization.

## Combining Verified and Custom Steps

Call verified workflows as steps inside your own `@workflow`, wrapping them with
custom pre/post-processing:

```python
from latch import workflow, small_task
from latch.verified import alphafold
from latch.types import LatchFile

@small_task
def preprocess_sequence(raw_fasta: LatchFile) -> LatchFile:
    return processed_fasta

@small_task
def postprocess_structure(pdb_file: LatchFile) -> LatchFile:
    return analysis_results

@workflow
def custom_structure_pipeline(input_fasta: LatchFile) -> LatchFile:
    processed = preprocess_sequence(raw_fasta=input_fasta)
    structure = alphafold(sequence_fasta=processed, model_preset="monomer_ptm")
    return postprocess_structure(pdb_file=structure)
```

## When to Use Which

**Verified** for standard, well-established, reproducible analyses on validated
tools. **Custom** for novel methods, bespoke preprocessing, proprietary tools,
or experimental pipelines. Enumerate what is currently available with the SDK's
verified-workflow listing helper (name varies by version — check the docs), and
pin `workflow_version` where a run must stay reproducible.
