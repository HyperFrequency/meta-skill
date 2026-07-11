# ClinVar Data Formats and Bulk Download

ClinVar publishes complete releases for download in three formats. Pick by how
much detail you need and which tools consume it.

## Bulk access

Base location:

```
https://ftp.ncbi.nlm.nih.gov/pub/clinvar/
```

HTTPS is the recommended transport; the historical `ftp://` host still resolves.

### Release schedule

- **Monthly release** — first Thursday of each month. Complete dataset with
  release notes, **archived indefinitely**. Pin one of these for reproducible
  pipelines.
- **Weekly update** — every Monday. Incremental to the current monthly release;
  retained until the next monthly. Keeps you in sync with the website.

### Directory layout

```
pub/clinvar/
├── xml/
│   ├── clinvar_variation/     # VCV files (variant-centric)
│   │   ├── weekly_release/
│   │   └── archive/
│   └── RCV/                   # RCV files (variant-condition pairs)
├── vcf_GRCh37/                # VCF, GRCh37/hg19
├── vcf_GRCh38/                # VCF, GRCh38/hg38
├── tab_delimited/
│   ├── variant_summary.txt.gz
│   ├── var_citations.txt.gz
│   └── cross_references.txt.gz
└── README.txt
```

## XML (most complete)

Full submission detail, evidence, and metadata. Multi-GB compressed — always
stream.

### VCV — VariationArchive (variant-centric)

- Location `xml/clinvar_variation/`; accession `VCV000000001.1`.
- File `ClinVarVariationRelease_YYYY-MM-DD.xml.gz`.
- Best when you care about a variant regardless of condition.

```xml
<VariationArchive VariationID="12345" VariationType="single nucleotide variant">
  <VariationName>NM_000059.3(BRCA2):c.1310_1313del (p.Lys437fs)</VariationName>
  <InterpretedRecord>
    <Interpretations>
      <ClinicalSignificance>Pathogenic</ClinicalSignificance>
      <ReviewStatus>reviewed by expert panel</ReviewStatus>
    </Interpretations>
  </InterpretedRecord>
  <ClinicalAssertionList><!-- individual SCV submissions --></ClinicalAssertionList>
</VariationArchive>
```

### RCV — Record (variant–condition pair)

- Location `xml/RCV/`; accession `RCV000000001.1`.
- One record per variant–condition pair; a variant with several conditions has
  several RCVs. Best for disease-specific interpretation.

### SCV — Submission

Individual submitter interpretations nested inside VCV/RCV; accession
`SCV000000001.1`.

## VCF

For genomic pipelines. **Excludes** variants >10 kb, cytogenetic variants,
complex structural variants, and anything without precise breakpoints. Match the
genome build to your data.

- GRCh37: `vcf_GRCh37/clinvar.vcf.gz`
- GRCh38: `vcf_GRCh38/clinvar.vcf.gz`

### Key INFO fields

| Field | Meaning |
|-------|---------|
| ALLELEID | ClinVar allele ID |
| CLNSIG | Clinical significance |
| CLNREVSTAT | Review status |
| CLNDN | Condition name(s) |
| CLNVC | Variant type |
| CLNVCSO | Sequence Ontology term |
| GENEINFO | `symbol:GeneID` |
| MC | Molecular consequence |
| RS | dbSNP rsID |
| AF_ESP / AF_EXAC / AF_TGP | Allele frequency (ESP / ExAC / 1000G) |

```
13  32339912  rs80357382  A  G  .  .  ALLELEID=38447;CLNDN=Breast-ovarian_cancer,_familial_2;CLNSIG=Pathogenic;CLNREVSTAT=reviewed_by_expert_panel;GENEINFO=BRCA2:675
```

## Tab-delimited

Quick filtering and database loading. `variant_summary.txt.gz` carries selected
metadata for every genome-mapped variant.

Notable columns: `VariationID`, `Type`, `Name`, `GeneID`, `GeneSymbol`,
`ClinicalSignificance`, `ReviewStatus`, `LastEvaluated`, `RS# (dbSNP)`,
`Chromosome`, `PositionVCF`, `ReferenceAlleleVCF`, `AlternateAlleleVCF`,
`Assembly`, `PhenotypeIDS`, `Origin`, `SubmitterCategories`.

Companion files: `var_citations.txt.gz` (allele/variation ↔ dbSNP/dbVar/PubMed)
and `cross_references.txt.gz` (variation ↔ OMIM/UniProtKB/GTR with modified
dates).

> Column **positions** in `variant_summary.txt` are not guaranteed stable across
> releases — key off the header row, not hard-coded `cut -f` indices, in
> long-lived scripts.

## Choosing a format

| Need | Format |
|------|--------|
| Full evidence, submission detail, comprehensive DB | XML |
| Annotate/overlap sequencing calls, standard bioinformatics tools | VCF |
| Fast filters, spreadsheets, quick stats | Tab-delimited |

## Accessions

| Type | Format | Scope | Version bumps when |
|------|--------|-------|--------------------|
| VCV | `VCV000012345.6` | all data for one variant | variant data changes |
| RCV | `RCV000056789.4` | one variant–condition interpretation | interpretation changes |
| SCV | `SCV000098765.2` | one submitter's interpretation | submission updates |

`VariationID` and `AlleleID` are stable numeric IDs; `rsID` cross-references
dbSNP when available.

## Processing recipes

### XML — stream, don't load

```python
import gzip, xml.etree.ElementTree as ET

with gzip.open("ClinVarVariationRelease.xml.gz", "rt") as f:
    for _, elem in ET.iterparse(f, events=("end",)):
        if elem.tag == "VariationArchive":
            vid = elem.attrib.get("VariationID")
            # extract significance / review status here
            elem.clear()   # free memory — essential on multi-GB files
```

### VCF — bcftools (preferred) / pysam

```bash
# filter by significance
bcftools view -i 'INFO/CLNSIG~"Pathogenic"' clinvar.vcf.gz
# restrict to a gene family
bcftools view -i 'INFO/GENEINFO~"BRCA"' clinvar.vcf.gz
# annotate your calls (clinvar.vcf.gz must have a .tbi index beside it)
bcftools annotate -a clinvar.vcf.gz -c INFO your_variants.vcf
```

In Python prefer `pysam` or `cyvcf2`; `PyVCF` (the `vcf` module) is unmaintained.

```python
import pysam
vcf = pysam.VariantFile("clinvar.vcf.gz")
for rec in vcf:
    clnsig = rec.info.get("CLNSIG")
    if clnsig and any("Pathogenic" in c for c in clnsig):
        print(rec.chrom, rec.pos, rec.info.get("GENEINFO"), clnsig)
```

### Tab-delimited — pandas

```python
import pandas as pd
df = pd.read_csv("variant_summary.txt.gz", sep="\t", compression="gzip")
pathogenic = df[df["ClinicalSignificance"].str.contains("Pathogenic", na=False)]
by_gene = pathogenic.groupby("GeneSymbol").size().sort_values(ascending=False)
```

## Download snippets

```bash
FTP=https://ftp.ncbi.nlm.nih.gov/pub/clinvar

# Pin a specific monthly XML archive (reproducible)
wget $FTP/xml/clinvar_variation/ClinVarVariationRelease_YYYY-MM.xml.gz

# VCF for one build + its tabix index
wget $FTP/vcf_GRCh38/clinvar.vcf.gz
wget $FTP/vcf_GRCh38/clinvar.vcf.gz.tbi

# Tab-delimited summary
wget $FTP/tab_delimited/variant_summary.txt.gz
```

## Quality notes

- VCF omits large/complex variants — use XML when completeness matters.
- Older submissions predate current standardization; weigh recency.
- Not every HGVS expression maps to genomic coordinates.
- Cross-check formats, verify build, and carry gnomAD frequency for context.

## References

- FTP primer: https://www.ncbi.nlm.nih.gov/clinvar/docs/ftp_primer/
- XML schema docs: https://www.ncbi.nlm.nih.gov/clinvar/docs/xml_schemas/
- VCF spec: https://samtools.github.io/hts-specs/VCFv4.3.pdf
- README: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/README.txt
