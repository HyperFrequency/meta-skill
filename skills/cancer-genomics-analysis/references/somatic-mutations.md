# Somatic Mutations, Annotation, and TMB

Detecting somatic (tumor-acquired) variants, annotating their functional impact,
and deriving the tumor mutational burden (TMB) immunotherapy biomarker.

## Why tumor-normal, not tumor-only

Somatic calling separates variants acquired by the tumor from the patient's
germline background. A **matched normal** (blood, adjacent tissue) is the germline
reference. Tumor-only calling has a much higher false-positive rate because
germline variants and sequencing artifacts masquerade as somatic events; if you
must run tumor-only, lean hard on a panel-of-normals and a population germline
resource (gnomAD) to subtract common variants.

## GATK Mutect2 best-practice chain

The Broad "somatic short variant" workflow is more than one command. Run the full
chain — skipping the contamination and orientation-bias steps inflates false
positives.

```bash
# 1. Call raw somatic variants (tumor + matched normal)
gatk Mutect2 \
  -R ref.fa \
  -I tumor.bam -I normal.bam \
  -normal <NORMAL_SM> \                 # read-group SM name of the normal sample
  --germline-resource af-only-gnomad.vcf.gz \
  --panel-of-normals pon.vcf.gz \
  --f1r2-tar-gz f1r2.tar.gz \
  -O unfiltered.vcf.gz

# 2. Model FFPE / oxidation orientation bias
gatk LearnReadOrientationModel -I f1r2.tar.gz -O read-orientation-model.tar.gz

# 3. Estimate cross-sample contamination
gatk GetPileupSummaries -I tumor.bam -V common_biallelic.vcf.gz -L intervals.bed -O pileups.table
gatk CalculateContamination -I pileups.table --tumor-segmentation segments.table -O contamination.table

# 4. Apply all filters in one pass
gatk FilterMutectCalls \
  -R ref.fa -V unfiltered.vcf.gz \
  --contamination-table contamination.table \
  --tumor-segmentation segments.table \
  --ob-priors read-orientation-model.tar.gz \
  -O filtered.vcf.gz
```

Notes and gotchas:

- `-normal` takes the **sample name** from the normal BAM's `@RG SM:` tag, not a
  literal string and not the file path. Mismatched names are a common silent
  failure — Mutect2 will treat the "normal" as a second tumor.
- The `-tumor`/`--tumor-sample` argument from older GATK is no longer required;
  tumor is the default and any non-`-normal` sample is treated as tumor.
- Build the panel-of-normals separately from a cohort of normals
  (`Mutect2` tumor-only per normal → `GenomicsDBImport` → `CreateSomaticPanelOfNormals`).
- `FilterMutectCalls` only *flags* records in the `FILTER` column; it does not drop
  them. Keep only `FILTER == PASS` downstream.

## Annotation (functional impact)

Use SnpEff or Ensembl VEP to add gene, transcript, and consequence terms. Both
write annotation into the VCF `INFO` field (`ANN=` for SnpEff, `CSQ=` for VEP).

```bash
# SnpEff — writes an ANN field per variant
snpEff -v GRCh38.105 filtered.vcf.gz > annotated.vcf

# or Ensembl VEP — writes a CSQ field
vep -i filtered.vcf.gz -o annotated.vcf --cache --assembly GRCh38 --vcf
```

The genome database version (e.g. `GRCh38.105`) must match your reference build.
Consequence strings you will parse later live inside these fields:
`missense_variant`, `stop_gained`, `frameshift_variant`, `splice_*`, etc.

## Parsing and filtering a VCF (cyvcf2)

`cyvcf2` is a fast pysam/htslib-backed reader. The VCF must be bgzip-compressed
and tabix-indexed for random access:
`bcftools view -O z -o out.vcf.gz in.vcf && tabix -p vcf out.vcf.gz`.

```python
import cyvcf2
import pandas as pd

def parse_vcf(vcf_path, min_qual=30, min_dp=10, min_af=0.05):
    """Parse a (SnpEff-annotated) VCF into a DataFrame with quality filters.

    Filters: PASS only, minimum QUAL, minimum total depth (DP),
    minimum variant allele frequency (AF).
    """
    vcf = cyvcf2.VCF(vcf_path)
    rows = []
    for v in vcf:
        # v.FILTER is None when the record is PASS
        if v.FILTER is not None and v.FILTER != "PASS":
            continue

        depth = v.INFO.get("DP") or 0
        af_raw = v.INFO.get("AF")
        allele_freq = af_raw[0] if isinstance(af_raw, (list, tuple)) else (af_raw or 0)

        if v.QUAL is not None and v.QUAL < min_qual:
            continue
        if depth < min_dp or allele_freq < min_af:
            continue

        annotation = v.INFO.get("ANN", "")
        # SnpEff ANN is pipe-delimited; field index 3 is the gene name
        gene = annotation.split("|")[3] if annotation else ""

        rows.append({
            "chrom": v.CHROM, "pos": v.POS,
            "ref": v.REF, "alt": ",".join(v.ALT),
            "qual": v.QUAL, "depth": depth, "af": allele_freq,
            "gene": gene,
        })
    return pd.DataFrame(rows)
```

Recommended filter floors for whole-exome tumor-normal: `DP >= 10`, `AF >= 0.05`.
Whole-genome and cell-free-DNA assays need different floors (WGS tolerates lower
depth per site; ctDNA requires ultra-sensitive callers and much lower AF).

## Tumor mutational burden (TMB)

TMB = number of qualifying somatic mutations divided by the megabases of
sequence assayed. It is an FDA-recognized companion biomarker for immune
checkpoint inhibitors — TMB-High tumors tend to respond better.

```python
import cyvcf2

NONSYN_TERMS = ("missense", "stop_gained", "frameshift", "nonsense", "splice")

def calculate_tmb(vcf_path, assayed_mb=35.0, min_af=0.05, min_dp=10):
    """Mutations per megabase, plus a nonsynonymous-only rate.

    assayed_mb: callable footprint of the panel/exome (typically 30-40 Mb for WES).
    Requires SnpEff/VEP annotation for the nonsynonymous count.
    """
    vcf = cyvcf2.VCF(vcf_path)
    total_pass = 0
    nonsynonymous = 0
    for v in vcf:
        if v.FILTER is not None and v.FILTER != "PASS":
            continue
        depth = v.INFO.get("DP") or 0
        af_raw = v.INFO.get("AF")
        allele_freq = af_raw[0] if isinstance(af_raw, (list, tuple)) else (af_raw or 0)
        if depth < min_dp or allele_freq < min_af:
            continue
        total_pass += 1
        annotation = (v.INFO.get("ANN", "") or "").lower()
        if any(term in annotation for term in NONSYN_TERMS):
            nonsynonymous += 1

    tmb_all = total_pass / assayed_mb
    tmb_nonsyn = nonsynonymous / assayed_mb
    label = "TMB-High" if tmb_all >= 10 else ("TMB-Intermediate" if tmb_all >= 5 else "TMB-Low")
    return {"tmb": tmb_all, "tmb_nonsyn": tmb_nonsyn, "class": label}
```

TMB pitfalls:

- **Denominator must match the assay.** Use the actual callable Mb of the panel,
  not a nominal exome size. Small targeted panels compute TMB on far less than
  35 Mb and need their own calibrated thresholds.
- The 10 mut/Mb "high" cutoff is assay-dependent; harmonize against the specific
  panel's validated threshold before clinical use.
- Residual germline or contamination inflates TMB — verify the germline resource
  and contamination filters actually ran.
- Report nonsynonymous (coding) rate for clinical interpretation; synonymous
  variants are usually excluded.
