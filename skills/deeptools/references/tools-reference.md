# deepTools Command Reference

Every deepTools utility is a standalone CLI command. This reference groups them
by role and lists the parameters that matter in practice. Flags follow deepTools
convention: most tools accept a long form (`--numberOfProcessors`) and a short
alias (`-p`). Almost all tools share `--region chr:start-end`, `-p/--numberOfProcessors`,
`--ignoreDuplicates`, `--minMappingQuality`, `--samFlagInclude/--samFlagExclude`,
and `--minFragmentLength/--maxFragmentLength`.

## BAM and bigWig Processing

### bamCoverage

Converts one BAM into a normalized coverage track (bigWig or bedGraph). Coverage
is reads per bin.

Key parameters:

- `--bam, -b` — input BAM (indexed). Required.
- `--outFileName, -o` — output track. Required.
- `--outFileFormat, -of` — `bigwig` (default) or `bedgraph`.
- `--normalizeUsing` — `RPKM`, `CPM`, `BPM`, `RPGC`, or `None` (default).
- `--effectiveGenomeSize` — required when `--normalizeUsing RPGC`.
- `--binSize` — resolution in bp (default 50; use 10 for sharp ChIP signal).
- `--extendReads, -e` — extend reads to fragment length. Use for ChIP-seq; never
  for RNA-seq.
- `--centerReads` — center reads at fragment midpoint for sharper peaks.
- `--filterRNAstrand forward|reverse` — split stranded RNA-seq coverage.
- `--MNase` — score only the fragment center (nucleosome positioning).
- `--Offset` — position-specific offset (RiboSeq, GROseq).
- `--smoothLength` — moving-average window to reduce noise.
- `--ignoreForNormalization chrX chrY chrM` — exclude chromosomes from the
  normalization scale factor.
- `--scaleFactor` — apply a manual multiplier (e.g. spike-in factor).

```bash
# ChIP-seq, RPGC-normalized
bamCoverage --bam chip.bam -o chip.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398 --binSize 10 --extendReads 200 \
    --ignoreDuplicates -p 8
```

Guardrails: RNA-seq → no `--extendReads`; never `--ignoreDuplicates` after GC
correction.

### bamCompare

Compares two BAMs bin-by-bin into a single track, correcting for depth
differences.

- `--bamfile1, -b1` / `--bamfile2, -b2` — the two BAMs. Required.
- `--outFileName, -o` — output. Required.
- `--operation` — `log2` (default), `ratio`, `subtract`, `add`, `mean`,
  `reciprocal_ratio`, `first`, `second`.
- `--scaleFactorsMethod` — depth-scaling method: `readCount` (default), `SES`, or
  `None`. This is the *between-sample* scaling and is distinct from
  `--normalizeUsing`.
- `--normalizeUsing` — `RPKM`, `CPM`, `BPM`, `RPGC`, or `None` (default). To use
  it you must set `--scaleFactorsMethod None` (the two are mutually exclusive);
  `RPGC` additionally requires `--effectiveGenomeSize`.
- `--pseudocount` — avoid divide-by-zero (default 1).
- `--binSize` — output bin width (default 50).

```bash
bamCompare -b1 chip.bam -b2 input.bam -o log2ratio.bw \
    --operation log2 --scaleFactorsMethod readCount --extendReads 200 -p 8
```

### multiBamSummary

Computes read coverage over genomic windows across many BAMs, emitting a
compressed `.npz` matrix for `plotCorrelation` / `plotPCA`.

- Modes: `bins` (genome-wide equal windows, default 10 kb) or `BED-file`
  (restrict to `--BED regions.bed`).
- `--bamfiles, -b` — space-separated indexed BAMs. Required.
- `--outFileName, -o` — `.npz` matrix. Required.
- `--binSize`, `--labels`, `--outRawCounts` (tab-delimited coords + per-sample
  counts).

```bash
multiBamSummary bins --bamfiles s1.bam s2.bam s3.bam -o counts.npz -p 8
multiBamSummary BED-file --BED peaks.bed --bamfiles s1.bam s2.bam -o counts.npz
```

### multiBigwigSummary

Same idea as `multiBamSummary` but over bigWig tracks (use when comparing
already-normalized coverage). Same `bins` / `BED-file` modes.

### alignmentSieve

Filters a BAM on the fly and writes a reusable filtered BAM.

- `--bam, -b` / `--outFile, -o`.
- `--shift` — arbitrary read shift; `--ATACshift` — apply the standard Tn5
  offset for ATAC-seq automatically.
- Standard filters: `--minMappingQuality`, `--ignoreDuplicates`,
  `--minFragmentLength/--maxFragmentLength`, `--samFlagInclude/--samFlagExclude`.

### computeGCBias / correctGCBias

`computeGCBias` measures GC bias from amplification/sequencing; `correctGCBias`
rewrites the BAM to remove it. Both need a 2bit reference.

- `--bamfile, -b`, `--effectiveGenomeSize`, `--genome, -g` (2bit).
- `computeGCBias`: `--fragmentLength, -l` (single-end), `--biasPlot`,
  `--frequenciesFile`.
- `correctGCBias`: `--GCbiasFrequenciesFile` (from computeGCBias),
  `--correctedFile, -o`.

Only correct when bias is real, and never `--ignoreDuplicates` on a corrected
BAM.

## Quality Control

### plotFingerprint

The primary ChIP-seq QC. Plots cumulative read coverage to judge enrichment.

- `--bamfiles, -b` (input + ChIP), `--plotFile, -o`, `--labels`.
- `--extendReads`, `--ignoreDuplicates`, `--centerReads`.
- `--outQualityMetrics` — writes Jensen-Shannon distance and other metrics.
- `--outRawCounts` — per-bin counts.

Interpretation: input control ≈ straight diagonal; strong ChIP rises steeply
toward the top rank (reads concentrated in few bins); weak enrichment hugs the
diagonal.

### plotCoverage

Shows the genome-wide read-depth distribution to judge whether sequencing depth
is adequate. `--bamfiles`, `--plotFile`, `--numberOfSamples` (positions sampled,
default 1,000,000), `--ignoreDuplicates`.

### bamPEFragmentSize

Fragment-length distribution for paired-end data. `--bamfiles`,
`--histogram/-hist`, `--maxFragmentLength` (default 1000), `--logScale`,
`--outRawFragmentLengths`. ATAC-seq should show a nucleosome ladder; ChIP-seq
typically 200-600 bp.

### plotCorrelation

Correlates samples from a `multiBamSummary`/`multiBigwigSummary` `.npz`.

- `--corData, -in` (`.npz`), `--corMethod pearson|spearman`,
  `--whatToShow heatmap|scatterplot`, `--plotFile, -o`.
- `--skipZeros`, `--removeOutliers` (MAD filter), `--plotNumbers`,
  `--outFileCorMatrix`, `--colorMap`.

Pearson is sensitive to outliers (normal data); Spearman is rank-based (robust,
non-normal). Replicates should correlate > 0.9.

### plotPCA

PCA from the same `.npz`. `--corData, -in`, `--plotFile, -o`,
`--outFileNameData` (loadings + eigenvalues), `--transpose` (rows = samples),
`--ntop` (top-N variable rows, default 1000), `--PCs` (default `1 2`), `--log2`,
`--rowCenter`.

## Visualization

### computeMatrix

Builds the per-region signal matrix consumed by `plotHeatmap`/`plotProfile`.

- Modes: `reference-point` (signal relative to `--referencePoint TSS|TES|center`)
  or `scale-regions` (regions stretched to uniform length).
- `-S` bigWig score file(s), `-R` BED/GTF region file(s), `-o` output `.gz`. All
  required.
- `-b` upstream length, `-a` downstream length, `-m` region-body length
  (scale-regions only), `-bs/--binSize`.
- `--skipZeros`, `--minThreshold/--maxThreshold`,
  `--sortRegions ascending|descending|keep|no`,
  `--sortUsing mean|median|max|min|sum|region_length`,
  `--averageTypeBins mean|median|min|max|sum|std`.
- Exports: `--outFileNameMatrix` (tab-delimited), `--outFileSortedRegions`.

```bash
computeMatrix reference-point -S signal.bw -R genes.bed \
    --referencePoint TSS -b 2000 -a 2000 -o matrix.gz -p 8
computeMatrix scale-regions -S signal.bw -R genes.bed -b 1000 -a 1000 -m 3000 -o matrix.gz
```

### plotHeatmap

Region heatmap from a matrix.

- `-m` matrix, `-o` image (png/eps/pdf/svg).
- Clustering: `--kmeans`, `--hclust`, `--silhouette`.
- Color/scale: `--colorMap`, `--colorList`, `--zMin/--zMax`, `--alpha`,
  `--interpolationMethod`, `--dpi`.
- Layout: `--heatmapHeight/--heatmapWidth` (3-100 cm), `--whatToShow`
  (`'plot, heatmap and colorbar'`), `--boxAroundHeatmaps`.
- Labels: `--samplesLabel`, `--regionsLabel`, `--refPointLabel`,
  `--startLabel/--endLabel`, `--xAxisLabel/--yAxisLabel`.
- Export: `--outFileSortedRegions`, `--outFileNameMatrix`.

### plotProfile

Meta-profile from a matrix. `-m`, `-o`,
`--plotType lines|fill|se|std|overlapped_lines|heatmap`, `--colors`,
`--perGroup`, `--yMin/--yMax`, `--averageType`, clustering flags as above,
`--outFileNameData` (export tab data).

### plotEnrichment

Percentage of alignments overlapping region sets — the basis for FRiP.

- `--bamfiles, -b`, `--BED` (one or more region files), `--plotFile, -o`.
- `--labels`, `--regionLabels`, `--perSample`, `--outRawCounts`.
- Read processing: `--extendReads`, `--ignoreDuplicates`, `--centerReads`,
  fragment/quality/flag filters.

```bash
plotEnrichment -b input.bam chip.bam --BED peaks_up.bed peaks_down.bed \
    --regionLabels "Up" "Down" -o enrichment.png --extendReads 200 --ignoreDuplicates
```

## Miscellaneous

### computeMatrixOperations

Manipulates existing `computeMatrix` outputs without recomputation. Subcommands:
`cbind` (column-merge), `rbind` (row-merge), `subset` (pick samples/regions),
`filterStrand`, `filterValues`, `sort`, `dataRange`.

```bash
computeMatrixOperations cbind -m m1.gz m2.gz -o combined.gz
computeMatrixOperations subset -m matrix.gz --samples 0 2 -o subset.gz
```

### estimateReadFiltering

Predicts the effect of filters without filtering. `--bamfiles`, `--sampleSize`
(default 100,000), then test `--minMappingQuality`, `--ignoreDuplicates`,
`--minFragmentLength/--maxFragmentLength`.
