# deepTools Workflows

Complete, copy-paste pipelines for the common assays. Replace filenames,
effective genome size (see `genome-sizes.md`), and `-p 8` with your core count.

## ChIP-seq Quality Control

Run this before any figure work.

```bash
# 1. Coverage matrix across the genome, then correlation + PCA
multiBamSummary bins \
    --bamfiles Input1.bam Input2.bam ChIP1.bam ChIP2.bam \
    --labels Input_rep1 Input_rep2 ChIP_rep1 ChIP_rep2 \
    -o readCounts.npz -p 8

plotCorrelation -in readCounts.npz --corMethod pearson \
    --whatToShow heatmap --plotFile correlation_heatmap.png --plotNumbers

plotPCA -in readCounts.npz -o PCA_plot.png -T "PCA of ChIP-seq samples"

# 2. Depth adequacy
plotCoverage --bamfiles Input1.bam ChIP1.bam ChIP2.bam \
    --labels Input ChIP_rep1 ChIP_rep2 --plotFile coverage.png \
    --ignoreDuplicates -p 8

# 3. Fragment-size distribution (paired-end)
bamPEFragmentSize --bamfiles Input1.bam ChIP1.bam ChIP2.bam \
    --histogram fragmentSizes.png --plotTitle "Fragment Size Distribution"

# 4. GC bias — detect, correct only if real
computeGCBias --bamfile ChIP1.bam --effectiveGenomeSize 2913022398 \
    --genome genome.2bit --fragmentLength 200 --biasPlot GCbias.png \
    --frequenciesFile freq.txt
correctGCBias --bamfile ChIP1.bam --effectiveGenomeSize 2913022398 \
    --genome genome.2bit --GCbiasFrequenciesFile freq.txt \
    --correctedFile ChIP1_GCcorrected.bam

# 5. ChIP enrichment strength
plotFingerprint --bamfiles Input1.bam ChIP1.bam ChIP2.bam \
    --labels Input ChIP_rep1 ChIP_rep2 --plotFile fingerprint.png \
    --extendReads 200 --ignoreDuplicates -p 8 \
    --outQualityMetrics fingerprint_metrics.txt
```

Read the results: replicates cluster together and separate from input; fragment
sizes match the library prep (200-600 bp); fingerprint rises steeply for a good
ChIP, hugs the diagonal for a failed one. Do NOT pass `--ignoreDuplicates` on a
GC-corrected BAM.

## ChIP-seq Full Analysis (BAM → figures)

```bash
# 1. Normalized coverage tracks (input and ChIP)
for s in Input ChIP; do
  bamCoverage --bam ${s}.bam -o ${s}_coverage.bw --normalizeUsing RPGC \
      --effectiveGenomeSize 2913022398 --binSize 10 --extendReads 200 \
      --ignoreDuplicates -p 8
done

# 2. Log2 ratio track (enrichment positive, depletion negative)
bamCompare -b1 ChIP.bam -b2 Input.bam -o ChIP_vs_Input_log2.bw \
    --operation log2 --scaleFactorsMethod readCount --binSize 10 \
    --extendReads 200 --ignoreDuplicates -p 8

# 3. Signal matrix around the TSS
computeMatrix reference-point --referencePoint TSS \
    -S ChIP_coverage.bw -R genes.bed -b 3000 -a 3000 --binSize 10 \
    --sortRegions descend --sortUsing mean \
    -o matrix_TSS.gz --outFileNameMatrix matrix_TSS.tab -p 8

# 4. Heatmap
plotHeatmap -m matrix_TSS.gz -o heatmap_TSS.png --colorMap RdBu \
    --whatToShow 'plot, heatmap and colorbar' --zMin -3 --zMax 3 \
    --refPointLabel TSS --xAxisLabel "Distance from TSS (bp)" \
    --heatmapHeight 15 --kmeans 3

# 5. Meta-profile
plotProfile -m matrix_TSS.gz -o profile_TSS.png --plotType lines --perGroup \
    --colors blue --plotTitle "ChIP-seq signal around TSS" \
    --refPointLabel TSS

# 6. Enrichment at peaks (FRiP-style)
plotEnrichment -b Input.bam ChIP.bam --BED peaks.bed --labels Input ChIP \
    --plotFile enrichment.png --outRawCounts enrichment_counts.tab \
    --extendReads 200 --ignoreDuplicates
```

## RNA-seq Strand-Specific Coverage

Never `--extendReads` (it would span splice junctions). One track per strand.

```bash
bamCoverage --bam rnaseq.bam -o forward_coverage.bw \
    --filterRNAstrand forward --normalizeUsing CPM --binSize 1 -p 8
bamCoverage --bam rnaseq.bam -o reverse_coverage.bw \
    --filterRNAstrand reverse --normalizeUsing CPM --binSize 1 -p 8
```

For gene-level coverage that accounts for gene length, use `--normalizeUsing RPKM`.

## ATAC-seq (Tn5 offset)

```bash
# 1. Shift reads for the Tn5 insertion offset
alignmentSieve --bam atacseq.bam --outFile atacseq_shifted.bam --ATACshift \
    --minFragmentLength 38 --maxFragmentLength 2000 --ignoreDuplicates

# 2. Coverage from the shifted BAM
bamCoverage --bam atacseq_shifted.bam -o atacseq_coverage.bw \
    --normalizeUsing RPGC --effectiveGenomeSize 2913022398 --binSize 1 -p 8

# 3. Fragment-size QC — expect a nucleosome ladder
bamPEFragmentSize --bamfiles atacseq.bam --histogram fragmentSizes_atac.png \
    --maxFragmentLength 1000
```

A healthy ATAC library shows peaks near ~50 bp (nucleosome-free), ~200 bp
(mono-nucleosome), ~400 bp (di-nucleosome).

## Multi-Sample Comparison

```bash
# 1. One normalized track per sample
for s in Control_ChIP Treated_ChIP; do
  bamCoverage --bam ${s}.bam -o ${s}.bw --normalizeUsing RPGC \
      --effectiveGenomeSize 2913022398 --binSize 10 --extendReads 200 \
      --ignoreDuplicates -p 8
done

# 2. Scaled gene-body matrix over both samples
computeMatrix scale-regions -S Control_ChIP.bw Treated_ChIP.bw -R genes.bed \
    -b 1000 -a 1000 -m 3000 --binSize 10 --sortRegions descend \
    --sortUsing mean -o matrix_multi.gz -p 8

# 3. Heatmap and profile
plotHeatmap -m matrix_multi.gz -o heatmap_comparison.png --colorMap Blues \
    --whatToShow 'plot, heatmap and colorbar' --samplesLabel Control Treated \
    --heatmapHeight 15 --kmeans 4
plotProfile -m matrix_multi.gz -o profile_comparison.png --plotType lines \
    --perGroup --colors blue red --samplesLabel Control Treated \
    --startLabel TSS --endLabel TES
```

## Peak-Region Analysis

```bash
computeMatrix reference-point --referencePoint center \
    -S ChIP_coverage.bw -R peaks.bed -b 2000 -a 2000 --binSize 10 \
    -o matrix_peaks.gz -p 8
plotHeatmap -m matrix_peaks.gz -o heatmap_peaks.png --colorMap YlOrRd \
    --refPointLabel "Peak Center" --heatmapHeight 15 --sortUsing max
```

## Troubleshooting & Performance

- **Out of memory** → process a chromosome at a time: `--region chr1`.
- **Missing BAM index** → `samtools index input.bam`.
- **Slow** → raise `-p/--numberOfProcessors`; prototype on
  `--region chr1:1-1000000`.
- **bigWig too large** → increase `--binSize` (e.g. `50`); prefer bigWig over
  bedGraph.
- Keep intermediate `.gz` matrices so you can re-plot with new colors/clustering
  without recomputing.
- Use a consistent normalization method across all samples in one comparison,
  and confirm every BAM and region file uses the same genome build.
