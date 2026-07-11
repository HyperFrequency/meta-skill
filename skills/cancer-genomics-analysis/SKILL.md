---
name: cancer-genomics-analysis
version: 0.1.0
description: >-
  Computational cancer-genomics workflows over tumor sequencing data: somatic
  mutation calling from tumor-normal pairs (GATK Mutect2 best-practice chain),
  VCF parsing/filtering/annotation (cyvcf2 + SnpEff/VEP), tumor mutational burden
  (TMB) biomarkers, structural-variant classification, copy-number profiling and
  segmentation (CNVkit), tumor purity/ploidy, NMF metagene extraction from
  expression matrices with cophenetic rank selection, and DNA-damage-response
  co-expression network analysis. Use when you have tumor (± matched normal)
  WES/WGS or RNA-seq and need somatic variants, CNV/SV calls, TMB, or
  transcriptional programs. Do NOT use for germline-only pipelines, single-cell
  or spatial data, raw read alignment/QC, mutational-signature deconvolution, or
  regulated clinical variant interpretation — for that, cross-check the COSMIC
  and ClinVar databases. Uses the `scikit-learn` and `networkx` sibling skills.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "cyvcf2: MIT; scikit-learn: BSD-3-Clause; networkx: BSD-3-Clause; gseapy: MIT"
---

# Cancer Genomics Analysis

## Overview

Turn tumor sequencing data into quantitative, interpretable genomic findings.
This skill covers the four workhorse analyses of a somatic cancer study: calling
and annotating somatic mutations, profiling copy number and structural variants,
estimating tumor purity/ploidy, and extracting transcriptional programs from
expression data. The tooling is standard and open: GATK Mutect2, SnpEff/VEP,
CNVkit, `cyvcf2`, scikit-learn NMF, and `networkx`.

This file is a **router**. Each capability below links to a `references/` file
that holds the runnable commands, exact parameters, and failure modes. Read the
capability map, jump to the reference you need, then come back for boundaries.

## When to Use This Skill

- Calling somatic variants from tumor-normal (or tumor-only) WES/WGS.
- Filtering, annotating, and tabulating a somatic VCF; computing TMB.
- Detecting and classifying structural variants (DEL/DUP/INV/BND/translocations).
- Profiling copy number, calling gains/losses/amplifications/deep deletions.
- Estimating tumor purity and ploidy before interpreting absolute copy number.
- Extracting NMF metagene programs from a tumor expression matrix and labeling
  them by pathway enrichment.
- Comparing DNA-damage-response co-expression networks between tumor and normal.

## When NOT to Use This Skill

- **Germline-only** variant calling / ACMG classification — a different pipeline.
- **Single-cell or spatial** genomics — needs a scanpy-style stack, not these
  bulk-tissue workflows.
- **Raw-read processing** (alignment, dedup, BQSR, FASTQ QC) — that is upstream.
- **Mutational-signature deconvolution** (SBS/COSMIC 96-context NMF) — use a
  dedicated signatures package; it is distinct from the *expression* NMF here.
- **Regulated clinical interpretation / reporting** — this skill produces the
  quantitative substrate; pathogenicity and therapy calls are out of scope.
  Validate findings against the COSMIC and ClinVar databases.

## Setup

```bash
uv pip install cyvcf2 pysam scikit-learn networkx gseapy pandas numpy scipy
# Command-line callers install separately (e.g. via bioconda):
# conda install -c bioconda gatk4 snpeff cnvkit bcftools
```

## Capability Map

### Somatic mutations, annotation, and TMB
The GATK Mutect2 best-practice chain (contamination + orientation-bias filtering),
SnpEff/VEP annotation, `cyvcf2` parsing with quality filters, and tumor mutational
burden with classification thresholds and assay-footprint caveats.
→ `references/somatic-mutations.md`

### Copy number, purity/ploidy, and structural variants
CNVkit `batch` and granular pipelines, segment calling by log2 ratio, purity-aware
integer copy-number calling, why low purity understates gains/losses (and the
real tools for it — ASCAT/FACETS/Sequenza/PureCN), and structural-variant parsing
including breakend/translocation handling.
→ `references/copy-number-sv.md`

### Expression signatures (NMF metagenes) and DDR networks
NMF decomposition of a genes-x-samples matrix into interpretable metagene
programs, cophenetic-correlation rank selection, `gseapy` enrichment labeling, and
DNA-damage-response co-expression network comparison between tumor and normal.
→ `references/expression-signatures.md`

### Best practices, failure modes, and boundaries
Filter floors, the full troubleshooting table (VCF indexing, sample-name
mismatches, purity compression, NMF instability, TMB denominators, breakends), and
explicit scope boundaries.
→ `references/troubleshooting.md`

## Quick Start

Parse a somatic VCF and rank the most-mutated genes. The VCF must be bgzipped and
tabix-indexed (`bcftools view -O z -o out.vcf.gz in.vcf && tabix -p vcf out.vcf.gz`).

```python
import cyvcf2
import pandas as pd

vcf = cyvcf2.VCF("somatic.filtered.vcf.gz")
rows = []
for v in vcf:
    if v.FILTER is not None and v.FILTER != "PASS":   # None == PASS in cyvcf2
        continue
    annotation = v.INFO.get("ANN", "")                 # SnpEff pipe-delimited
    rows.append({
        "chrom": v.CHROM, "pos": v.POS,
        "ref": v.REF, "alt": ",".join(v.ALT),
        "af": v.INFO.get("AF"), "dp": v.INFO.get("DP"),
        "gene": annotation.split("|")[3] if annotation else "",
    })

df = pd.DataFrame(rows)
print(f"PASS variants: {len(df)}")
print(df["gene"].value_counts().head(10))
```

## Related Skills

- `scikit-learn` — the NMF decomposition and clustering behind metagene extraction.
- `networkx` — graph construction and analysis for the DDR co-expression networks.
- `statistical-analysis` — significance testing for enrichment and group comparisons.
- External databases (not skills): validate calls against **COSMIC** (cancer
  mutations) and **ClinVar** (clinical significance).
