# Effective Genome Sizes

The effective genome size is the length of the **mappable** genome — the portion
reads can be uniquely assigned to. deepTools needs it for RPGC normalization
(`--normalizeUsing RPGC`) and for the GC-bias tools. Getting it wrong (e.g. an
hg19 value on hg38 data) skews every RPGC-normalized value.

## Two Calculation Conventions

1. **Non-N bases** — count of non-N nucleotides in the reference. Conservative,
   widely applicable; use this when unsure.
2. **Unique mappability** — bases uniquely mappable at a given read length
   (optionally allowing edit distance). Use with strict quality filtering /
   multimapper removal.

## Common Organisms (non-N bases)

| Organism | Assembly | Effective size | Flag |
|----------|----------|----------------|------|
| Human | GRCh38/hg38 | 2,913,022,398 | `--effectiveGenomeSize 2913022398` |
| Human | GRCh37/hg19 | 2,864,785,220 | `--effectiveGenomeSize 2864785220` |
| Mouse | GRCm39/mm39 | 2,654,621,837 | `--effectiveGenomeSize 2654621837` |
| Mouse | GRCm38/mm10 | 2,652,783,500 | `--effectiveGenomeSize 2652783500` |
| Zebrafish | GRCz11 | 1,368,780,147 | `--effectiveGenomeSize 1368780147` |
| *Drosophila* | dm6 | 142,573,017 | `--effectiveGenomeSize 142573017` |
| *C. elegans* | WBcel235/ce11 | 100,286,401 | `--effectiveGenomeSize 100286401` |
| *C. elegans* | ce10 | 100,258,171 | `--effectiveGenomeSize 100258171` |

## Read-Length-Specific (unique mappability)

For strictly filtered reads, mappability rises with read length.

Human GRCh38: 50 bp ≈ 2.7 B · 75 bp ≈ 2.8 B · 100 bp ≈ 2.8 B · 150 bp ≈ 2.9 B ·
250 bp ≈ 2.9 B.

Mouse GRCm38: 50 bp ≈ 2.3 B · 75 bp ≈ 2.5 B · 100 bp ≈ 2.6 B.

## Where It's Used

```bash
# RPGC coverage
bamCoverage --bam input.bam -o output.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398

# RPGC scaling in a comparison (RPGC is a --normalizeUsing method, so
# --scaleFactorsMethod must be set to None)
bamCompare -b1 treatment.bam -b2 control.bam -o comparison.bw \
    --scaleFactorsMethod None --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398

# GC-bias detection
computeGCBias --bamfile input.bam --effectiveGenomeSize 2913022398 \
    --genome genome.2bit --fragmentLength 200 --biasPlot bias.png
```

## Shorthand Codes

deepTools' `--effectiveGenomeSize` takes an **integer only** — it has no built-in
name aliases, so always pass the numeric value from the table above. The familiar
`hs` / `mm` / `dm` / `ce` genome shortcuts belong to *other* tools (notably MACS2's
`-g`), not to deepTools; do not pass them to `--effectiveGenomeSize`.

| Shortcut (MACS2 etc.) | deepTools value to use instead |
|-----------------------|--------------------------------|
| `hs` (human, GRCh38)  | `2913022398` |
| `mm` (mouse, GRCm38)  | `2652783500` |
| `dm` (fly, dm6)       | `142573017` |
| `ce` (worm, ce11)     | `100286401` |

## Custom Genomes

Compute the non-N base count directly:

```bash
# UCSC faCount
faCount genome.fa | grep total | awk '{print $2-$7}'

# seqtk
seqtk comp genome.fa | awk '{x+=$2}END{print x}'
```

Authoritative values and method details:
https://deeptools.readthedocs.io/en/latest/content/feature/effectiveGenomeSize.html
