# Variant Files (VCF/BCF)

`VariantFile` reads and writes VCF (text or bgzipped `.vcf.gz`) and BCF (binary).
Records expose alleles, quality, filters, INFO fields, and per-sample genotypes.

## Opening

```python
import pysam

vcf   = pysam.VariantFile("example.vcf")       # plain text
vcfgz = pysam.VariantFile("example.vcf.gz")    # bgzipped, tabix-indexable
bcf   = pysam.VariantFile("example.bcf")        # binary
out   = pysam.VariantFile("out.vcf", "w", header=vcf.header)
```

## Header

- `header.samples` — sample names.
- `header.contigs` — dict of contigs; `header.contigs[name].length`.
- `header.info`, `header.formats`, `header.filters` — definition dicts, each
  entry carrying `.description`, `.number`, `.type`.
- `header.add_line("##INFO=<...>")` and `header.add_sample(name)` to extend.

```python
print(list(vcf.header.samples))
for name in vcf.header.info:
    print(name, vcf.header.info[name].description)
```

## Reading records

```python
for v in vcf:                                   # sequential
    print(f"{v.chrom}:{v.pos} {v.ref}>{v.alts}")

for v in vcf.fetch("chr1", 1000000, 2000000):   # region; 0-based, half-open numeric args
    print(v.pos, v.id)
```

`fetch()` needs a `.tbi` (VCF.gz) or `.csi` (BCF) index. Numeric `start`/`stop`
args are **0-based, half-open** — the same convention as alignment/FASTA fetch
(only the region-string form is 1-based). This differs from the file's displayed
1-based `POS`: `v.pos` is 1-based, but `v.start`/`v.stop` and the `fetch()` args
are all 0-based. To fetch the single base at a variant, use
`vcf.fetch(v.chrom, v.pos - 1, v.pos)`.

## VariantRecord attributes

**Position** — `chrom`; `pos` (1-based, as in the file); `start` (0-based);
`stop` (0-based, exclusive); `id` (e.g. rsID, or `None`).

**Alleles** — `ref` (string); `alts` (tuple of alt strings, or `None`);
`alleles` (ref + alts tuple).

**Quality / filter** — `qual` (float or `None`); `filter` (mapping; `"PASS" in
v.filter`, `v.filter.keys()`, `v.filter.add("PASS")`).

### INFO fields

`v.info` behaves like a dict. Always check membership first — fields are often
absent.

```python
if "DP" in v.info:
    depth = v.info["DP"]
if "AF" in v.info:
    for af in v.info["AF"]:      # Number=A fields come back as tuples
        ...
```

### Genotypes and per-sample FORMAT data

`v.samples` maps sample name → record; each supports FORMAT keys.

```python
for name in v.samples:
    s = v.samples[name]
    gt = s["GT"]                 # tuple of allele indices, e.g. (0, 1)
    dp = s["DP"] if "DP" in s else None
    if s.phased:                 # phased "|" vs unphased "/"
        ...
    print(name, gt, s.alleles)
```

Genotype conventions: `0`=REF, `1`=first ALT, `2`=second ALT, ...
`(0, 0)` hom-ref, `(0, 1)` het, `(1, 1)` hom-alt, `(None, None)` missing.
Genotypes are **tuples** and may contain `None`; guard before arithmetic.

## Writing

```python
header = pysam.VariantHeader()
header.contigs.add("chr1", length=248956422)
header.add_line('##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">')
header.add_line('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">')
header.add_sample("sample1")

out = pysam.VariantFile("out.vcf", "w", header=header)

rec = out.new_record()
rec.chrom = "chr1"
rec.pos = 100000
rec.id = "rs123456"
rec.ref = "A"
rec.alts = ("G",)
rec.qual = 30
rec.filter.add("PASS")
rec.info["DP"] = 100
rec.samples["sample1"]["GT"] = (0, 1)
out.write(rec)
```

`new_record()` also accepts `contig=`, `start=`, `stop=`, `alleles=`, `id=`,
`qual=`, `filter=`, `info=` to clone from an existing record in one call.

## Filtering patterns

```python
# by QUAL / depth
[v for v in vcf if v.qual and v.qual >= 30]
[v for v in vcf if "DP" in v.info and v.info["DP"] >= 20]

# by genotype for a sample
s = v.samples["sample1"]["GT"]
has_alt = bool(s) and any(a for a in s if a not in (0, None))
is_hom_alt = s == (1, 1)

# by FILTER status
passed = "PASS" in v.filter or len(v.filter) == 0
```

## Sample subsetting (careful path)

To emit a subset of samples, copy the header, clear and re-add the wanted
samples, then for each record build a `new_record()` and copy the selected
samples' FORMAT data with `.update()`:

```python
new_header = invcf.header.copy()
new_header.samples.clear()
for name in keep:
    new_header.samples.add(name)
out = pysam.VariantFile("out.vcf", "w", header=new_header)

for v in invcf:
    rec = out.new_record(contig=v.chrom, start=v.start, stop=v.stop,
                         alleles=v.alleles, id=v.id, qual=v.qual,
                         filter=v.filter, info=v.info)
    for name in keep:
        rec.samples[name].update(v.samples[name])
    out.write(rec)
```

## Indexing

```python
pysam.tabix_index("example.vcf", preset="vcf", force=True)  # -> .vcf.gz + .tbi
pysam.bcftools.index("example.bcf")                          # -> .csi
```

Tabix requires bgzip compression; `tabix_index` compresses for you.

## Performance & pitfalls

- Prefer BCF (or bgzipped VCF) for compression and region-query speed.
- Check `in v.info` / `in sample` before access — missing fields raise `KeyError`.
- `v.start` is 0-based while `v.pos` is 1-based; bridge to BAM/FASTA numeric
  calls with `v.pos - 1`.
- When subsetting samples, update both the header and each record's FORMAT
  fields or downstream tools will reject the output.
