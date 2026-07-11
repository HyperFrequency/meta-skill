# Plasmid & Gene Maps (dna_features_viewer)

Both plasmid maps and linear gene tracks use Biopython to read a GenBank record
and `dna_features_viewer` to render features as colored arrows/blocks. The only
differences are the record class (`CircularGraphicRecord` vs `GraphicRecord`) and
optional region clipping for gene tracks.

## GenBank → GraphicFeature

```python
from Bio import SeqIO
from dna_features_viewer import GraphicFeature, GraphicRecord, CircularGraphicRecord

record = SeqIO.read("input.gb", "genbank")   # exactly one record
```

Each Biopython `SeqFeature` maps to a `GraphicFeature`:

| GraphicFeature arg | Source |
|--------------------|--------|
| `start` | `int(feat.location.start)` (0-based, inclusive) |
| `end`   | `int(feat.location.end)` (0-based, exclusive) |
| `strand` | `feat.location.strand or 1` (None → 1, drawn as forward arrow) |
| `color` | looked up from the feature-type color map below |
| `label` | first present qualifier (see fallback order) |

**Label fallback order** — take the first qualifier that exists:

- Plasmid map: `label` → `product` → `gene` → `feat.type`
- Gene track: `label` → `gene` → `product` → `locus_tag` → `note` → `feat.type`

`feat.qualifiers[key]` is a list; take `[0]`.

## Feature-type color map

Plasmid map (skip `source` and bare `gene`; `source` returns `None` → drop it):

```python
PLASMID_COLORS = {
    "CDS": "#3498db", "gene": "#3498db", "promoter": "#2ecc71",
    "terminator": "#e74c3c", "rep_origin": "#f39c12",
    "misc_feature": "#9b59b6", "primer_bind": "#1abc9c",
    "regulatory": "#2ecc71",
}
```

Gene track (richer; skip only `source`):

```python
GENE_COLORS = {
    "CDS": "#3498db", "gene": "#2980b9", "mRNA": "#85c1e9",
    "tRNA": "#1abc9c", "rRNA": "#16a085", "ncRNA": "#48c9b0",
    "promoter": "#2ecc71", "terminator": "#e74c3c", "rep_origin": "#f39c12",
    "misc_feature": "#9b59b6", "regulatory": "#2ecc71",
    "mobile_element": "#e67e22", "repeat_region": "#f1c40f",
    "sig_peptide": "#d35400", "mat_peptide": "#c0392b",
    "exon": "#3498db", "intron": "#bdc3c7",
}
```

Unknown feature types fall back to a neutral grey `#95a5a6`.

## Circular plasmid map

```python
features = build_features(record, PLASMID_COLORS)   # list[GraphicFeature]
rec = CircularGraphicRecord(sequence_length=len(record.seq), features=features)
ax, _ = rec.plot(figure_width=8)                    # square-ish, 8x8 default
ax.set_title(f"{record.name}\n({len(record.seq):,} bp)",
             fontsize=14, fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig("plasmid_map.svg", dpi=300, bbox_inches="tight")
```

`.plot(figure_width=...)` creates its own figure and returns `(ax, _)`. Do not
pre-create a figure; set the title on the returned `ax`.

## Linear map / gene track with region clipping

For a linear map, swap in `GraphicRecord`. For a genomic sub-region, clip
features to `[start, end)` and shift coordinates so the region starts at 0:

```python
def build_features(record, colors, start=None, end=None):
    feats = []
    for f in record.features:
        if f.type == "source":
            continue
        fs, fe = int(f.location.start), int(f.location.end)
        if start is not None and fe < start:      # entirely left of region
            continue
        if end is not None and fs > end:           # entirely right of region
            continue
        fs = max(fs, start) if start is not None else fs   # clip to window
        fe = min(fe, end) if end is not None else fe
        feats.append(GraphicFeature(
            start=fs - (start or 0), end=fe - (start or 0),
            strand=f.location.strand or 1, color=colors.get(f.type, "#95a5a6"),
            label=get_label(f)))
    return feats

region_len = (end or len(record.seq)) - (start or 0)
rec = GraphicRecord(sequence_length=region_len, features=build_features(...))
ax, _ = rec.plot(figure_width=14)                 # wide, 14x4 default aspect
```

## GFF input

`SeqIO.read(..., "genbank")` does **not** parse GFF. To render GFF annotations,
convert to a Biopython `SeqRecord` first:

```python
from BCBio import GFF          # pip install bcbio-gff
rec = next(GFF.parse("annotations.gff", base_dict=...))   # yields SeqRecord(s)
# then reuse rec.features exactly as above
```

`dna_features_viewer` also ships a `BiopythonTranslator` /
`GraphicRecord.from_gff` convenience in recent versions, but the explicit path
above is version-stable.

## Gotchas

- **`CompoundLocation` (joined/spliced features)**: `int(feat.location.start)`
  gives the outermost span. To draw each exon block separately, iterate
  `feat.location.parts`.
- **Very dense maps**: labels overlap. Pass `label=None` for minor features, or
  raise `figure_width`; `dna_features_viewer` auto-stacks overlapping features
  into rows on linear records.
- **Origin-spanning features** (wrap past position 0 on a circular plasmid) are
  drawn correctly by `CircularGraphicRecord` only if the GenBank encodes the wrap
  as a `CompoundLocation`; a single span that exceeds `sequence_length` is not.
