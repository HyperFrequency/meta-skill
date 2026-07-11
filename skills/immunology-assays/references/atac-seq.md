# ATAC-seq Chromatin Accessibility

Peak calling with MACS2, a quick differential-accessibility scan, and HOMER
motif enrichment. MACS2 and HOMER are external CLIs (install via bioconda); the
Python here wraps them and analyzes their output.

## 1. Peak Calling with MACS2

ATAC-seq needs Tn5-aware parameters: shift reads to center on the cut site and
extend so the pileup reflects accessible fragments rather than read ends.

```python
import subprocess
import pandas as pd

GENOME_SIZES = {"hs": "hs", "mm": "mm", "dm": "dm", "ce": "ce"}  # human/mouse/fly/worm

def call_peaks(bam_path, name, out_dir="macs2_out",
               genome="hs", qvalue=0.05, broad=False):
    """Call ATAC-seq peaks. Paired-end BAM required (-f BAMPE)."""
    cmd = [
        "macs2", "callpeak",
        "-t", bam_path,
        "-f", "BAMPE",                 # paired-end fragments
        "-g", GENOME_SIZES[genome],
        "--nomodel",                   # skip the ChIP-style shifting model
        "--shift", "-100",
        "--extsize", "200",            # center a 200 bp window on the Tn5 cut
        "-q", str(qvalue),
        "-n", name,
        "--outdir", out_dir,
    ]
    if broad:
        cmd.append("--broad")          # broad = open-chromatin domains
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"MACS2 failed:\n{r.stderr}")
    ext = "broadPeak" if broad else "narrowPeak"
    return f"{out_dir}/{name}_peaks.{ext}"
```

**Narrow vs broad**: narrow peaks (default) suit TF-footprint / nucleosome-free
regions; broad peaks suit large open-chromatin domains. Call whichever matches
the biological question — do not mix them across a comparison.

### Parsing peak files

`narrowPeak` and `broadPeak` are BED6+ formats. `narrowPeak` has a 10th column
(`peak`, the summit offset) that `broadPeak` lacks.

```python
def parse_peaks(path, broad=False):
    cols = ["chrom", "start", "end", "name", "score", "strand",
            "signal", "pvalue", "qvalue"]
    if not broad:
        cols += ["peak"]               # narrowPeak summit offset
    df = pd.read_csv(path, sep="\t", header=None, names=cols)
    df["width"] = df["end"] - df["start"]
    print(f"{len(df)} peaks, mean width {df['width'].mean():.0f} bp")
    return df
```

## 2. Differential Accessibility

Given a **peak × sample integer count matrix** (reads per consensus peak),
compare two conditions. The function below is a fast non-parametric scan for
exploration; it is **not** a substitute for a count-based model.

```python
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

def differential_accessibility(count_matrix, conditions, padj_threshold=0.05):
    """count_matrix: peaks x samples (int counts). conditions: label per column."""
    groups = sorted(set(conditions))
    if len(groups) != 2:
        raise ValueError("expected exactly two conditions")
    g1 = [i for i, c in enumerate(conditions) if c == groups[0]]
    g2 = [i for i, c in enumerate(conditions) if c == groups[1]]

    rows = []
    for peak in count_matrix.index:
        v1 = count_matrix.loc[peak].iloc[g1].to_numpy()
        v2 = count_matrix.loc[peak].iloc[g2].to_numpy()
        log2fc = np.log2((v2.mean() + 1) / (v1.mean() + 1))   # +1 pseudocount
        _, p = mannwhitneyu(v1, v2, alternative="two-sided")
        rows.append({"peak": peak, "log2FC": log2fc, "pvalue": p})

    df = pd.DataFrame(rows)
    df["padj"] = multipletests(df["pvalue"], method="fdr_bh")[1]
    sig = df[df["padj"] < padj_threshold]
    print(f"{len(sig)}/{len(df)} DA peaks  "
          f"(+{(sig['log2FC'] > 0).sum()} / -{(sig['log2FC'] < 0).sum()})")
    return df
```

> **Use a real model for publication.** Mann-Whitney ignores the mean-variance
> structure of counts and has no power with the typical 2–3 replicates per
> group. For anything reportable, move the same count matrix into a
> negative-binomial workflow — DESeq2, edgeR, or `pydeseq2` — and use size-factor
> normalization. MACS2 also ships `bdgdiff` for a bedGraph-based two-condition
> differential when you lack a count matrix.

Generating the count matrix: build a consensus peak set (union/intersection of
per-sample peaks), then count reads per peak per sample (e.g. `bedtools
multicov`, or `deeptools` for normalized coverage — see the `deeptools` sibling
skill).

## 3. Motif Enrichment with HOMER

```python
def homer_motifs(peak_bed, genome, out_dir, size=200, threads=4):
    """HOMER de-novo + known motif enrichment over a peak BED."""
    cmd = ["findMotifsGenome.pl", peak_bed, genome, out_dir,
           "-size", str(size), "-mask", "-p", str(threads)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_dir
```

`genome` is a HOMER genome tag (e.g. `hg38`, `mm10`) that must be preinstalled
via `perl configureHomer.pl -install <genome>`. Restrict `-size` to ~200 bp
around summits for TF motifs; widen it for broad domains. Results land in
`knownResults.html` and `homerResults.html`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| far too many peaks | permissive threshold or noisy library | raise `-q`; filter to fold-enrichment > 2; check FRiP |
| high mitochondrial read fraction | incomplete mito depletion | remove chrM reads before calling; it inflates background |
| MACS2 "no fragments" / crash | single-end BAM passed as `BAMPE` | use true paired-end alignments, or switch `-f BAM` (loses fragment sizing) |
| no motifs enriched | wrong genome tag or peaks too wide | verify the HOMER genome is installed; shrink `-size`; ensure peaks are summit-centered |
| DA scan finds nothing | too few replicates for Mann-Whitney | switch to `pydeseq2`/DESeq2 with proper normalization |
