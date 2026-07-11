# Copy Number, Purity/Ploidy, and Structural Variants

Profiling large-scale genome alterations: copy-number gains/losses, tumor purity
and ploidy, and structural rearrangements.

## Copy number analysis with CNVkit

CNVkit infers copy number from read depth over target and antitarget bins,
corrects with a pooled normal reference, then segments the corrected log2 ratios.
The one-shot `batch` command runs the whole pipeline; use it unless you need to
inspect intermediates.

```bash
# One-shot: coverage -> reference -> fix -> segment
cnvkit.py batch tumor.bam \
  --normal normal.bam \
  --targets targets.bed \
  --fasta ref.fa \
  --output-reference reference.cnn \
  --output-dir cnv_out/
# Produces cnv_out/tumor.cnr (bin-level) and cnv_out/tumor.cns (segments)
```

The granular equivalent, when you need to reuse a reference or tune each stage:

```bash
cnvkit.py coverage tumor.bam targets.bed -o tumor.targetcoverage.cnn
cnvkit.py reference normal.targetcoverage.cnn -f ref.fa -o reference.cnn
cnvkit.py fix tumor.targetcoverage.cnn tumor.antitargetcoverage.cnn reference.cnn -o tumor.cnr
cnvkit.py segment tumor.cnr -o tumor.cns
```

### Reading and calling segments

The `.cns` file is tab-delimited with columns `chromosome, start, end, gene,
log2, depth, probes, weight`. The `log2` column is the copy ratio relative to the
normal reference (0 = diploid-neutral).

```python
import pandas as pd

def call_segments(cns_path):
    """Classify CNVkit segments into copy-number states by log2 ratio."""
    df = pd.read_csv(cns_path, sep="\t")
    df["call"] = "neutral"
    df.loc[df["log2"] > 0.3, "call"] = "gain"
    df.loc[df["log2"] > 0.8, "call"] = "amplification"
    df.loc[df["log2"] < -0.3, "call"] = "loss"
    df.loc[df["log2"] < -1.0, "call"] = "deep_deletion"
    return df
```

The log2 thresholds above are **heuristic** defaults for a roughly-pure diploid
tumor. Prefer CNVkit's own integer-copy-number caller, which rescales by purity
and ploidy:

```bash
cnvkit.py call tumor.cns --purity 0.7 -o tumor.call.cns
```

**Focal vs arm-level:** a high-level amplification spanning < ~3-5 Mb is a *focal*
event and far more likely to be a driver (e.g. `ERBB2`, `MYC`) than a whole-arm
gain. Filter on `end - start` to separate them.

## Tumor purity and ploidy

Purity (fraction of tumor cells in the sample) and ploidy (average genome copy
number) jointly determine how observed log2 ratios and variant allele fractions
map to integer copy states. Low purity **compresses** log2 ratios toward zero, so
uncorrected calls systematically underestimate the magnitude of gains and losses.
Always estimate purity before interpreting absolute copy number.

Do **not** ship a naive standard-deviation heuristic as a purity estimate — it is
only a sanity-check proxy. Use an established allele-aware caller:

- **ASCAT** — allele-specific CN, purity and ploidy from SNP array or WES/WGS.
- **FACETS** — matched tumor-normal WES/WGS, joint segmentation + purity/ploidy.
- **Sequenza** — purity/ploidy from tumor-normal sequencing with a grid search.
- **PureCN** — purity/ploidy and CN from targeted panels (integrates with GATK).

These solve the purity/ploidy grid jointly from B-allele frequencies and depth,
which a log2-only heuristic cannot do. If you only need a rough coarse proxy for a
QC dashboard, a depth-ratio spread over segments correlates weakly with purity —
label it explicitly as a proxy, never as a calibrated estimate.

## Structural variants

SVs (deletions, duplications, inversions, translocations, insertions) are called
by dedicated tools — Manta, DELLY, LUMPY, GRIDSS — that read discordant pairs and
split reads. They share a VCF convention: `SVTYPE`, `SVLEN`, `END`, plus
paired-end (`PE`) and split-read (`SR`) support counts.

```python
import cyvcf2
import pandas as pd

def parse_sv_vcf(vcf_path):
    """Parse a structural-variant VCF (Manta/DELLY/LUMPY-style INFO fields)."""
    vcf = cyvcf2.VCF(vcf_path)
    rows = []
    for v in vcf:
        svlen = v.INFO.get("SVLEN")
        rows.append({
            "chrom": v.CHROM, "pos": v.POS,
            "end": v.INFO.get("END", v.POS),
            "svtype": v.INFO.get("SVTYPE", "UNKNOWN"),
            "svlen": abs(svlen) if svlen else 0,
            "pe_support": v.INFO.get("PE", 0),
            "sr_support": v.INFO.get("SR", 0),
            "qual": v.QUAL,
            "filter": v.FILTER or "PASS",
        })
    return pd.DataFrame(rows)
```

SV interpretation notes:

- **Breakend (`BND`) records** encode translocations as paired mates in the ALT
  field; `SVLEN`/`END` are not meaningful for them — join mates by `MATEID`.
- Require both `PE` and `SR` support for confident somatic calls; PE-only or
  SR-only events at low counts are frequently artifacts.
- Fusion-relevant rearrangements (e.g. `BCR-ABL1`, `EML4-ALK`) are `BND`/inversion
  events joining two genes — annotate breakpoints against gene models to detect
  in-frame fusions.
