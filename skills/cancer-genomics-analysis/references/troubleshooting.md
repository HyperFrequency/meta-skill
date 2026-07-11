# Best Practices, Failure Modes, and Boundaries

## Best practices

1. **Prefer paired tumor-normal** for somatic calling; reserve tumor-only for
   when no normal exists, and then use a panel-of-normals + gnomAD germline
   resource to subtract germline and artifact calls.
2. **Filter, then interpret.** Keep `FILTER == PASS`, apply depth (`DP >= 10` WES)
   and allele-frequency (`AF >= 0.05` WES) floors. Adjust floors per assay type
   (WGS, targeted panel, ctDNA all differ).
3. **Annotate with a standard tool** (SnpEff or VEP) whose genome build matches
   your reference, then validate key calls in COSMIC and ClinVar before drawing
   conclusions.
4. **Estimate purity before absolute copy number.** Low purity compresses log2
   ratios and understates gains/losses; use ASCAT/FACETS/Sequenza/PureCN.
5. **NMF needs non-negative input** (TPM/RPKM/counts) and a stability-selected
   rank — never feed log fold-changes or z-scores, and never trust a single
   `k` picked by eye.
6. **Compute TMB on the assay's callable footprint**, not a nominal 35 Mb, and
   harmonize thresholds against the specific panel.
7. **Corroborate multi-omic signals.** A CNV loss, a somatic mutation, and a lost
   co-expression edge on the same gene are far stronger together than any one
   alone.

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `cyvcf2` fails to open / can't seek | VCF not bgzipped + tabix-indexed | `bcftools view -O z -o out.vcf.gz in.vcf && tabix -p vcf out.vcf.gz` |
| Mutect2 treats normal as tumor | `-normal` value ≠ normal BAM `@RG SM:` | Pass the exact SM sample name, not the file path |
| Flood of somatic false positives | Skipped contamination / orientation-bias filtering | Run the full GetPileupSummaries → CalculateContamination → LearnReadOrientationModel → FilterMutectCalls chain |
| Copy-number gains look too weak | Low tumor purity compressing log2 | Estimate purity and call with `cnvkit.py call --purity`, or use FACETS/ASCAT |
| CNVkit over-segments (many tiny segments) | Segmentation too sensitive / noisy bins | Raise the segmentation threshold; increase bin size; drop low-`weight` bins |
| NMF results differ run to run | Random init, unstable rank | Use `init="nndsvda"`; select `k` by cophenetic-correlation consensus |
| NMF raises `ValueError` on input | Negative values in the matrix | Clip to zero; confirm you passed TPM/counts, not log-ratios |
| TMB implausibly high | Wrong denominator or residual germline | Use the true callable Mb; verify germline-resource + contamination filters ran |
| SV `SVLEN`/`END` empty for a record | It is a `BND` (breakend/translocation) | Join mates via `MATEID`; don't compute a length |

## Boundaries — what this skill does NOT cover

- **Raw-read processing**: alignment (BWA-MEM/minimap2), duplicate marking, base
  quality recalibration, and FASTQ QC happen upstream of everything here.
- **Germline-only analysis**: HaplotypeCaller / DeepVariant germline pipelines and
  ACMG classification are a different workflow.
- **Single-cell genomics**: scRNA/scDNA and spatial pipelines need dedicated
  tooling (a scanpy-style stack), not these bulk workflows.
- **Clinical variant interpretation / reporting**: pathogenicity classification and
  therapy matching are regulated activities — this skill produces the quantitative
  substrate, not the clinical call. Cross-check COSMIC and ClinVar.
- **Mutational signature deconvolution** (SBS/COSMIC signatures via NMF over 96
  trinucleotide contexts) is related but distinct from the *expression* metagene
  NMF here; use a dedicated signatures package (e.g. SigProfiler) for that.

## External references

- GATK somatic short-variant best practices: https://gatk.broadinstitute.org/
- CNVkit: https://cnvkit.readthedocs.io/
- SnpEff: https://pcingola.github.io/SnpEff/ · Ensembl VEP: https://www.ensembl.org/vep
- COSMIC: https://cancer.sanger.ac.uk/cosmic · ClinVar: https://www.ncbi.nlm.nih.gov/clinvar/
