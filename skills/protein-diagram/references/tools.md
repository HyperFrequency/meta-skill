# Tool Reference

Every script writes an image whose format is chosen by the `--output` extension
(`.png`, `.svg`, or `.pdf`). All accept `--dpi` (default 300). Run any script
with `-h` to print its argparse help.

---

## `draw_domain_map.py` — domain architecture

Pfam/InterPro-style linear map: a grey backbone with colored, labeled domain
boxes and a legend.

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--output` | path | **required** | PNG/SVG/PDF |
| `--length` | int | inferred | Protein length in residues |
| `--domains` | str | — | Inline JSON array **or** path to a `.json` file |
| `--uniprot` | str | — | UniProt accession; fetches InterPro domains + length over the network |
| `--title` | str | auto | Figure title |
| `--figsize` | `WxH` | `12x3` | Inches, e.g. `14x3` |
| `--dpi` | int | `300` | Resolution |

Provide **either** `--domains` (with `--length`, or length inferred from the
largest `end`) **or** `--uniprot`. Domain object schema:

```json
{"name": "Kinase", "start": 150, "end": 400, "color": "#3498db"}
```

- `color` is optional; omitted domains draw from a 15-color colorblind-safe
  palette in order.
- A domain label is only drawn when the domain spans more than ~8% of the total
  length (short domains stay unlabeled but appear in the legend).
- The legend is shown only when there are 10 or fewer domains.

## `draw_features.py` — feature tracks

Point features (single residue) render as annotated markers on a backbone;
region features (a span) render as boxes on a second track.

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--output` | path | **required** | PNG/SVG/PDF |
| `--length` | int | inferred | Protein length |
| `--features` | str | — | Inline JSON array **or** path to `.json` |
| `--uniprot` | str | — | Accession; fetches annotated features + length over the network |
| `--title` | str | auto | Figure title |
| `--figsize` | `WxH` | `14x6` | Inches |
| `--max-features` | int | `50` | Truncates to the first N features |
| `--dpi` | int | `300` | Resolution |

Point vs region is decided by which keys are present:

```json
{"name": "pY412", "position": 412, "type": "phosphorylation", "color": "orange"}
{"name": "Activation loop", "start": 380, "end": 420, "type": "region"}
```

Recognized `type` values (each maps to a color + marker; unknown types fall back
to a grey circle): `site`, `active_site`, `binding`, `ptm`, `phosphorylation`,
`glycosylation`, `acetylation`, `mutation`, `variant`, `disulfide`, `signal`,
`transit`, `region`, `domain`. `region`/`domain` types with `start`/`end` draw
as boxes; everything else with `position` draws as a marker.

## `draw_secondary_structure.py` — helix/sheet/coil track

Segments consecutive residues by DSSP class and draws helices as rounded boxes,
sheets as right-arrows, coil as thin bars. Prints helix/sheet/coil counts and
percentages.

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--input` | path | **required** | PDB file |
| `--output` | path | **required** | PNG/SVG/PDF |
| `--chain` | str | **required** | Chain ID, e.g. `A` |
| `--show-residue-numbers` | flag | off | Accepted; see limitation in `conventions.md` |
| `--title` | str | none | Figure title |
| `--figsize` | `WxH` | `14x2` | Inches |
| `--dpi` | int | `300` | Resolution |

DSSP → category mapping: `H`/`G`/`I` → helix; `E`/`B` → sheet; `T`/`S`/`-` →
coil. Needs an external DSSP binary (`mkdssp` or `dssp`) on `PATH`.

## `draw_ramachandran.py` — phi/psi scatter

Backbone dihedral scatter over the full ±180° square. Glycine and proline
residues are tracked separately and can be highlighted with distinct markers.

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--input` | path | **required** | PDB file |
| `--output` | path | **required** | PNG/SVG/PDF |
| `--chain` | str | all chains | Restrict to one chain |
| `--highlight-glycine` | flag | off | Gly as red triangles |
| `--highlight-proline` | flag | off | Pro as blue squares |
| `--show-regions` | flag | off | Draws **approximate** favored/allowed ellipses |
| `--title` | str | auto | Figure title |
| `--figsize` | `WxH` | `8x8` | Inches (kept square) |
| `--dpi` | int | `300` | Resolution |

## `draw_contact_map.py` — contact / distance map

Computes an all-vs-all C-alpha distance matrix and renders it as a heatmap, or a
binary contact map thresholded at `--cutoff`.

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--input` | path | **required** | PDB file |
| `--output` | path | **required** | PNG/SVG/PDF |
| `--chain` | str | **required** | Chain ID |
| `--cutoff` | float | `8.0` | Contact distance in Å (used with `--binary`) |
| `--binary` | flag | off | Binary contact map instead of distance heatmap |
| `--cmap` | str | `viridis_r` (distance) / `Greys` (binary) | Any matplotlib colormap |
| `--title` | str | auto | Figure title |
| `--figsize` | `WxH` | `8x8` | Inches |
| `--dpi` | int | `300` | Resolution |

Only standard residues with a `CA` atom are used; heteroatoms/waters are skipped.
Axis ticks show real residue numbers.

## `draw_alignment.py` — MSA panel

Wraps pyMSAviz `MsaViz`. There is **no** `--figsize` (pyMSAviz derives the size
from sequence count/length and `--wrap`).

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--input` | path | **required** | Aligned FASTA (primary) or Clustal |
| `--output` | path | **required** | PNG/SVG/PDF |
| `--start` | int | 1 | 1-indexed start column |
| `--end` | int | end | Inclusive end column |
| `--wrap` | int | none | Wrap at N columns |
| `--show-conservation` | flag | off | Adds a consensus/conservation bar |
| `--color-scheme` | choice | `Clustal` | See below |
| `--title` | str | none | Figure title |
| `--dpi` | int | `300` | Resolution |

Color-scheme choices: `Clustal`, `Zappo`, `Taylor`, `Flower`, `Buried`,
`Cinema`, `MAEditor`, `Helix`.

---

## Input-format cheat sheet

| Format | Extension | Used by | How to provide |
|--------|-----------|---------|----------------|
| PDB | `.pdb` | Ramachandran, contact map, secondary structure | `--input path.pdb` |
| Aligned FASTA | `.fasta`, `.fa` | MSA | `--input aln.fasta` |
| Clustal | `.aln` | MSA | `--input aln.aln` (pyMSAviz auto-detects; confirm it parses) |
| Domain JSON | `.json` | domain map | `--domains file.json` or inline array |
| Feature JSON | `.json` | feature tracks | `--features file.json` or inline array |
| UniProt accession | inline | domain map, feature tracks | `--uniprot P00519` (network fetch) |

mmCIF (`.cif`) is **not** parsed by these scripts (they use BioPython
`PDBParser`, not `MMCIFParser`) — convert to PDB first. See
`references/conventions.md`.
