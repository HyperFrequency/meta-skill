# Integrated Workflows & Command-Line Tools

Recipes that combine `AlignmentFile`, `VariantFile`, `FastaFile`, and
`TabixFile`, plus the samtools/bcftools subcommand wrappers. All examples use
0-based numeric coordinates unless a region string is shown.

## BAM quality-control statistics

Single sequential pass; `read_callback` / flag accessors do the classification.

```python
def bam_stats(bam):
    f = pysam.AlignmentFile(bam, "rb")
    s = dict(total=0, mapped=0, unmapped=0, paired=0, proper=0, dup=0)
    for r in f.fetch(until_eof=True):
        s["total"] += 1
        s["unmapped" if r.is_unmapped else "mapped"] += 1
        if r.is_paired:
            s["paired"] += 1
            s["proper"] += r.is_proper_pair
        s["dup"] += r.is_duplicate
    f.close()
    s["mapping_rate"] = s["mapped"] / s["total"] if s["total"] else 0
    return s
```

For quick counts, `samtools flagstat` via the wrapper is faster:
`pysam.samtools.flagstat(bam)` returns the report as a string.

## Coverage analysis

`pileup()` gives per-position depth; wrap it to build arrays, find low-coverage
runs, or summarize.

```python
def coverage_array(bam, chrom, start, end):
    f = pysam.AlignmentFile(bam, "rb")
    cov = [0] * (end - start)
    for col in f.pileup(chrom, start, end, truncate=True):
        cov[col.pos - start] = col.nsegments
    f.close()
    return cov
```

`truncate=True` restricts columns to the requested window (otherwise pileup
emits columns for reads overhanging the edges). To find sub-threshold runs, walk
the columns tracking whether you are inside a low-coverage stretch and close the
interval when depth rises back above `min_coverage`.

## Validate variants against read support

Confirm an ALT allele is actually observed in the alignments before trusting a
call — pileup the variant locus and tally the base each read contributes.

```python
def alt_support(samfile, v):
    counts = {a: 0 for a in (v.ref, *(v.alts or ()))}
    for col in samfile.pileup(v.chrom, v.pos - 1, v.pos, truncate=True):
        if col.pos != v.pos - 1:               # 0-based match to 1-based POS
            continue
        for p in col.pileups:
            if not p.is_del and not p.is_refskip:
                b = p.alignment.query_sequence[p.query_position]
                if b in counts:
                    counts[b] += 1
    return counts
```

Keep only variants whose alt count clears a threshold. Remember `v.pos - 1`
bridges the 1-based VCF POS into pysam's 0-based pileup coordinates.

## Annotate variants with BAM depth

```python
def annotate_depth(vcf_in, bam, vcf_out):
    vcf = pysam.VariantFile(vcf_in)
    bam = pysam.AlignmentFile(bam, "rb")
    if "DP" not in vcf.header.info:
        vcf.header.info.add("DP", "1", "Integer", "Total depth from BAM")
    out = pysam.VariantFile(vcf_out, "w", header=vcf.header)
    for v in vcf:
        v.info["DP"] = bam.count(v.chrom, v.pos - 1, v.pos)
        out.write(v)
    for h in (vcf, bam, out):
        h.close()
```

## Extract reference context around variants

Fetch a soft-masked window and upper-case the variant bases so the site stands
out in the output FASTA.

```python
def variant_contexts(vcf_in, fasta_in, out, window=50):
    vcf, fa = pysam.VariantFile(vcf_in), pysam.FastaFile(fasta_in)
    with open(out, "w") as fh:
        for v in vcf:
            start = max(0, v.pos - window - 1)      # 1-based POS -> 0-based
            ctx = fa.fetch(v.chrom, start, v.pos + window)
            i = v.pos - 1 - start                   # variant offset in window
            fh.write(f">{v.chrom}:{v.pos} {v.ref}>{v.alts}\n")
            fh.write(ctx[:i].lower() + ctx[i:i+len(v.ref)].upper()
                     + ctx[i+len(v.ref):].lower() + "\n")
    vcf.close(); fa.close()
```

## Filter/subset a BAM by region and quality

```python
def filter_bam(inp, outp, chrom, start, end, min_mapq=20):
    f = pysam.AlignmentFile(inp, "rb")
    o = pysam.AlignmentFile(outp, "wb", template=f)
    for r in f.fetch(chrom, start, end):
        if r.mapping_quality >= min_mapq and not r.is_duplicate:
            o.write(r)
    f.close(); o.close()
    pysam.index(outp)                               # writes outp.bai
```

## Variants overlapping annotated intervals (VCF + BED)

```python
def variants_by_gene(vcf_file, bed_gz):
    vcf = pysam.VariantFile(vcf_file)
    bed = pysam.TabixFile(bed_gz)
    out = {}
    for gene in bed.fetch(parser=pysam.asBed()):
        out[gene.name] = [
            (v.chrom, v.pos, v.ref, v.alts)
            for v in vcf.fetch(gene.contig, gene.start, gene.end)
        ]
    vcf.close(); bed.close()
    return out
```

## Integration patterns (quick map)

| Combine | Purpose |
| --- | --- |
| BAM + FASTA | verify alignments, extract aligned reference bases |
| BAM + VCF | validate variants, compute allele support/frequency |
| VCF + BED/GTF | annotate variants with gene/region names |
| BAM + BED | region-restricted coverage statistics |
| FASTA + VCF | extract variant-context sequences |
| multiple BAMs | compare coverage/variants across samples |

## Command-line tools (samtools / bcftools)

pysam exposes the full CLI as Python callables under `pysam.samtools.*` and
`pysam.bcftools.*`. Arguments are passed as separate strings exactly as on the
command line; most return captured stdout as a string.

```python
pysam.samtools.sort("-o", "sorted.bam", "input.bam")
pysam.samtools.index("sorted.bam")
pysam.samtools.view("-b", "-q", "20", "-o", "region.bam",
                    "input.bam", "chr1:1000-2000")
pysam.samtools.faidx("reference.fasta")
pysam.bcftools.view("-O", "z", "-o", "output.vcf.gz", "input.vcf")
pysam.bcftools.index("output.vcf.gz")
```

Errors surface as exceptions:

```python
try:
    pysam.samtools.sort("-o", "out.bam", "input.bam")
except pysam.SamtoolsError as e:
    print("samtools failed:", e)
```

## Performance notes for pipelines

- Index every file you query by region; scan (`until_eof=True`) only when you
  genuinely need every record.
- Parallelize across independent regions, each with its own file handle
  (`AlignmentFile` handles are not safe to share across threads).
- Prefer `count()` over `pileup()` when you only need depth, not per-base calls.
- Stream FASTQ and large BAMs record-by-record; do not materialize whole files.
- Close writers explicitly (or use `with`) so BAM/VCF outputs are finalized.
